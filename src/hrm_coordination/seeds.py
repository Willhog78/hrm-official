from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random

from .model import canonical_json


@dataclass(frozen=True)
class SeedBank:
    """Deterministic namespace isolation for component-local random streams.

    A stream seed depends only on the master seed and explicit stream ID. Consuming
    random numbers from one stream therefore cannot advance or perturb another.
    """

    master_seed: str

    def derive_int(self, stream_id: str) -> int:
        if not stream_id:
            raise ValueError("stream_id required")
        payload = canonical_json({"master_seed": str(self.master_seed), "stream_id": str(stream_id)})
        digest = hashlib.sha256(payload.encode("utf-8")).digest()
        return int.from_bytes(digest[:16], "big", signed=False)

    def stream(self, stream_id: str) -> random.Random:
        return random.Random(self.derive_int(stream_id))
