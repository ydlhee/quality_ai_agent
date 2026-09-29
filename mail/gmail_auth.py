from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent.parent

CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"


# 현재 단계에서는 Gmail 메일 조회 + 발송에 필요한 권한을 사용한다.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]


def get_gmail_service():
    """
    Google OAuth 인증을 수행하고 Gmail API Service 객체를 반환한다.

    최초 실행:
        브라우저에서 Google 로그인 및 권한 승인
        → token.json 생성

    이후 실행:
        token.json을 사용하여 자동 인증
    """

    credentials = None

    # 기존 인증 토큰이 있으면 불러온다.
    if TOKEN_PATH.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_PATH),
            SCOPES
        )

    # 인증정보가 없거나 유효하지 않은 경우
    if not credentials or not credentials.valid:

        # Refresh Token이 있으면 자동 갱신
        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(Request())

        # 최초 인증
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"OAuth 인증 파일을 찾을 수 없습니다: "
                    f"{CREDENTIALS_PATH}"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH),
                SCOPES
            )

            credentials = flow.run_local_server(
                port=0
            )

        # 인증 결과 저장
        TOKEN_PATH.write_text(
            credentials.to_json(),
            encoding="utf-8"
        )

    # Gmail API Service 생성
    service = build(
        "gmail",
        "v1",
        credentials=credentials
    )

    return service


def test_gmail_connection():
    """
    Gmail API 연결을 테스트한다.
    메일을 읽거나 발송하지 않고 현재 인증 계정 정보만 확인한다.
    """

    service = get_gmail_service()

    profile = (
        service
        .users()
        .getProfile(userId="me")
        .execute()
    )

    print("Gmail API 연결 성공")
    print(f"Email: {profile.get('emailAddress')}")
    print(f"Messages: {profile.get('messagesTotal')}")
    print(f"Threads: {profile.get('threadsTotal')}")


if __name__ == "__main__":
    test_gmail_connection()