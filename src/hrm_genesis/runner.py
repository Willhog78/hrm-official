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
from .ecology.plants import (
    build_producer_state,
    evolve_producers,
    seed_initial_producers,
)
from .interfaces.authorities import (
    AuthorityRegistration,
    GENESIS_SYSTEM_AUTHORITY,
    GENESIS_TICK_RESOURCE,
    WORLD_AUTHORITY,
    WORLD_STATE_RESOURCE,
    MATTER_AUTHORITY,
    MATTER_STATE_RESOURCE,
    ECOLOGY_AUTHORITY,
    ECOLOGY_STATE_RESOURCE,
    validate_registrations,
)
from .interfaces.snapshots import GenesisSnapshot, capture_snapshot
from .matter.pools import build_matter_state
from .matter.transfers import evolve_matter
from .world.state import build_world_state, evolve_world


CLOCK_SCHEDULE_ID = "genesis.clock"
WORLD_SCHEDULE_ID = "world.environment"
MATTER_SCHEDULE_ID = "matter.environment"
BIOSPHERE_SCHEDULE_ID = "ecology.producers"


class GenesisSimulation:
    """Genesis runner through G2.

    World owns terrain/climate forcing. Matter owns conserved environmental
    material reservoirs. Producer ecology owns living/seed/detrital plant matter.

    When producer ecology is enabled, Matter hydrology and producer changes are
    resolved in one atomic cross-authority transaction per epoch.
    """

    def __init__(self, config: GenesisConfig):
        self.config = config
        self.seed_bank = SeedBank(config.master_seed)

        authorities = [
            StateAuthority(
                GENESIS_SYSTEM_AUTHORITY,
                {GENESIS_TICK_RESOURCE: 0},
            )
        ]

        if config.physical_world_enabled:
            world_state = build_world_state(
                width=config.world_width,
                height=config.world_height,
                ticks_per_year=config.ticks_per_year,
                master_seed=config.master_seed,
                seed_bank=self.seed_bank,
            )
            authorities.append(
                StateAuthority(WORLD_AUTHORITY, {WORLD_STATE_RESOURCE: world_state})
            )

        matter_state = None
        producer_state = None
        if config.matter_enabled:
            matter_state = build_matter_state(
                width=config.world_width,
                height=config.world_height,
                seed_bank=self.seed_bank,
            )

        if config.producer_ecology_enabled:
            if matter_state is None:
                raise ValueError("producer ecology requires Matter state")
            producer_state = build_producer_state(
                width=config.world_width,
                height=config.world_height,
            )
            matter_state, producer_state = seed_initial_producers(
                matter_state,
                producer_state,
                self.seed_bank,
            )

        if matter_state is not None:
            authorities.append(
                StateAuthority(MATTER_AUTHORITY, {MATTER_STATE_RESOURCE: matter_state})
            )

        if producer_state is not None:
            authorities.append(
                StateAuthority(ECOLOGY_AUTHORITY, {ECOLOGY_STATE_RESOURCE: producer_state})
            )

        self.authorities = authorities
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
        self._register_schedules()

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

        expected = {GENESIS_SYSTEM_AUTHORITY}
        if config.physical_world_enabled:
            expected.add(WORLD_AUTHORITY)
        if config.matter_enabled:
            expected.add(MATTER_AUTHORITY)
        if config.producer_ecology_enabled:
            expected.add(ECOLOGY_AUTHORITY)
        if set(fabric.authority_ids) != expected:
            raise ValueError("checkpoint authority set does not match GenesisConfig")

        obj.orchestrator = TemporalOrchestrator(
            fabric,
            contract_dt=restored_dt,
            start_epoch=int(orchestrator_state["epoch"]),
        )
        obj._register_schedules()
        return obj

    def _register_schedules(self) -> None:
        self.orchestrator.register(
            ScheduleSpec(CLOCK_SCHEDULE_ID, 1, 0, 1),
            self._clock_callback,
        )
        if self.config.physical_world_enabled:
            self.orchestrator.register(
                ScheduleSpec(WORLD_SCHEDULE_ID, 1, 0, 1),
                self._world_callback,
            )

        if self.config.producer_ecology_enabled:
            self.orchestrator.register(
                ScheduleSpec(BIOSPHERE_SCHEDULE_ID, 1, 0, 1),
                self._biosphere_callback,
            )
        elif self.config.matter_enabled:
            self.orchestrator.register(
                ScheduleSpec(MATTER_SCHEDULE_ID, 1, 0, 1),
                self._matter_callback,
            )

    def _clock_callback(self, ctx, fabric: TransactionFabric):
        current = fabric.projection(
            GENESIS_SYSTEM_AUTHORITY,
            [GENESIS_TICK_RESOURCE],
        )[GENESIS_TICK_RESOURCE]
        return [
            TransactionProposal(
                proposal_id=f"g0-clock-{ctx.epoch:012d}",
                transaction_id=f"g0-tx-clock-{ctx.epoch:012d}",
                proposer_id=CLOCK_SCHEDULE_ID,
                logical_epoch=ctx.epoch,
                mutations=(
                    Mutation(
                        ref=ResourceRef(GENESIS_SYSTEM_AUTHORITY, GENESIS_TICK_RESOURCE),
                        expected_version=current.version,
                        new_value=int(current.value) + 1,
                    ),
                ),
                provenance=ProvenanceContribution(
                    source_authority=GENESIS_SYSTEM_AUTHORITY,
                    operation="GENESIS_CLOCK_TICK",
                ),
            )
        ]

    def _world_callback(self, ctx, fabric: TransactionFabric):
        current = fabric.projection(
            WORLD_AUTHORITY,
            [WORLD_STATE_RESOURCE],
        )[WORLD_STATE_RESOURCE]
        next_state = evolve_world(dict(current.value), ctx.epoch)
        return [
            TransactionProposal(
                proposal_id=f"g1-world-{ctx.epoch:012d}",
                transaction_id=f"g1-tx-world-{ctx.epoch:012d}",
                proposer_id=WORLD_SCHEDULE_ID,
                logical_epoch=ctx.epoch,
                mutations=(
                    Mutation(
                        ref=ResourceRef(WORLD_AUTHORITY, WORLD_STATE_RESOURCE),
                        expected_version=current.version,
                        new_value=next_state,
                    ),
                ),
                provenance=ProvenanceContribution(
                    source_authority=WORLD_AUTHORITY,
                    operation="PHYSICAL_WORLD_STEP",
                ),
            )
        ]

    def _matter_callback(self, ctx, fabric: TransactionFabric):
        matter = fabric.projection(
            MATTER_AUTHORITY,
            [MATTER_STATE_RESOURCE],
        )[MATTER_STATE_RESOURCE]
        world = fabric.projection(
            WORLD_AUTHORITY,
            [WORLD_STATE_RESOURCE],
        )[WORLD_STATE_RESOURCE]
        next_state = evolve_matter(dict(matter.value), dict(world.value), ctx.epoch)
        return [
            TransactionProposal(
                proposal_id=f"g1-5-matter-{ctx.epoch:012d}",
                transaction_id=f"g1-5-tx-matter-{ctx.epoch:012d}",
                proposer_id=MATTER_SCHEDULE_ID,
                logical_epoch=ctx.epoch,
                mutations=(
                    Mutation(
                        ref=ResourceRef(MATTER_AUTHORITY, MATTER_STATE_RESOURCE),
                        expected_version=matter.version,
                        new_value=next_state,
                    ),
                ),
                provenance=ProvenanceContribution(
                    source_authority=MATTER_AUTHORITY,
                    operation="MATTER_ENVIRONMENT_STEP",
                ),
            )
        ]

    def _biosphere_callback(self, ctx, fabric: TransactionFabric):
        matter = fabric.projection(
            MATTER_AUTHORITY,
            [MATTER_STATE_RESOURCE],
        )[MATTER_STATE_RESOURCE]
        ecology = fabric.projection(
            ECOLOGY_AUTHORITY,
            [ECOLOGY_STATE_RESOURCE],
        )[ECOLOGY_STATE_RESOURCE]
        world = fabric.projection(
            WORLD_AUTHORITY,
            [WORLD_STATE_RESOURCE],
        )[WORLD_STATE_RESOURCE]

        hydrated_matter = evolve_matter(dict(matter.value), dict(world.value), ctx.epoch)
        next_ecology, next_matter = evolve_producers(
            dict(ecology.value),
            hydrated_matter,
            dict(world.value),
            ctx.epoch,
        )

        return [
            TransactionProposal(
                proposal_id=f"g2-biosphere-{ctx.epoch:012d}",
                transaction_id=f"g2-tx-biosphere-{ctx.epoch:012d}",
                proposer_id=BIOSPHERE_SCHEDULE_ID,
                logical_epoch=ctx.epoch,
                mutations=(
                    Mutation(
                        ref=ResourceRef(MATTER_AUTHORITY, MATTER_STATE_RESOURCE),
                        expected_version=matter.version,
                        new_value=next_matter,
                    ),
                    Mutation(
                        ref=ResourceRef(ECOLOGY_AUTHORITY, ECOLOGY_STATE_RESOURCE),
                        expected_version=ecology.version,
                        new_value=next_ecology,
                    ),
                ),
                provenance=ProvenanceContribution(
                    source_authority=ECOLOGY_AUTHORITY,
                    operation="PRODUCER_ECOLOGY_STEP",
                ),
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

    def world_state(self) -> dict:
        if not self.config.physical_world_enabled:
            raise RuntimeError("physical world is disabled")
        return dict(
            self.fabric.projection(WORLD_AUTHORITY, [WORLD_STATE_RESOURCE])[
                WORLD_STATE_RESOURCE
            ].value
        )

    def matter_state(self) -> dict:
        if not self.config.matter_enabled:
            raise RuntimeError("matter is disabled")
        return dict(
            self.fabric.projection(MATTER_AUTHORITY, [MATTER_STATE_RESOURCE])[
                MATTER_STATE_RESOURCE
            ].value
        )

    def ecology_state(self) -> dict:
        if not self.config.producer_ecology_enabled:
            raise RuntimeError("producer ecology is disabled")
        return dict(
            self.fabric.projection(ECOLOGY_AUTHORITY, [ECOLOGY_STATE_RESOURCE])[
                ECOLOGY_STATE_RESOURCE
            ].value
        )

    def write_checkpoint(self, path: str | Path) -> None:
        from .checkpoint import write_genesis_checkpoint
        write_genesis_checkpoint(path, self)

    @classmethod
    def load_checkpoint(cls, path: str | Path, config: GenesisConfig) -> "GenesisSimulation":
        from .checkpoint import load_genesis_checkpoint
        return load_genesis_checkpoint(path, config)
