# label: wrong
# pattern: silent data loss: rows with other date formats are skipped
import csv
from datetime import datetime
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["month"])
    writer.writeheader()
    for row in reader:
        try:
            day = datetime.strptime(row["day"], "%Y-%m-%d")
        except ValueError:
            continue
        row["month"] = day.strftime("%Y-%m")
        writer.writerow(row)
