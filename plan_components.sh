#!/usr/bin/env bash

#set -euo pipefail
#
## === Default Config ===
#COMPONENT_DIR="$(PWD)/components"
#USE_DOCKER=${USE_DOCKER:-false}
#DOCKER_IMAGE_NAME="tf-dep-planner"
#DOCKERFILE="./Dockerfile"
#PYTHON_SCRIPT="grouped_sort.py"
#YAML_FILE=""
#
## === Set up virtual env
#python3 -m venv venv
#source ./venv/bin/activate
#pip3 install -r requirements.txt
#
#
## === Parse arguments ===
#ARGS=()
#while [[ $# -gt 0 ]]; do
#  case "$1" in
#    --yaml)
#      YAML_FILE="$2"
#      shift 2
#      ;;
#    --component-dir)
#      COMPONENT_DIR="$2"
#      shift 2
#      ;;
#    *)
#      ARGS+=("$1")
#      shift
#      ;;
#  esac
#done
#
## === Get component names ===
#if [[ -n "$YAML_FILE" ]]; then
#  if ! command -v yq &> /dev/null; then
#    echo "Error: 'yq' is required for --yaml"
#    exit 1
#  fi
#  echo "[*] Reading components from $YAML_FILE"
#  COMPONENTS=($(yq '.components[]' "$YAML_FILE"))
#elif [[ ${#ARGS[@]} -gt 0 ]]; then
#  COMPONENTS=("${ARGS[@]}")
#else
#  COMPONENTS=($(ls -1 "$COMPONENT_DIR"))
#fi
#
## === Resolve paths ===
#COMPONENT_PATHS=()
#for name in "${COMPONENTS[@]}"; do
#  full_path="$COMPONENT_DIR/$name"
#  if [[ -d "$full_path" ]]; then
#    COMPONENT_PATHS+=("$full_path")
#  else
#    echo "Warning: component '$name' not found in $COMPONENT_DIR"
#  fi
#done
#
#if [[ ${#COMPONENT_PATHS[@]} -eq 0 ]]; then
#  echo "No valid components found"
#  exit 1
#fi
#

#!/bin/bash

# Print help message
usage() {
    echo "Usage: $0 -y <components.yaml> -d <component_dir1> [<component_dir2> ...] [-v]"
    echo
    echo "Options:"
    echo "  -y <yaml_file>        YAML file specifying components to include"
    echo "  -d <directories...>   One or more component directories to scan"
    echo "  -v                    Enable verbose/debug output"
    echo "  -h                    Show this help message"
    exit 1
}

## === Default Config ===
USE_DOCKER=${USE_DOCKER:-false}
DOCKER_IMAGE_NAME="tf-dep-planner"
DOCKERFILE="./Dockerfile"
VERBOSE=""
YAML_FILE=""
COMPONENT_DIRS=()

printf "[INFO] USE_DOCKER: %s" "${USE_DOCKER}"

# Parse arguments manually
while [[ $# -gt 0 ]]; do
    case "$1" in
        -y)
            YAML_FILE="$2"
            shift 2
            ;;
        -d)
            shift
            while [[ $# -gt 0 && "$1" != -* ]]; do
                COMPONENT_DIRS+=("$1")
                shift
            done
            ;;
        -v)
            VERBOSE="--verbose"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "[ERROR] Unknown argument: $1"
            usage
            ;;
    esac
done

# Check required inputs
if [[ -z "$YAML_FILE" || ${#COMPONENT_DIRS[@]} -eq 0 ]]; then
    echo "[ERROR] YAML file and component directories are required."
    usage
fi

# Locate the Python script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/grouped_sort.py"

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "[ERROR] Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

### === Execute Python script ===
if [[ "$USE_DOCKER" == "true" ]]; then
  if ! docker image inspect "$DOCKER_IMAGE_NAME" &> /dev/null; then
    printf "[INFO] Building Docker image %s..." "${DOCKER_IMAGE_NAME}"
    docker build -t "$DOCKER_IMAGE_NAME" -f "$DOCKERFILE" .
  fi
  docker run --rm -v "$(pwd):/mnt" "$DOCKER_IMAGE_NAME" \
    "${COMPONENT_DIRS[@]/#/.\/}" --yaml "$YAML_FILE" $VERBOSE | tee execution_plan.yaml
else
  printf "[INFO] Running locally"
  source ./setup_venv.sh
  pip install -r requirements.txt
  python3 "$PYTHON_SCRIPT" "${COMPONENT_DIRS[@]}" --yaml "$YAML_FILE" $VERBOSE | tee execution_plan.yaml
fi
