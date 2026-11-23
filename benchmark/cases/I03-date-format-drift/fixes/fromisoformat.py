# label: wrong
# pattern: stricter parser: fromisoformat rejects unpadded dates the job accepted
import csv
from datetime import datetime
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["month"])
    writer.writeheader()
    for row in reader:
        day = datetime.fromisoformat(row["day"].replace("/", "-"))
        row["month"] = day.strftime("%Y-%m")
        writer.writerow(row)
