# R03-dedupe: de-duplication rewritten with a dict

Refactor original.py (simplify the de-duplication loop). The output must stay exactly the same for every input.

Files: `original.py` (below) and `sample.csv` (normal data).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    seen = set()
    for row in reader:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        writer.writerow(row)
```
