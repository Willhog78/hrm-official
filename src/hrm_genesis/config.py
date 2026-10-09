from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from hrm_coordination.model import digest_obj


@dataclass(frozen=True)
class GenesisConfig:
    master_seed: str = "hrm-genesis"
    contract_dt_numerator: int = 1
    contract_dt_denominator: int = 1
    max_parallel_domains: int = 32
    physical_world_enabled: bool = True
    matter_enabled: bool = True
    producer_ecology_enabled: bool = False
    consumer_ecology_enabled: bool = False
    human_biology_enabled: bool = False
    human_cognition_enabled: bool = False
    human_actions_enabled: bool = False
    multi_population_enabled: bool = False
    material_scale_factor: float = 1.0
    human_calibration_enabled: bool = False
    # G10.3 capacity model v1. Off by default; earlier configs, fingerprints
    # and results are unchanged.
    agentus_capacities_enabled: bool = False
    # Write-only, bounded own-experience model; legacy fingerprints omit "none".
    agentus_transition_model: str = "none"
    # Opt-in physical placement; absent/False preserves historical fingerprints.
    agentus_subcell_position_enabled: bool = False
    # Opt-in costed local movement, material placement and surface joining.
    agentus_local_work_enabled: bool = False
    # Opt-in incremental interlacing of existing held surfaces.
    agentus_surface_work_enabled: bool = False
    # Opt-in real wind; omitted from legacy fingerprints.
    genesis_wind_enabled: bool = False
    # Experimental ablation of capacity v1: "" or a "+"-joined set of
    # "plant_diet" (no sampling of unknown food kinds), "no_interactions" (no
    # manipulation or capture) and "no_recall" (no travel toward remembered
    # food).
    agentus_capacity_ablation: str = ""
    # Thirst as an interoceptive planning drive (G10.4 baseline correction).
    # On by default wherever Agentus cognition is enabled; set False only to
    # reproduce pre-G10.4 results, whose fingerprints omit this key.
    agentus_thirst_enabled: bool = True
    # G10.6 behavioural/locomotion integrity (baseline correction): partial food
    # anchors a hungry agent, dependents move physically, sleep recovers fatigue.
    # False reproduces pre-G10.6 runs exactly.
    agentus_behavior_integrity_enabled: bool = True
    # G10.7a: what observers can learn from others. "visible-v1" (default)
    # passes only visible acts and visible consequences, appraised by the
    # observer's own values; "g10.4-legacy" reproduces the G10.4 path that
    # copied the actor's reward and the eater's energy yield.
    agentus_observation_model: str = "visible-v1"
    # G10.7a step 2: bounded memory of witnessed events (write-only until
    # imitation exists). Active only with capacities and a visible model.
    agentus_event_memory_enabled: bool = True
    # G10.7a step 2.5: which witnessed events are kept when memory is full.
    # "consequence" (default): conspicuous events stick better; "fifo"
    # reproduces step 2 (newest kept).
    agentus_event_memory_retention: str = "consequence"
    # G10.7a step 3: remembered conspicuous acts raise the chance of trying the
    # same act when physically possible. No value or recipe is transferred.
    agentus_imitation_enabled: bool = True
    # G10.7a step 4: when hungry with nowhere known to go, an agent may go where
    # a visible individual is, valued only by its own experience of doing so.
    agentus_following_enabled: bool = True
    # Reference physiology (G10.5). "reference-v2" adds fat reserves, lean
    # catabolism, realistic lactation and size^0.75 child metabolism.
    agentus_physiology_version: str = "reference-v1"
    # Consumer (animal) timebase. "elapsed-time-v2" (default) converts
    # per-month trait rates to the run's tick length (as durations already
    # are) and gives movement, hunt attempts and predator attacks one
    # opportunity per month of elapsed time; "elapsed-time-v1" converts rates
    # only (D2); "per-tick-legacy" reproduces pre-D2 runs. All identical at
    # 12 ticks/year.
    consumer_timebase: str = "elapsed-time-v2"
    # Producer (plant) timebase. Plant rates and ages are stated per day (the
    # daily world is the reference). "elapsed-time-v1" (default) converts them
    # to the run's tick length; "per-tick-legacy" reproduces earlier runs.
    # Both are identical at 365 ticks/year.
    producer_timebase: str = "elapsed-time-v1"
    # Caregiving (docs/architecture/CAREGIVING_SOLID_FOOD.md). "solid-food-v1"
    # (default) lets a caregiver hand food it obtained from the shared cell to a
    # dependent child; "none" reproduces earlier runs. Active with capacities.
    caregiving_model: str = "solid-food-v1"
    # Nursing (docs/architecture/DEMAND_LIMITED_MILK.md). "demand-limited-v1"
    # (default) makes only the milk the child can receive and charges the
    # mother for what is made; "supply-capped-legacy" reproduces earlier runs.
    # "remaining-demand-v2" is an opt-in: youngest dependents first, solids
    # before milk, with milk limited by the remaining store room.
    # Active for calibrated humans.
    nursing_model: str = "demand-limited-v1"
    # Water cycle at material scale (docs/architecture/WATER_CYCLE_SCALE.md).
    # "material-v1" (default) scales rain, infiltration, soil capacity,
    # evaporation and the plants' water threshold with material_scale_factor,
    # as G10.1 already scales the water and biomass inventories;
    # "unscaled-legacy" reproduces earlier runs. Identical at scale 1.
    water_cycle_scale: str = "material-v1"
    # One energy store for eating, hand-feeding and nursing
    # (docs/architecture/CHILD_ENERGY_STORE.md). "size-scaled-v1" (default)
    # bounds every credit by energy_capacity_kcal x development_scale and
    # records energy a full store refuses; "unscaled-eating-legacy" reproduces
    # earlier runs (eating capped at the adult capacity, nursing cuts back).
    child_energy_store: str = "size-scaled-v1"
    world_width: int = 8
    world_height: int = 8
    ticks_per_year: int = 120

    def __post_init__(self) -> None:
        if not self.master_seed:
            raise ValueError("master_seed required")
        if self.contract_dt_numerator <= 0 or self.contract_dt_denominator <= 0:
            raise ValueError("contract_dt must be positive")
        if self.max_parallel_domains < 1:
            raise ValueError("max_parallel_domains must be >= 1")
        if self.world_width < 2 or self.world_height < 2:
            raise ValueError("world dimensions must be >= 2")
        if self.ticks_per_year < 4:
            raise ValueError("ticks_per_year must be >= 4")
        if self.material_scale_factor < 1.0:
            raise ValueError("material_scale_factor must be >= 1.0")
        if self.consumer_timebase not in ("elapsed-time-v2", "elapsed-time-v1", "per-tick-legacy"):
            raise ValueError("consumer_timebase must be 'elapsed-time-v2', 'elapsed-time-v1' or 'per-tick-legacy'")
        if self.producer_timebase not in ("elapsed-time-v1", "per-tick-legacy"):
            raise ValueError("producer_timebase must be 'elapsed-time-v1' or 'per-tick-legacy'")
        if self.human_calibration_enabled and self.ticks_per_year != 365:
            raise ValueError("human_calibration_enabled requires ticks_per_year == 365")
        if self.human_calibration_enabled and self.material_scale_factor < 100.0:
            raise ValueError("human_calibration_enabled requires material_scale_factor >= 100")
        if self.matter_enabled and not self.physical_world_enabled:
            raise ValueError("matter_enabled requires physical_world_enabled in G1.5")
        if self.producer_ecology_enabled and not self.matter_enabled:
            raise ValueError("producer_ecology_enabled requires matter_enabled")
        if self.consumer_ecology_enabled and not self.producer_ecology_enabled:
            raise ValueError("consumer_ecology_enabled requires producer_ecology_enabled")
        if self.human_biology_enabled and not self.consumer_ecology_enabled:
            raise ValueError("human_biology_enabled requires consumer_ecology_enabled")
        if self.human_cognition_enabled and not self.human_biology_enabled:
            raise ValueError("human_cognition_enabled requires human_biology_enabled")
        if self.human_actions_enabled and not self.human_cognition_enabled:
            raise ValueError("human_actions_enabled requires human_cognition_enabled")
        if self.agentus_capacities_enabled and not (self.human_actions_enabled and self.human_calibration_enabled):
            raise ValueError("agentus_capacities_enabled requires human_actions_enabled and human_calibration_enabled")
        if self.agentus_transition_model not in {"none", "experienced-transitions-v1", "experienced-transitions-v2", "experienced-transitions-v3", "experienced-transitions-v4"}:
            raise ValueError("unknown agentus_transition_model")
        if self.agentus_transition_model != "none" and not self.agentus_capacities_enabled:
            raise ValueError("agentus_transition_model requires agentus_capacities_enabled")
        if self.agentus_transition_model in {"experienced-transitions-v2", "experienced-transitions-v3", "experienced-transitions-v4"} and self.child_energy_store != "size-scaled-v1":
            raise ValueError("valued transitions require size-scaled-v1 energy accounting")
        if self.agentus_physiology_version not in {"reference-v1", "reference-v2"}:
            raise ValueError("unknown agentus_physiology_version")
        if self.agentus_physiology_version != "reference-v1" and not self.human_calibration_enabled:
            raise ValueError("agentus_physiology_version requires human_calibration_enabled")
        parts = [p for p in self.agentus_capacity_ablation.split("+") if p]
        if not set(parts) <= {"plant_diet", "no_interactions", "no_recall"} or len(parts) != len(set(parts)):
            raise ValueError("unknown agentus_capacity_ablation")
        if self.caregiving_model not in {"solid-food-v1", "none"}:
            raise ValueError("unknown caregiving_model")
        if self.nursing_model not in {"demand-limited-v1", "remaining-demand-v2", "supply-capped-legacy"}:
            raise ValueError("unknown nursing_model")
        if self.water_cycle_scale not in {"material-v1", "unscaled-legacy"}:
            raise ValueError("unknown water_cycle_scale")
        if self.child_energy_store not in {"size-scaled-v1", "unscaled-eating-legacy"}:
            raise ValueError("unknown child_energy_store")
        if self.agentus_observation_model not in {"visible-v1", "g10.4-legacy"}:
            raise ValueError("unknown agentus_observation_model")
        if self.agentus_subcell_position_enabled and not self.agentus_capacities_enabled:
            raise ValueError("subcell position requires Agentus capacities")
        if self.agentus_local_work_enabled and not self.agentus_subcell_position_enabled:
            raise ValueError("local work requires subcell position")
        if self.agentus_surface_work_enabled and not self.agentus_capacities_enabled:
            raise ValueError("surface work requires Agentus capacities")
        if self.agentus_event_memory_retention not in {"consequence", "fifo"}:
            raise ValueError("unknown agentus_event_memory_retention")
        if self.agentus_capacity_ablation and not self.agentus_capacities_enabled:
            raise ValueError("agentus_capacity_ablation requires agentus_capacities_enabled")
        if self.multi_population_enabled and not self.human_actions_enabled:
            raise ValueError("multi_population_enabled requires human_actions_enabled")

    @property
    def thirst_planning_active(self) -> bool:
        """Thirst needs a planner to act on; it is inert without cognition."""
        return self.agentus_thirst_enabled and self.human_cognition_enabled

    @property
    def behavior_integrity_active(self) -> bool:
        return self.agentus_behavior_integrity_enabled and self.human_biology_enabled

    @property
    def event_memory_active(self) -> bool:
        return (self.agentus_event_memory_enabled and self.agentus_capacities_enabled
                and self.agentus_observation_model != "g10.4-legacy")

    @property
    def imitation_active(self) -> bool:
        return self.agentus_imitation_enabled and self.event_memory_active

    @property
    def following_active(self) -> bool:
        return (self.agentus_following_enabled and self.agentus_capacities_enabled
                and self.human_cognition_enabled and self.agentus_observation_model != "g10.4-legacy")

    @property
    def solid_food_active(self) -> bool:
        return self.caregiving_model == "solid-food-v1" and self.agentus_capacities_enabled and self.human_cognition_enabled

    @property
    def energy_store_active(self) -> bool:
        return (self.child_energy_store == "size-scaled-v1" and self.human_biology_enabled
                and self.human_calibration_enabled)

    @property
    def water_scale_active(self) -> bool:
        return (self.water_cycle_scale == "material-v1" and self.matter_enabled
                and self.material_scale_factor != 1.0)

    @property
    def demand_milk_active(self) -> bool:
        return (self.nursing_model in {"demand-limited-v1", "remaining-demand-v2"} and self.human_biology_enabled
                and self.human_calibration_enabled)

    @property
    def contract_dt(self) -> Fraction:
        return Fraction(self.contract_dt_numerator, self.contract_dt_denominator)

    def canonical(self) -> dict[str, object]:
        canonical = {
            "master_seed": self.master_seed,
            "contract_dt_numerator": self.contract_dt_numerator,
            "contract_dt_denominator": self.contract_dt_denominator,
            "max_parallel_domains": self.max_parallel_domains,
            "physical_world_enabled": self.physical_world_enabled,
            "matter_enabled": self.matter_enabled,
            "producer_ecology_enabled": self.producer_ecology_enabled,
            "consumer_ecology_enabled": self.consumer_ecology_enabled,
            "human_biology_enabled": self.human_biology_enabled,
            "human_cognition_enabled": self.human_cognition_enabled,
            "human_actions_enabled": self.human_actions_enabled,
            "multi_population_enabled": self.multi_population_enabled,
            "material_scale_factor": self.material_scale_factor,
            "human_calibration_enabled": self.human_calibration_enabled,
            "world_width": self.world_width,
            "world_height": self.world_height,
            "ticks_per_year": self.ticks_per_year,
            "genesis_phase": "G8" if self.multi_population_enabled else ("G7" if self.human_actions_enabled else ("G6" if self.human_cognition_enabled else ("G5" if self.human_biology_enabled else ("G3" if self.consumer_ecology_enabled else "G2")))),
        }
        if self.agentus_capacities_enabled:
            # Present only when enabled so earlier fingerprints do not change.
            canonical["agentus_capacities_enabled"] = True
            canonical["agentus_capacity_model"] = "capacity-v2"
        if self.agentus_capacity_ablation:
            canonical["agentus_capacity_ablation"] = self.agentus_capacity_ablation
        if self.agentus_transition_model != "none":
            canonical["agentus_transition_model"] = self.agentus_transition_model
        if self.thirst_planning_active:
            canonical["agentus_thirst_enabled"] = True
        if self.agentus_capacities_enabled and self.agentus_observation_model != "g10.4-legacy":
            canonical["agentus_observation_model"] = self.agentus_observation_model
        if self.genesis_wind_enabled:
            canonical["genesis_wind"] = "persistent-vector-v1"
        if self.agentus_subcell_position_enabled:
            canonical["agentus_subcell_position"] = "cell-local-v1"
        if self.agentus_local_work_enabled:
            canonical["agentus_local_work"] = "local-material-v1"
        if self.agentus_surface_work_enabled:
            canonical["agentus_surface_work"] = "incremental-interlace-v1"
        if self.event_memory_active:
            canonical["agentus_event_memory"] = "witnessed-v2" if self.agentus_event_memory_retention == "consequence" else "witnessed-v1"
        if self.imitation_active:
            canonical["agentus_imitation"] = "witnessed-act-v1"
        if self.following_active:
            canonical["agentus_following"] = "visible-peer-v1"
        if self.solid_food_active:
            canonical["agentus_caregiving"] = self.caregiving_model
        if self.demand_milk_active:
            canonical["agentus_nursing"] = self.nursing_model
        if self.water_scale_active:
            canonical["water_cycle_scale"] = self.water_cycle_scale
        if self.energy_store_active:
            canonical["agentus_energy_store"] = self.child_energy_store
        if self.behavior_integrity_active:
            canonical["agentus_behavior_integrity"] = "g10.6"
        if self.agentus_physiology_version != "reference-v1":
            canonical["agentus_physiology_version"] = self.agentus_physiology_version
        if (self.consumer_ecology_enabled and self.ticks_per_year != 12
                and self.consumer_timebase != "per-tick-legacy"):
            # Present only where it changes behaviour, so monthly-tick and
            # legacy fingerprints do not change.
            canonical["consumer_timebase"] = self.consumer_timebase
        if (self.producer_ecology_enabled and self.ticks_per_year != 365
                and self.producer_timebase != "per-tick-legacy"):
            # Present only where it changes behaviour: daily and legacy
            # fingerprints do not change.
            canonical["producer_timebase"] = self.producer_timebase
        return canonical

    def fingerprint(self) -> str:
        return digest_obj(self.canonical())
