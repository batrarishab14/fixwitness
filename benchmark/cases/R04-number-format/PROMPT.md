# R04-number-format: f-string formatting replaced

Refactor original.py (remove the f-string formatting). The output must stay exactly the same for every input.

Files: `original.py` (below) and `sample.csv` (normal data).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["total"])
    writer.writeheader()
    for row in reader:
        total = float(row["price"]) * int(row["qty"])
        row["total"] = f"{total:.2f}"
        writer.writerow(row)
```
