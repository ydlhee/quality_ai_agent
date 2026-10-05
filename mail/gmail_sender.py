import base64
from email.message import EmailMessage

from mail.gmail_auth import get_gmail_service


def send_gmail(
    to_email,
    subject,
    body,
    reply_to_message_id=None,
    thread_id=None,
):
    """
    Gmail API를 이용해 메일을 실제 발송한다.

    reply_to_message_id와 thread_id가 있으면
    기존 Gmail Thread에 회신하는 방식으로 발송할 수 있다.
    """

    if not to_email or "@" not in to_email:
        raise ValueError("유효한 수신자 이메일 주소가 필요합니다.")

    if not subject or not subject.strip():
        raise ValueError("메일 제목이 필요합니다.")

    if not body or not body.strip():
        raise ValueError("메일 본문이 필요합니다.")

    service = get_gmail_service()

    message = EmailMessage()
    message["To"] = to_email.strip()
    message["Subject"] = subject.strip()
    message.set_content(body)

    if reply_to_message_id:
        message["In-Reply-To"] = reply_to_message_id
        message["References"] = reply_to_message_id

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    request_body = {
        "raw": encoded_message
    }

    if thread_id:
        request_body["threadId"] = thread_id

    sent_message = (
        service
        .users()
        .messages()
        .send(
            userId="me",
            body=request_body,
        )
        .execute()
    )

    return {
        "success": True,
        "message_id": sent_message.get("id"),
        "thread_id": sent_message.get("threadId"),
        "to": to_email,
        "subject": subject,
    }

def get_gmail_account_email():
    """현재 Gmail API에 인증된 발신 계정의 이메일 주소를 반환한다."""
    service = get_gmail_service()

    profile = (
        service.users()
        .getProfile(userId="me")
        .execute()
    )

    return profile.get("emailAddress") or ""

