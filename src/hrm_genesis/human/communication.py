from __future__ import annotations

from .actions import validate_sequence

MAX_SIGNAL_ACTIONS = 12

def signal_sequence(sender: dict, sequence: list[str] | tuple[str, ...]) -> dict:
    seq = validate_sequence(sequence)[:MAX_SIGNAL_ACTIONS]
    return {
        "sender_id": str(sender["id"]),
        "primitive_sequence": list(seq),
    }

def imitate_signal(receiver: dict, signal: dict) -> dict:
    learned = [tuple(x) for x in receiver.get("learned_sequences", [])]
    seq = validate_sequence(signal["primitive_sequence"])
    if seq not in learned:
        learned.append(seq)
    updated = dict(receiver)
    updated["learned_sequences"] = [list(x) for x in learned[-16:]]
    updated["last_teacher_id"] = str(signal["sender_id"])
    return updated
