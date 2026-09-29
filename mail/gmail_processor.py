import re
from pathlib import Path
from pprint import pprint

from mail.gmail_receiver import (
    get_recent_messages,
    download_message_attachments,
)

from parser.drawing_parser import parse_drawing_pdf
from parser.pdf_parser import parse_inspection_pdf
from parser.quality_certificate_parser import parse_certificate_pdf

from database.mail_case_repository import (
    get_case_id_by_thread,
    get_thread_by_case_id,
)


# ============================================================
# AeroChange 업무 메일 확인
# ============================================================

def is_aerochange_mail(message):
    """
    현재 개발 단계에서는 제목에 AeroChange가 포함된 메일을
    AeroChange 업무 메일로 처리한다.
    """

    subject = message.get("subject", "")

    return "aerochange" in subject.lower()


# ============================================================
# Case ID 추출
# ============================================================

def extract_case_id(message):
    """
    제목 또는 본문에서 CASE-001 형식의 Case ID를 찾는다.
    """

    subject = message.get("subject", "")
    body = message.get("body", "")

    text = f"{subject}\n{body}"

    match = re.search(
        r"\bCASE-\d{3,}\b",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0).upper()


# ============================================================
# Thread 연결 정보 조회
# ============================================================

def get_thread_mapping(thread_id):
    """
    thread_id에 연결된 Case와 최초 message_id를 조회한다.

    기존 repository의 get_case_id_by_thread()와
    get_thread_by_case_id()를 조합하여 사용한다.
    """

    if not thread_id:
        return None

    case_id = get_case_id_by_thread(
        thread_id
    )

    if not case_id:
        return None

    mapping = get_thread_by_case_id(
        case_id
    )

    if not mapping:
        return None

    # 혹시 같은 Case에 다른 Thread가 존재하는 상황을 방지
    if mapping.get("thread_id") != thread_id:
        return None

    return mapping


# ============================================================
# 메일 유형 분류
# ============================================================

def classify_message(message):
    """
    메일 역할을 분류한다.

    분류 규칙

    1. AeroChange 메일이 아니면 IGNORE

    2. Gmail Thread가 기존 Case에 연결되어 있고,
       현재 message_id가 initial_message_id와 같으면
       최초 메일이므로 INITIAL

    3. Gmail Thread가 기존 Case에 연결되어 있고,
       현재 message_id가 최초 message_id와 다르면
       SUPPLEMENTAL

    4. 제목/본문에 기존 Case ID가 있으면
       SUPPLEMENTAL

    5. 어느 Case와도 연결되지 않은 AeroChange 메일이면
       NEW
    """

    # --------------------------------------------------------
    # 1. AeroChange 업무 메일 여부
    # --------------------------------------------------------

    if not is_aerochange_mail(message):

        return {
            "mail_type": "IGNORE",
            "case_id": None,
            "reason": "AeroChange 업무 메일이 아닙니다.",
        }

    thread_id = message.get(
        "thread_id"
    )

    message_id = message.get(
        "message_id"
    )

    # --------------------------------------------------------
    # 2. Gmail Thread 연결 정보 확인
    # --------------------------------------------------------

    mapping = get_thread_mapping(
        thread_id
    )

    if mapping:

        thread_case_id = mapping.get(
            "case_id"
        )

        initial_message_id = mapping.get(
            "initial_message_id"
        )

        # ----------------------------------------------------
        # 최초 메일
        # ----------------------------------------------------

        if (
            initial_message_id
            and message_id == initial_message_id
        ):

            return {
                "mail_type": "INITIAL",
                "case_id": thread_case_id,
                "reason": (
                    f"{thread_case_id}를 생성한 "
                    "최초 요청 메일입니다."
                ),
            }

        # ----------------------------------------------------
        # 같은 Thread의 후속 메일
        # ----------------------------------------------------

        return {
            "mail_type": "SUPPLEMENTAL",
            "case_id": thread_case_id,
            "reason": (
                f"Gmail Thread가 기존 "
                f"{thread_case_id}와 연결되어 있으며 "
                "최초 메일 이후 수신된 후속 자료입니다."
            ),
        }

    # --------------------------------------------------------
    # 3. 제목 / 본문에 Case ID가 있는지 확인
    # --------------------------------------------------------

    case_id = extract_case_id(
        message
    )

    if case_id:

        return {
            "mail_type": "SUPPLEMENTAL",
            "case_id": case_id,
            "reason": (
                f"메일에서 기존 Case ID "
                f"{case_id}가 확인되었습니다."
            ),
        }

    # --------------------------------------------------------
    # 4. 신규 Case 후보
    # --------------------------------------------------------

    return {
        "mail_type": "NEW",
        "case_id": None,
        "reason": (
            "기존 Gmail Thread 및 Case ID와 연결되지 않은 "
            "신규 설계변경 요청 메일입니다."
        ),
    }


# ============================================================
# 문서 유형 판별
# ============================================================

def detect_document_type(file_path):
    """
    파일명 규칙을 기준으로 문서 유형을 판별한다.

    DWG-* : 도면
    INS-* : 검사성적서
    MAT-* : 소재성적서
    HT-*  : 열처리성적서
    """

    file_name = Path(
        file_path
    ).name.upper()

    if file_name.startswith("DWG-"):
        return "DRAWING"

    if file_name.startswith("INS-"):
        return "INSPECTION_REPORT"

    if file_name.startswith("MAT-"):
        return "MATERIAL_CERTIFICATE"

    if file_name.startswith("HT-"):
        return "HEAT_TREATMENT_CERTIFICATE"

    return "OTHER"


# ============================================================
# 첨부문서 Parser 실행
# ============================================================

def parse_attachment(file_path):
    """
    첨부파일의 문서 유형을 판별하고
    해당 Parser를 실행한다.
    """

    document_type = detect_document_type(
        file_path
    )

    result = {
        "file_path": str(file_path),
        "file_name": Path(file_path).name,
        "document_type": document_type,
        "parse_status": None,
        "structured_data": None,
        "error": None,
    }

    try:

        # ----------------------------------------------------
        # Drawing
        # ----------------------------------------------------

        if document_type == "DRAWING":

            structured_data = parse_drawing_pdf(
                file_path
            )

        # ----------------------------------------------------
        # Inspection Report
        # ----------------------------------------------------

        elif document_type == "INSPECTION_REPORT":

            structured_data = parse_inspection_pdf(
                file_path
            )

            if (
                structured_data.get(
                    "missing_fields"
                )
                or structured_data.get(
                    "errors"
                )
            ):

                result[
                    "parse_status"
                ] = "WARNING"

                result[
                    "structured_data"
                ] = structured_data

                return result

        # ----------------------------------------------------
        # Material Certificate
        # ----------------------------------------------------

        elif document_type == "MATERIAL_CERTIFICATE":

            structured_data = parse_certificate_pdf(
                file_path
            )

        # ----------------------------------------------------
        # Heat Treatment Certificate
        # ----------------------------------------------------

        elif (
            document_type
            == "HEAT_TREATMENT_CERTIFICATE"
        ):

            structured_data = parse_certificate_pdf(
                file_path
            )

        # ----------------------------------------------------
        # 지원하지 않는 문서
        # ----------------------------------------------------

        else:

            result[
                "parse_status"
            ] = "UNSUPPORTED"

            return result

        result[
            "parse_status"
        ] = "SUCCESS"

        result[
            "structured_data"
        ] = structured_data

        return result

    except Exception as error:

        result[
            "parse_status"
        ] = "ERROR"

        result[
            "error"
        ] = str(error)

        return result


# ============================================================
# 메일 하나 처리
# ============================================================

def process_message(message):
    """
    메일 하나를 처리한다.

    1. 최초/신규/후속 메일 분류
    2. 첨부파일 다운로드
    3. 문서 유형 판별
    4. Parser 실행
    """

    classification = classify_message(
        message
    )

    result = {
        "message_id": message.get(
            "message_id"
        ),
        "thread_id": message.get(
            "thread_id"
        ),
        "from": message.get(
            "from"
        ),
        "subject": message.get(
            "subject"
        ),
        "body": message.get(
            "body"
        ),
        "mail_type": classification[
            "mail_type"
        ],
        "case_id": classification[
            "case_id"
        ],
        "reason": classification[
            "reason"
        ],
        "saved_attachments": [],
        "parsed_documents": [],
    }

    if (
        classification[
            "mail_type"
        ] == "IGNORE"
    ):
        return result

    # --------------------------------------------------------
    # 첨부파일 다운로드
    # --------------------------------------------------------

    if message.get(
        "attachments"
    ):

        saved_files = (
            download_message_attachments(
                message
            )
        )

        result[
            "saved_attachments"
        ] = saved_files

        # ----------------------------------------------------
        # 모든 첨부문서 자동 Parsing
        # ----------------------------------------------------

        for file_path in saved_files:

            parsed_document = (
                parse_attachment(
                    file_path
                )
            )

            result[
                "parsed_documents"
            ].append(
                parsed_document
            )

    return result


# ============================================================
# 최근 AeroChange 메일 처리
# ============================================================

def process_recent_messages(
    max_results=10
):

    messages = get_recent_messages(
        max_results=max_results
    )

    results = []

    for message in messages:

        result = process_message(
            message
        )

        results.append(
            result
        )

    return results


# ============================================================
# 터미널 테스트 출력
# ============================================================

def print_processing_results(
    max_results=10
):

    results = process_recent_messages(
        max_results=max_results
    )

    print()

    print(
        f"AeroChange 메일 "
        f"{len(results)}건 처리"
    )

    print("=" * 70)

    if not results:

        print(
            "처리할 AeroChange 메일이 없습니다."
        )

        return

    for index, result in enumerate(
        results,
        start=1,
    ):

        print()
        print(
            f"[메일 {index}]"
        )

        print(
            f"Subject: "
            f"{result['subject']}"
        )

        print(
            f"From: "
            f"{result['from']}"
        )

        print(
            f"Thread ID: "
            f"{result['thread_id']}"
        )

        print(
            f"Mail Type: "
            f"{result['mail_type']}"
        )

        print(
            f"Case ID: "
            f"{result['case_id']}"
        )

        print(
            f"Reason: "
            f"{result['reason']}"
        )

        print()
        print(
            "[첨부파일]"
        )

        if result[
            "saved_attachments"
        ]:

            for file_path in result[
                "saved_attachments"
            ]:

                print(
                    f"- {file_path}"
                )

        else:

            print("- 없음")

        print()
        print(
            "[문서 분석 결과]"
        )

        if not result[
            "parsed_documents"
        ]:

            print(
                "- 분석된 문서 없음"
            )

        for document in result[
            "parsed_documents"
        ]:

            print()

            print(
                f"파일: "
                f"{document['file_name']}"
            )

            print(
                f"문서 유형: "
                f"{document['document_type']}"
            )

            print(
                f"Parser 상태: "
                f"{document['parse_status']}"
            )

            if document[
                "parse_status"
            ] in {
                "SUCCESS",
                "WARNING",
            }:

                print(
                    "구조화 데이터:"
                )

                pprint(
                    document[
                        "structured_data"
                    ],
                    sort_dicts=False,
                )

                if (
                    document[
                        "parse_status"
                    ]
                    == "WARNING"
                ):

                    print(
                        "일부 필드 누락 또는 "
                        "본문 오류가 있습니다."
                    )

            elif (
                document[
                    "parse_status"
                ]
                == "ERROR"
            ):

                print(
                    f"Parser 오류: "
                    f"{document['error']}"
                )

            else:

                print(
                    "지원하지 않는 문서 형식"
                )

        print()
        print("-" * 70)


# ============================================================
# 직접 실행
# ============================================================

if __name__ == "__main__":

    print_processing_results(
        max_results=10
    )