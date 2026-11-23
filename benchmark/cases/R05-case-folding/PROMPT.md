# R05-case-folding: lower() replaced by casefold()

Refactor original.py (make the key normalisation 'more correct for Unicode'). The output must stay exactly the same for every input.

Files: `original.py` (below) and `sample.csv` (normal data).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["city_key"])
    writer.writeheader()
    for row in reader:
        row["city_key"] = row["city"].strip().lower()
        writer.writerow(row)
```
