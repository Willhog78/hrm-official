"""Streaming replay ledger: identical evidence, bounded memory, exact resume."""

from __future__ import annotations

import gzip
import json

import pytest

from hrm_coordination import ProvenanceError, StreamingReplayLedger
from hrm_genesis import GenesisSimulation
from hrm_genesis.checkpoint import load_genesis_checkpoint, write_genesis_checkpoint
from qualification.genesis.tier_observer import build_config

DAYS = 16


@pytest.fixture(scope="module")
def config():
    return build_config("agentus-demography-a", "v1")


@pytest.fixture(scope="module")
def reference(config):
    sim = GenesisSimulation(config)
    sim.run(DAYS)
    return sim


def test_streaming_matches_in_memory_and_keeps_only_a_buffer(tmp_path, config, reference):
    sim = GenesisSimulation(config, ledger_path=str(tmp_path / "l.gz"), ledger_buffer_epochs=4)
    sim.run(DAYS)
    assert isinstance(sim.ledger, StreamingReplayLedger)
    assert sim.ledger.digest() == reference.ledger.digest()
    assert sim.fabric.causal_state_digest() == reference.fabric.causal_state_digest()
    assert len(sim.ledger.epoch_blocks) == 4 and sim.ledger.expected_epoch == DAYS
    assert sim.ledger.verify_chain()
    assert sim.ledger.replay_state() == reference.ledger.replay_state()
    assert sim.ledger.latest_state() == sim.ledger.replay_state()


def test_tampered_stream_fails_verification(tmp_path, config):
    path = tmp_path / "l.gz"
    sim = GenesisSimulation(config, ledger_path=str(path))
    sim.run(4)
    sim.ledger.close()
    lines = [json.loads(x) for x in gzip.open(path, "rb")]
    lines[2]["records"][0]["committed"][0]["new_value"] = {"edited": True}
    with open(path, "wb") as out:
        for obj in lines:
            out.write(gzip.compress((json.dumps(obj) + "\n").encode()))
    assert not sim.ledger.verify_chain()


def test_checkpoint_resume_equals_uninterrupted_and_discards_later_epochs(tmp_path, config, reference):
    sim = GenesisSimulation(config, ledger_path=str(tmp_path / "l.gz"))
    sim.run(DAYS // 2)
    ck = tmp_path / "ck.json"
    write_genesis_checkpoint(ck, sim)
    sim.run(3)  # evidence written after the checkpoint
    resumed = load_genesis_checkpoint(ck, config)
    assert resumed.ledger.expected_epoch == DAYS // 2
    resumed.run(DAYS - DAYS // 2)
    assert resumed.ledger.digest() == reference.ledger.digest()
    assert resumed.fabric.causal_state_digest() == reference.fabric.causal_state_digest()
    assert resumed.human_state() == reference.human_state()  # Agentus memories included
    assert resumed.ledger.verify_chain()


def test_checkpoint_with_edited_state_is_rejected(tmp_path, config):
    sim = GenesisSimulation(config, ledger_path=str(tmp_path / "l.gz"))
    sim.run(3)
    ck = tmp_path / "ck.json"
    write_genesis_checkpoint(ck, sim)
    payload = json.loads(ck.read_text())
    humans = next(a for a in payload["fabric"]["authorities"] if "human" in a["authority_id"])
    rid = next(iter(humans["state"]))
    humans["state"][rid]["humans"][0]["energy"] = 1.0
    ck.write_text(json.dumps(payload))
    with pytest.raises(ProvenanceError):
        load_genesis_checkpoint(ck, config)
