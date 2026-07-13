# SMF Swarm 2.0 — Phase 1 Definition of Done

**Date:** 2026-07-13  
**Owner:** Aiona Edge  
**Status:** LOCKED for first implementation run  
**Process:** phd-level-full-stack-developer (Phase 0 → implement)

---

## In scope (Phase 1 only)

1. **Repo foundation** — installable Python package `smf-swarm` (v0.1.x), tests, README, ADRs.
2. **Capability Diagnostic (first-class)** — TRACE-inspired contrastive diagnosis of success vs fail trajectories; structured `CapabilityGap` output; mock mode for offline tests; optional OpenAI-compatible LLM backend.
3. **Governance hooks (real interfaces, minimal impl)**  
   - Agent identity (stable ID + metadata; extensible to crypto later)  
   - Append-only audit log with hash chain  
   - Capability permission checks (allow/deny by agent + capability name)  
4. **Minimal pipeline** — one entrypoint that: creates identity → runs diagnostic under permission check → writes audit events → returns gaps.
5. **Verification** — unit tests green; ad-hoc smoke script.

## Explicitly OUT of scope (later phases)

- Full HBHC cryptographic revocation
- Multi-tenant RBAC / enterprise SSO
- Dynamic topology engine / Council of High Intelligence
- LoRA training / GRPO
- Hermes Chat deep integration (optional note only)
- Production multi-node deploy

## Success criteria (checkable)

- [ ] `pytest -q` passes offline (mock diagnostic, no network)
- [ ] Diagnostic returns ranked gaps from fixture trajectories
- [ ] Every pipeline action emits an audit event with hash chain integrity
- [ ] Unauthorized capability exercise is denied and audited
- [ ] Docs: README + PHASE1_DOD + ADR-0001 governance-first

## Non-goals for this run

- Replacing `smfworks/smf-swarm` v1 predict pipeline
- Public PyPI release
- Full Swarm 2.0 seven-layer platform
