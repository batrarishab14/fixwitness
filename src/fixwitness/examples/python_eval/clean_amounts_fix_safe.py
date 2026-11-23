"""Normalise the amount column of a payments CSV and add amount_cents.

Usage: python3 clean_amounts_fix_safe.py input.csv output.csv
"""
import csv
import sys


def parse_amount(text):
    """Parse a numeric literal without executing code. Whole numbers stay integers."""
    s = text.strip()
    try:
        return int(s, 0)
    except ValueError:
        return float(s)


src, dst = sys.argv[1], sys.argv[2]
with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = parse_amount(row["amount"])  # fix: no eval
        row["amount"] = amount
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
