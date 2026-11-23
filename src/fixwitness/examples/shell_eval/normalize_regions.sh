#!/usr/bin/env bash
# Normalise the region column: trim and collapse whitespace, upper-case.
# Usage: bash normalize_regions.sh input.csv output.csv
set -u
in="$1"; out="$2"
{
  IFS= read -r header
  printf '%s\n' "$header"
  while IFS=, read -r id region amount; do
    region=$(eval echo $region)   # finding: command injection (CWE-78), eval on untrusted input
    region=$(printf '%s' "$region" | tr '[:lower:]' '[:upper:]')
    printf '%s,%s,%s\n' "$id" "$region" "$amount"
  done
} < "$in" > "$out"
