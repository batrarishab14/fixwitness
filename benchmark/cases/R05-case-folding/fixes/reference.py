# label: correct
# pattern: same lower(), moved into a helper
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]


def city_key(s):
    return s.strip().lower()

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["city_key"])
    writer.writeheader()
    for row in reader:
        row["city_key"] = city_key(row["city"])
        writer.writerow(row)
