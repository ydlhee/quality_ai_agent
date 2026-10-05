# ==========================================
# HOLD 후속조치 Rule
# ==========================================

HOLD_REQUEST_RULES = {

    "INSPECTION_DATA_MISSING": {
        "request_type": "inspection_document",
        "required_items": [
            "검사성적서 또는 검사자료"
        ]
    },

    "MEASUREMENT_MISSING": {
        "request_type": "inspection_data",
        "required_items": [
            "치수 측정값"
        ]
    },

    "REVISION_MISMATCH": {
        "request_type": "revision_correction",
        "required_items": [
            "요구 Revision이 반영된 수정 문서"
        ]
    },

    "LOT_ID_MISMATCH": {
        "request_type": "lot_information_correction",
        "required_items": [
            "대상 Lot 번호가 올바르게 기재된 수정 문서"
        ]
    },

    "HEAT_NO_MISSING": {
        "request_type": "heat_no_document",
        "required_items": [
            "Heat No.가 확인되는 소재성적서"
        ]
    },

    "HEAT_NO_MISMATCH": {
        "request_type": "heat_no_correction",
        "required_items": [
            "올바른 Heat No.가 확인되는 소재성적서 또는 증빙자료"
        ]
    },

    "MATERIAL_DATA_MISSING": {
        "request_type": "material_document",
        "required_items": [
            "재질 정보가 확인되는 소재성적서"
        ]
    },

    "HEAT_TREATMENT_DATA_MISSING": {
        "request_type": "heat_treatment_document",
        "required_items": [
            "열처리 조건이 확인되는 열처리성적서"
        ]
    }
}


# ==========================================
# REJECT → SCAR Rule
# ==========================================

REJECT_RULES = {

    "DIMENSION_OUT_OF_TOLERANCE": {
        "nonconformance_type":
            "DIMENSION_NONCONFORMANCE"
    },

    "MATERIAL_MISMATCH": {
        "nonconformance_type":
            "MATERIAL_NONCONFORMANCE"
    },

    "HEAT_TREATMENT_MISMATCH": {
        "nonconformance_type":
            "HEAT_TREATMENT_NONCONFORMANCE"
    }
}


# ==========================================
# HOLD 보완요청 생성
# ==========================================

def build_hold_request(
    lot_id,
    issue_code,
    reason,
    requirement=None
):

    if (
        issue_code == "REQUIRED_DOCUMENT_MISSING"
        and requirement
    ):
        if isinstance(requirement, list):
            required_items = requirement
        else:
            required_items = [requirement]

        rule = {
            "request_type": "required_document",
            "required_items": required_items
        }

    else:
        rule = HOLD_REQUEST_RULES.get(
            issue_code,
            {
                "request_type": "additional_document",
                "required_items": [
                    "품질검증에 필요한 보완자료"
                   ]
                }
        )

        required_items = rule[
            "required_items"
        ]

    draft_message = (
        "안녕하세요.\n"
        "AeroChange 품질관리 담당자입니다.\n\n"
        f"{lot_id} 품질검증 결과, 추가 확인이 필요한 사항이 "
        "확인되어 아래와 같이 보완자료를 요청드립니다.\n\n"
        f"- 대상 Lot: {lot_id}\n"
        f"- 확인사항: {reason}\n"
        f"- 요청자료: {', '.join(required_items)}\n\n"
        "원활한 품질검증 및 후속 절차 진행을 위해 "
        "상기 내용을 확인하시어 수정 또는 보완된 자료를 "
        "본 메일로 회신해 주시기 바랍니다.\n\n"
        "회신된 자료는 기존 Case에 연계하여 재검증할 예정입니다.\n\n"
        "협조해 주셔서 감사합니다.\n"
        "AeroChange 품질관리 담당자 드림"
    )

    return {
        "request_type":
            rule["request_type"],

        "required_items":
            required_items,

        "draft_message":
            draft_message
    }


# ==========================================
# REJECT SCAR 초안 생성
# ==========================================

def build_scar_draft(
    lot_id,
    issue_code,
    reason
):

    rule = REJECT_RULES.get(
        issue_code,
        {
            "nonconformance_type":
                "PRODUCT_NONCONFORMANCE"
        }
    )

    return {
        "title":
            "Supplier Corrective Action Request",

        "target_lot":
            lot_id,

        "nonconformance_type":
            rule["nonconformance_type"],

        "issue_code":
            issue_code,

        "nonconformance":
            reason,

        "requested_response": [
            "부적합 원인분석",
            "즉시 시정조치",
            "재발방지대책",
            "시정조치 완료 증빙자료"
        ],

        "draft_message": (
            "안녕하세요.\n"
            "AeroChange 품질관리 담당자입니다.\n\n"
            f"{lot_id} 품질검증 결과, 설계 및 품질 요구조건과 "
            "일치하지 않는 사항이 확인되어 아래와 같이 "
            "시정조치를 요청드립니다.\n\n"
            f"- 대상 Lot: {lot_id}\n"
            f"- 부적합 유형: {rule['nonconformance_type']}\n"
            f"- 부적합 사항: {reason}\n\n"
            "요청사항\n"
            "- 부적합 원인분석\n"
            "- 즉시 시정조치\n"
            "- 재발방지대책\n"
            "- 시정조치 완료 증빙자료\n\n"
            "상기 부적합 사항을 검토하시어 필요한 시정조치를 "
            "수행해 주시고, 조치 완료 후 관련 자료를 "
            "본 메일로 회신해 주시기 바랍니다.\n\n"
            "회신된 자료는 기존 Case에 연계하여 재검증할 예정입니다.\n\n"
            "협조해 주셔서 감사합니다.\n"
            "AeroChange 품질관리 담당자 드림"
        )
    }


# ==========================================
# PASS Action
# ==========================================

def build_pass_action(item):

    return {
        "lot_id":
            item["lot_id"],

        "decision":
            "PASS",

        "issue_code":
            item["issue_code"],

        "action":
            "NONE",

        "description":
            "추가 조치 없음",

        "next_state":
            "COMPLETED",

        "request":
            None,

        "scar_draft":
            None,

        "revalidation": {
            "required": False,
            "tool": None,
            "target_lot":
                item["lot_id"],
            "trigger": None
        }
    }


# ==========================================
# HOLD Action
# ==========================================

def build_hold_action(item):

    request = build_hold_request(
        item["lot_id"],
        item["issue_code"],
        item["reason"],
        item.get("requirement")
    )

    return {
        "lot_id":
            item["lot_id"],

        "decision":
            "HOLD",

        "issue_code":
            item["issue_code"],

        "action":
            "CORRECTION_REQUEST",

        "description":
            "누락 또는 오류 자료에 대한 정정 요청",

        "next_state":
            "WAITING_FOR_CORRECTION",

        "issue":
            item["reason"],

        "request":
            request,

        "scar_draft":
            None,

        "revalidation": {
            "required": True,
            "tool": "validate_quality",
            "target_lot":
                item["lot_id"],
            "trigger":
                "corrected_document_received"
        }
    }


# ==========================================
# REJECT Action
# ==========================================

def build_reject_action(item):

    scar_draft = build_scar_draft(
        item["lot_id"],
        item["issue_code"],
        item["reason"]
    )

    return {
        "lot_id":
            item["lot_id"],

        "decision":
            "REJECT",

        "issue_code":
            item["issue_code"],

        "action":
            "REJECT_LOT",

        "description":
            "제품 요구조건 미달로 Lot 반품 및 SCAR 검토",

        "next_state":
            "WAITING_FOR_CORRECTIVE_ACTION",

        "issue":
            item["reason"],

        "request":
            None,

        "scar_draft":
            scar_draft,

        "revalidation": {
            "required": True,
            "tool": "validate_quality",
            "target_lot":
                item["lot_id"],
            "trigger":
                "corrective_action_received"
        }
    }


# ==========================================
# Decision별 Handler
# ==========================================

ACTION_HANDLERS = {
    "PASS": build_pass_action,
    "HOLD": build_hold_action,
    "REJECT": build_reject_action
}


# ==========================================
# Follow-up Tool
# ==========================================

def handle_followup(
    validation_result,
    case_id
):

    actions = []

    lot_results = validation_result.get(
        "result",
        {}
    ).get(
        "lot_results",
        []
    )

    for item in lot_results:

        decision = item.get(
            "decision"
        )

        handler = ACTION_HANDLERS.get(
            decision
        )

        if handler is None:
            continue

        action_result = handler(
            item
        )

        actions.append(
            action_result
        )

    return {
        "status": "success",

        "case_id": case_id,

        "result": {
            "actions": actions
        },

        "evidence":
            validation_result.get(
                "evidence",
                []
            ),

        "missing_items":
            validation_result.get(
                "missing_items",
                []
            )
    }