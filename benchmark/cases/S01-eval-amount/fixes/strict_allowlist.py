# label: wrong
# pattern: allowlist too strict: valid formats such as 1e3 or +7 are rejected
import re


def parse(s):
    s = s.strip()
    if not re.fullmatch(r"-?\d+(\.\d+)?", s):
        raise ValueError(f"bad amount {s!r}")
    return float(s) if "." in s else int(s)


import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = parse(row["amount"])
        row["amount"] = amount
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
