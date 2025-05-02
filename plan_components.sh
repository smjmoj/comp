#!/usr/bin/env bash

set -euo pipefail

COMPONENT_DIR="$(pwd)/components"
USE_DOCKER=${USE_DOCKER:-false}
DOCKER_IMAGE_NAME="tf-dep-planner"
DOCKERFILE="./Dockerfile"
PYTHON_SCRIPT="grouped_sort.py"
YAML_FILE=""

# Parse args
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yaml)
      YAML_FILE="$2"
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

# Determine component list
if [[ -n "$YAML_FILE" ]]; then
  if ! command -v yq &> /dev/null; then
    echo "Error: 'yq' required for --yaml"
    exit 1
  fi
  echo "[*] Reading components from $YAML_FILE"
  COMPONENTS=($(yq '.components[]' "$YAML_FILE"))
elif [[ ${#ARGS[@]} -gt 0 ]]; then
  COMPONENTS=("${ARGS[@]}")
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
  echo "No valid components found"
  exit 1
fi

# Run dependency planner
if [[ "$USE_DOCKER" == "true" ]]; then
  if ! docker image inspect "$DOCKER_IMAGE_NAME" &> /dev/null; then
    echo "[*] Building Docker image $DOCKER_IMAGE_NAME..."
    docker build -t "$DOCKER_IMAGE_NAME" -f "$DOCKERFILE" .
  fi
  docker run --rm -v "$(pwd):/mnt" "$DOCKER_IMAGE_NAME" \
    "${COMPONENT_PATHS[@]/#/.\/}" | tee execution_plan.yaml
else
  echo "[*] Running locally"
  python "$PYTHON_SCRIPT" "${COMPONENT_PATHS[@]}" | tee execution_plan.yaml
fi
