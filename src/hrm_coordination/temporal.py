from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Iterable, Sequence

from .fabric import TransactionFabric
from .model import TransactionProposal, ResolutionBatch


@dataclass(frozen=True)
class ScheduleSpec:
    authority_id: str
    period_ticks: int
    phase_ticks: int = 0
    feedback_lag_ticks: int = 1

    def __post_init__(self):
        if self.period_ticks <= 0:
            raise ValueError("period_ticks must be positive")
        if self.phase_ticks < 0 or self.phase_ticks >= self.period_ticks:
            raise ValueError("phase_ticks outside cadence")
        if self.feedback_lag_ticks != 1:
            # Stage 1 enforces exactly one epoch of lag (ledger: causal parents must
            # be prior-epoch evidence). A larger declared lag would not be enforced,
            # so it is rejected rather than accepted as a promise nothing keeps.
            raise ValueError(
                "feedback_lag_ticks must be 1 in Stage 1 (only a one-epoch lag is enforced)"
            )

    def due(self, epoch: int) -> bool:
        return epoch >= self.phase_ticks and (epoch - self.phase_ticks) % self.period_ticks == 0


@dataclass(frozen=True)
class EpochContext:
    epoch: int
    contract_dt: Fraction
    feedback_lag_ticks: int


ProposalCallback = Callable[[EpochContext, TransactionFabric], Sequence[TransactionProposal]]


class TemporalOrchestrator:
    """Logical scheduler. Due systems read the same pre-commit epoch state.

    Call order may vary; all proposals are collected before one resolution boundary,
    preventing same-epoch recursive read-after-write priority.
    """

    def __init__(self, fabric: TransactionFabric, contract_dt: Fraction = Fraction(1, 1), start_epoch: int = 0):
        if contract_dt <= 0:
            raise ValueError("contract_dt must be positive")
        self.fabric = fabric
        self.contract_dt = contract_dt
        self.epoch = int(start_epoch)
        self._schedules: dict[str, tuple[ScheduleSpec, ProposalCallback]] = {}

    def register(self, spec: ScheduleSpec, callback: ProposalCallback) -> None:
        if spec.authority_id in self._schedules:
            raise ValueError(f"duplicate schedule authority {spec.authority_id}")
        self._schedules[spec.authority_id] = (spec, callback)

    def due_authorities(self) -> tuple[str, ...]:
        return tuple(sorted(aid for aid, (spec, _) in self._schedules.items() if spec.due(self.epoch)))

    def step(self, worker_order: Iterable[str] | None = None) -> ResolutionBatch:
        due = set(self.due_authorities())
        if worker_order is None:
            order = sorted(due)
        else:
            supplied = [aid for aid in worker_order if aid in due]
            if set(supplied) != due or len(supplied) != len(due):
                raise ValueError("worker_order must contain every due authority exactly once")
            order = supplied

        proposals: list[TransactionProposal] = []
        for aid in order:
            spec, callback = self._schedules[aid]
            ctx = EpochContext(self.epoch, self.contract_dt, spec.feedback_lag_ticks)
            proposals.extend(callback(ctx, self.fabric))
        batch = self.fabric.resolve(self.epoch, proposals)
        self.epoch += 1
        return batch

    def run(self, ticks: int, order_fn: Callable[[tuple[str, ...], int], Iterable[str]] | None = None) -> tuple[ResolutionBatch, ...]:
        out = []
        for _ in range(ticks):
            due = self.due_authorities()
            order = None if order_fn is None else order_fn(due, self.epoch)
            out.append(self.step(order))
        return tuple(out)

    def checkpoint(self) -> dict:
        return {
            "epoch": self.epoch,
            "contract_dt_numerator": self.contract_dt.numerator,
            "contract_dt_denominator": self.contract_dt.denominator,
            "schedules": [
                {
                    "authority_id": spec.authority_id,
                    "period_ticks": spec.period_ticks,
                    "phase_ticks": spec.phase_ticks,
                    "feedback_lag_ticks": spec.feedback_lag_ticks,
                }
                for spec, _ in sorted(self._schedules.values(), key=lambda pair: pair[0].authority_id)
            ],
        }
