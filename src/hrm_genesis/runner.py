from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from hrm_coordination import (
    Mutation,
    ProvenanceContribution,
    ReplayLedger,
    ResourceRef,
    ScheduleSpec,
    StateAuthority,
    TemporalOrchestrator,
    TransactionFabric,
    TransactionProposal,
)
from hrm_coordination.seeds import SeedBank

from .config import GenesisConfig
from .interfaces.authorities import (
    AuthorityRegistration,
    GENESIS_SYSTEM_AUTHORITY,
    GENESIS_TICK_RESOURCE,
    validate_registrations,
)
from .interfaces.snapshots import GenesisSnapshot, capture_snapshot


CLOCK_SCHEDULE_ID = "genesis.clock"


class GenesisSimulation:
    """G0 integration shell.

    The Stage-1 StateAuthority used here is intentionally a blank integration
    fixture. It owns only the logical Genesis tick marker. G1 must introduce real
    physical-world authorities rather than storing world semantics in this fixture.
    """

    def __init__(self, config: GenesisConfig):
        self.config = config
        self.seed_bank = SeedBank(config.master_seed)

        system = StateAuthority(
            GENESIS_SYSTEM_AUTHORITY,
            {GENESIS_TICK_RESOURCE: 0},
        )
        self.authorities = [system]
        registrations = tuple(
            AuthorityRegistration(authority.authority_id, authority.port())
            for authority in self.authorities
        )
        validate_registrations(registrations)

        self.ledger = ReplayLedger(config.fingerprint())
        for authority in self.authorities:
            state = {
                resource_id: snapshot.value
                for resource_id, snapshot in authority.port().snapshot().items()
            }
            self.ledger.register_genesis(authority.authority_id, state)

        self.fabric = TransactionFabric(
            config.master_seed,
            [item.port for item in registrations],
            self.ledger,
            max_parallel_domains=config.max_parallel_domains,
        )
        self.orchestrator = TemporalOrchestrator(
            self.fabric,
            contract_dt=config.contract_dt,
            start_epoch=0,
        )
        self._register_clock()

    @classmethod
    def _from_restored(
        cls,
        *,
        config: GenesisConfig,
        orchestrator_state: dict[str, Any],
        fabric: TransactionFabric,
        ledger: ReplayLedger,
        authorities: list[StateAuthority],
    ) -> "GenesisSimulation":
        obj = cls.__new__(cls)
        obj.config = config
        obj.seed_bank = SeedBank(config.master_seed)
        obj.authorities = authorities
        obj.ledger = ledger
        obj.fabric = fabric

        restored_dt = Fraction(
            int(orchestrator_state["contract_dt_numerator"]),
            int(orchestrator_state["contract_dt_denominator"]),
        )
        if restored_dt != config.contract_dt:
            raise ValueError("checkpoint contract_dt does not match GenesisConfig")

        obj.orchestrator = TemporalOrchestrator(
            fabric,
            contract_dt=restored_dt,
            start_epoch=int(orchestrator_state["epoch"]),
        )
        obj._register_clock()
        return obj

    def _register_clock(self) -> None:
        self.orchestrator.register(
            ScheduleSpec(
                authority_id=CLOCK_SCHEDULE_ID,
                period_ticks=1,
                phase_ticks=0,
                feedback_lag_ticks=1,
            ),
            self._clock_callback,
        )

    def _clock_callback(self, ctx, fabric: TransactionFabric):
        current = fabric.projection(
            GENESIS_SYSTEM_AUTHORITY,
            [GENESIS_TICK_RESOURCE],
        )[GENESIS_TICK_RESOURCE]
        next_value = int(current.value) + 1
        proposal_id = f"g0-clock-{ctx.epoch:012d}"
        transaction_id = f"g0-tx-clock-{ctx.epoch:012d}"
        return [
            TransactionProposal(
                proposal_id=proposal_id,
                transaction_id=transaction_id,
                proposer_id=CLOCK_SCHEDULE_ID,
                logical_epoch=ctx.epoch,
                mutations=(
                    Mutation(
                        ref=ResourceRef(
                            GENESIS_SYSTEM_AUTHORITY,
                            GENESIS_TICK_RESOURCE,
                        ),
                        expected_version=current.version,
                        new_value=next_value,
                    ),
                ),
                provenance=ProvenanceContribution(
                    causal_parents=(),
                    source_authority=GENESIS_SYSTEM_AUTHORITY,
                    operation="GENESIS_CLOCK_TICK",
                ),
                fallible_claims={},
            )
        ]

    def run(self, ticks: int):
        if ticks < 0:
            raise ValueError("ticks must be >= 0")
        return self.orchestrator.run(ticks)

    def snapshot(self) -> GenesisSnapshot:
        return capture_snapshot(
            epoch=self.orchestrator.epoch,
            ledger_digest=self.ledger.digest(),
            fabric=self.fabric,
        )

    def write_checkpoint(self, path: str | Path) -> None:
        from .checkpoint import write_genesis_checkpoint

        write_genesis_checkpoint(path, self)

    @classmethod
    def load_checkpoint(cls, path: str | Path, config: GenesisConfig) -> "GenesisSimulation":
        from .checkpoint import load_genesis_checkpoint

        return load_genesis_checkpoint(path, config)
