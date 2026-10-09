"""Persistent simulation parentage; never an input to Agentus perception.

The existing birth gate checks adult contact, not courtship or fertilisation.
This opt-in model declares a stable pairing among the males satisfying that
gate. It records modeled paternity, not a recovered fact about legacy runs.
"""
from __future__ import annotations


PARENTAGE_MODEL = "recorded-pair-v1"


def enable_parentage(human_state: dict) -> None:
    """Initialize the register for a freshly seeded world, without RNG draws."""
    human_state["parentage_model"] = PARENTAGE_MODEL
    human_state["lineage"] = {}
    for person in human_state["humans"]:
        person.update(mother_id=None, father_id=None, birth_epoch=None)
        human_state["lineage"][str(person["id"])] = {
            "mother_id": None,
            "father_id": None,
            "birth_epoch": None,
            "death_epoch": None,
            "generation": int(person["generation"]),
            "sex": str(person["sex"]),
            "origin": "founder",
        }


def ancestor_ids(lineage: dict, person_id: str) -> set[str]:
    """Known maternal AND paternal ancestors, including records of the dead.

Missing records stop that path. A missing ancestor is unknown, not unrelated.
The visited set also makes malformed cyclic input terminate safely.
"""
    seen = {person_id}
    ancestors = set()
    pending = [person_id]
    while pending:
        record = lineage.get(pending.pop(), {})
        for key in ("mother_id", "father_id"):
            parent = record.get(key)
            if parent is not None and parent not in seen:
                seen.add(parent)
                ancestors.add(parent)
                pending.append(parent)
    return ancestors


def recorded_relationship(lineage: dict, first_id: str, second_id: str) -> str:
    """Relationship visible in the register, without claiming genetic viability."""
    if first_id not in lineage or second_id not in lineage:
        return "unknown_record"
    if first_id == second_id:
        return "self"
    first, second = lineage[first_id], lineage[second_id]
    first_parents = {first.get(k) for k in ("mother_id", "father_id")} - {None}
    second_parents = {second.get(k) for k in ("mother_id", "father_id")} - {None}
    if first_id in second_parents or second_id in first_parents:
        return "parent_child"
    if len(first_parents) == 2 and first_parents == second_parents:
        return "full_siblings"
    if first_parents & second_parents:
        return "half_siblings"
    first_ancestors = ancestor_ids(lineage, first_id)
    second_ancestors = ancestor_ids(lineage, second_id)
    if first_id in second_ancestors or second_id in first_ancestors:
        return "ancestor_descendant"
    if first_ancestors & second_ancestors:
        return "shared_ancestry"
    return "no_recorded_relation"


def record_birth(human_state: dict, child: dict, mother: dict,
                 eligible_males: list[dict], epoch: int) -> None:
    """Assign the lowest-ID eligible local male; this does not gate the birth."""
    candidates = sorted(str(person["id"]) for person in eligible_males)
    if not candidates:
        raise ValueError("recorded pairing requires an eligible male")
    father_id = candidates[0]
    mother_id = str(mother["id"])
    child.update(mother_id=mother_id, father_id=father_id, birth_epoch=int(epoch))
    lineage = human_state["lineage"]
    lineage[str(child["id"])] = {
        "mother_id": mother_id,
        "father_id": father_id,
        "birth_epoch": int(epoch),
        "death_epoch": None,
        "generation": int(child["generation"]),
        "sex": str(child["sex"]),
        "origin": "birth",
        "father_selection": "lowest-id-local-adult-v1",
        "candidate_father_ids": candidates,
        "parent_relationship": recorded_relationship(lineage, mother_id, father_id),
    }


def record_death(human_state: dict, person_id: str, epoch: int) -> None:
    human_state["lineage"][person_id]["death_epoch"] = int(epoch)
