# ADR-0001: Governance-first foundation for SMF Swarm 2.0

**Status:** Accepted  
**Date:** 2026-07-13  
**Deciders:** Aiona Edge (implementation), Michael Gannotti (sponsor)

## Context

Multi-agent frameworks often treat identity, permissions, and audit as afterthoughts. SMF Swarm 2.0 is differentiated by making governance architectural, not bolted on.

## Decision

Phase 1 implements **governance hooks** (identity, append-only hash-chained audit log, capability permission checks) as real, tested interfaces with minimal in-process implementations. Full cryptographic HBHC revocation is deferred to Phase 2.

Capability diagnosis is a **first-class platform module**, not SkillOpt-only code, with a mock backend for deterministic CI.

## Consequences

- All Phase 1 pipeline actions are identity-bound and auditable.
- Later crypto can replace identity store without changing call sites if interfaces hold.
- Offline tests remain fast and network-free.
- **Status (2026-07-13):** Phase 1 implementation met DoD; dual-path diagnostic (mock CI / LLM prod) validated on SkillOpt-style fixture. See `docs/PHASE1_STATUS.md`.

## Alternatives considered

1. **Governance later** — Rejected: recreates industry failure mode.
2. **Full HBHC in Phase 1** — Rejected: too large for first run; high risk of incomplete crypto.
3. **Depend only on SkillOpt prototype** — Rejected: wrong package boundary; Swarm needs a clean product surface.
