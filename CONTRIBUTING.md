# Contributing to AMAS

AMAS is currently in draft status and open for review.

## How to Contribute

### Feedback on the Specification

The most valuable contributions at this stage are:

- **Identify ambiguities** in the specification that would cause two implementations to behave differently.
- **Propose edge cases** that the conflict resolution protocol does not handle cleanly.
- **Challenge assumptions** — particularly around the tier classification of specific source types.
- **Prior art identification** — if you know of existing work that addresses the same problem space, please flag it.

Open an issue with the label `spec-feedback`.

### Implementation Reports

If you implement any portion of AMAS (even Level 1 minimal conformance), we want to hear about it:

- What worked as specified
- What required interpretation or judgment calls
- What was missing or underspecified

Open an issue with the label `implementation-report`.

### Code Contributions

The reference implementation (`reference/amcs.py`) accepts bug fixes and improvements that maintain backward compatibility with existing sealed cells. Changes that would invalidate previously sealed cells require a spec version bump and are handled through the spec review process, not code PRs.

### What We Are Not Looking For

- Marketing or promotional language changes to the README
- Weakening of HARD RULE constraints without a corresponding threat model justification
- Additions that introduce implicit behavior (AMAS is explicit-by-design)

## Code of Conduct

Be precise. Be constructive. Assume good faith. Disagree with evidence.
