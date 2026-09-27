from tools.drawing_compare import compare_revision
from tools.lot_trace import trace_affected_lots
from tools.quality_verify import verify_lots

changes = compare_revision(
    "data/rev_b.json",
    "data/rev_c.json"
)


print("===== 설계변경 분석 결과 =====")

for change in changes:
    print(
        f"{change['item']} : "
        f"{change['old']} → {change['new']}"
    )


affected_lots = trace_affected_lots(
    "data/lot.csv",
    "A1001",
    "B"
)


print("\n===== 영향 Lot =====")

for lot in affected_lots:
    print(lot)

    # 3. 품질검증
results = verify_lots(
    "data/inspection.csv",
    affected_lots,
    20.0,
    0.1
)

print("\n===== 품질검증 결과 =====")

for result in results:
    print(
        f"{result['lot_id']} : "
        f"{result['status']} "
        f"({result['reason']})"
    )