# Katala Connector

Date: 2026-05-20
Status: v0 theory and MVP scaffold

## Summary

Katala Connector is the layer that turns "繋ぐ" into a testable process.

It does not claim that a connection is correct. It generates a connection
hypothesis, scores it from multiple scholarly lenses, exposes uncertainty and
risk, and converts it into a small next action.

```text
Connect(a, b, context)
= create a low-translation-loss edge between people, knowledge, ideas,
  experiences, projects, or questions that can increase understanding,
  action, choice, recovery, or creation.
```

The output should never be a bare recommendation. It should be a mediated
connection:

- why this connection is proposed
- what variables it preserves
- what it may create together
- where translation loss or harm can happen
- what small action can test it

## Why This Belongs In Katala Match

Katala Match started with estate matching, but the deeper operation is not
"find a property." The deeper operation is:

```text
person variables <-> world options <-> evidence <-> other people <-> action
```

The same shape applies to:

- person to knowledge
- question to theory
- idea to implementation
- experience to reusable principle
- person to person
- project to external method

The Connector sits before `KatalaMediator`:

```text
Observe -> Variable extraction -> Connector -> Mediator -> Activation -> Feedback
```

Connector asks: "What should be connected?"

Mediator asks: "How do we connect it without erasing variables?"

## Core Definitions

### Connection

A connection is an evidence-backed edge between two nodes that may produce
action, understanding, option quality, or structural gain.

### Creativity

This adopts the existing creativity kit framing:

```text
Creativity(z)
= MeaningfulDistance(z)
  * Connectability(z)
  * StructuralGain(z)
  * PracticalGain(z)
  * Adoptability(z)
  - Fragility(z)
```

For Connector, creativity appears when a candidate edge is far enough to add
structure, but close enough to be translated and tested.

### Synergy

Synergy is the surplus created by a connection:

```text
Synergy(a, b, context)
= Value(a + b in context) - Value(a alone) - Value(b alone)
```

In v0, Katala estimates synergy qualitatively through:

- complementarity
- bridge value
- new action space
- structural gain
- reduced translation loss

## Node Model

Connector treats the following as nodes:

| Node | Meaning |
| --- | --- |
| `person` | A person represented by variables, needs, constraints, and context. |
| `knowledge` | A theory, paper, book, skill, document, or method. |
| `idea` | A proposed concept or design move. |
| `experience` | A past case, failure, success, or field observation. |
| `question` | A live uncertainty or inquiry. |
| `project` | A concrete goal or implementation context. |
| `action` | A small next step that can test a connection. |

Each node has:

- `themes`: surface topics
- `variables`: deeper reusable variables
- `needs`: what the node seeks
- `offers`: what the node can provide
- `constraints`: hard limits or safety boundaries
- `contexts`: timing, domain, or operating environment

## Edge Model

Each candidate edge is scored by:

```text
ConnectionValue(a, b, context)
= NeedFit
+ Complementarity
+ TranslationPotential
+ TimingFit
+ TrustPath
+ Novelty
+ SynergyGain
- TranslationLoss
- ActivationCost
- Risk
```

This is not a truth score. It is a "worth testing" score.

## Scholarly Source Families

Connector v0 maps existing scholarly ideas into operational axes:

| Family | Operational use |
| --- | --- |
| Psychology | Motivation, cognitive load, self-efficacy, resistance, affective safety. |
| Biology / ecology | Adaptation, niche fit, energy cost, exploration/exploitation, mutualism. |
| Cognitive science | Analogy, schema bridge, conceptual blending, memory and attention. |
| Social network science | Weak ties, structural holes, brokerage, bridge value. |
| Information theory | Signal/noise, compression, entropy, translation loss. |
| Creativity research | Remote association, divergent/convergent balance, combinational/exploratory/transformational creativity. |
| Sociology / anthropology | Role, power, trust, norm mismatch, relational capital. |
| Design / practice | Affordance, prototypeability, adoption cost, next action clarity. |

The source families are used as lenses, not as claims that one discipline owns
the correct answer.

Reference anchors:

- Granovetter, "The Strength of Weak Ties" (1973): https://doi.org/10.1086/225469
- Burt, "Structural Holes" (1992): https://doi.org/10.4159/9780674029095
- Shannon, "A Mathematical Theory of Communication" (1948): https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf
- Mednick, "The Associative Basis of the Creative Process" (1962): https://doi.org/10.1037/h0048850
- Kaufman and Beghetto, "Four C Model of Creativity" (2009): https://doi.org/10.1037/a0013688
- March, "Exploration and Exploitation in Organizational Learning" (1991): https://doi.org/10.1287/orsc.2.1.71
- Laland et al., niche construction overview: https://doi.org/10.1007/s10682-016-9821-z

## Safety Principle

Person-to-person connection is heavier than person-to-knowledge connection.

The default rollout should be:

```text
Phase 1: person <-> knowledge
Phase 2: question <-> knowledge <-> idea
Phase 3: person <-> person, with consent and burden gates
```

No person-to-person introduction should be emitted without:

- clear purpose
- opt-in or consent path
- expected burden
- privacy boundary
- refusal path
- next action that is smaller than "please help me"

## v0 Output Shape

Each connection candidate should return:

- source node
- target node
- connection type
- shared variables
- complementary variables
- axis scores
- total score
- rationale
- risks
- next action

Example:

```json
{
  "connection_type": "question_to_knowledge",
  "source": "繋ぐをアルゴリズム化したい",
  "target": "weak ties / structural holes",
  "shared_variables": ["bridge_value", "non-obvious_access"],
  "complementary_variables": ["network_brokerage", "exploration"],
  "next_action": "Connector axis tableにsocial_network scoreを追加する",
  "risk": "人脈紹介に直接使うと期待値と負担が重くなる"
}
```

