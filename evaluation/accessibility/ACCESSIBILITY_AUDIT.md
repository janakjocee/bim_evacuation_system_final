# Accessibility Audit

Status: automated checks complete; browser-only manual checks not yet signed off.

## Automated evidence

- Custom light and dark semantic text/background pairs are checked at a minimum
  WCAG contrast ratio of 4.5:1 by `tests/test_ui_workflows.py`.
- AppTest executes every main workflow control group, scenario details, manual
  corrections, review status, exports, all fire scenarios/growth classes/control
  boundaries and all worst-case origins/control boundaries.
- Form controls use visible Streamlit labels rather than placeholder-only labels.
- Risk and status information is presented in text as well as colour.
- The interface includes a reduced-motion media rule for custom hover movement.

These checks are evidence of selected accessibility properties, not a WCAG
conformance certification.

## Manual browser checklist

The project author should record date, browser, operating system and outcome for:

- keyboard-only traversal reaches every upload, tab, filter, details, correction,
  review and download control in a logical order;
- focus indicators remain visible in light and dark operating-system modes;
- browser zoom at 200% has no hidden controls or horizontal page-level clipping;
- screen-reader names for icon-prefixed buttons remain understandable;
- Plotly route/3D charts have adjacent textual summaries conveying the same key
  origin, destination, risk and route evidence;
- error, warning and success messages are announced and do not rely on colour;
- mobile-width layout remains usable for the demo, while desktop remains the
  recommended engineering-review viewport.

Manual outcome: **NOT EXECUTED / NOT SIGNED OFF**. Do not state WCAG compliance
in the dissertation unless this checklist is completed with retained evidence.
