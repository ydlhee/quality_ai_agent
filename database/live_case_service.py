import json

import re

import sqlite3

from pathlib import Path



from database.mail_case_repository import (

    get_case_id_by_thread,

    save_thread_case_mapping,

)





DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"





# ============================================================

# 공통 함수

# ============================================================



def _connect():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn





def _successful_documents(mail_result):

    """

    Parser가 SUCCESS인 문서만 반환한다.

    신규 Case 생성 시 WARNING / ERROR / UNSUPPORTED 문서는

    자동 등록하지 않는다.

    """

    return [

        document

        for document in mail_result.get("parsed_documents", [])

        if document.get("parse_status") == "SUCCESS"

        and document.get("structured_data")

    ]





def _documents_by_type(documents):

    grouped = {}



    for document in documents:

        document_type = document.get("document_type")



        grouped.setdefault(

            document_type,

            [],

        ).append(document)
