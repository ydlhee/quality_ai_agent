"""AeroChange Trace AI: 안전한 Tool 선택과 추가 검증계획 제안."""
import json
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import Literal

load_dotenv()

AVAILABLE_TOOLS = {
    "design_change": "설계변경 분석",
    "validation_plan": "검증계획 생성",
    "impact_trace": "영향범위 추적",
    "plan_review": "추가 검증계획 검토",
    "validate_quality": "품질검증 및 Risk 판단",
    "replan": "품질검증 결과 기반 동적 계획 재수립",
    "followup": "후속조치",
    "wait": "보완자료 또는 시정조치 자료 수신 대기",
    "finish": "Case 종료",
}

# 기존 백엔드가 인식하는 문서 유형으로 한정한다.
ALLOWED_ADDITIONAL_DOCUMENTS = {
    "DRAWING", "INSPECTION_REPORT", "MATERIAL_CERTIFICATE",
    "HEAT_TREATMENT_CERTIFICATE",
}


class AgentDecision(BaseModel):
    tool: Literal["design_change", "validation_plan", "plan_review", "impact_trace", "validate_quality", "followup", "wait", "finish"] = Field(description="반드시 지정된 영문 Tool ID 중 하나")
    reason: str = Field(description="근거가 있는 선택 이유")


class AdditionalCheck(BaseModel):
    document_type: str = Field(description="추가 확인할 문서 유형")
    reason: str = Field(description="변경사항 또는 증거와 연결되는 구체적인 이유")


class PlanReview(BaseModel):
    additional_checks: list[AdditionalCheck] = Field(
        default_factory=list,
        description="필수 검증계획에 추가할 확인 항목. 근거가 없으면 빈 목록",
    )
    reason: str = Field(description="계획 검토 이유")


def _llm():
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), temperature=0)


def allowed_next_tools(state):
    """실행기 지원 범위와 필수 검증 선행조건을 코드로 강제한다."""
    if not state.get("design_change_analyzed"):
        return ["design_change"]
    if not state.get("validation_plan_created"):
        return ["validation_plan"]
    # 두 독립 작업은 어느 순서로 수행해도 되지만 모두 완료해야 한다.
    independent = []
    if not state.get("plan_review_completed"):
        independent.append("plan_review")
    if not state.get("impact_traced"):
        independent.append("impact_trace")
    if independent:
        return independent
    if not state.get("quality_validated"):
        return ["validate_quality"]
    # 품질검증 이후 동적 재계획을 한 번 수행한다.
    if not state.get("replanning_completed", False):
        return ["replan"]
    if state.get("decision") in ("HOLD", "REJECT"):
        return ["wait"] if state.get("followup_completed") else ["followup"]
    if state.get("decision") == "PASS":
        return ["finish"]
    # 판정이 없으면 종료/대기하지 않고 명시적으로 오류를 보고한다.
    return []


def rule_based_decision(state):
    """LLM 오류 시 안전한 기본 경로를 선택한다."""
    allowed = allowed_next_tools(state)
    if not allowed:
        raise RuntimeError("판정 또는 실행 상태가 유효하지 않아 다음 Tool을 선택할 수 없습니다.")
    tool = allowed[0]
    return {"tool": tool, "reason": f"필수 선행조건을 확인하여 {AVAILABLE_TOOLS[tool]} 실행"}


def _build_agent_context(state):
    return {
        "case_id": state.get("case_id"),
        "case_status": state.get("case_status"),
        "allowed_tools": allowed_next_tools(state),
        "completed_steps": {key: bool(state.get(key)) for key in (
            "design_change_analyzed", "validation_plan_created",
            "plan_review_completed", "impact_traced", "quality_validated", "followup_completed",
        )},
        "quality_decision": state.get("decision"),
        "missing_items": state.get("missing_items", []),
        "additional_checks": state.get("additional_checks", []),
        "pending_actions": state.get("pending_actions", []),
        "tool_results": state.get("tool_results", {}),
    }


def _validate_llm_decision(decision, state):
    return decision.get("tool") in allowed_next_tools(state)


def llm_decision(state):
    context = _build_agent_context(state)
    prompt = (
        "당신은 항공기 설계변경 품질검증 AI Agent입니다. "
        "allowed_tools에 제시된 영문 Tool ID 중 하나만 선택하세요. "
        "plan_review는 설계변경 기반 추가 검증문서 검토이고 impact_trace는 영향 Lot 추적입니다. "
        "두 작업이 모두 가능하면 변경사항과 Case 상황을 고려해 어느 작업을 먼저 수행할지 결정하세요. "
        "필수 검증항목이나 PASS/HOLD/REJECT 판정을 변경하지 마세요. "
        "근거가 없는 사실을 만들지 마세요."
    )
    response = _llm().with_structured_output(AgentDecision).invoke([
        ("system", prompt),
        ("human", json.dumps(context, ensure_ascii=False, default=str)),
    ])
    return {"tool": response.tool.strip(), "reason": response.reason, "decision_source": "LLM"}


def decide_next_tool(state):
    """허용된 작업 안에서 LLM 선택; 실패 시 규칙 기반 복구."""
    allowed = allowed_next_tools(state)
    if not allowed:
        raise RuntimeError("실행 가능한 Tool이 없습니다. 상태와 품질 판정을 확인하세요.")
    try:
        decision = llm_decision(state)
        print(f"[Agent DEBUG] LLM 선택: {decision['tool']} | 허용 Tool: {allowed}")
        if _validate_llm_decision(decision, state):
            return decision
        fallback = rule_based_decision(state)
        fallback["reason"] = "허용되지 않은 LLM 선택으로 안전 규칙 적용: " + fallback["reason"]
    except Exception as error:
        fallback = rule_based_decision(state)
        fallback["reason"] = "LLM 호출 실패로 안전 규칙 적용: " + fallback["reason"]
        print(f"[Agent] LLM 호출 실패: {type(error).__name__}: {error}")
    fallback["decision_source"] = "RULE_FALLBACK"
    return fallback


def review_validation_plan(state):
    """필수 계획 생성 후 호출할 추가 검증 제안 함수.

    이 함수는 상태나 DB를 직접 변경하지 않는다. runner가 반환값을 검토해
    필수 문서와 합집합으로 병합해야 하며, 필수 항목 삭제는 허용하지 않는다.
    """
    plan = state.get("tool_results", {}).get("validation_plan", {}).get("result", {})
    changes = state.get("tool_results", {}).get("design_change", {}).get("result", {}).get("changes", [])
    mandatory = set(plan.get("required_documents", []))
    context = {
        "changes": changes,
        "mandatory_documents": sorted(mandatory),
        "available_additional_documents": sorted(ALLOWED_ADDITIONAL_DOCUMENTS),
    }
    try:
        response = _llm().with_structured_output(PlanReview).invoke([
            ("system", "항공기 설계변경의 필수 검증계획을 검토하세요. 변경사항에 명확한 근거가 "
             "있을 때만 추가 문서 확인을 제안하세요. 필수 검증항목을 삭제하거나 "
             "품질 기준을 새로 만들지 마세요. 추가 문서는 허용된 유형 중에서만 "
             "선택하세요. 근거가 부족하면 additional_checks를 빈 목록으로 반환하세요."),
            ("human", json.dumps(context, ensure_ascii=False, default=str)),
        ])
        checks = []
        seen = set(mandatory)
        for item in response.additional_checks:
            document_type = item.document_type.strip().upper()
            if document_type not in ALLOWED_ADDITIONAL_DOCUMENTS or document_type in seen:
                continue
            if not item.reason.strip():
                continue
            checks.append({"document_type": document_type, "reason": item.reason.strip()})
            seen.add(document_type)
        return {"additional_checks": checks, "reason": response.reason,
                "decision_source": "LLM", "required_documents": sorted(seen)}
    except Exception as error:
        print(f"[Agent] 검증계획 검토 실패: {type(error).__name__}: {error}")
        return {"additional_checks": [], "reason": "기존 필수 검증계획 유지",
                "decision_source": "RULE_FALLBACK", "required_documents": sorted(mandatory)}

class ReplanningDecision(BaseModel):
    """검증 결과를 바탕으로 추가 확인 필요성을 판단한다."""

    replanning_required: bool = Field(
        description="추가 검증계획 검토가 필요한지 여부"
    )
    reason: str = Field(
        description="검증 결과에 근거한 판단 이유"
    )
    suggested_checks: list[AdditionalCheck] = Field(
        default_factory=list,
        description="추가로 확인할 문서와 이유"
    )


def replan_from_quality_result(state):
    """품질검증 결과에 근거해 추가 확인 작업을 제안한다.

    실제 품질 판정이나 필수 검증항목은 변경하지 않는다.
    """
    quality = state.get("tool_results", {}).get("quality", {})
    context = {
        "decision": state.get("decision"),
        "missing_items": state.get("missing_items", []),
        "quality_result": quality.get("result", {}),
        "existing_additional_checks": state.get("additional_checks", []),
        "allowed_documents": sorted(ALLOWED_ADDITIONAL_DOCUMENTS),
    }

    response = _llm().with_structured_output(
        ReplanningDecision
    ).invoke([
        (
            "system",
            "당신은 항공기 품질검증 AI Agent입니다. "
            "품질검증 결과에서 새롭게 발견된 문제를 분석하고 "
            "추가 확인이 필요한 문서가 있는지 판단하세요. "
            "이미 확인 중인 문서는 중복 제안하지 마세요. "
            "필수 검증항목이나 PASS/HOLD/REJECT 판정은 "
            "절대 변경하지 마세요. "
            "근거가 부족하면 추가 확인을 제안하지 마세요."
        ),
        (
            "human",
            json.dumps(context, ensure_ascii=False, default=str)
        ),
    ])

    existing = {
        item["document_type"]
        for item in state.get("additional_checks", [])
    }

    mandatory = set(
        state.get("tool_results", {})
        .get("validation_plan", {})
        .get("result", {})
        .get("required_documents", [])
    )

    suggestions = []
    for item in response.suggested_checks:
        document_type = item.document_type.strip().upper()
        reason = item.reason.strip()

        if (
            document_type in ALLOWED_ADDITIONAL_DOCUMENTS
            and document_type not in existing
            and document_type not in mandatory
            and reason
        ):
            suggestions.append({
                "document_type": document_type,
                "reason": reason,
            })
            existing.add(document_type)

    return {
        "replanning_required": bool(suggestions),
        "reason": response.reason,
        "suggested_checks": suggestions,
        "decision_source": "LLM",
    }