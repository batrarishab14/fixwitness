import csv
from datetime import datetime
import sys

src, dst = sys.argv[1], sys.argv[2]


def parse_day(text):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognized date: {text!r}")


with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["month"])
    writer.writeheader()
    for row in reader:
        day = parse_day(row["day"])
        row["month"] = day.strftime("%Y-%m")
        writer.writerow(row)
