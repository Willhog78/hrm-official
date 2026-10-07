#!/bin/sh
# Run one test tier on a log-only runner (Railway) or locally.
#   HRM_TIER=fast                      micro + smoke (default; about 30 s)
#   HRM_TIER=smoke                     smoke only
#   HRM_TIER=diagnostic HRM_TIER_ARGS="infant --days 365"
#   HRM_TIER=full                      the existing 20-seed x 730-day validation
# Exit status is non-zero when a FAIL check trips.
cd "$(dirname "$0")/../.."
export PYTHONPATH=src:.
TIER="${HRM_TIER:-fast}"
echo "TIER_START: $TIER ${HRM_TIER_ARGS:-}"
# shellcheck disable=SC2086
python -m qualification.genesis.tiers "$TIER" ${HRM_TIER_ARGS:-}
STATUS=$?
echo "TIER_DONE: $TIER status=$STATUS"
exit $STATUS
