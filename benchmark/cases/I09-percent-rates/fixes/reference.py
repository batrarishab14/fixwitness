# label: correct
# pattern: '12%' means 0.12; everything else as before
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]


def parse_rate(s):
    t = s.strip()
    return float(t[:-1]) / 100 if t.endswith("%") else float(s)

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["fee"])
    writer.writeheader()
    for row in reader:
        rate = parse_rate(row["rate"])
        row["fee"] = f"{float(row['amount']) * rate:.2f}"
        writer.writerow(row)
