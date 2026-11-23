#!/usr/bin/env bash
# Normalise the region column: trim and collapse whitespace, upper-case.
# Usage: bash normalize_regions_fix_naive.sh input.csv output.csv
set -u
in="$1"; out="$2"
{
  IFS= read -r header
  printf '%s\n' "$header"
  while IFS=, read -r id region amount; do
    region=$(printf '%s' "$region" | tr '[:lower:]' '[:upper:]')   # fix: eval removed
    printf '%s,%s,%s\n' "$id" "$region" "$amount"
  done
} < "$in" > "$out"
