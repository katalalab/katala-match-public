# Katala Person Model

Date: 2026-05-18
Status: v0 implementation in `src/katala_match/core/person_model.py` and `core/match_context.py`

## Purpose

Katala should not reduce people to average matching fields. The person model keeps a person as an evidence-backed variable space so that unusual but valuable variables can survive scoring.

This implements Variable-as-Variable Matching:

- declared variables are useful, but incomplete
- observed choices reveal tradeoffs that self-report misses
- latent needs and unique strengths must be first-class
- context and power constraints decide whether a match is actually fair

## Four Layers

| Layer | File object | Meaning | Example |
|---|---|---|---|
| 1. Declared | `DeclaredLayer` | explicit goals, hard constraints, preferences, dislikes, direct quotes | budget cap, remote-only, "do not push me into a decision" |
| 2. Behavioral | `BehavioralLayer` | accepted/rejected options and revealed tradeoffs | chose more space over shorter commute |
| 3. Latent | `LatentLayer` | inferred needs, values, risks, unique strengths | safety, autonomy, systems thinking |
| 4. Context | `ContextLayer` | roles, stakeholders, time horizon, resources, safety/power constraints | parent, borrower/owner asymmetry, renewal deadline |

## Why This Matters

The old match style compresses people into shared columns. That works for commodity filtering but fails for people who have non-average strengths or non-obvious constraints.

Katala's rule is different:

1. Never treat a missing variable as absence of value.
2. Preserve provenance: declared, behavior, inference, or context.
3. Keep confidence separate from weight.
4. Let domain scorers read the same person model, not invent local profile formats.
5. Treat hard constraints as gates, not as low scores.

## Implementation Notes

`PersonModel.variables()` returns all known variables across the four layers. `PersonModel.variable_map()` keeps the strongest evidence per variable name by `weight * confidence`.

`hard_constraint_failures(candidate)` is intentionally simple. It proves that hard constraints can be reused across domains, but richer operators are still needed:

- numeric range constraints
- "must not contain" constraints
- temporal constraints
- bilateral constraints between two people

`MatchContext` is the current bridge from domain data into mediation. It carries:

- domain name
- candidate id, label, and payload
- people as `PersonModel`
- observed messages as `PersonMessage`
- shared case context

Concrete people belong in a case-local JSON file, not in this package. A
`PersonModel` is evidence for one matching run, not a global user profile.

## Known Gap

The new `jobs`, `coaching`, and `dating` demo domains prove the existing `Pipeline` abstraction is enough for Source/Gate/Scorer/Selector. They do not yet prove that `Pipeline` is enough for bilateral person-to-person matching. That requires either:

- a `MatchPair` candidate type, or
- a second pipeline stage that scores `PersonModel x Candidate`.

This is the main design pressure discovered in this implementation pass.
