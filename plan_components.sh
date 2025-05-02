#!/usr/bin/env bash

set -euo pipefail

# === CONFIG ===
COMPONENT_DIR="./project_dir/components"
USE_DOCKER=${USE_DOCKER:-false}
DOCKER_IMAGE_NAME="tf-dep-planner"
DOCKERFILE="./Dockerfile"
PYTHON_SCRIPT="grouped_sort.py"
YAML_FILE=""

# === PARSE ARGS ===
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

# === Resolve components from YAML or CLI args or filesystem ===
if [[ -n "$YAML_FILE" ]]; then
  if ! command -v yq &> /dev/null; then
    echo "Error: 'yq' is required to parse YAML. Install it via 'brew install yq' or 'sudo snap install yq'"
    exit 1
  fi
  echo "[*] Reading component list from YAML file: $YAML_FILE"
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
  echo "No valid components found. Exiting."
  exit 1
fi

# === Run planner ===
if [[ "$USE_DOCKER" == "true" ]]; then
  echo "[*] Running inside Docker"
  if ! docker image inspect "$DOCKER_IMAGE_NAME" > /dev/null 2>&1; then
    echo "[*] Docker image '$DOCKER_IMAGE_NAME' not found. Building it now..."
    docker build -t "$DOCKER_IMAGE_NAME" -f "$DOCKERFILE" .
  fi

  docker run --rm -v "$(pwd):/mnt" "$DOCKER_IMAGE_NAME" \
    "${COMPONENT_PATHS[@]/#/.\/}" | tee execution_plan.yaml
else
  echo "[*] Running locally via Python"
  python "$PYTHON_SCRIPT" "${COMPONENT_PATHS[@]}" | tee execution_plan.yaml
fi
