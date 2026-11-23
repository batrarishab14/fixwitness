# label: correct
# pattern: same Decimal half-up rounding, moved into a helper
import csv
from decimal import ROUND_HALF_UP, Decimal
import sys

src, dst = sys.argv[1], sys.argv[2]

CENT = Decimal("0.01")


def two_dp(text):
    return str(Decimal(text.strip()).quantize(CENT, rounding=ROUND_HALF_UP))

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_2dp"])
    writer.writeheader()
    for row in reader:
        row["amount_2dp"] = two_dp(row["amount"])
        writer.writerow(row)
