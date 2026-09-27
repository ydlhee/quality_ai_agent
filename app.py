import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

st.set_page_config(
    page_title="AeroChange Trace AI",
    layout="wide",
)

st.title("AeroChange Trace AI")
st.caption("항공기 설계변경 영향추적·협력업체 품질검증 AI Agent")

st.subheader("개발환경 확인")

if st.button("화면 실행 확인"):
    st.success("Streamlit 화면이 정상적으로 실행되었습니다.")

st.divider()
st.subheader("AI 연결 확인")

st.write("버튼을 누르면 예시 설계변경을 API로 보내 응답을 확인합니다.")

if st.button("AI 연결 테스트"):
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    if not api_key or api_key == "여기에_발급받은_API_키":
        st.error(".env 파일에 실제 API 키를 입력하고 앱을 다시 실행해주세요.")
        st.stop()

    try:
        client = OpenAI(api_key=api_key, timeout=30.0)

        with st.spinner("AI 응답을 기다리고 있습니다..."):
            response = client.responses.create(
                model=model,
                input=(
                    "다음 설계변경의 의미를 한국어 한 문장으로 설명해줘. "
                    "변경 전: 직경 10.00 ±0.10 mm. "
                    "변경 후: 직경 10.00 ±0.05 mm."
                ),
                max_output_tokens=200,
            )

        st.success("API 연결에 성공했습니다.")
        st.write(response.output_text)

    except Exception as error:
        st.error(f"API 연결 실패: {type(error).__name__}")
        st.info(
            "API 키, 결제·사용 한도, 모델 접근 권한, "
            "인터넷 연결을 확인해주세요."
        )