from __future__ import annotations

from dataclasses import dataclass

from hrm_coordination.authority import AuthorityPort


GENESIS_SYSTEM_AUTHORITY = "genesis.system"
GENESIS_TICK_RESOURCE = "tick"

WORLD_AUTHORITY = "world.environment"
WORLD_STATE_RESOURCE = "state"


@dataclass(frozen=True)
class AuthorityRegistration:
    authority_id: str
    port: AuthorityPort

    def __post_init__(self) -> None:
        if not self.authority_id:
            raise ValueError("authority_id required")
        if self.port.authority_id != self.authority_id:
            raise ValueError("authority_id does not match port owner")


def validate_registrations(registrations: tuple[AuthorityRegistration, ...]) -> None:
    ids = [item.authority_id for item in registrations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate authority registration")
