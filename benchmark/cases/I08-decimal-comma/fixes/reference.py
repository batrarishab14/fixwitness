# label: correct
# pattern: a single comma followed by 1-2 digits is a decimal comma
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]
import re

DECIMAL_COMMA = re.compile(r"\s*-?\d+,\d{1,2}\s*")


def parse(s):
    if DECIMAL_COMMA.fullmatch(s):
        s = s.replace(",", ".")
    return float(s)


with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = parse(row["amount"])
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
