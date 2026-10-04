"""AeroChange Trace AI 실행기: 필수 검증 및 최신 DB 기반 재추적."""

from agent.state import create_initial_state

from agent.agent import (

    decide_next_tool,

    review_validation_plan,

    replan_from_quality_result,

)



from tools.drawing_compare import analyze_design_change

from tools.verification_plan import create_validation_plan

from tools.lot_trace import trace_impact

from tools.quality_verify import validate_quality

from tools.followup import handle_followup

from database.case_repository import get_case, update_case_status



MAX_AGENT_STEPS = 12





def _impact_signature(case_data):

    """lot_trace.py가 실제 사용하는 입력만 비교한다."""

    case = case_data.get("case") or {}

    lot = case_data.get("lot") or {}

    return {

        "drawing_revision": case.get("drawing_revision"),

        "lot_no": lot.get("lot_no"),

        "part_no": lot.get("part_no"),

        "po_no": lot.get("po_no"),

        "production_date": lot.get("production_date"),

        "effectivity_date": lot.get("effectivity_date"),

        "lot_revision": lot.get("revision"),

    }





def _impact_changes(old, new):

    return {key: {"before": old.get(key), "after": value}

            for key, value in new.items() if old.get(key) != value}







def _get_quality_decision(result):

    """Lot 판정 우선순위: REJECT > HOLD > PASS. 결과가 없으면 HOLD."""

    decisions = [lot.get("decision") for lot in result.get("result", {}).get("lot_results", []) if lot.get("decision")]

    if "REJECT" in decisions:

        return "REJECT"

    if "HOLD" in decisions:

        return "HOLD"

    return "PASS" if decisions else "HOLD"





def _save_case_status(state, case_status):

    state["case_status"] = case_status

    update_case_status(state["case_id"], case_status)





def _record_trace(state, tool, reason, result, source, revalidation=None):

    entry = {

        "step": len(state["agent_trace"]) + 1,

        "tool": tool,

        "reason": reason,

        "result": result,

        "decision_source": source,

    }

    if revalidation is not None:

        entry["revalidation"] = revalidation

    state["agent_trace"].append(entry)

    state["history"].append(

        f"Agent 선택: {tool} | 판단 출처: {source} | 이유: {reason} | 결과: {result}"

    )





def _review_plan(state):

    """LLM 제안을 필수 문서와 합집합으로 병합한다. LLM은 필수 문서를 제거할 수 없다."""

    mandatory = state["tool_results"]["validation_plan"]["result"].get("required_documents", [])

    review = review_validation_plan(state)

    # runner에서도 허용 목록을 재검증한다. 알 수 없는 문서 유형은 전달하지 않는다.

    allowed = {"DRAWING", "INSPECTION_REPORT", "MATERIAL_CERTIFICATE", "HEAT_TREATMENT_CERTIFICATE"}

    checks = []

    seen = set(mandatory)

    for item in review.get("additional_checks", []):

        doc = item.get("document_type", "").strip().upper()

        reason = item.get("reason", "").strip()

        if doc in allowed and doc not in seen and reason:

            checks.append({"document_type": doc, "reason": reason})

            seen.add(doc)

    state["additional_checks"] = checks

    state["plan_review_completed"] = True

    state["plan_adjustments"].append({

        "mandatory_documents": list(mandatory),

        "additional_checks": [item.copy() for item in checks],

        "effective_required_documents": sorted(seen),

        "reason": review.get("reason", ""),

        "decision_source": review.get("decision_source", "UNKNOWN"),

    })

    _record_trace(state, "plan_review", review.get("reason", "검증계획 검토"),

                  f"추가 문서 {len(checks)}건", review.get("decision_source", "UNKNOWN"))

    return sorted(seen)





def _required_documents(state):

    plan = state["tool_results"]["validation_plan"]["result"]

    mandatory = set(plan.get("required_documents", []))

    additional = {item["document_type"] for item in state.get("additional_checks", [])}

    return sorted(mandatory | additional)





def _apply_quality_result(state, result):

    state["quality_validated"] = True

    state["tool_results"]["quality"] = result

    state["evidence"] = result.get("evidence", [])

    state["missing_items"] = result.get("missing_items", [])

    state["decision"] = _get_quality_decision(result)





def run_case(case_id: str):

    """Case 검증. LLM 추가 문서 제안은 품질 Tool의 필수 문서 확인에 반영한다."""

    state = create_initial_state(case_id)

    case_data = get_case(case_id)

    if case_data is None:

        raise ValueError(f"Case를 찾을 수 없습니다: {case_id}")

    state["impact_input_snapshot"] = _impact_signature(case_data)



    for _ in range(MAX_AGENT_STEPS):

        decision = decide_next_tool(state)

        tool_name = decision["tool"]

        reason = decision["reason"]

        source = decision.get("decision_source", "UNKNOWN")



        if tool_name == "finish":

            if state.get("decision") != "PASS" or not all(state.get(k) for k in (

                "design_change_analyzed", "validation_plan_created", "plan_review_completed", "impact_traced", "quality_validated"

            )):

                raise ValueError("필수 검증 완료 및 PASS 확인 전에는 종료할 수 없습니다.")

            _save_case_status(state, "COMPLETED")

            _record_trace(state, "finish", reason, "COMPLETED", source)

            return state



        if tool_name == "wait":

            if state.get("decision") not in ("HOLD", "REJECT"):

                raise ValueError("HOLD/REJECT가 아닌 상태에서는 보완 대기할 수 없습니다.")

            wait_status = ("WAITING_FOR_CORRECTION" if state["decision"] == "HOLD"

                           else "WAITING_FOR_CORRECTIVE_ACTION")

            _save_case_status(state, wait_status)

            state["revalidation_required"] = True

            _record_trace(state, "wait", reason, wait_status, source)

            return state



        if tool_name == "design_change":

            result = analyze_design_change(case_data, case_id)

            if result.get("status") != "success":

                raise RuntimeError(f"설계변경 분석 실패: {result}")

            state["design_change_analyzed"] = True

            state["tool_results"]["design_change"] = result

            state["agent_phase"] = "DESIGN_ANALYZED"

            execution_result = "success"



        elif tool_name == "validation_plan":

            changes = state["tool_results"]["design_change"]["result"]["changes"]

            result = create_validation_plan(changes, case_id)

            if result.get("status") != "success":

                raise RuntimeError(f"검증계획 생성 실패: {result}")

            state["validation_plan_created"] = True

            state["tool_results"]["validation_plan"] = result

            state["agent_phase"] = "PLAN_CREATED"

            execution_result = "success"



        elif tool_name == "plan_review":

            if not state.get("validation_plan_created") or state.get("plan_review_completed"):

                raise ValueError("검증계획 검토의 선행조건이 충족되지 않았습니다.")

            _review_plan(state)

            # _review_plan 자체가 plan_review trace를 기록한다.

            continue



        elif tool_name == "impact_trace":

            result = trace_impact(case_data, case_id)

            if result.get("status") != "success":

                raise RuntimeError(f"영향범위 추적 실패: {result}")

            state["impact_traced"] = True

            state["tool_results"]["impact"] = result

            state["agent_phase"] = "IMPACT_TRACED"

            execution_result = "success"



        elif tool_name == "validate_quality":

            if not state.get("plan_review_completed") or not state.get("impact_traced"):

                raise ValueError("계획 검토와 영향범위 추적이 완료되어야 품질검증할 수 있습니다.")

            affected_lots = state["tool_results"]["impact"].get("result", {}).get("affected_lots", [])

            result = validate_quality(case_data, affected_lots, case_id,

                                      required_documents=_required_documents(state))

            if result.get("status") != "success":

                raise RuntimeError(f"품질검증 실패: {result}")

            _apply_quality_result(state, result)

            state["agent_phase"] = "QUALITY_VALIDATED"

            execution_result = state["decision"]

        elif tool_name == "replan":

            if not state.get("quality_validated"):

                raise ValueError(

                    "품질검증 완료 전에는 동적 재계획을 수행할 수 없습니다."

                )



            if state.get("replanning_completed", False):

                raise ValueError(

                    "동일 실행에서 재계획을 중복 수행할 수 없습니다."

                )



            review = replan_from_quality_result(state)



            # LLM 제안을 실행기가 다시 검증한다.

            allowed = {

                "DRAWING",

                "INSPECTION_REPORT",

                "MATERIAL_CERTIFICATE",

                "HEAT_TREATMENT_CERTIFICATE",

            }



            existing = set(_required_documents(state))

            accepted = []



            for item in review.get("suggested_checks", []):

                doc = item.get("document_type", "").strip().upper()

                reason_text = item.get("reason", "").strip()



                if doc in allowed and doc not in existing and reason_text:

                    accepted.append({

                        "document_type": doc,

                        "reason": reason_text,

                    })

                    existing.add(doc)



            state["additional_checks"].extend(accepted)

            state["replanning_completed"] = True



            state["plan_adjustments"].append({

                "type": "DYNAMIC_REPLAN",

                "additional_checks": accepted,

                "effective_required_documents": sorted(existing),

                "reason": review.get("reason", ""),

                "decision_source": review.get(

                    "decision_source", "UNKNOWN"

                ),

            })



            if accepted:

                affected_lots = (

                    state["tool_results"]["impact"]

                    .get("result", {})

                    .get("affected_lots", [])

                )



                result = validate_quality(

                    case_data,

                    affected_lots,

                    case_id,

                    required_documents=_required_documents(state),

                )



                if result.get("status") != "success":

                    raise RuntimeError(

                        f"동적 재계획 후 품질검증 실패: {result}"

                    )



                # 동적 재계획은 추가 검증이다. 기존 부적합을 해제하지 않는다.
                previous_decision = state.get("decision")
                previous_quality = state["tool_results"].get("quality")
                previous_evidence = list(state.get("evidence", []))
                previous_missing = list(state.get("missing_items", []))

                _apply_quality_result(state, result)

                priority = {"PASS": 0, "HOLD": 1, "REJECT": 2}
                if priority.get(previous_decision, 0) > priority.get(
                    state["decision"], 0
                ):
                    # 판정뿐 아니라 후속조치가 사용하는 품질 결과와
                    # 근거도 이전의 더 엄격한 결과로 복구한다.
                    state["dynamic_replan_quality_result"] = result
                    state["decision"] = previous_decision
                    state["tool_results"]["quality"] = previous_quality
                    state["evidence"] = previous_evidence
                    state["missing_items"] = previous_missing



            state["plan_revision"] += int(bool(accepted))

            state["agent_phase"] = "REPLANNING_COMPLETED"



            execution_result = (

                f"추가 검증항목 {len(accepted)}건 반영, "

                f"최종 판정 {state['decision']}"

            )

        elif tool_name == "followup":

            result = handle_followup(state["tool_results"]["quality"], case_id)

            if result.get("status") != "success":

                raise RuntimeError(f"후속조치 실패: {result}")

            state["followup_completed"] = True

            state["tool_results"]["followup"] = result

            state["agent_phase"] = "FOLLOWUP_COMPLETED"

            execution_result = "success"



        else:

            raise ValueError(f"알 수 없는 Tool이 선택되었습니다: {tool_name}")



        _record_trace(state, tool_name, reason, execution_result, source)



    raise RuntimeError("Agent 최대 실행 횟수 초과: 반복 실행을 중단했습니다.")





def revalidate_case(state):

    """보완자료 수신 후 기존 영향범위와 확정된 필수/추가 문서 목록으로 재검증한다."""

    case_id = state["case_id"]

    if not state.get("revalidation_required"):

        raise ValueError("현재 Case는 재검증 대기 상태가 아닙니다.")

    if state.get("case_status") not in (

        "WAITING_FOR_CORRECTION", "WAITING_FOR_CORRECTIVE_ACTION"

    ):

        raise ValueError("현재 Case 상태에서는 재검증을 수행할 수 없습니다.")



    case_data = get_case(case_id)

    if case_data is None:

        raise ValueError(f"Case를 찾을 수 없습니다: {case_id}")



    # 변경 감지는 최초 실행 당시 입력과 최신 DB 조회 결과를 비교한다.

    # 최초 실행 당시의 snapshot이 없는 구버전 state는 안전하게 재추적한다.

    latest_signature = _impact_signature(case_data)

    previous_signature = state.get("impact_input_snapshot")

    changed = (_impact_changes(previous_signature, latest_signature)

               if previous_signature is not None else {"snapshot": "MISSING"})



    if "drawing_revision" in changed:

        # Case Revision 갱신만으로는 도면 비교/필수 검증계획의 유효성을 보장할 수 없다.

        # 실행 상태를 변경하기 전에 중단한다.

        raise RuntimeError(

            "Case drawing_revision이 변경됐습니다. 승인된 DB 갱신과 "

            "새 도면 기반 설계분석/검증계획 재생성이 필요합니다. "

            "기존 state로 재검증하지 마세요."

        )



    _save_case_status(state, "REVALIDATING")

    state["revalidation_count"] += 1

    state["history"].append(

        f"재검증 #{state['revalidation_count']} 시작 | 최신 DB 데이터를 조회했습니다."

    )



    if changed:

        # Revision/Effectivity 갱신은 별도 승인·DB 갱신 절차에서 먼저 완료해야 한다.

        # 여기서는 DB를 변경하지 않고 최신 데이터를 재조회하여 추적한다.

        impact_result = trace_impact(case_data, case_id)

        if impact_result.get("status") != "success":

            raise RuntimeError(f"영향범위 재추적 실패: {impact_result}")

        state["tool_results"]["impact"] = impact_result

        state["impact_input_snapshot"] = latest_signature

        state["impact_traced"] = True

        state["plan_adjustments"].append({

            "type": "IMPACT_RETRACE", "changes": changed,

            "reason": "Revision/Effectivity 또는 Lot 추적 입력이 변경되어 영향범위를 재추적",

            "decision_source": "RULE_SAFETY",

        })

        _record_trace(

            state, "impact_trace", f"최신 DB의 추적 입력 변경 감지: {changed}",

            impact_result.get("result", {}).get("impact_status", "success"),

            "RULE_SAFETY", state["revalidation_count"]

        )

    else:

        impact_result = state["tool_results"].get("impact", {})

        _record_trace(state, "impact_reuse", "Revision/Effectivity/Lot 추적 입력 변경 없음",

                      "기존 영향범위 재사용", "RULE_SAFETY", state["revalidation_count"])



    affected_lots = impact_result.get("result", {}).get("affected_lots", [])

    # Effectivity 이전 등 영향 대상이 없는 경우 품질 Tool이 기본 Lot을

    # 임의로 재검증하지 않도록 자동 완료를 막고 검토를 요청한다.

    if not affected_lots:

        state["decision"] = "HOLD"

        state["revalidation_required"] = True

        _save_case_status(state, "WAITING_FOR_CORRECTION")

        _record_trace(state, "wait", "영향 대상 Lot이 없어 적용 범위 검토 필요",

                      "WAITING_FOR_CORRECTION", "RULE_SAFETY", state["revalidation_count"])

        return state

    result = validate_quality(case_data, affected_lots, case_id,

                              required_documents=_required_documents(state))

    if result.get("status") != "success":

        raise RuntimeError(f"재검증 실패: {result}")

    _apply_quality_result(state, result)

    _record_trace(state, "validate_quality",

                  "보완자료 수신 후 기존 영향 Lot에 대해 재검증합니다.",

                  state["decision"], "RULE", state["revalidation_count"])



    if state["decision"] == "PASS":

        _save_case_status(state, "COMPLETED")

        state["revalidation_required"] = False

        state["followup_completed"] = True

        _record_trace(state, "finish", "재검증 결과 PASS로 종료합니다.", "COMPLETED", "RULE")

        return state



    state["followup_completed"] = False

    followup_result = handle_followup(result, case_id)

    if followup_result.get("status") != "success":

        raise RuntimeError(f"재검증 후속조치 실패: {followup_result}")

    state["followup_completed"] = True

    state["tool_results"]["followup"] = followup_result

    _record_trace(state, "followup", f"재검증 결과 {state['decision']} 후속조치가 필요합니다.",

                  "success", "RULE")

    wait_status = ("WAITING_FOR_CORRECTION" if state["decision"] == "HOLD"

                   else "WAITING_FOR_CORRECTIVE_ACTION")

    _save_case_status(state, wait_status)

    state["revalidation_required"] = True

    _record_trace(state, "wait", "추가 자료 수신 대기", wait_status, "RULE")

    return state
