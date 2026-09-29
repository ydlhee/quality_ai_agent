import base64
from email.header import decode_header
from pathlib import Path

from mail.gmail_auth import get_gmail_service


# ============================================================
# 기본 경로 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Gmail에서 받은 첨부파일 저장 위치
ATTACHMENT_DIR = BASE_DIR / "data" / "mail_attachments"


# ============================================================
# MIME Header 디코딩
# ============================================================

def decode_mime_header(value):
    """
    MIME 인코딩된 제목, 발신자 등을
    사람이 읽을 수 있는 문자열로 변환한다.
    """

    if not value:
        return ""

    decoded_parts = decode_header(value)

    result = []

    for part, encoding in decoded_parts:

        if isinstance(part, bytes):

            result.append(
                part.decode(
                    encoding or "utf-8",
                    errors="replace"
                )
            )

        else:
            result.append(part)

    return "".join(result)


# ============================================================
# Header 값 가져오기
# ============================================================

def get_header(headers, name):
    """
    Gmail message headers에서
    원하는 Header 값을 찾는다.
    """

    for header in headers:

        if header.get("name", "").lower() == name.lower():

            return decode_mime_header(
                header.get("value", "")
            )

    return ""


# ============================================================
# Gmail Base64 본문 디코딩
# ============================================================

def decode_body(data):
    """
    Gmail API의 Base64 URL-safe 데이터를
    문자열로 변환한다.
    """

    if not data:
        return ""

    decoded = base64.urlsafe_b64decode(
        data.encode("utf-8")
    )

    return decoded.decode(
        "utf-8",
        errors="replace"
    )


# ============================================================
# 메일 본문 추출
# ============================================================

def extract_body(payload):
    """
    Gmail 메시지에서 text/plain 본문을 우선 추출한다.
    """

    mime_type = payload.get(
        "mimeType",
        ""
    )

    body_data = (
        payload
        .get("body", {})
        .get("data")
    )

    # 일반 텍스트 메일
    if mime_type == "text/plain" and body_data:

        return decode_body(
            body_data
        )

    # Multipart 메일
    for part in payload.get("parts", []):

        body = extract_body(
            part
        )

        if body:
            return body

    # 단일 파트 메일
    if body_data:

        return decode_body(
            body_data
        )

    return ""


# ============================================================
# 첨부파일 정보 추출
# ============================================================

def extract_attachments(payload):
    """
    Gmail 메시지에서 첨부파일 정보를 찾는다.
    """

    attachments = []

    filename = payload.get(
        "filename",
        ""
    )

    body = payload.get(
        "body",
        {}
    )

    attachment_id = body.get(
        "attachmentId"
    )

    inline_data = body.get(
        "data"
    )

    if filename:

        attachments.append({
            "filename": decode_mime_header(
                filename
            ),
            "attachment_id": attachment_id,
            "inline_data": inline_data,
            "mime_type": payload.get(
                "mimeType",
                ""
            )
        })

    # Multipart 내부 첨부파일도 재귀 탐색
    for part in payload.get("parts", []):

        attachments.extend(
            extract_attachments(
                part
            )
        )

    return attachments


# ============================================================
# AeroChange 메일 조회
# ============================================================

def get_recent_messages(max_results=10):
    """
    Gmail에서 AeroChange 업무 메일만 조회한다.

    제목에 [AeroChange]가 포함된 메일만 가져온다.
    """

    service = get_gmail_service()

    response = (
        service
        .users()
        .messages()
        .list(
            userId="me",

            # 중요:
            # 개인 메일 전체를 가져오지 않고
            # AeroChange 메일만 조회한다.
            q='subject:"[AeroChange]"',

            maxResults=max_results
        )
        .execute()
    )

    messages = response.get(
        "messages",
        []
    )

    results = []

    for item in messages:

        message = (
            service
            .users()
            .messages()
            .get(
                userId="me",
                id=item["id"],
                format="full"
            )
            .execute()
        )

        payload = message.get(
            "payload",
            {}
        )

        headers = payload.get(
            "headers",
            []
        )

        result = {

            "message_id":
                message.get("id"),

            "thread_id":
                message.get("threadId"),

            "from":
                get_header(
                    headers,
                    "From"
                ),

            "to":
                get_header(
                    headers,
                    "To"
                ),

            "subject":
                get_header(
                    headers,
                    "Subject"
                ),

            "date":
                get_header(
                    headers,
                    "Date"
                ),

            "body":
                extract_body(
                    payload
                ),

            "attachments":
                extract_attachments(
                    payload
                )
        }

        results.append(
            result
        )

    return results


# ============================================================
# 안전한 파일명 처리
# ============================================================

def safe_filename(filename):
    """
    첨부파일 이름에 경로 문자가 포함되어 있어도
    지정된 폴더 밖으로 저장되지 않도록 한다.
    """

    return Path(
        filename
    ).name


# ============================================================
# 첨부파일 하나 다운로드
# ============================================================

def download_attachment(
    service,
    message_id,
    attachment,
    save_dir
):
    """
    Gmail 첨부파일 하나를
    실제 파일로 저장한다.
    """

    filename = safe_filename(
        attachment["filename"]
    )

    attachment_id = attachment.get(
        "attachment_id"
    )

    inline_data = attachment.get(
        "inline_data"
    )

    # 일반 Gmail 첨부파일
    if attachment_id:

        attachment_data = (
            service
            .users()
            .messages()
            .attachments()
            .get(
                userId="me",
                messageId=message_id,
                id=attachment_id
            )
            .execute()
        )

        encoded_data = (
            attachment_data
            .get("data")
        )

    # 작은 첨부파일 등이
    # 메시지 내부에 직접 들어있는 경우
    else:

        encoded_data = inline_data

    if not encoded_data:

        raise ValueError(
            f"첨부파일 데이터를 찾을 수 없습니다: {filename}"
        )

    file_data = (
        base64
        .urlsafe_b64decode(
            encoded_data.encode(
                "utf-8"
            )
        )
    )

    save_path = (
        save_dir
        / filename
    )

    save_path.write_bytes(
        file_data
    )

    return save_path


# ============================================================
# 특정 메일의 첨부파일 전체 다운로드
# ============================================================

def download_message_attachments(message):
    """
    특정 Gmail 메시지의 모든 첨부파일을 저장한다.

    메시지 ID별 폴더를 생성하여
    동일한 파일명이 충돌하지 않도록 한다.
    """

    attachments = message.get(
        "attachments",
        []
    )

    if not attachments:

        return []

    service = get_gmail_service()

    message_id = message[
        "message_id"
    ]

    message_dir = (
        ATTACHMENT_DIR
        / message_id
    )

    message_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    saved_files = []

    for attachment in attachments:

        save_path = download_attachment(
            service=service,
            message_id=message_id,
            attachment=attachment,
            save_dir=message_dir
        )

        saved_files.append(
            str(save_path)
        )

    return saved_files


# ============================================================
# 테스트 출력
# ============================================================

def print_recent_messages(
    max_results=10,
    download_attachments=True
):
    """
    AeroChange 메일을 조회해서
    PowerShell에 출력한다.
    """

    messages = get_recent_messages(
        max_results=max_results
    )

    print()

    print(
        f"AeroChange 메일 "
        f"{len(messages)}건 조회"
    )

    print("=" * 70)

    # 검색 결과 없음
    if not messages:

        print(
            "[AeroChange]가 제목에 포함된 "
            "메일이 없습니다."
        )

        return

    for index, message in enumerate(
        messages,
        start=1
    ):

        print()

        print(
            f"[메일 {index}]"
        )

        print(
            f"Message ID: "
            f"{message['message_id']}"
        )

        print(
            f"Thread ID: "
            f"{message['thread_id']}"
        )

        print(
            f"From: "
            f"{message['from']}"
        )

        print(
            f"To: "
            f"{message['to']}"
        )

        print(
            f"Subject: "
            f"{message['subject']}"
        )

        print(
            f"Date: "
            f"{message['date']}"
        )

        print(
            "Attachments:",
            [
                item["filename"]
                for item
                in message["attachments"]
            ]
        )

        body = (
            message["body"]
            .strip()
            .replace(
                "\r",
                ""
            )
        )

        # 출력이 너무 길어지는 것을 방지
        if len(body) > 500:

            body = (
                body[:500]
                + "..."
            )

        print("Body:")

        print(
            body
        )

        # 첨부파일 저장
        if (
            download_attachments
            and message["attachments"]
        ):

            saved_files = (
                download_message_attachments(
                    message
                )
            )

            print(
                "Saved attachments:"
            )

            for saved_file in saved_files:

                print(
                    f"  - {saved_file}"
                )

        print(
            "-" * 70
        )


# ============================================================
# 직접 실행
# ============================================================

if __name__ == "__main__":

    print_recent_messages(
        max_results=10,
        download_attachments=True
    )