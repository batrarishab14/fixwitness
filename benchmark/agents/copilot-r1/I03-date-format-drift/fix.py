import csv
from datetime import datetime
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["month"])
    writer.writeheader()

    for row in reader:
        raw_day = row["day"]

        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                day = datetime.strptime(raw_day, fmt)
                break
            except ValueError:
                pass
        else:
            raise ValueError(f"time data {raw_day!r} does not match expected formats")

        row["month"] = day.strftime("%Y-%m")
        writer.writerow(row)
