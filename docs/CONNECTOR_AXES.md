# Connector Evaluation Axes

Date: 2026-05-20
Status: v0 scoring lenses

Connector uses multi-axis evaluation because "繋ぐ" has no single correct
answer. A useful connection can be psychologically right but socially risky,
biologically costly but creatively valuable, or semantically distant but
structurally powerful.

## Axis Table

| Axis | Main question | Positive signals | Negative signals | Example score use |
| --- | --- | --- | --- | --- |
| Psychological | Can the person receive and act on this connection now? | motivation fit, lower anxiety, self-efficacy, clear next step | overload, shame, resistance, identity threat | `NeedFit - ActivationCost - Risk` |
| Biological / ecological | Does this improve adaptation or niche fit without excessive energy cost? | niche fit, recovery, mutualism, exploration/exploitation balance | energy drain, maladaptation, one-sided extraction | `TimingFit + Complementarity - ActivationCost` |
| Cognitive | Does it create a usable bridge between schemas? | analogy, chunking, compression, attention fit | abstraction overload, schema mismatch | `TranslationPotential - TranslationLoss` |
| Social network | Does it bridge useful distance safely? | weak tie value, structural hole bridge, trust path, brokerage | burden asymmetry, low trust, privacy leak | `TrustPath + Novelty + Complementarity - Risk` |
| Information theory | Does the connection increase signal and reduce noise? | compression, reduced ambiguity, lower entropy, clear evidence | noisy link, lossy translation, overfitting | `TranslationPotential - TranslationLoss` |
| Creativity | Does it create meaningful novelty that can be adopted? | meaningful distance, structural gain, transfer, practical use | mere novelty, fragility, no adoption path | `Novelty + SynergyGain - Risk` |
| Sociology / anthropology | Does it respect role, norm, power, and context? | consent, role clarity, norm fit, relational capital | coercion, status mismatch, hidden power | `TrustPath - Risk` |
| Design / practice | Can it be tested as a small action? | prototypeability, low friction, measurable next step | vague inspiration, no action, high setup cost | `PracticalGain - ActivationCost` |

## Scoring Contract

Each axis score is a bounded value:

```text
0.0 = weak or absent
0.5 = plausible but uncertain
1.0 = strong and evidence-backed
```

Each score carries:

- `evidence`: concrete matching variables or observations
- `risk`: why this axis could fail
- `next_probe`: what to ask or do next
- `source_theory`: scholarly lens used to interpret the score

## Why Axis Scores Beat One Score

One score hides the reason a connection is useful or dangerous. Axis scores
allow outputs like:

```text
High creativity, high cognitive bridge, low social safety.
=> Good as a reading recommendation; bad as a direct person introduction.
```

or:

```text
High psychological fit, low novelty.
=> Good support; not a creative breakthrough.
```

## Minimum Gates

Connector should not emit a strong recommendation when any of these are true:

- `risk >= 0.75`
- person-to-person target without consent path
- `translation_loss >= 0.75` and no clarifying question is generated
- `activation_cost >= 0.8` and no smaller action exists
- hard constraints are violated

When a gate fails, Connector should output a question or smaller bridge instead
of a recommendation.

## Feedback Labels

There is no "correct" label. Feedback should be weak and longitudinal:

| Label | Meaning |
| --- | --- |
| `activated` | The user took the next action. |
| `decision_helpful` | The connection helped a decision move. |
| `novel_useful` | It was unexpected but useful. |
| `later_useful` | It became useful after time passed. |
| `too_heavy` | It required too much effort or burden. |
| `unsafe` | It created social, emotional, privacy, or power risk. |
| `redundant` | It added no structure beyond what was already known. |
| `misfit` | It did not match the actual need or context. |

## Recommended v0 Weights

For person-to-knowledge:

```text
NeedFit              0.20
Complementarity      0.15
TranslationPotential 0.15
TimingFit            0.10
TrustPath            0.05
Novelty              0.10
SynergyGain          0.20
Risk penalties       0.20
Activation penalties 0.10
Translation penalties 0.15
```

For person-to-person, increase `Risk`, `TrustPath`, and consent gates before
any introduction is suggested.

