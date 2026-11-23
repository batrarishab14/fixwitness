# label: correct
# pattern: no eval; keep the trim-and-collapse behaviour eval gave for free
#!/usr/bin/env bash
# Normalise the region column: trim and collapse whitespace, upper-case.
set -u
in="$1"; out="$2"
{
  IFS= read -r header
  printf '%s\n' "$header"
  while IFS=, read -r id region amount; do
    region=$(printf '%s' "$region" | tr -s '[:space:]' ' ')
    region="${region# }"
    region="${region% }"
    region=$(printf '%s' "$region" | tr '[:lower:]' '[:upper:]')
    printf '%s,%s,%s\n' "$id" "$region" "$amount"
  done
} < "$in" > "$out"
