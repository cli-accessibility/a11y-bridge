# CLI Accessibility — Presentation Notes

---

## Slide 1: The Problem

### During Development — The Builders Have No Standard

Teams building CLI tools (developers, QA, DevOps) have no way to know if their tool is accessible. There is no WCAG for terminals. No test suite. No compliance checklist. Each team guesses independently — most don't think about it at all.

Result: tools ship with accessibility gaps nobody measured.

### After Development — Two Groups Are Locked Out

**Group 1: "I can't see the output"**

This group includes blind users with screen readers, low-vision users with magnifiers, and color-blind users. They all face the same core problem: CLI output is unstructured text with no semantic markup.

- A screen reader reads `oc get pods` as a stream of words — no column headers, no row boundaries
- A magnifier user sees 20 characters at a time across a 100-character table — no color to scan by
- A color-blind user can't distinguish red errors from green successes when color is the only indicator

These aren't edge cases. 8% of males have color vision deficiency. Over 2 million developers globally have a visual disability.

**Group 2: "I can't type the input"**

This group includes motor-impaired users (RSI, paralysis, switch access), non-technical users (PMs, support engineers, students), and anyone who doesn't have CLI syntax memorized.

- A motor-impaired user needs to type `oc get pods -n rhtas-tenant --sort-by='.status.phase'` — 55 characters of precise syntax with dots, quotes, and dashes
- A product manager checking release status doesn't know the difference between `oc get` and `oc describe`
- A support engineer troubleshooting a customer environment needs to run 5 commands they don't remember

The common thread: CLI tools demand expert syntax knowledge and precise motor control. No alternative input exists.

---

## Slide 2: The Solution

### During Development — CLI-ACS Conformance Suite

**For the builders.** A Go binary that evaluates any CLI tool against 98 accessibility criteria across 9 domains. Produces a conformance report the org can publish.

```bash
cli-acs check /usr/bin/oc
```

**Output:** "oc passes 24 of 31 tested criteria. Failures: no examples in help text (HD-6), no man page (HD-9), no --no-color flag (CV-3)."

The org now has:
- A measurable baseline
- Specific gaps to fix, prioritized by severity (Level A → Level AA → Level AAA)
- A publishable report for procurement and compliance teams
- A CI gate: `cli-acs check --threshold AA` fails the build if accessibility regresses

### After Development — a11y-bridge Wrapper

**For the users.** A Python tool that wraps any CLI binary and compensates for its accessibility gaps. The org's CLI doesn't need to change.

**For Group 1 — "I can't see the output":**

| Problem | a11y-bridge compensation |
|---|---|
| Tables are word soup for screen readers | Converts to labeled sentences: `NAME: nginx. STATUS: Running.` |
| No color hierarchy for low-vision users | Adds semantic color: Running=green, Error=red, Pending=yellow |
| Color is sole indicator for color-blind users | Adds text prefixes: `[OK]`, `[ERROR]`, `[WARN]` alongside color |
| Unicode symbols are meaningless to screen readers | Replaces: ✓→`[OK]`, ✗→`[FAIL]`, ⚠→`[WARN]` |
| Hyperlinks invisible to assistive tech | Extracts URLs as visible text |

```bash
# Screen reader user
a11y-bridge --domain screen-reader oc get pods

# Low-vision user
a11y-bridge --domain color oc get pods
```

**For Group 2 — "I can't type the input":**

| Problem | a11y-bridge compensation |
|---|---|
| Commands require precise syntax | AI translates natural language: "show failing pods" → `oc get pods --field-selector=status.phase=Failed` |
| Can't type fast (motor impairment) | Voice input: press `v`, speak, press Enter |
| Don't know the right command (non-technical) | AI suggests commands and explains output in plain language |
| Error messages are jargon | AI explains: "You don't have permission. Ask your admin to run..." |
| Need hands-free operation | Audio output speaks results, earcons for success/failure |

```bash
# Motor-impaired or non-technical user
a11y-bridge --domain color,audio --askai oc

you: v
heard: are any pods failing
result: 1 pod failing. failing-demo, status Error, 5 restarts.
(spoken aloud)
```

### The Full Loop

```
DURING DEVELOPMENT                    AFTER DEVELOPMENT
                                      
Org builds CLI tool                   Users operate the CLI
        |                                     |
        v                                     v
CLI-ACS Conformance Suite             a11y-bridge wraps the CLI
        |                                     |
        v                                     v
Conformance report:                   Compensates per group:
"24/31 criteria pass"                 
                                      Group 1 (can't see):
Fix gaps in next release              → labels, color, symbols
        |                             
        v                             Group 2 (can't type):
Tool improves over time               → AI, voice, plain language
```

The suite tells builders where to improve. a11y-bridge ensures users are never blocked while waiting.

---

## Timing

| Section | Duration |
|---|---|
| Slide 1: During development — no standard | 15s |
| Slide 1: Group 1 — can't see the output | 20s |
| Slide 1: Group 2 — can't type the input | 25s |
| Slide 2: Conformance suite for builders | 20s |
| Slide 2: a11y-bridge for Group 1 | 20s |
| Slide 2: a11y-bridge for Group 2 | 20s |
| **Total** | **2 min** |
