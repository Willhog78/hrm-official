from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from hrm_coordination import (
    Mutation,
    ProvenanceContribution,
    ReplayLedger,
    StreamingReplayLedger,
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
from .ecology.animals import (
    build_consumer_state,
    enable_fresh_tissue,
    evolve_consumers,
    seed_initial_consumers,
)
from .human.biology import (
    build_human_state,
    evolve_agentus_step,
    evolve_humans,
    seed_initial_humans,
)
from .human.interactions import enable_capacities
from .matter.objects import seed_natural_fragments
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
    CONSUMER_AUTHORITY,
    CONSUMER_STATE_RESOURCE,
    HUMAN_AUTHORITY,
    HUMAN_STATE_RESOURCE,
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
CONSUMER_BIOSPHERE_SCHEDULE_ID = "ecology.consumers"
HUMAN_BIOSPHERE_SCHEDULE_ID = "human.biology"


class GenesisSimulation:
    """Genesis runner through G3.

    World owns terrain/climate forcing. Matter owns environmental reservoirs.
    Producer ecology owns plants/seeds/detritus. Consumer ecology owns animals
    and carcasses.

    With consumers enabled, hydrology, producers and consumers are committed
    atomically so feeding/drinking cannot race lower-level material updates.
    """

    def __init__(self, config: GenesisConfig, *, ledger_path: str | None = None, ledger_buffer_epochs: int = 8):
        """`ledger_path`: stream replay evidence to this file and keep only the
        last `ledger_buffer_epochs` epochs in memory (StreamingReplayLedger).
        The simulation never reads ledger history, so outcomes and the ledger
        digest are identical either way; only memory use differs."""
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
        consumer_state = None
        human_state = None
        if config.matter_enabled:
            matter_state = build_matter_state(
                width=config.world_width,
                height=config.world_height,
                seed_bank=self.seed_bank,
                scale_factor=config.material_scale_factor,
            )
            if config.water_scale_active:
                # Present only where it changes behaviour (scale != 1).
                matter_state["water_scale"] = float(config.material_scale_factor)

        if config.producer_ecology_enabled:
            if matter_state is None:
                raise ValueError("producer ecology requires Matter state")
            producer_state = build_producer_state(
                width=config.world_width,
                height=config.world_height,
                ticks_per_year=config.ticks_per_year,
                timebase=config.producer_timebase,
            )
            matter_state, producer_state = seed_initial_producers(
                matter_state,
                producer_state,
                self.seed_bank,
                biomass_scale_factor=config.material_scale_factor,
            )

        if config.consumer_ecology_enabled:
            if matter_state is None or producer_state is None:
                raise ValueError("consumer ecology requires Matter and producer state")
            consumer_state = build_consumer_state(
                width=config.world_width,
                height=config.world_height,
                seed_bank=self.seed_bank,
                ticks_per_year=config.ticks_per_year,
                timebase=config.consumer_timebase,
            )
            consumer_state, producer_state, matter_state = seed_initial_consumers(
                consumer_state,
                producer_state,
                matter_state,
            )

        if config.human_biology_enabled:
            if matter_state is None or producer_state is None or consumer_state is None:
                raise ValueError("human biology requires Matter, producers, and consumers")
            human_state = build_human_state(
                width=config.world_width,
                height=config.world_height,
                seed_bank=self.seed_bank,
                cognition_enabled=config.human_cognition_enabled,
                actions_enabled=config.human_actions_enabled,
                multi_population_enabled=config.multi_population_enabled,
                calibrated=config.human_calibration_enabled,
                ticks_per_year=config.ticks_per_year,
                physiology_version=config.agentus_physiology_version,
            )
            human_state, producer_state, matter_state = seed_initial_humans(
                human_state,
                producer_state,
                matter_state,
            )
            if config.demand_milk_active:
                human_state = dict(human_state)
                human_state["nursing_model"] = config.nursing_model
            if config.energy_store_active:
                human_state = dict(human_state)
                human_state["energy_store_model"] = config.child_energy_store
            if config.thirst_planning_active:
                human_state = dict(human_state)
                human_state["thirst_planning"] = True
            if config.behavior_integrity_active:
                human_state = dict(human_state)
                human_state["behavior_integrity"] = True
            if config.agentus_capacities_enabled:
                # Loose weathered stone is part of initial conditions; its total
                # is the fixed lithic ledger quantity. Fresh carcass tissue is
                # split from decayed tissue so spoilage can matter.
                lithic_cells, lithic_total = seed_natural_fragments(
                    world_state["cells"], config.master_seed
                )
                matter_state = dict(matter_state)
                matter_state["lithic_cells"] = lithic_cells
                if config.agentus_observation_model != "g10.4-legacy":
                    human_state = dict(human_state)
                    human_state["observation_model"] = config.agentus_observation_model
                if config.event_memory_active:
                    human_state = dict(human_state)
                    human_state["event_memory"] = True
                    if config.agentus_event_memory_retention == "consequence":
                        human_state["event_memory_retention"] = "consequence"
                    if config.imitation_active:
                        human_state["imitation"] = True
                if config.following_active:
                    human_state = dict(human_state)
                    human_state["following"] = True
                if config.solid_food_active:
                    human_state = dict(human_state)
                    human_state["caregiving_model"] = config.caregiving_model
                matter_state["initial_lithic_kg"] = lithic_total
                consumer_state = enable_fresh_tissue(consumer_state)
                human_state = enable_capacities(human_state)
                if config.agentus_capacity_ablation:
                    human_state["capacity_ablation"] = config.agentus_capacity_ablation

        if matter_state is not None:
            authorities.append(
                StateAuthority(MATTER_AUTHORITY, {MATTER_STATE_RESOURCE: matter_state})
            )

        if producer_state is not None:
            authorities.append(
                StateAuthority(ECOLOGY_AUTHORITY, {ECOLOGY_STATE_RESOURCE: producer_state})
            )

        if consumer_state is not None:
            authorities.append(
                StateAuthority(CONSUMER_AUTHORITY, {CONSUMER_STATE_RESOURCE: consumer_state})
            )

        if human_state is not None:
            authorities.append(
                StateAuthority(HUMAN_AUTHORITY, {HUMAN_STATE_RESOURCE: human_state})
            )

        self.authorities = authorities
        registrations = tuple(
            AuthorityRegistration(authority.authority_id, authority.port())
            for authority in self.authorities
        )
        validate_registrations(registrations)

        self.ledger = (
            ReplayLedger(config.fingerprint()) if ledger_path is None
            else StreamingReplayLedger(config.fingerprint(), ledger_path, buffer_epochs=ledger_buffer_epochs)
        )
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
        if config.consumer_ecology_enabled:
            expected.add(CONSUMER_AUTHORITY)
        if config.human_biology_enabled:
            expected.add(HUMAN_AUTHORITY)
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

        if self.config.human_biology_enabled:
            self.orchestrator.register(
                ScheduleSpec(HUMAN_BIOSPHERE_SCHEDULE_ID, 1, 0, 1),
                self._human_biosphere_callback,
            )
        elif self.config.consumer_ecology_enabled:
            self.orchestrator.register(
                ScheduleSpec(CONSUMER_BIOSPHERE_SCHEDULE_ID, 1, 0, 1),
                self._consumer_biosphere_callback,
            )
        elif self.config.producer_ecology_enabled:
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


    def _consumer_biosphere_callback(self, ctx, fabric: TransactionFabric):
        matter = fabric.projection(
            MATTER_AUTHORITY,
            [MATTER_STATE_RESOURCE],
        )[MATTER_STATE_RESOURCE]
        producers = fabric.projection(
            ECOLOGY_AUTHORITY,
            [ECOLOGY_STATE_RESOURCE],
        )[ECOLOGY_STATE_RESOURCE]
        consumers = fabric.projection(
            CONSUMER_AUTHORITY,
            [CONSUMER_STATE_RESOURCE],
        )[CONSUMER_STATE_RESOURCE]
        world = fabric.projection(
            WORLD_AUTHORITY,
            [WORLD_STATE_RESOURCE],
        )[WORLD_STATE_RESOURCE]

        hydrated_matter = evolve_matter(dict(matter.value), dict(world.value), ctx.epoch)
        next_producers, matter_after_plants = evolve_producers(
            dict(producers.value),
            hydrated_matter,
            dict(world.value),
            ctx.epoch,
        )
        next_consumers, final_producers, final_matter = evolve_consumers(
            dict(consumers.value),
            next_producers,
            matter_after_plants,
            dict(world.value),
            ctx.epoch,
        )

        return [
            TransactionProposal(
                proposal_id=f"g3-biosphere-{ctx.epoch:012d}",
                transaction_id=f"g3-tx-biosphere-{ctx.epoch:012d}",
                proposer_id=CONSUMER_BIOSPHERE_SCHEDULE_ID,
                logical_epoch=ctx.epoch,
                mutations=(
                    Mutation(
                        ref=ResourceRef(MATTER_AUTHORITY, MATTER_STATE_RESOURCE),
                        expected_version=matter.version,
                        new_value=final_matter,
                    ),
                    Mutation(
                        ref=ResourceRef(ECOLOGY_AUTHORITY, ECOLOGY_STATE_RESOURCE),
                        expected_version=producers.version,
                        new_value=final_producers,
                    ),
                    Mutation(
                        ref=ResourceRef(CONSUMER_AUTHORITY, CONSUMER_STATE_RESOURCE),
                        expected_version=consumers.version,
                        new_value=next_consumers,
                    ),
                ),
                provenance=ProvenanceContribution(
                    source_authority=CONSUMER_AUTHORITY,
                    operation="CONSUMER_ECOLOGY_STEP",
                ),
            )
        ]


    def _human_biosphere_callback(self, ctx, fabric: TransactionFabric):
        matter = fabric.projection(
            MATTER_AUTHORITY,
            [MATTER_STATE_RESOURCE],
        )[MATTER_STATE_RESOURCE]
        producers = fabric.projection(
            ECOLOGY_AUTHORITY,
            [ECOLOGY_STATE_RESOURCE],
        )[ECOLOGY_STATE_RESOURCE]
        consumers = fabric.projection(
            CONSUMER_AUTHORITY,
            [CONSUMER_STATE_RESOURCE],
        )[CONSUMER_STATE_RESOURCE]
        humans = fabric.projection(
            HUMAN_AUTHORITY,
            [HUMAN_STATE_RESOURCE],
        )[HUMAN_STATE_RESOURCE]
        world = fabric.projection(
            WORLD_AUTHORITY,
            [WORLD_STATE_RESOURCE],
        )[WORLD_STATE_RESOURCE]

        hydrated_matter = evolve_matter(dict(matter.value), dict(world.value), ctx.epoch)
        next_producers, matter_after_plants = evolve_producers(
            dict(producers.value),
            hydrated_matter,
            dict(world.value),
            ctx.epoch,
        )
        next_consumers, producers_after_consumers, matter_after_consumers = evolve_consumers(
            dict(consumers.value),
            next_producers,
            matter_after_plants,
            dict(world.value),
            ctx.epoch,
        )
        if self.config.agentus_capacities_enabled:
            # Capacity v1 may kill animals and eat carcass tissue, so the
            # Agentus step also returns the Consumer state it changed.
            next_humans, final_producers, final_matter, consumers_after_humans = evolve_agentus_step(
                dict(humans.value),
                producers_after_consumers,
                matter_after_consumers,
                dict(world.value),
                ctx.epoch,
                cognition_enabled=self.config.human_cognition_enabled,
                actions_enabled=self.config.human_actions_enabled,
                consumer_state=next_consumers,
            )
        else:
            next_humans, final_producers, final_matter = evolve_humans(
                dict(humans.value),
                producers_after_consumers,
                matter_after_consumers,
                dict(world.value),
                ctx.epoch,
                cognition_enabled=self.config.human_cognition_enabled,
                actions_enabled=self.config.human_actions_enabled,
                consumer_state=next_consumers,
            )
            consumers_after_humans = next_consumers

        return [
            TransactionProposal(
                proposal_id=f"g5-biosphere-{ctx.epoch:012d}",
                transaction_id=f"g5-tx-biosphere-{ctx.epoch:012d}",
                proposer_id=HUMAN_BIOSPHERE_SCHEDULE_ID,
                logical_epoch=ctx.epoch,
                mutations=(
                    Mutation(
                        ref=ResourceRef(MATTER_AUTHORITY, MATTER_STATE_RESOURCE),
                        expected_version=matter.version,
                        new_value=final_matter,
                    ),
                    Mutation(
                        ref=ResourceRef(ECOLOGY_AUTHORITY, ECOLOGY_STATE_RESOURCE),
                        expected_version=producers.version,
                        new_value=final_producers,
                    ),
                    Mutation(
                        ref=ResourceRef(CONSUMER_AUTHORITY, CONSUMER_STATE_RESOURCE),
                        expected_version=consumers.version,
                        new_value=consumers_after_humans,
                    ),
                    Mutation(
                        ref=ResourceRef(HUMAN_AUTHORITY, HUMAN_STATE_RESOURCE),
                        expected_version=humans.version,
                        new_value=next_humans,
                    ),
                ),
                provenance=ProvenanceContribution(
                    source_authority=HUMAN_AUTHORITY,
                    operation="HUMAN_BIOLOGY_STEP",
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

    def consumer_state(self) -> dict:
        if not self.config.consumer_ecology_enabled:
            raise RuntimeError("consumer ecology is disabled")
        return dict(
            self.fabric.projection(CONSUMER_AUTHORITY, [CONSUMER_STATE_RESOURCE])[
                CONSUMER_STATE_RESOURCE
            ].value
        )

    def human_state(self) -> dict:
        if not self.config.human_biology_enabled:
            raise RuntimeError("human biology is disabled")
        return dict(
            self.fabric.projection(HUMAN_AUTHORITY, [HUMAN_STATE_RESOURCE])[
                HUMAN_STATE_RESOURCE
            ].value
        )

    def write_checkpoint(self, path: str | Path) -> None:
        from .checkpoint import write_genesis_checkpoint
        write_genesis_checkpoint(path, self)

    @classmethod
    def load_checkpoint(cls, path: str | Path, config: GenesisConfig) -> "GenesisSimulation":
        from .checkpoint import load_genesis_checkpoint
        return load_genesis_checkpoint(path, config)
