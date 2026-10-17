# daily-sky

Paul's personal daily-astrology surface. Real ephemeris facts + a fixed Sabian-symbol lookup + corpus-grounded readings. Feeds a pi widget and a Hermes line.

> Facts are computed, never invented. Symbols are looked up, never generated. Interpretations are cited to source notes, never made up. No predictions.

## What it does

```
sky.py brief    → 3-line widget card (moon phase · day's symbol · tightest transit)
sky.py hermes   → 1-line brief for the phone (≤240 chars)
sky.py today    → full computed sky (transits, aspects, moon phase)
sky.py natal    → Paul's chart + symbols for every body
map-corpus.py   → full card with cited readings from the knowledge notes
```

## Layout

| File | Role |
|------|------|
| `sky.py` | The engine. Swiss Ephemeris (`pyswisseph`) → positions, aspects, moon phase; maps each degree to its Sabian symbol. |
| `sabian-symbols.json` | The 360-symbol table (Aries 1 → Pisces 30), from the Sabian Calculator app data. |
| `map-corpus.py` | Enriches a transit list with readings from the knowledge notes, each cited. |
| `ISA.md` | The Ideal State Artifact — goal, criteria, features, decisions, findings. |
| `sky-YYYY-MM-DD.md` | Generated cards (git-ignored). |

## Setup

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python pyswisseph
```

## Natal data (ground truth)

Born 1997-08-06, 14:03 local, Manila PH (UTC+8), 14.60°N 120.98°E.

Positions computed from Swiss Ephemeris (JPL DE431). Verified to match astro.com to the arcminute on all 11 bodies. **The Lisa PDF reading disagrees** on Moon (Virgo 16 vs its 27-28), Ascendant (Sag 11°56' vs its 14-15), and Chiron (Virgo 27 vs its Libra 27) — the ephemeris is ground truth.

## The pi widget

`toolbelt/pi-lifeos/extensions/sky-widget.ts` renders the 3-line brief under the editor at session start, and exposes `/sky` (full card), `/sky natal` (the chart), `/sky raw` (computed sky).

Engine path is configurable via `SKY_ENGINE` / `SKY_PYTHON`.

## Layer doctrine

1. **FACT** — positions, aspects, phases. Computed, never interpreted.
2. **SYMBOL** — the Sabian image for a degree. A lookup, not a reading.
3. **READING** — assembled from `toolbelt/lifeos/knowledge/Ideas/` (Gregory, Ensworth, Burgess), each line cited. Unsourced transits say so.

## Sources

- Swiss Ephemeris (`pyswisseph`) — JPL DE431-based; the standard high-precision engine.
- Sabian symbol table — Sabian Calculator (Ruby Fumizki) app data.
- Reading corpus — `pam-gregory-you-dont-really-believe-in-astrology.md`, `heather-ensworth-astrological-ages-and-galactic-center.md`, `sabian-symbols-system-reference.md`, `astrology-as-mirror-paul-s-natal-chart-and-transits.md`.

## The browser surface (`serve.py`)

A local HTTP server, the durable-pi / odysseus-factory pattern:

```bash
.venv/bin/python serve.py            # serves http://localhost:4782 and opens it
.venv/bin/python serve.py --no-open  # serve only
```

Routes: `/` today's card · `/natal` the chart · `/raw` plain text.
The page renders the Sabian artwork (Ruby Fumizki) for the moon and every transit,
plus the corpus footer. Facts + lookups, no predictions.

`/sky` in pi starts this server if it is not running and opens the browser.
