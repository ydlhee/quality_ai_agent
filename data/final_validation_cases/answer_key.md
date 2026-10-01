# 추가 테스트 정답표

가상 구조화 자료입니다. PDF 추출·DB·Agent·Tool 실행 결과가 아닙니다.

| Case | 목적 | 예상 판정 | 예상 원인 | 정답 상태 | 실행 상태 |
|---|---|---|---|---|---|
| QA-001 | Effectivity 당일 새 Revision 적용 | PASS | NO_ISSUE | DEFINED | NOT_RUN |
| QA-002 | Effectivity 전날 구 Revision 생산 | EXCLUDED | 해당 없음 | DEFINED | NOT_RUN |
| QA-003 | 공차 하한값 19.90 | PASS | NO_ISSUE | DEFINED | NOT_RUN |
| QA-004 | 공차 상한값 20.10 | PASS | NO_ISSUE | DEFINED | NOT_RUN |
| QA-005 | 공차 상한 초과 20.11 | REJECT | DIMENSION_OUT_OF_TOLERANCE | DEFINED | NOT_RUN |
| QA-006 | Lot C, 검사성적서만 B | HOLD | REVISION_MISMATCH | DEFINED | NOT_RUN |
| QA-007 | 요구 재질과 소재성적서 불일치 | REJECT | MATERIAL_MISMATCH | DEFINED | NOT_RUN |
| QA-008 | 재질 변경 후 필수 소재성적서 누락 | HOLD | REQUIRED_DOCUMENT_MISSING | DEFINED | NOT_RUN |
| QA-009 | 검사성적서가 다른 Lot을 가리킴 | 미확정 | LOT_ID_MISMATCH | PENDING_TEAM_DECISION | NOT_RUN |
| QA-010 | 구버전 검사성적서와 공차 초과 동시 발생 | REJECT | DIMENSION_OUT_OF_TOLERANCE | DEFINED | NOT_RUN |

## 사용 방법

- 1번 담당자는 scenario.json의 phases를 읽고 case_data만 기존 Tool에 전달합니다.
- expected와 answer.json은 정답이며, Agent/LLM/판정 함수의 입력으로 전달하지 않습니다.
- QA-002는 영향범위 제외가 정답입니다. 품질 PASS와 구분합니다.
- QA-009는 판정 미확정이므로 성공/실패 집계에서 별도로 구분합니다. 정답 확정 전 자동 합격 처리하지 않습니다.
- QA-010은 문서 Revision 문제와 공차 초과가 동시에 있는 사례입니다. 실제 결과가 HOLD여도 정답을 결과에 맞춰 바꾸지 않습니다.
- evidence의 json_pointer는 같은 Case의 scenario.json 내부 경로입니다. PDF가 없으므로 페이지 번호를 만들지 않았습니다.
- 실제 판정, 원인, 통과 여부와 실행시간은 1번의 실행 결과로 별도 기록합니다.
