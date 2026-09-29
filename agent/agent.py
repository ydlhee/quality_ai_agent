import json
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


load_dotenv()


AVAILABLE_TOOLS = {
    "design_change": "설계변경 분석",
    "validation_plan": "검증계획 생성",
    "impact_trace": "영향범위 추적",
    "validate_quality": "품질검증 및 Risk 판단",
    "followup": "후속조치",
    "wait": "보완자료 또는 시정조치 자료 수신 대기",
    "finish": "Case 종료",
}


class AgentDecision(BaseModel):
    """LLM이 반환해야 하는 다음 행동 형식."""

    tool: str = Field(
        description=(
            "다음에 수행할 행동. "
            "design_change, validation_plan, impact_trace, "
            "validate_quality, followup, wait, finish 중 하나"
        )
    )

    reason: str = Field(
        description="해당 행동을 선택한 이유"
    )


def rule_based_decision(state):
    """
    기존 Rule 기반 판단 로직.

    LLM 호출 실패, API 오류, 잘못된 Tool 선택 등이 발생할 경우
    안전한 fallback으로 사용한다.
    """

    # 1. 설계변경 분석
    if not state["design_change_analyzed"]:
        return {
            "tool": "design_change",
            "reason": "설계변경 분석이 아직 수행되지 않았습니다."
        }

    # 2. 검증계획 생성
    if not state["validation_plan_created"]:
        return {
            "tool": "validation_plan",
            "reason": (
                "설계변경 분석이 완료되어 "
                "검증계획 생성이 필요합니다."
            )
        }

    # 3. 영향범위 추적
    if not state["impact_traced"]:
        return {
            "tool": "impact_trace",
            "reason": (
                "검증계획이 생성되어 "
                "변경 영향범위 확인이 필요합니다."
            )
        }

    # 4. 품질검증
    if not state["quality_validated"]:
        return {
            "tool": "validate_quality",
            "reason": (
                "영향 대상 Lot이 확인되어 "
                "품질검증이 필요합니다."
            )
        }

    # 5. HOLD / REJECT 후속조치
    if (
        state["decision"] in ["HOLD", "REJECT"]
        and not state["followup_completed"]
    ):
        return {
            "tool": "followup",
            "reason": (
                f"품질검증 결과가 {state['decision']}이므로 "
                "후속조치가 필요합니다."
            )
        }

    # 6. HOLD 후 보완자료 대기
    if (
        state["decision"] == "HOLD"
        and state["followup_completed"]
    ):
        return {
            "tool": "wait",
            "reason": (
                "보완요청이 생성되었습니다. "
                "협력사의 보완자료 수신을 기다립니다."
            )
        }

    # 7. REJECT 후 시정조치 자료 대기
    if (
        state["decision"] == "REJECT"
        and state["followup_completed"]
    ):
        return {
            "tool": "wait",
            "reason": (
                "부적합 후속조치가 생성되었습니다. "
                "협력사의 시정조치 자료 수신을 기다립니다."
            )
        }

    # 8. PASS → 종료
    return {
        "tool": "finish",
        "reason": (
            "품질검증 결과가 PASS이며 "
            "필요한 검증 절차가 완료되어 Case를 종료합니다."
        )
    }


def _build_agent_context(state):
    """
    LLM에게 전달할 Case 상태를 필요한 정보만 추려서 구성한다.

    전체 문서 원문을 그대로 전달하지 않고,
    Tool 수행 여부와 이전 Tool 결과를 중심으로 전달한다.
    """

    return {
        "case_id": state.get("case_id"),

        "case_status": state.get("case_status"),

        "completed_steps": {
            "design_change_analyzed": state.get(
                "design_change_analyzed",
                False
            ),
            "validation_plan_created": state.get(
                "validation_plan_created",
                False
            ),
            "impact_traced": state.get(
                "impact_traced",
                False
            ),
            "quality_validated": state.get(
                "quality_validated",
                False
            ),
            "followup_completed": state.get(
                "followup_completed",
                False
            ),
        },

        "quality_decision": state.get("decision"),

        "missing_items": state.get(
            "missing_items",
            []
        ),

        "revalidation_required": state.get(
            "revalidation_required",
            False
        ),

        "revalidation_count": state.get(
            "revalidation_count",
            0
        ),

        "tool_results": state.get(
            "tool_results",
            {}
        ),
    }


def _validate_llm_decision(decision, state):
    """
    LLM이 선택한 행동이 현재 Case 상태에서 허용되는지 검증한다.

    LLM은 Tool을 선택할 수 있지만,
    필수 검증 절차를 건너뛸 수 없다.
    """

    tool_name = decision["tool"]

    if tool_name not in AVAILABLE_TOOLS:
        return False

    # 설계변경 분석 전에는 다른 검증 단계로 갈 수 없음
    if (
        not state["design_change_analyzed"]
        and tool_name != "design_change"
    ):
        return False

    # 검증계획 생성 전에는 이후 단계로 갈 수 없음
    if (
        state["design_change_analyzed"]
        and not state["validation_plan_created"]
        and tool_name != "validation_plan"
    ):
        return False

    # 영향범위 추적 전에는 품질검증으로 갈 수 없음
    if (
        state["validation_plan_created"]
        and not state["impact_traced"]
        and tool_name != "impact_trace"
    ):
        return False

    # 품질검증 전에는 후속조치/종료 불가
    if (
        state["impact_traced"]
        and not state["quality_validated"]
        and tool_name != "validate_quality"
    ):
        return False

    # HOLD / REJECT인데 후속조치가 아직 없으면 followup 필요
    if (
        state["quality_validated"]
        and state["decision"] in ["HOLD", "REJECT"]
        and not state["followup_completed"]
        and tool_name != "followup"
    ):
        return False

    # HOLD / REJECT 후 후속조치 완료 → wait
    if (
        state["decision"] in ["HOLD", "REJECT"]
        and state["followup_completed"]
        and tool_name != "wait"
    ):
        return False

    # PASS 상태에서는 finish만 허용
    if (
        state["quality_validated"]
        and state["decision"] == "PASS"
        and tool_name != "finish"
    ):
        return False

    return True


def llm_decision(state):
    """
    OpenAI LLM이 현재 Case 상태와 Tool 결과를 분석하여
    다음 행동을 선택한다.
    """

    model_name = os.getenv(
        "OPENAI_MODEL",
        "gpt-4.1-mini"
    )

    llm = ChatOpenAI(
        model=model_name,
        temperature=0
    )

    structured_llm = llm.with_structured_output(
        AgentDecision
    )

    context = _build_agent_context(state)

    system_prompt = """
당신은 항공기 설계변경 품질검증 AI Agent입니다.

당신의 역할은 현재 Case 상태와 이전 Tool 실행 결과를 분석하여
다음에 수행해야 할 행동을 선택하는 것입니다.

사용 가능한 행동은 다음과 같습니다.

1. design_change
   설계변경 내용을 분석합니다.

2. validation_plan
   설계변경 결과를 기반으로 필요한 검증계획을 생성합니다.

3. impact_trace
   Drawing-Part-PO-Lot 관계와 Effectivity를 기반으로
   설계변경 영향범위를 추적합니다.

4. validate_quality
   영향 대상 Lot의 품질문서를 검증하고
   PASS / HOLD / REJECT 판단 결과를 확인합니다.

5. followup
   HOLD 또는 REJECT 발생 시
   보완요청 또는 부적합 후속조치를 생성합니다.

6. wait
   후속조치가 생성된 뒤
   협력사의 보완자료 또는 시정조치 자료를 기다립니다.

7. finish
   모든 필수 검증이 완료되고 품질검증 결과가 PASS이면
   Case를 종료합니다.


중요한 제약조건:

- 필수 검증 단계를 임의로 생략하지 마십시오.
- 품질 기준을 새로 만들거나 변경하지 마십시오.
- PASS / HOLD / REJECT 판정을 임의로 변경하지 마십시오.
- 품질 판정은 validate_quality Tool의 결과를 따르십시오.
- Evidence가 없는 내용을 사실처럼 판단하지 마십시오.
- HOLD 또는 REJECT이면 필요한 후속조치를 수행해야 합니다.
- 후속조치가 완료되면 새로운 자료가 들어올 때까지 wait를 선택하십시오.
- PASS이고 모든 필수 단계가 완료된 경우에만 finish를 선택하십시오.
- 반드시 사용 가능한 행동 중 하나만 선택하십시오.

당신은 품질 판정 기준을 결정하는 것이 아니라,
현재 상태를 바탕으로 다음 작업을 orchestration하는 Agent입니다.
"""

    user_prompt = (
        "현재 Case 상태는 다음과 같습니다.\n\n"
        + json.dumps(
            context,
            ensure_ascii=False,
            default=str,
            indent=2
        )
        + "\n\n현재 상태에서 다음에 수행해야 할 행동 하나와 "
        "그 이유를 결정하십시오."
    )

    response = structured_llm.invoke([
        ("system", system_prompt),
        ("human", user_prompt),
    ])

    return {
        "tool": response.tool,
        "reason": response.reason,
        "decision_source": "LLM"
    }


def decide_next_tool(state):
    """
    LLM을 이용하여 다음 Tool을 선택한다.

    LLM 호출 실패 또는 안전하지 않은 Tool 선택이 발생하면
    기존 Rule 기반 판단으로 자동 전환한다.
    """

    try:
        decision = llm_decision(state)

        if _validate_llm_decision(
            decision,
            state
        ):
            return decision

        fallback = rule_based_decision(state)

        fallback["reason"] = (
            "LLM이 현재 상태에서 허용되지 않는 행동을 선택하여 "
            "안전 규칙에 따라 판단했습니다. "
            + fallback["reason"]
        )

        fallback["decision_source"] = "RULE_FALLBACK"

        return fallback

    except Exception as error:
        fallback = rule_based_decision(state)

        fallback["reason"] = (
            "LLM 호출을 사용할 수 없어 "
            "안전 규칙에 따라 판단했습니다. "
            + fallback["reason"]
        )

        fallback["decision_source"] = "RULE_FALLBACK"

        print(
            f"[Agent] LLM 호출 실패 → Rule fallback: "
            f"{type(error).__name__}: {error}"
        )

        return fallback