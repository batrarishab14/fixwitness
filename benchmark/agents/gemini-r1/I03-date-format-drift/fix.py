import csv
from datetime import datetime
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["month"])
    writer.writeheader()
    for row in reader:
        day_str = row["day"].strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                day = datetime.strptime(day_str, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Unrecognized date format: {day_str}")
        row["month"] = day.strftime("%Y-%m")
        writer.writerow(row)
