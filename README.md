\# AeroChange Trace AI



\## 항공기 설계변경 전주기 품질검증 AI Agent



AeroChange Trace AI는 항공기 제조 과정에서 발생하는 설계변경 정보를 분석하고,

변경 영향범위와 관련 품질문서를 추적하여 품질검증 및 후속조치를 지원하는 AI Agent입니다.



도면 Revision 변경 이후 발생하는 품질검증 업무를



설계변경 분석

→ 검증계획 생성

→ 영향범위 추적

→ 품질검증

→ PASS / HOLD / REJECT 판정

→ 후속조치

→ 보완자료 재검증



의 전 과정으로 연결합니다.





\## 1. 개발 배경



항공기 제조에서는 설계변경이 발생하면 변경된 Revision, 치수, 공차,

재질, 열처리 조건 등이 적용 시점(Effectivity) 이후 생산되는 부품과

협력업체 품질문서에 정확하게 반영되어야 합니다.



그러나 도면, PO, Lot, 검사성적서, 소재성적서, 열처리성적서 등의 정보가

여러 문서와 시스템에 분산되어 있어 품질 담당자가 변경 적용 대상과

반영 여부를 반복적으로 확인해야 합니다.



AeroChange Trace AI는 이러한 설계변경 이후의 품질검증 과정을

AI Agent 기반으로 연결하여 변경사항 추적, 품질검증, 후속조치 및

재검증을 지원합니다.





\## 2. 주요 기능



\### ① 설계변경 분석



변경 전·후 도면을 비교하여 다음과 같은 설계변경 정보를 분석합니다.



\- Revision

\- 주요 치수

\- 공차

\- 재질

\- 열처리 조건





\### ② 검증계획 생성



설계변경 유형을 기반으로 필요한 품질검증 항목과 확인 문서를 생성합니다.



예:



\- 치수/공차 변경 → 검사성적서 확인

\- 재질 변경 → 소재성적서 확인

\- 열처리 변경 → 열처리성적서 확인





\### ③ 영향범위 추적



다음 Digital Thread를 기반으로 설계변경의 영향범위를 추적합니다.



Drawing → Part → PO → Lot → Quality Document



Effectivity와 Lot 정보를 함께 고려하여 변경 적용 대상 Lot을 식별합니다.





\### ④ 품질검증 및 판정



설계 요구조건과 실제 품질문서의 데이터를 교차검증합니다.



주요 검증 대상:



\- 도면 Revision 일치 여부

\- 치수 및 공차 만족 여부

\- 재질 일치 여부

\- 열처리 조건 일치 여부

\- 필수 품질문서 존재 여부



검증 결과는 다음 세 가지 상태로 판정합니다.



\- PASS: 모든 품질검증 기준 만족

\- HOLD: 추가 자료 또는 확인 필요

\- REJECT: 품질 요구조건 불만족





\### ⑤ 후속조치 및 재검증



HOLD 또는 REJECT 발생 시 후속조치를 생성합니다.



HOLD:

보완자료 요청



REJECT:

부적합 사항 및 시정조치 요청(SCAR)



보완자료가 수신되면 기존 Case에 연결하여 관련 항목을 다시 검증할 수 있습니다.





\## 3. AI Agent



LangChain과 OpenAI API 기반 AI Agent를 사용합니다.



Agent는 현재 Case의 상태와 이전 Tool 실행 결과를 바탕으로

다음에 실행할 Tool을 선택합니다.



주요 Tool:



1\. 설계변경 분석

2\. 검증계획 생성

3\. 영향범위 추적

4\. 품질검증

5\. 후속조치 및 재검증



Agent의 Tool 선택 과정과 실행 결과는 Agent 실행 이력에서 확인할 수 있습니다.



필수 품질검증 기준과 최종 품질판정은 사전에 정의된 규칙을 기반으로 처리하여,

LLM이 임의로 품질 기준을 변경하지 않도록 구성했습니다.





\## 4. Gmail 기반 품질업무 연계



Gmail을 통해 협력업체와 품질자료를 송수신할 수 있습니다.



지원 흐름:



협력업체 설계변경 요청 메일

→ Gmail 수신

→ 첨부문서 분석

→ Case 생성

→ AI Agent 품질검증

→ HOLD 발생

→ 보완자료 요청 메일 발송

→ 협력업체 회신

→ 기존 Case 연결

→ 보완자료 등록

→ AI Agent 재검증



실제 Gmail을 이용한 E2E 테스트에서

초기 검사성적서 누락으로 HOLD 판정된 Case에 대해

보완자료 요청 메일을 발송하고,

협력업체가 회신한 검사성적서를 기존 Case에 연결하여

재검증 후 PASS로 전환되는 흐름을 확인했습니다.



보완자료 등록 및 재검증 단계에는 담당자 승인 절차를 두어

품질업무의 Human-in-the-loop 구조를 유지합니다.





\## 5. Demo Case



\### CASE-001 — PASS



정상 품질문서가 모두 존재하고 품질 요구조건을 만족하는 Case입니다.



Expected Result: PASS





\### CASE-002 — HOLD



필수 품질정보 또는 문서가 부족하여 추가 확인이 필요한 Case입니다.



Expected Result: HOLD





\### CASE-003 — REJECT



품질 요구조건을 만족하지 않는 항목이 존재하는 Case입니다.



Expected Result: REJECT





\## 6. 기술 스택



\- Python

\- Streamlit

\- SQLite

\- LangChain

\- OpenAI API

\- PyMuPDF

\- Pydantic

\- pandas

\- ReportLab

\- Gmail API





\## 7. 프로젝트 구조



```text

quality\_ai\_agent/

│

├── agent/

│   ├── agent.py

│   ├── runner.py

│   └── state.py

│

├── tools/

│   ├── drawing\_compare.py

│   ├── verification\_plan.py

│   ├── lot\_trace.py

│   ├── quality\_verify.py

│   └── followup.py

│

├── database/

│   ├── case\_repository.py

│   ├── drawing\_repository.py

│   ├── lot\_repository.py

│   ├── supplemental\_repository.py

│   └── outbound\_mail\_repository.py

│

├── parser/

│   ├── drawing\_parser.py

│   ├── pdf\_parser.py

│   └── quality\_certificate\_parser.py

│

├── mail/

│   ├── gmail\_auth.py

│   ├── gmail\_receiver.py

│   ├── gmail\_processor.py

│   └── gmail\_sender.py

│

├── ui/

│   └── components.py

│

├── data/

│   ├── test\_cases/

│   └── final\_validation\_cases/

│

├── app\_aerospace\_qms\_v3.py

├── requirements.txt

└── README.md

