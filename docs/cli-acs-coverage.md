# CLI-ACS Coverage

axcli compensates for all 15 criteria in the CLI-ACS Color & Visual Presentation domain (CV-1 through CV-15).

## How It Works

The CLI-ACS conformance suite (`cli-acs`) evaluates whether a CLI binary meets accessibility criteria. axcli compensates for failures — if a binary fails a criterion, axcli applies the fix at runtime.

For example, if `oc` fails CV-1 (color as sole information channel), axcli detects the color codes and adds text prefixes so a screen reader user gets `[ERROR] connection refused` instead of just red text.

## Coverage Matrix

| Criterion | What the spec requires | Sighted mode | Screen reader mode |
|---|---|---|---|
| CV-1: Color not sole info | Additional indicators alongside color | Adds color to status words | Adds `[OK]`/`[ERROR]`/`[WARN]` text prefixes |
| CV-2: NO_COLOR | Suppress color when NO_COLOR set | N/A (adds color) | Detects and enables text mode |
| CV-3: --no-color | Per-invocation color control | N/A (adds color) | Strips all ANSI |
| CV-4: TTY-aware | No ANSI when piped | Detects TTY for mode selection | Strips when piped |
| CV-5: TERM=dumb | No ANSI with TERM=dumb | N/A (adds color) | Detects and enables text mode |
| CV-6: --color modes | always/never/auto flag | Handled at source | Strips everything |
| CV-7: FORCE_COLOR | Force color env var | Handled at source | Strips everything |
| CV-8: 4-bit ANSI | Prefer user-customizable colors | Uses 4-bit ANSI only | Strips all color |
| CV-9: No bg assumption | Readable on light and dark | Uses safe foreground colors | Strips all color |
| CV-10: Config precedence | Predictable flag/env hierarchy | Handled at source | Strips everything |
| CV-11: High contrast | Readable in high contrast mode | N/A | Plain text output |
| CV-12: Inverse video | Structure without styling | Preserves | Converts to `[SELECTED: text]` |
| CV-13: OSC 8 hyperlinks | Degrade gracefully | Preserves | Extracts URL as `(link: URL)` text |
| CV-14: FG/BG contrast | 4.5:1 ratio for color pairs | Adds safe colors only | Strips all color |
| CV-15: Unicode symbols | Text alternatives for symbols | Preserves | Replaces 30+ symbols with text |

## Related

- [CLI-ACS Conformance Specification](https://github.com/sampras343/cli-accessibility-spec) — the standard these criteria come from
- [Color & Visual Presentation spec](https://github.com/sampras343/cli-accessibility-spec/blob/main/spec/color-and-visual-presentation.md) — detailed background on terminal color accessibility
