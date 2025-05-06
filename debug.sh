#!/usr/bin/env bash

find components -name '*.tf' | while read file; do
  echo "[CHECKING] $file"
  python -c "import hcl2; print(hcl2.load(open('$file')))" 2>/dev/null
done
