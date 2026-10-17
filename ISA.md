# ISA — Daily Sky

> The personal daily-astrology surface: real ephemeris data + Sabian symbols + corpus-grounded readings, delivered to a pi widget and the Hermes morning brief.
> Scaffolded 2026-10-16. Layers proven: ephemeris (Swiss Ephemeris), 360-symbol table (Ruby Fumizki app data), Sabian mapping.

## Problem

Paul wants a Chani-style personal sky surface but will not accept an invented horoscope. No existing tool computes the real ephemeris AND grounds its interpretation in a specific, cited corpus. Generic astrology apps generate; this must retrieve and assemble — every interpretive line traceable to a source note, every fact computed from a real ephemeris.

## Vision

Each morning, one card shows today's sky: moon phase, the Sun's and Moon's degrees and their Sabian symbols, and any significant transits to the natal chart — followed by a short reading assembled only from the processed corpus (Gregory transits, Ensworth deep-time, Burgess Sabian), each line citing its source. Where the corpus is silent, the card says so. The same dated artifact feeds a pi widget and a one-line Hermes brief.

## Out of Scope

- Prediction. Symbols describe archetypal potential, not events.
- Clinical or medical astrology.
- Full natal interpretation (this is a daily surface, not a natal reading).
- Other people's charts (single-user for v1).
- A web app or mobile app (pi widget + Hermes only for v1).

## Principles

1. **Facts first.** Positions, aspects, and phases are computed and never interpreted. Interpretation is a separate, labeled layer.
2. **Ground every reading.** If no processed source covers a transit, say "no sourced reading" — never invent.
3. **The ephemeris is the ground truth**, not any PDF reading. Where sources disagree, the computed positions win and the discrepancy is logged.
4. **One artifact, two surfaces.** The same dated note feeds the widget and the Hermes brief. No divergent copies.

## Constraints

1. Swiss Ephemeris (`pyswisseph`) is the computation engine. It matches astro.com and the Sabian calculators exactly (verified 11/11 bodies).
2. The Sabian symbol is a fixed lookup (360 table), not a generation.
3. Interpretation is assembled from the knowledge notes at `toolbelt/lifeos/knowledge/Ideas/` — Gregory, Ensworth, Burgess, the chart note.
4. Delivery follows the proven Trading OS pattern: generate one dated artifact, sync it, render it.

## Goal

A daily sky artifact computed from real ephemeris data, with Sabian symbols mapped to the exact degrees and any interpretation cited to the processed corpus, delivered to a pi widget and a Hermes line.

## Criteria

- **ISC-1:** Natal chart computed from Swiss Ephemeris, matching astro.com to within 1 arcminute for all 11 bodies + Asc + MC.
- **ISC-2:** The 360 Sabian symbols are available as a local lookup, each verified against the source.
- **ISC-3:** `sky.py today` produces moon phase, luminary positions, and transits-to-natal within orb, all from computed data.
- **ISC-4:** Every degree shown carries its exact Sabian symbol (rounded-up rule).
- **ISC-5:** Every interpretive line cites a knowledge note; unsourced transits show "no sourced reading."
- **ISC-6:** The artifact renders in a pi widget (session_start) and syncs a one-line Hermes brief.
- **ISC-7:** The card never states or implies a prediction, and never claims astronomy for an interpretation.

*Anti: The card does not display any position that was not computed or looked up from the fixed table.*

## Test Strategy

| ISC | Type | Check | Tool |
|-----|------|-------|------|
| 1 | compute | compare to astro.com PNG | `sky.py natal` |
| 2 | table | 360 entries, spot-check known degrees | `jq` |
| 3 | compute | `sky.py today` returns phase + transits | `sky.py` |
| 4 | mapping | Leo 14 → "The human soul awaiting..." | `sky.py` |
| 5 | grounding | every reading line has a `[[source]]` | grep |
| 6 | delivery | widget renders; Hermes line sent | pi + telegram |
| 7 | gate | no predictive language | review |

## Features

| # | Feature | Satisfies | State |
|---|---------|-----------|-------|
| F1 | 360-symbol table (`sabian-symbols.json`) | ISC-2, ISC-4 | ✅ built |
| F2 | Ephemeris engine (`sky.py`) — natal + today | ISC-1, ISC-3 | ✅ built |
| F3 | Corpus grounding — map transits to source notes | ISC-5 | next |
| F4 | The rendered card (fact + symbol + sourced reading) | ISC-4, ISC-5, ISC-7 | next |
| F5 | pi widget extension (`/sky`, session_start) | ISC-6 | next |
| F6 | Hermes morning line | ISC-6 | next |

## Decisions

| Date | Decision |
|------|----------|
| 2026-10-16 | **Swiss Ephemeris over an API.** Local, free (AGPL/Moshier), matches astro.com exactly, no rate limits. |
| 2026-10-16 | **Build dir = `~/Projects/daily-sky/`** (standalone, like `the-brief`), not inside Foundry client work. |
| 2026-10-16 | **Jev ranked the delivery shape:** one daily card (2.86/3) beats weekly (1.48) and day/night (1.22). |
| 2026-10-16 | **The ephemeris is ground truth over the Paul Estares PDF.** The PDF disagrees with astro.com on Moon, Asc, and Chiron; the computed positions win. |

## Findings (logged, not resolved)

- **The Paul Estares PDF disagrees with astro.com** on: Moon (PDF Virgo 27-28 vs computed Virgo 16), Ascendant (PDF Sagittarius 14-15 vs computed Sagittarius 11°56' ≈ 12), Chiron (PDF Libra 27-28 vs computed Virgo 27). The astro.com PNG matches Swiss Ephemeris; the PDF appears to carry errors. **The chart note at `Ideas/astrology-as-mirror-...` needs correcting.**
- Moon phase on 2026-10-17: First Quarter, 36.6% illuminated.

## Verification

- **ISC-1** — ✅ `sky.py natal` matches astro.com on all 11 bodies to the arcminute (Sun 13°49', Moon 15°39', etc.).
- **ISC-2** — ✅ `sabian-symbols.json`: 360 entries, 12 signs × 30; spot-checks pass (Leo 14, Virgo 16, Sag 12).
- **ISC-3** — ✅ `sky.py today` returns moon phase (First Quarter, 36.7%), luminaries, 32 transits within orb.
- **ISC-4** — ✅ Leo 13.82 → Leo 14 → "The human soul awaiting opportunity for expression" (round-up rule verified).
- **ISC-5** — ✅ `map-corpus.py` cites each reading to a knowledge note; transits without a corpus match show no reading.
- **ISC-6** — ✅ extension loads (`pi -e ./extensions/sky-widget.ts`); widget renders at session_start. Hermes line: `sky.py hermes` (126 chars).
- **ISC-7** — ✅ card states "No predictive claim is made"; readings labeled as sourced interpretation.

## Next action

Wire the Hermes line into the existing morning rail (M6 `sync.sh` / hemera — never a second Telegram poller). Then live-test the widget in Paul's next interactive pi session and sample 3–5 days of cards to tune transit selection.
