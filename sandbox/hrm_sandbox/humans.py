"""Human agents: bodily needs, perception-limited memory, and value learning.

Nothing here names a technique. Agents hold at most one object, and the only
learned quantity is Q[(held_signature, verb, target_category)] -- expected food
from doing `verb` to a target while holding an object with that signature.
Signatures are coarse perceptual property buckets (hard / sharp / long), so an
agent generalises across stones it has never touched but cannot see "tool".

Learning channels:
  * own experience (ALPHA);
  * watching someone nearby act and seeing the outcome (ALPHA_OBS), gated by
    attention and familiarity. Every threshold crossing records its source.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .ecology import Item

ADULT = 500
INFANT = 150
OLD = 2400
HUNGER_RATE = 0.45
THIRST_RATE = 0.7
ALPHA = 0.25
ALPHA_OBS = 0.12
GAMMA = 0.8
KNOW = 7.0  # Q level at which the observer counts a non-bare-hand behaviour as "held"
HAND = Item(0, "hand", 0, 0, hardness=3.0)

# Innate priors: biologically plausible baseline tendencies, bare hands only.
INNATE = {
    ("hand", "strike", "rabbit"): 5.0,
    ("hand", "strike", "nut"): 2.0,
}

SIGS = ("hand", "h--", "h-L", "hS-", "hSL", "H--", "H-L", "HS-", "HSL")
SIG_CODE = {s: i for i, s in enumerate(SIGS)}


def sig(item: Item | None) -> str:
    if item is None:
        return "hand"
    return (
        ("H" if item.hardness >= 4.0 else "h")
        + ("S" if item.sharpness >= 0.4 else "-")
        + ("L" if item.length >= 0.8 else "-")
    )


def category(item: Item) -> str:
    return "nut" if item.kind == "nut" else "obj:" + sig(item)


def describe_sig(s: str) -> str:
    if s == "hand":
        return "bare hand"
    words = ["hard" if s[0] == "H" else "soft"]
    if s[1] == "S":
        words.append("sharp")
    if s[2] == "L":
        words.append("long")
    return " ".join(words) + " object"


def describe(key: tuple[str, str, str]) -> str:
    held, verb, target = key
    tgt = describe_sig(target[4:]) if target.startswith("obj:") else target
    if verb == "bind":
        return f"bind {describe_sig(held)} to {tgt}"
    return f"{verb} {tgt} with {describe_sig(held)}"


@dataclass(eq=False)
class Human:
    id: int
    x: int
    y: int
    female: bool
    age: int
    band: int  # origin label for display/observer only; never read causally
    curiosity: float
    attention: float
    mother: int | None = None
    hunger: float = 20.0
    thirst: float = 10.0
    alive: bool = True
    held: Item | None = None
    q: dict[tuple[str, str, str], float] = field(default_factory=dict)
    known: dict[tuple[str, str, str], tuple[int, int]] = field(default_factory=dict)
    familiar: dict[int, int] = field(default_factory=dict)
    mem_shore: set[tuple[int, int]] = field(default_factory=set)
    mem_bush: dict[tuple[int, int], tuple[float, int]] = field(default_factory=dict)
    mem_nuts: dict[tuple[int, int], int] = field(default_factory=dict)
    target: tuple | None = None
    plan_timer: int = 0
    last_birth: int = -10_000
    heading: tuple[int, int] = (1, 0)
    children: int = 0
    seen_items: list[Item] = field(default_factory=list)
    seen_rabbits: list = field(default_factory=list)

    # --- value learning --------------------------------------------------
    def qv(self, key: tuple[str, str, str]) -> float:
        v = self.q.get(key)
        if v is not None:
            return v
        if key[0] != "hand":
            return self.qv(("hand", key[1], key[2]))
        return INNATE.get(key, 0.0)

    def value_of(self, s: str) -> float:
        best = max(self.qv((s, "strike", "nut")), self.qv((s, "strike", "rabbit")))
        for k, v in self.q.items():
            if k[0] == s and v > best:
                best = v
        return best

    def learn(self, key: tuple[str, str, str], food: float, result: str | None,
              rate: float, tick: int, source: int) -> bool:
        """TD(0) update. Returns True when this update makes the behaviour 'known'."""
        target = food + (GAMMA * self.value_of(result) if result else 0.0)
        old = self.qv(key)
        self.q[key] = old + rate * (target - old)
        if key[0] != "hand" and self.q[key] >= KNOW and key not in self.known:
            self.known[key] = (tick, source)
            return True
        return False

    @property
    def stage(self) -> int:
        return 0 if self.age < INFANT else (1 if self.age < ADULT else 2)
