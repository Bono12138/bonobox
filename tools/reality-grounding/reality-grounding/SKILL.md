---
name: reality-grounding
description: Actively discover how a situation really works before advice, planning, or system design. Use when the answer may depend on missing facts, actual permissions, stakeholder behaviour, informal practice, available evidence, or feasibility; inspect approved sources and ask only decision-changing questions instead of guessing or prescribing an ideal process.
---

# Reality Grounding

Find enough reality to make the next decision without inventing an ideal
organisation. This Skill is not a questionnaire and not a one-turn advice
generator. It owns an active loop of inquiry, action, observed feedback and
revision until the user confirms a real stopping point.

Standalone version: `0.3.0`.

Read `references/active-inquiry.md` when material facts are missing, the user
asks for proactive investigation, or the available source should be chosen.
Read `references/reality-record-contract.md` when the task needs a durable case
record or will feed a later strategy or execution step. Use
`scripts/validate_reality_record.py` before treating a substantial reality
record as ready for strategy. Use `references/evaluation-cases.md` when testing
or changing this Skill's routing and inquiry behaviour.

## Lock the decision first

Identify the decision the user must make, the desired result, unacceptable
downside, time limit, and which new fact could change the action. If there is no
real decision yet, clarify the problem before collecting broad background.

Separate:

- verified fact;
- direct user observation or report;
- formal rule;
- observed practice;
- supported inference;
- working hypothesis;
- unknown.

A document proves what it says, not that people follow it. A repeated Agent
claim does not turn a hypothesis into a fact.

Before substantial advice, decide whether the current information can actually
separate the available routes. If a material unknown changes the actor, first
step, feasibility or social risk, ask first. A short preview of the branches
may explain the question; it must not become a premature catalogue of advice.

## Investigate actively

For every unknown that could change the decision:

1. Write the different answers and how each would change the next action.
2. Look first for evidence that already exists and is authorised: actual task
   files, prior outputs, system records, approved business sources, logs,
   queries, messages supplied by the user, or direct observation.
3. Use a tool or source the user has authorised to inspect the strongest
   available evidence. Do not request a new governance document when an existing SQL,
   report, example, screenshot, run record, or responsible operator can answer
   the question.
4. If existing evidence cannot answer it, use a small reversible probe or ask
   the narrowest question whose answers lead to different actions.
5. Update the reality record, reconsider the remaining gaps, and repeat only
   while another answer could still change the decision.

Do not ask the user to repeat information already available in the current
conversation or approved workspace. Do not wait for a perfect picture when the
remaining uncertainty does not change the action.

Assume the user may report only the painful symptom and may not know what
background matters. The Agent owns gap discovery and the next inquiry. Do not
wait for the user to volunteer the rest or ask them to perform the analysis.

## Check actual execution conditions

Inspect only the dimensions that matter to this case:

- interests and private costs;
- decision, veto, delay and resource power;
- information held by each actor;
- formal rules versus observed practice;
- current authority, access, time, skill, budget and relationships;
- dependencies on other people and their default inaction;
- previous behaviour and expectations created by repeated interaction;
- failures, exceptions, rework and human takeover;
- acceptance, responsibility, stopping and exit conditions.

Consider self-interest and bounded rationality. Resistance may also come from
missing information, limited skill, habit, fear of responsibility or lack of
time. Keep competing explanations until evidence separates them.

## Ask only useful questions

Ask when the answer can change the decision, risk boundary, required authority,
or first executable step and cannot be obtained more reliably from an approved
source. Prefer one to three high-value questions at a time.

A useful question states or internally records:

- what is unknown;
- why it matters now;
- what action follows from materially different answers;
- what existing example or observation would be enough.

If the user is unlikely to know the formal answer, ask for the last real case,
current file, actual operator, observed failure, or other concrete evidence.
Do not ask someone to describe a complete SOP when the task can be discovered
from actual work and artefacts.

Make questions answerable from ordinary observation. Use scene choices,
relative positions, recent events and visible behaviour instead of requesting
measurements or abstractions the user is unlikely to know. For example, ask
whether everyone can hear one another or the office is divided into separate
areas, rather than asking for exact floor area. If the user does not know,
change the evidence route or ask for an observable proxy.

## Find the blocked transition

Break the desired change into the states that must occur. Identify which
transition is blocked before searching for solutions. A user may already know
the physical remedy while being unable to make another person recognise the
problem. In that case, more remedies do not help; the work is to create a
credible, low-cost path to awareness.

When a direct transition is blocked, search for alternate carriers and
settings: an informal influencer, trusted peer, naturally outspoken person,
existing joke, routine, meeting, physical layout, timing, default rule, or a
small reversible probe. Do not restrict the actor map to the user and formal
roles such as manager, HR or administrator.

An indirect scene may carry both the diagnostic signal and an available next
action. For example, a conversation that the relevant person can naturally
overhear may cause self-recognition while also mentioning the behaviour that
would remove the problem. Treat this as designed information flow, not as a
generic recommendation to hint or manipulate. Check audience size, source
certainty, power relations, local humour, deniability, humiliation risk and
how the scene can stop if it lands badly.

## Keep ownership after the first action

Choose a proportional action or reversible probe, state what the user should
observe, and ask what actually happened. Update the hypotheses and choose the
next inquiry or action. Do not blame execution merely because the expected
effect did not occur, and do not repeat the same advice unchanged.

Giving advice is not completion. The issue stops only when the user confirms
the outcome is achieved or acceptable, chooses to stop, or further progress
requires unavailable access or authority.

## Refuse the ideal-world shortcut

Before recommending an action, check whether it assumes:

- authority or access the user does not have;
- willing cooperation with no reason to expect it;
- a document, system, budget or role that has not been shown to exist;
- formal rules being followed in practice;
- complete information held by every actor;
- an inferred motive being true;
- somebody else accepting cost, risk or maintenance for no visible reason.

If an assumption is material, investigate it, branch the plan, or mark the
action infeasible. Do not hide it inside polished advice.

## Finish at a real stopping point

The grounding pass can end in one of four states:

- **ready:** material branches are supported and strategy can begin;
- **ask user:** one or more decision-changing questions require the user's
  observation, choice or authority;
- **proceed with assumptions:** remaining gaps do not justify more collection
  and the assumptions and consequences are explicit;
- **blocked:** required evidence or action is unavailable without new access or
  authority.

Do not mark the record ready while a critical or high-impact gap remains open.
The output must tell the next method what is known, what remains uncertain,
what the user can actually do, and which routes have already been ruled out.

## Public-use boundary

The Skill changes the Agent's investigation instructions. It does not grant
access to files, systems, messages or people. Use only sources and tools already
authorised for the current task. Do not ask the user to paste credentials,
private company data or confidential documents into chat merely to complete a
reality record.
