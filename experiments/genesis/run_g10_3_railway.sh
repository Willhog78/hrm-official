#!/bin/sh
# G10.3 capacity v1 multiseed experiment for a log-only runner (Railway).
# Each run prints one CAPACITY_RESULT JSON line; read results from the log.
cd "$(dirname "$0")/../.."
export PYTHONPATH=src:.
PARALLEL="${HRM_PARALLEL:-3}"
echo "CAPACITY_START: parallel=$PARALLEL"
for arm in ${HRM_ARMS:-v0 v1 plant_diet no_interactions no_recall}; do
  for seed in a b c d; do
    echo "$arm agentus-demography-$seed"
  done
done | xargs -P "$PARALLEL" -L 1 sh -c 'python experiments/genesis/run_agentus_capacity_multiseed.py --arm "$0" --seed "$1" || echo "CAPACITY_FAILED: $0 $1"'
echo "CAPACITY_ALL_DONE"
