# label: wrong
# pattern: silent wrong value: unparseable amounts become 0
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        try:
            amount = float(row["amount"])
        except ValueError:
            amount = 0.0
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
