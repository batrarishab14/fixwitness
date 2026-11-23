"""Load a payments extract and add amount_cents.

Usage: python3 load_payments.py input.csv output.csv
This job started failing when the upstream system began sending amounts like "1,250.00".
"""
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]
with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = float(row["amount"])  # ValueError on "1,250.00"
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
