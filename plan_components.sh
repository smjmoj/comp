#!/usr/bin/env bash

set -euo pipefail

# === CONFIG ===
COMPONENT_DIR="./project_dir/components"
USE_DOCKER=${USE_DOCKER:-false}
DOCKER_IMAGE_NAME="tf-dep-planner"
PYTHON_SCRIPT="grouped_sort.py"

# === Resolve components to paths ===
if [[ $# -gt 0 ]]; then
  COMPONENTS=("$@")
else
  COMPONENTS=($(ls -1 "$COMPONENT_DIR"))
fi

COMPONENT_PATHS=()
for name in "${COMPONENTS[@]}"; do
  full_path="$COMPONENT_DIR/$name"
  if [[ -d "$full_path" ]]; then
    COMPONENT_PATHS+=("$full_path")
  else
    echo "Warning: component '$name' not found in $COMPONENT_DIR"
  fi
done

if [[ ${#COMPONENT_PATHS[@]} -eq 0 ]]; then
  echo "No valid components found. Exiting."
  exit 1
fi

# === Run planner ===
if [[ "$USE_DOCKER" == "true" ]]; then
  echo "[*] Running inside Docker"
  docker run --rm -v "$(pwd):/mnt" "$DOCKER_IMAGE_NAME" \
    "${COMPONENT_PATHS[@]/#/.\/}" | tee execution_plan.yaml
else
  echo "[*] Running locally via Python"
  python "$PYTHON_SCRIPT" "${COMPONENT_PATHS[@]}" | tee execution_plan.yaml
fi
