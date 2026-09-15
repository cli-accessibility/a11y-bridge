# a11y-bridge Demo Script (4 minutes)

A live demonstration of end-to-end CLI accessibility: from identifying gaps to bridging them with AI and voice.

**Audience:** Developers, accessibility teams, platform engineers.

**Setup before demo:**
- Terminal open, font size large enough for screen sharing
- `oc` logged into a cluster with pods running
- `A11Y_AI_KEY` and `A11Y_AI_PROVIDER` exported
- Piper voice model downloaded (`a11y-bridge setup`)
- Whisper model cached (run one `v` command beforehand so the model is loaded)

---

## Part 1: The Problem (45 seconds)

**Say:** "CLI tools are text-based, so people assume they're accessible. They're not. Let me show you."

**Run:**

```bash
oc get pods -n rhtas-tenant
```

**Say:** "This looks fine to us — a table with columns. But a screen reader reads it as:"

**Read aloud monotonically:** "NAME READY STATUS RESTARTS AGE model transparency on push z8v8x build images zero pod zero slash four Completed zero five m twenty eight s"

**Say:** "No column headers. No structure. The user has no idea which value belongs to which field. And this is a well-designed tool."

---

## Part 2: Measuring the Gap (45 seconds)

**Say:** "We built a conformance suite that evaluates any binary against 31 accessibility criteria. Let's check oc."

**Run:**

```bash
cli-acs check --domain color,help /usr/bin/oc
```

**Say while output appears:** "The suite auto-discovers the tool's capabilities — parses its help text, probes flags, tests color behavior."

**Point to results:** "oc passes 12 of 31 criteria. It fails on [point to specific failures] — no examples in help, no man page, no web docs link. These are the gaps. Now let's bridge them."

---

## Part 3: a11y-bridge Wraps It (45 seconds)

**Say:** "a11y-bridge wraps any CLI tool and makes its output accessible. Same command, prefix it."

**Run:**

```bash
a11y-bridge --domain screen-reader oc get pods -n rhtas-tenant
```

**Say:** "Every value is now paired with its column header. NAME colon nginx. STATUS colon Running. A screen reader can read this linearly and the user knows exactly what each value means."

**Run:**

```bash
a11y-bridge --domain color oc get pods -n rhtas-tenant
```

**Say:** "For sighted users, same command adds color — Running in green, CrashLoopBackOff in red, Pending in yellow. One tool, adapts to who's using it."

---

## Part 4: AI + Voice (1 minute 15 seconds)

**Say:** "But the real power is this — natural language with voice. No commands to memorize."

**Run:**

```bash
a11y-bridge --domain color,audio --askai oc
```

**Wait for the session prompt, then type:**

```
what projects do I have access to
```

**Let the AI run the command and speak the result. Then type:**

```
how many pods are running in rhtas-tenant
```

**Let it speak. Then type:**

```
are any of them failing
```

**Let it speak. Point out:** "Notice I didn't type a single oc command. I described what I wanted. The AI figured out the command, ran it safely, summarized the output, and spoke it."

**Then demonstrate voice input:**

```
v
```

**Say into mic:** "show me the latest build"

**Press Enter. Let it process and speak the result.**

**Say:** "Speech to text, AI interpretation, command execution, output summarization, text to speech. All offline-capable, all running locally."

**Type:**

```
quit
```

---

## Part 5: The Full Picture (30 seconds)

**Say:** "Three tools, one ecosystem:"

**Count on fingers or point to diagram:**

"One — the CLI-ACS specification. 98 criteria that define what accessible CLI tools should do."

"Two — the conformance suite. Tests any binary against those criteria, produces a report."

"Three — a11y-bridge. Compensates for what the tools lack. Color for sighted users, labels for screen readers, AI for natural language, voice for hands-free operation."

"The spec tells developers what to build. The suite measures where they are. a11y-bridge makes it work today, for every tool, regardless of whether the developer thought about accessibility."

---

## Commands Quick Reference

Copy-paste these before the demo to have them ready:

```bash
# Part 1: The problem
oc get pods -n rhtas-tenant

# Part 2: Conformance check
cli-acs check --domain color,help /usr/bin/oc

# Part 3: Accessible output
a11y-bridge --domain screen-reader oc get pods -n rhtas-tenant
a11y-bridge --domain color oc get pods -n rhtas-tenant

# Part 4: AI + voice session
a11y-bridge --domain color,audio --askai oc
# Then type: what projects do I have access to
# Then type: how many pods are running in rhtas-tenant
# Then type: are any of them failing
# Then type: v (speak into mic)
# Then type: quit
```

## Timing Checklist

| Part | Duration | Cumulative |
|---|---|---|
| The Problem | 0:45 | 0:45 |
| Measuring the Gap | 0:45 | 1:30 |
| a11y-bridge Wraps It | 0:45 | 2:15 |
| AI + Voice | 1:15 | 3:30 |
| The Full Picture | 0:30 | 4:00 |

## Pre-Demo Checklist

- [ ] `oc` logged in with pods in a namespace
- [ ] `cli-acs` binary built and on PATH
- [ ] `a11y-bridge` installed (`pip install -e .`)
- [ ] `A11Y_AI_KEY` and `A11Y_AI_PROVIDER` exported
- [ ] Piper voice model at `~/.cache/a11y-bridge/piper/`
- [ ] Whisper model cached (run `a11y-bridge --domain audio --askai oc` once, type `v`, speak, quit)
- [ ] Speaker volume up
- [ ] Terminal font size large for screen share
- [ ] No sensitive data in the namespace (output will be visible)
