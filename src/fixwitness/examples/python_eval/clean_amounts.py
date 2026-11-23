"""Normalise the amount column of a payments CSV and add amount_cents.

Usage: python3 clean_amounts.py input.csv output.csv
"""
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]
with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = eval(row["amount"])  # finding: code injection (CWE-95), eval on untrusted input
        row["amount"] = amount
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
