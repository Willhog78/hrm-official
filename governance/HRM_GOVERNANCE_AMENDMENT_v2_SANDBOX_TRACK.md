# HRM Governance Amendment v2 — Exploratory Sandbox Track

**Date:** 2026-09-23
**Status:** PROPOSED. It takes effect when the project owner signs below.
**Amends:** HRM Master Development Plan v1.1, §11 (Development Discipline: "one active stage at a time").

## Problem

Under §9/§11, no human behaviour can be run until Stages 1–8 have each been built, qualified,
reviewed, and frozen in sequence. That keeps the evidence chain clean. It also means years of
work with nothing to watch, and no early signal on whether the later-stage design ideas behave
interestingly at all.

## Change

A parallel **sandbox track** (`sandbox/`) is permitted alongside the active stage:

1. Sandbox simulations may model any layer (world, ecology, humans, cognition, social
   learning) at any fidelity, regardless of which governed stage is active or frozen.
2. Sandbox outputs are **never** qualification evidence. They may not be cited in a stage
   contract, review, freeze decision, or §8 status assignment.
3. Governed code (`src/`, `qualification/`, `tests/`, `drafts/`) must not import sandbox code.
   Sandbox code may import governed code read-only.
4. A sandbox mechanism enters the governed build only the way Stage-0 salvage does. It is
   a candidate idea with a stated causal purpose, rebuilt and qualified under §8.1 in its own stage.
   Sandbox code does not migrate forward merely because it ran.
5. The sandbox still follows §2: no scripted technologies, social orders, or outcomes. It is
   loosened on rigour, not on the core rule. Otherwise it would show nothing about the model's
   premise.

## What this does not change

The stage gates, the review policy (Amendment v1), Stage 1's ACTIVE / not-frozen status, and
Stage 2's quarantine are unchanged.

## Owner sign-off

- [ ] Approved by project owner: ____________________  Date: __________
