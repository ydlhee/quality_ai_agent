# AeroChange Trace AI

## 항공기 설계변경 전주기 품질검증 AI Agent

AeroChange Trace AI는 항공기 제조 과정에서 발생하는 설계변경 정보를 분석하고,
변경 영향범위와 관련 품질문서를 추적하여 품질검증 및 후속조치를 지원하는 AI Agent입니다.

설계변경 이후 수행되는 업무를 다음과 같은 하나의 흐름으로 연결합니다.

설계변경 분석 → 검증계획 생성 → 영향범위 추적 → 품질검증 → PASS/HOLD/REJECT 판정 → 후속조치 및 재검증

---

## 1. 주요 기능

### 설계변경 분석
변경 전·후 도면을 비교하여 Revision, 주요 치수, 공차, 재질, 열처리 조건 등의 변경사항을 분석합니다.

### 검증계획 생성
설계변경 유형에 따라 필요한 품질검증 항목과 확인 문서를 생성합니다.

### 영향범위 추적
Drawing → Part → PO → Lot → Quality Document 관계와 Effectivity를 기반으로 설계변경 적용 대상을 추적합니다.

### 품질검증 및 판정
설계 요구조건과 실제 품질문서를 교차검증하여 다음 상태로 판정합니다.

- PASS: 품질검증 기준 만족
- HOLD: 자료 누락 또는 추가 확인 필요
- REJECT: 품질 요구조건 불만족

### 후속조치 및 재검증
HOLD 발생 시 보완자료 요청을 지원하고, REJECT 발생 시 부적합 후속조치를 지원합니다.
보완자료가 수신되면 기존 Case와 연결하여 관련 항목을 재검증할 수 있습니다.

---

## 2. AI Agent

LangChain과 OpenAI API를 기반으로 AI Agent를 구성하였습니다.

Agent는 현재 Case 상태와 이전 Tool 실행 결과를 바탕으로 다음에 수행할 작업을 선택합니다.

주요 Tool은 다음과 같습니다.

1. 설계변경 분석
2. 검증계획 생성
3. 영향범위 추적
4. 품질검증 및 판정
5. 후속조치 및 재검증

품질검증 기준과 최종 판정 규칙은 사전에 정의된 규칙을 기반으로 처리하여
LLM이 임의로 품질 기준을 변경하지 않도록 구성하였습니다.

---

## 3. Gmail 연계

Gmail API를 활용하여 품질 관련 메일과 첨부자료를 Case에 연결할 수 있습니다.

HOLD 발생 시 보완자료 요청 메일을 작성·전송하고,
보완자료가 회신되면 기존 Case와 연결하여 재검증할 수 있도록 구성하였습니다.

※ Gmail 기능을 사용하려면 별도의 Google API 인증 설정이 필요합니다.

---

## 4. 검증

가상 구조화 항공 품질자료를 기반으로 15개 검증 Case를 구성하였습니다.

검증 항목:

- Effectivity 기반 영향 Lot 식별
- Revision 불일치 탐지
- 치수·공차 초과 탐지
- 재질 불일치 탐지
- 열처리 조건 불일치 탐지
- 필수 품질문서 누락 탐지
- 측정값 누락 탐지
- HOLD 후 보완자료 재검증

검증 스크립트:

```powershell
python test_validation_cases.py
```

---

## 5. 실행 환경

권장 환경:

- Windows 10/11
- Python 3.12
- 테스트 환경: Python 3.12.7

---

## 6. 설치 방법

### 1) 저장소 Clone

```powershell
git clone https://github.com/ydlhee/quality_ai_agent.git
cd quality_ai_agent
```

### 2) Python 3.12 가상환경 생성

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) 패키지 설치

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4) 환경변수 설정

프로젝트의 `.env.example`을 참고하여 `.env` 파일을 생성합니다.

```text
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_MODEL=gpt-4.1-mini
```

실제 API Key는 GitHub에 업로드하지 않습니다.

### 5) 애플리케이션 실행

```powershell
streamlit run app.py
```

실행 후 표시되는 로컬 Streamlit 주소로 접속합니다.

---

## 7. 기술 스택

- Python
- Streamlit
- SQLite
- LangChain
- OpenAI API
- Pydantic
- pandas
- ReportLab
- PDF Parser
- Gmail API

---

## 8. 프로젝트 구조

```text
quality_ai_agent/
├── app.py
├── agent/
│   ├── agent.py
│   ├── runner.py
│   └── state.py
├── tools/
├── database/
├── parser/
├── mail/
├── ui/
├── data/
│   ├── test_cases/
│   └── validation_cases_v2/
├── test_validation_cases.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 9. 주의사항

- 실제 OpenAI API Key는 저장소에 포함하지 않습니다.
- Gmail 연계 기능은 Google API 인증 환경이 설정된 경우 사용할 수 있습니다.
- 제출 및 재현 환경에서는 Python 3.12 사용을 권장합니다.