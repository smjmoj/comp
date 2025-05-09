#!/bin/bash

## Run parallel batches of terraform components.
## Requires input in the form of a yaml file.
## As output by grouped_sort.py / plan_components.sh

##  execution_plan.yaml
##
##  execution_plan:
##    - [vpc, dns, bastion]
##    - [app, database]
##    - [cache]

##  ./run_tf_batches.sh                   # Run normally, continue on error
##  ./run_tf_batches.sh --fail-fast      # Stop after first failed batch
##  ./run_tf_batches.sh --yaml myplan.yaml  # Use custom YAML file


set -e

# === CONFIGURATION ===
YAML_FILE="execution_plan.yaml"
LOG_DIR="./logs"
FAIL_FAST=false

# === ARGUMENT PARSING ===
while [[ $# -gt 0 ]]; do
  case $1 in
    --fail-fast)
      FAIL_FAST=true
      shift
      ;;
    --yaml)
      YAML_FILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

mkdir -p "$LOG_DIR"

# === FUNCTION TO RUN TERRAFORM IN A SUBSHELL ===
run_terraform() {
  local ENV_DIR=$1
  local LOG_FILE="$LOG_DIR/${ENV_DIR}.log"

  (
    echo "[$ENV_DIR] Starting at $(date)" | tee -a "$LOG_FILE"
    cd "$ENV_DIR" || { echo "[$ENV_DIR] Directory not found" | tee -a "$LOG_FILE"; exit 1; }

    echo "[$ENV_DIR] terraform init" | tee -a "$LOG_FILE"
    terraform init >> "$LOG_FILE" 2>&1 || exit 1

    echo "[$ENV_DIR] terraform plan" | tee -a "$LOG_FILE"
    terraform plan >> "$LOG_FILE" 2>&1 || exit 1

    echo "[$ENV_DIR] terraform apply" | tee -a "$LOG_FILE"
    terraform apply -auto-approve >> "$LOG_FILE" 2>&1 || exit 1

    echo "[$ENV_DIR] Completed successfully at $(date)" | tee -a "$LOG_FILE"
  ) &
  echo $!  # Return the PID of the background job
}

# === MAIN EXECUTION LOOP ===
BATCH_COUNT=$(yq '.execution_plan | length' "$YAML_FILE")

for ((i=0; i<BATCH_COUNT; i++)); do
  echo -e "\n Starting batch $((i+1))..."

  DIRS=($(yq ".execution_plan[$i][]" "$YAML_FILE"))
  declare -a PIDS=()
  declare -A PID_TO_DIR=()

  # Start subshells
  for DIR in "${DIRS[@]}"; do
    PID=$(run_terraform "$DIR")
    PIDS+=("$PID")
    PID_TO_DIR["$PID"]="$DIR"
  done

  # Wait and track exit codes
  BATCH_FAILED=false
  for PID in "${PIDS[@]}"; do
    wait "$PID"
    STATUS=$?
    DIR="${PID_TO_DIR[$PID]}"
    if [[ $STATUS -ne 0 ]]; then
      echo "Error in $DIR (PID $PID). Exit code: $STATUS"
      BATCH_FAILED=true
    fi
  done

  if $BATCH_FAILED; then
    echo "Batch $((i+1)) failed."
    if $FAIL_FAST; then
      echo "Stopping execution due to --fail-fast."
      exit 1
    fi
  else
    echo "Batch $((i+1)) completed successfully."
  fi
done

echo -e "\n All batches completed."
