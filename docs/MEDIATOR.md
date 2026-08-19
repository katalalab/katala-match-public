# Katala Mediator

Status: v0 implementation in `src/katala_match/core/mediator.py`,
`core/translation_loss.py`, and `core/llm_mediator.py`.

## Summary

The mediator turns "AI matching" into mediation. Its job is not to maximize
generic agreement. Its job is to preserve each person's variables, reduce
translation loss, and produce a next action that does not erase minority
constraints.

This extends Variable-as-Variable Matching into conversations:

- people are variable spaces, not profile rows
- statements lose meaning when moved across people and contexts
- mediation must detect that loss before ranking options

## Relation to the Habermas Machine

The loop is inspired by the published Habermas Machine design
(`google-deepmind/habermas_machine`): generate multiple candidate consensus
statements, predict each participant's ranking, aggregate, then revise after
critiques. No code or prompt text from that project is included here — only the
loop shape. The objective differs:

| Habermas Machine | Katala Mediator |
|---|---|
| citizens' jury consensus | bilateral/multilateral need matching |
| opinion text | `PersonModel` + `PersonMessage` |
| candidate statement | candidate match explanation or next action |
| reward model ranks agreement | coverage + translation-loss score |
| critique round | hearing question / NVC repair / variable clarification |
| social choice winner | least-erasing candidate, with unresolved variables visible |

## Translation Loss L1-L7

Implemented in `translation_loss.py`.

| Level | Name | Why it matters |
|---|---|---|
| L1 | lexical ambiguity | "safe", "properly", "feels good" are not conditions |
| L2 | RSA pragmatic mismatch | people imply more than they literally say |
| L3 | NVC need translation | complaints often hide unmet needs and requests |
| L4 | preference compression | one score can erase incompatible variables |
| L5 | context omission | the same sentence means different things by role/timing |
| L6 | power/incentive distortion | agreement may be compliance under pressure |
| L7 | temporal drift | today's need may not be next month's need |

L2 and L3 are the hot path. If both are high, the mediator should ask a
question before recommending a match.

## Prompt Shape

`KATALA_MEDIATOR_PROMPT` avoids majority averaging:

```text
Goal:
- Produce a candidate statement or match explanation that preserves each
  person's hard constraints, names the shared variable overlap, and identifies
  unresolved translation losses.

Rules:
- Do not average people into a generic majority preference.
- Separate explicit preferences from inferred needs.
- Translate criticism into observation, feeling, need, and request when possible.
- Keep minority hard constraints visible.
- Return: candidate statement, variable coverage, unresolved risks, next question.
```

Structured outputs and evidence are requested rather than hidden reasoning text.

## Current API

`KatalaMediator.mediate(question, people, messages, candidates=None, context=None)`
returns:

- `winner`: top candidate statement
- `sorted_candidates`: all candidates ordered by aggregate score
- `rankings`: per-person coverage and translation-loss report
- `next_questions`: generated when loss is high

The current ranking score is:

```text
score = variable_coverage * 0.7 + (1 - translation_loss) * 0.3
```

Deliberately simple and testable. A learned ranker can replace it later.

## LLM Extension

`core/llm_mediator.py` provides a provider-neutral structured output shape:

- `StructuredMediatorOutput`
- `StructuredMediator` protocol
- `GeminiStructuredMediator` / `ClaudeStructuredMediator` (optional extras)
- `build_llm_mediator_prompt(context, deterministic)`

The LLM layer consumes a deterministic `MediationResult` plus `MatchContext` and
renders candidate explanation, NVC translation, unresolved variables, and next
questions. It does not replace hard gates or hide minority constraints.

## Jobs False-Negative Path

`domains/jobs/false_negative.py` and `domains/jobs/mediator_adapter.py` show why
Variable-as-Variable Matching matters:

- a candidate can be rejected by average signals such as degree, years,
  company tier, or keyword score
- the same candidate can be rescued when the role needs rare variables such as
  ambiguous problem structuring, operator empathy, or agentic tooling literacy
- the rescue uses the same `MatchContext -> KatalaMediator` shape as any other
  domain

## Remaining Design Pressure

The common `Pipeline` interface is still candidate-centric, while mediation is
naturally person-pair or group-state centric. Recommended next changes:

1. Let domain scorers accept both `Candidate` and `PersonModel`.
2. Add a selector that can preserve minority hard constraints across groups.
3. Promote LLM mediator rendering from optional adapter to a verified path once
   model/provider settings are pinned.
