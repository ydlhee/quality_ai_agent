"""Dynamic replan regression: REJECT must survive a later PASS and reach followup.
Uses mocks only: no DB write, no API call.
"""
from unittest.mock import patch
import agent.runner as runner

initial_quality = {
    'status': 'success',
    'result': {'lot_results': [{'decision': 'REJECT', 'issue_type': 'DIMENSION_OUT_OF_TOLERANCE'}]},
    'evidence': [{'reason': 'Original dimension out of tolerance'}],
    'missing_items': [],
}
later_quality = {
    'status': 'success',
    'result': {'lot_results': [{'decision': 'PASS'}]},
    'evidence': [{'reason': 'Supplemental check passed'}],
    'missing_items': [],
}
state = {
    'case_id': 'TEST-REJECT-PRESERVE', 'tool_results': {}, 'agent_trace': [], 'history': [],
    'plan_adjustments': [], 'additional_checks': [], 'plan_revision': 0,
    'design_change_analyzed': False, 'validation_plan_created': False,
    'plan_review_completed': False, 'impact_traced': False, 'quality_validated': False,
    'replanning_completed': False, 'followup_completed': False,
}
steps = iter(['design_change', 'validation_plan', 'plan_review', 'impact_trace',
              'validate_quality', 'replan', 'followup', 'wait'])
seen = {'quality_calls': 0, 'followup_input': None}

def decide(_state):
    tool = next(steps)
    return {'tool': tool, 'reason': 'Mock regression', 'decision_source': 'TEST_MOCK'}

def validate(*args, **kwargs):
    seen['quality_calls'] += 1
    return initial_quality if seen['quality_calls'] == 1 else later_quality

def followup(quality, case_id):
    seen['followup_input'] = quality
    return {'status': 'success', 'result': {}}

with patch.multiple(runner,
    create_initial_state=lambda case_id: state,
    get_case=lambda case_id: {'case': {}, 'lot': {}},
    update_case_status=lambda *args: None,
    decide_next_tool=decide,
    analyze_design_change=lambda *args: {'status': 'success', 'result': {'changes': []}},
    create_validation_plan=lambda *args: {'status': 'success', 'result': {'required_documents': ['DRAWING']}},
    review_validation_plan=lambda *args: {'additional_checks': [], 'reason': 'Initial plan', 'decision_source': 'TEST_MOCK'},
    trace_impact=lambda *args: {'status': 'success', 'result': {'affected_lots': ['LOT-TEST']}},
    validate_quality=validate,
    replan_from_quality_result=lambda *args: {'suggested_checks': [{'document_type': 'HEAT_TREATMENT_CERTIFICATE', 'reason': 'Supplemental check'}], 'reason': 'Mock replan', 'decision_source': 'TEST_MOCK'},
    handle_followup=followup,
):
    result = runner.run_case('TEST-REJECT-PRESERVE')

assert seen['quality_calls'] == 2, seen
assert result['decision'] == 'REJECT', result['decision']
assert result['case_status'] == 'WAITING_FOR_CORRECTIVE_ACTION', result['case_status']
assert result['tool_results']['quality'] == initial_quality
assert result['evidence'] == initial_quality['evidence']
assert seen['followup_input'] == initial_quality
assert result['dynamic_replan_quality_result'] == later_quality
assert result['plan_revision'] == 1
print('QUALITY_CALLS:', seen['quality_calls'])
print('FINAL_DECISION:', result['decision'])
print('CASE_STATUS:', result['case_status'])
print('FOLLOWUP_RECEIVED_ORIGINAL_REJECT:', seen['followup_input'] == initial_quality)
print('ALL_ASSERTIONS_PASSED')
