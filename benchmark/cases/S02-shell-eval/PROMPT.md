# S02-shell-eval: eval echo in a shell normaliser

A scanner flagged original.sh: 'eval echo $region' allows command injection (CWE-78). Fix it without changing the output for any valid input.

Files: `original.sh` (below) and `sample.csv` (normal data).
The job is run as: `bash {script} {input} {output}`

Reply with the complete fixed file only.

```bash
#!/usr/bin/env bash
# Normalise the region column: trim and collapse whitespace, upper-case.
set -u
in="$1"; out="$2"
{
  IFS= read -r header
  printf '%s\n' "$header"
  while IFS=, read -r id region amount; do
    region=$(eval echo $region)
    region=$(printf '%s' "$region" | tr '[:lower:]' '[:upper:]')
    printf '%s,%s,%s\n' "$id" "$region" "$amount"
  done
} < "$in" > "$out"
```
