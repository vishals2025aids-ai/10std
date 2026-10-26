import csv
import config
import pipeline


def run_evaluation(csv_path=config.TESTS_CSV):
    if not csv_path.exists():
        print(f"[ERROR] {csv_path} not found.")
        return

    total = 0
    top1_hits = 0
    top3_hits = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = (row.get("query") or "").strip()
            expected_subject = (row.get("subject") or "").strip().lower()
            expected_page = int(row.get("page") or 0)
            if not query or not expected_page:
                continue

            total += 1
            res = pipeline.resolve(query)
            pages = res.get("pages", [])

            matched_ranks = [
                idx
                for idx, p in enumerate(pages[:3])
                if p["subject"].lower() == expected_subject and int(p["page"]) == expected_page
            ]

            if matched_ranks and matched_ranks[0] == 0:
                top1_hits += 1
            if matched_ranks:
                top3_hits += 1

    if total == 0:
        print("No valid test rows found in tests.csv.")
        return

    top1_acc = (top1_hits / total) * 100
    top3_acc = (top3_hits / total) * 100
    print(f"Evaluated {total} queries from {csv_path.name}:")
    print(f"  Top-1 Accuracy: {top1_hits}/{total} ({top1_acc:.1f}%)")
    print(f"  Top-3 Accuracy: {top3_hits}/{total} ({top3_acc:.1f}%)")


if __name__ == "__main__":
    run_evaluation()
