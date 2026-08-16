# Qualified Review Protocol

Workflow implementation status: **EXECUTABLE IN THE RESEARCH REVIEW TAB**

Review execution status: **NOT EXECUTED**

This protocol prepares a bounded domain-review activity. It does not claim that
expert validation has occurred.

The Streamlit workflow records the governance reference, competence scope,
cases reviewed, five ratings, safety-critical findings, required corrections,
reviewer sign-off reference and project-author disposition. Records are
exportable and included in the complete JSON evidence package. The software
does not verify reviewer identity or qualifications and never converts a saved
record into automatic professional validation.

## Governance gate

Before recruiting or recording any person, obtain written confirmation from the
supervisor that the activity is covered by the approved project ethics position.
The approved proposal described no participant interviews/questionnaires; a new
participant study may require an amendment. Do not collect names, employer details
or personal data without an approved lawful process and participant information.

## Reviewer criteria

- Chartered or demonstrably qualified fire-safety professional, building-control
  professional, or academic specialising in fire/evacuation engineering.
- Familiarity with BIM/IFC is desirable but not mandatory.
- Conflict of interest and competence scope recorded without unnecessary personal
  data.

## Evaluation pack

- controlled IFC ground-truth report;
- one semantic public IFC partial case;
- Montebello geometry-derived limitation case;
- one regulation evidence trace;
- one normal evacuation scenario;
- one worst-case route disruption;
- one ASET/RSET-inspired fire screen;
- complete assumption registry and claim boundary.

## Review questions

1. Are verified and inferred BIM relationships distinguished clearly enough?
2. Are route, width and travel-distance measurements represented correctly for
   the supplied controlled case?
3. Are the scenario explanation and evidence trace understandable and complete?
4. Could any risk/check label be mistaken for approval or statutory compliance?
5. Are the fire/worst-case assumptions and score directions transparent?
6. Which output is useful for early-stage screening, and which should be removed?
7. What minimum additional evidence is required before practical use?

Use a five-point relevance/clarity scale only if ethics approval covers it. Retain
verbatim qualitative comments only with explicit consent.

## Acceptance rule

Objective 5 may be described as externally reviewed only after at least one
qualified reviewer has completed the protocol and every safety-critical correction
has been resolved or explicitly dispositioned. One reviewer remains preliminary
evidence, not generalisable validation.

## Execution steps

1. Obtain the written supervisor/ethics confirmation reference.
2. Run a representative IFC and open `Research Review`.
3. Expand `Structured Preliminary Domain Review`.
4. Have the permitted reviewer complete the record without collecting
   unnecessary personal data.
5. Download the preliminary review JSON and retain the referenced sign-off.
6. Resolve or explicitly disposition every safety-critical correction.
7. Report the review as preliminary external evidence, not certification.
