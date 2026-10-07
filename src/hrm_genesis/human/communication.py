from __future__ import annotations

from .actions import validate_sequence

MAX_SIGNAL_ACTIONS = 12

# G10.7a: this path writes the sender's action recipe straight into the
# receiver. Nothing physical carries it (no channel, range, cost or
# perception), so it is not available to live behaviour. It survives only to
# reproduce the G7 gate record, and must be asked for by name.
G7_LEGACY = "g7-legacy"


def _require_legacy(compatibility: str | None) -> None:
    if compatibility != G7_LEGACY:
        raise ValueError(
            "direct recipe transfer is non-physical; it exists only for G7 reproduction "
            f"(pass compatibility={G7_LEGACY!r})"
        )


def signal_sequence(sender: dict, sequence: list[str] | tuple[str, ...], *, compatibility: str | None = None) -> dict:
    _require_legacy(compatibility)
    seq = validate_sequence(sequence)[:MAX_SIGNAL_ACTIONS]
    return {
        "sender_id": str(sender["id"]),
        "primitive_sequence": list(seq),
    }

def imitate_signal(receiver: dict, signal: dict, *, compatibility: str | None = None) -> dict:
    _require_legacy(compatibility)
    learned = [tuple(x) for x in receiver.get("learned_sequences", [])]
    seq = validate_sequence(signal["primitive_sequence"])
    if seq not in learned:
        learned.append(seq)
    updated = dict(receiver)
    updated["learned_sequences"] = [list(x) for x in learned[-16:]]
    updated["last_teacher_id"] = str(signal["sender_id"])
    return updated
