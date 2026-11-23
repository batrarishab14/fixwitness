#!/usr/bin/env bash
# Normalise the region column: trim and collapse whitespace, upper-case.
# Usage: bash normalize_regions_fix_safe.sh input.csv output.csv
set -u
in="$1"; out="$2"
{
  IFS= read -r header
  printf '%s\n' "$header"
  while IFS=, read -r id region amount; do
    # fix: no eval. Keep the whitespace handling eval used to give us for free.
    region=$(printf '%s' "$region" | tr -s '[:space:]' ' ')
    region="${region# }"
    region="${region% }"
    region=$(printf '%s' "$region" | tr '[:lower:]' '[:upper:]')
    printf '%s,%s,%s\n' "$id" "$region" "$amount"
  done
} < "$in" > "$out"
