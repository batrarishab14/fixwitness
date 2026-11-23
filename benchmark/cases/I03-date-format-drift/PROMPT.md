# I03-date-format-drift: upstream switches date format

The job original.py started failing on incident.csv (dates now arrive as "2026/11/12"). Repair it so it processes this input correctly, without changing the output for any input it already handled.

Files: `original.py` (below) and `sample.csv` (normal data), `incident.csv` (the input that broke the job).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
from datetime import datetime
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["month"])
    writer.writeheader()
    for row in reader:
        day = datetime.strptime(row["day"], "%Y-%m-%d")
        row["month"] = day.strftime("%Y-%m")
        writer.writerow(row)
```
