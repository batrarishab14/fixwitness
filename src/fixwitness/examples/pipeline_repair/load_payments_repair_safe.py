"""Load a payments extract and add amount_cents.

Usage: python3 load_payments_repair_safe.py input.csv output.csv
"""
import csv
import re
import sys

THOUSANDS = re.compile(r"\s*[+-]?\d{1,3}(,\d{3})+(\.\d+)?\s*")


def parse_amount(text):
    """Accept thousands separators ("1,250.00"); everything else is parsed exactly as before."""
    if THOUSANDS.fullmatch(text):
        text = text.replace(",", "")
    return float(text)


src, dst = sys.argv[1], sys.argv[2]
with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = parse_amount(row["amount"])  # repair
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
