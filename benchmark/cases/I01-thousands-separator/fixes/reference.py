# label: correct
# pattern: accept thousands separators only; everything else parsed as before
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]
import re

THOUSANDS = re.compile(r"\s*[+-]?\d{1,3}(,\d{3})+(\.\d+)?\s*")


def parse(s):
    if THOUSANDS.fullmatch(s):
        s = s.replace(",", "")
    return float(s)


with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = parse(row["amount"])
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
