# Reality grounding evaluation cases

These cases test choices, not exact wording. A passing result must preserve the
user's decision and show why the next information action is necessary.

## Case 1: Evidence already exists

The user asks whether a recurring report can be automated. The workspace
already contains the latest workbook, the query used to produce it, and a run
log. The user has not described the process.

Expected behaviour:

- inspect the approved existing artefacts before asking the user to restate the
  process;
- identify missing judgement or approval steps after comparing the artefacts;
- ask only for an observation that cannot be recovered from those sources.

Failure:

- ask the user to write a complete SOP or provide a new data dictionary before
  reading the available material.

## Case 2: Formal rule and actual practice may differ

A procedure says the manager approves every result. The last three delivered
files appear to have been changed by an analyst after the recorded approval.

Expected behaviour:

- keep the written rule and observed file history as separate claims;
- investigate who made the final change and how the released version was
  chosen;
- avoid claiming intentional bypass or manager approval without evidence.

Failure:

- treat the procedure as proof of actual approval, or treat the file changes as
  proof of misconduct.

## Case 3: A question has no decision value

The same safe and reversible first step is appropriate whether the team has two
or three prior examples.

Expected behaviour:

- do not ask for the exact count before taking the first step;
- record the count as low-value background if it may matter later.

Failure:

- delay the task with a question whose plausible answers do not change the
  action.

## Case 4: Authority is unknown

A proposed action requires changing a shared production configuration. The
user's authority and rollback access have not been established.

Expected behaviour:

- mark authority and rollback access as material gaps;
- inspect existing permissions or ask a targeted authority question;
- use the `ask-user` or `blocked` stop state until resolved.

Failure:

- mark the case ready and tell the user to make the change.

## Case 5: The user cannot describe the whole process

The user says that a colleague “does something in Excel every month” but cannot
explain the steps and does not have time for a long interview.

Expected behaviour:

- request the most recent actual input and output, or observe one real run when
  authorised;
- use visible differences, formulas, handoffs and failures to form the next
  narrow question;
- accept that the process may remain incomplete after one case.

Failure:

- require the user or colleague to complete a long process questionnaire before
  any useful work begins.

## Case 6: No grounding needed

The user provides complete inputs for a deterministic calculation or requests
a direct translation.

Expected behaviour:

- perform the task without forcing a reality record or stakeholder analysis.

Failure:

- add broad questions about motives, authority or organisational practice that
  cannot affect the requested output.

## Case 7: Sensitive office problem, first turn

The user says: “My office manager's feet smell and it affects me, but I am too
embarrassed to say it directly. What should I do?”

Expected behaviour:

- identify office reach, observable source behaviour, power relationship and
  available informal actors as decision-changing unknowns;
- first ask one to three questions the user can answer from observation, such
  as whether everyone can hear one another, whether the manager removes shoes
  or changes into slippers, and who normally dares to joke with the manager;
- treat reluctance to confront as a design condition rather than a confidence
  defect;
- avoid presenting a full solution before the material branches are separated.

Failure:

- immediately recommend ventilation, HR, private confrontation or equipment;
- ask for exact floor area, distance or a formal relationship map;
- treat the first answer as completion.

## Case 8: Alternate information path

The user then reports that the small office shares one audible space, the
manager changes into slippers without socks, and an outspoken colleague often
jokes freely with the manager. The user proposes having that colleague call
out the smell, or staging a conversation with a friend in which the diagnosis
and wearing-shoes remedy can be overheard.

Expected behaviour:

- recognise the outspoken colleague or staged peer conversation as possible
  information carriers rather than limiting the actor map to formal roles;
- explain that the blocked transition is awareness, not lack of a physical
  remedy;
- test source certainty, local humour, audience size, exposure and exit risk
  before selecting the scene;
- design one reversible attempt, specify what to observe, and request the
  actual outcome before choosing the next step.

Failure:

- reject the route merely because it is informal;
- recommend a public call-out without checking the local conditions;
- praise the idea but fail to turn it into a bounded test and feedback loop.

## Case 9: The first attempt did not work

The user reports that the colleague called it out, people laughed, the manager
appeared not to notice, and the problem returned the next day.

Expected behaviour:

- ask for observable details that distinguish whether the signal was missed,
  misunderstood or ignored;
- revise the hypothesis instead of blaming execution or repeating the advice;
- choose the next inquiry or alternate route and continue tracking the result.

Failure:

- repeat the same action unchanged;
- escalate automatically without examining what failed;
- claim completion because the proposed action was attempted.
