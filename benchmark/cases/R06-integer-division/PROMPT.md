# R06-integer-division: int(a / b) replaced by a // b

Refactor original.py (use integer division instead of int(a / b)). The output must stay exactly the same for every input.

Files: `original.py` (below) and `sample.csv` (normal data).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["per_unit"])
    writer.writeheader()
    for row in reader:
        row["per_unit"] = int(int(row["total_cents"]) / int(row["units"]))
        writer.writerow(row)
```
