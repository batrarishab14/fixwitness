"""Load a payments extract and add amount_cents.

Usage: python3 load_payments_repair_naive.py input.csv output.csv
"""
import csv
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = float(re.sub(r"[^0-9.]", "", row["amount"]))  # repair: keep only digits and dots
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
