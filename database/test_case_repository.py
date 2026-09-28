from case_repository import get_case


CASE_IDS = [
    "CASE-001",
    "CASE-002",
    "CASE-003",
]


def test_cases():
    for case_id in CASE_IDS:
        data = get_case(case_id)

        print("=" * 60)
        print(f"Case ID: {case_id}")

        if data is None:
            print("Case를 찾을 수 없습니다.")
            continue

        case = data["case"]
        documents = data["documents"]

        inspection_documents = [
            document
            for document in documents
            if document["document_type"]
            == "INSPECTION_REPORT"
        ]

        drawing_documents = [
            document
            for document in documents
            if document["document_type"]
            == "DRAWING"
        ]

        supplemental_documents = [
            document
            for document in documents
            if document["document_stage"]
            == "SUPPLEMENTAL"
        ]

        all_structured = all(
            document["structured_data"] is not None
            for document in documents
        )

        print(f"Part: {case['part_no']}")
        print(f"PO: {case['po_no']}")
        print(f"Lot: {case['lot_no']}")
        print(f"Supplier: {case['supplier_name']}")

        print(
            f"도면 문서 수: "
            f"{len(drawing_documents)}"
        )

        print(
            f"검사성적서 수: "
            f"{len(inspection_documents)}"
        )

        print(
            f"보완문서 수: "
            f"{len(supplemental_documents)}"
        )

        print(
            "보완메일 존재: "
            f"{data['supplemental_email'] is not None}"
        )

        print(
            "모든 현재 문서 구조화 완료: "
            f"{all_structured}"
        )

        print("현재 등록 문서:")

        for document in documents:
            print(
                f"  - {document['file_name']} "
                f"[{document['document_stage']}]"
            )


if __name__ == "__main__":
    test_cases()