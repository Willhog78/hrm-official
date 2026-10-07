#!/bin/sh
# G10.3/G10.4 Agentus multiseed experiment for a log-only runner (Railway).
# Each run prints one CAPACITY_RESULT JSON line; read results from the log.
cd "$(dirname "$0")/../.."
export PYTHONPATH=src:.
PARALLEL="${HRM_PARALLEL:-3}"
SEEDS="${HRM_SEEDS:-agentus-demography-a agentus-demography-b agentus-demography-c agentus-demography-d}"
if [ "$SEEDS" = "all" ]; then
  SEEDS="$(python -c 'import sys; sys.path.insert(0, "experiments/genesis"); from run_agentus_capacity_multiseed import SEEDS; print(" ".join(SEEDS))')"
fi
echo "CAPACITY_START: parallel=$PARALLEL seeds=$(echo $SEEDS | wc -w)"
for arm in ${HRM_ARMS:-v0 v1 plant_diet no_interactions no_recall}; do
  for seed in $SEEDS; do
    echo "$arm $seed"
  done
done | xargs -P "$PARALLEL" -L 1 sh -c 'python experiments/genesis/run_agentus_capacity_multiseed.py --arm "$0" --seed "$1" || echo "CAPACITY_FAILED: $0 $1"'
echo "CAPACITY_ALL_DONE"
