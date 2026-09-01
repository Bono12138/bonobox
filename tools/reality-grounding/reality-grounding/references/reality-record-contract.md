# Reality record contract

A reality record preserves the evidence and remaining uncertainty needed for
one decision. It is not a general stakeholder database.

## Required sections

### Decision

- `question`: the choice or judgement that must be made now;
- `desired_outcome`: the result the user is trying to obtain;
- `unacceptable_downside`: the loss or exposure that must be avoided;
- `deadline`: the real time limit when one exists.

### Claims

Each claim has a unique ID, statement and one status:

- `verified_fact`;
- `direct_observation`;
- `user_report`;
- `formal_rule`;
- `observed_practice`;
- `supported_inference`;
- `working_hypothesis`;
- `unknown`.

Facts, observations, reports and rules record source type, reference, date and
scope. An inference or hypothesis points to supporting claim IDs and, when
useful, evidence that would disprove it.

### Constraints

Record only conditions that can change the action: authority, access, time,
resource, required cooperation, rule or risk. Mark each as verified, reported
or unknown. An unknown material constraint must appear as a gap.

### Decision-changing gaps

Each gap states:

- the unanswered question;
- which decision branch it affects;
- impact: `critical`, `high`, `medium` or `low`;
- how different answers change the action;
- current status: `open`, `resolved`, `deferred` or `blocked`;
- the next evidence action and why that source is appropriate.

Permitted next actions are:

- `inspect-existing-evidence`;
- `use-approved-tool`;
- `observe-real-work`;
- `run-reversible-probe`;
- `ask-targeted-question`;
- `proceed-with-assumption`;
- `blocked-by-permission`.

### Proposed actions

Every proposed action names the actor, required conditions, supporting claim or
resolved-gap IDs, completion state, stopping condition and fallback. A proposal
that depends on unknown authority, access or cooperation is not yet feasible.

### Stop state

Use exactly one state:

- `ready`;
- `ask-user`;
- `proceed-with-assumptions`;
- `blocked`.

The reason must explain why further investigation would or would not change the
decision. List any remaining material gap IDs.

## Promotion rules

| Produced item | Default destination | Promotion condition |
|---|---|---|
| raw source or direct observation | source evidence | authorship, date and scope recorded |
| current case fact | case state | supported by an approved source or direct observation |
| actor motive | case hypothesis | never treated as fact without evidence |
| stable personal preference | profile candidate | repeated or directly confirmed |
| stable business rule | domain-knowledge candidate | verified through the owning knowledge process |
| action plan | decision artifact | not evidence merely because it was generated |
| observed outcome | case history and source evidence | actual result recorded with time and context |

Every promoted item keeps provenance, scope and effective time. An inference
cannot become a fact by being repeated across Agent outputs.

## Machine validation

For substantial cases, store the record as JSON and run:

```bash
python scripts/validate_reality_record.py path/to/reality-record.json
```

The validator checks structural conditions that should not depend on prose
quality: evidence-bearing claims have sources, material gaps have branches and
next actions, targeted questions can change the action, unknown execution
constraints are tracked, and a `ready` record has no open critical or
high-impact gap. It cannot prove that a source is true or that the proposed
strategy is good.
