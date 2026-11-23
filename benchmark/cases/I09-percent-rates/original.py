import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["fee"])
    writer.writeheader()
    for row in reader:
        rate = float(row["rate"])
        row["fee"] = f"{float(row['amount']) * rate:.2f}"
        writer.writerow(row)
