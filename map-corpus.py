#!/usr/bin/env python3
"""
map-corpus.py — enrich a sky.py transit list with sourced corpus readings.
Reads JSON from sky.py --json, adds a 'reading' field per transit where the corpus has coverage.
Every reading cites its source note.
"""
import json, sys, os, subprocess
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

def get_sky():
    """Run sky.py and return parsed JSON."""
    result = subprocess.run(
        [sys.executable, os.path.join(HERE, "sky.py"), "today", "--json"],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout)


def corpus_reading(transit_body, natal_body, aspect):
    """Return a reading line + source citation for a known transit type.
    This is an initial mapping — it covers the most common transit types
    from the processed corpus."""

    readings = []

    # --- Saturn transits (from Pam Gregory corpus) ---
    if transit_body == "Saturn":
        readings.append((
            "Saturn transits are about hard work, patience, and responsibility. "
            "When resisted, consequences arrive from the outside. When cooperated with, "
            "hard-won recognition follows.",
            "Pam Gregory, 'You Don't Really Believe in Astrology, Do You?' — transit-by-planet section",
            "lifeos/knowledge/Ideas/pam-gregory-you-dont-really-believe-in-astrology.md"
        ))

    # --- Uranus transits (from Pam Gregory) ---
    if transit_body == "Uranus":
        readings.append((
            "Uranus transits break rules, shatter containers, and demand individual truth. "
            "If you refuse to change during a Uranus transit, change arrives from outside as disruption.",
            "Pam Gregory — Uranus transit section",
            "lifeos/knowledge/Ideas/pam-gregory-you-dont-really-believe-in-astrology.md"
        ))

    # --- Jupiter transits (from Pam Gregory) ---
    if transit_body == "Jupiter":
        readings.append((
            "Jupiter is a 12-year reward cycle. Effort produces rewards more easily during "
            "a Jupiter transit. A good time to focus on career, start a business, or expand.",
            "Pam Gregory — Jupiter transit section",
            "lifeos/knowledge/Ideas/pam-gregory-you-dont-really-believe-in-astrology.md"
        ))

    # --- Pluto transits (from Pam Gregory) ---
    if transit_body == "Pluto":
        readings.append((
            "Pluto transits bring intensity, transformation, and empowerment. "
            "Issues of control, power, and deep healing arise. After the stress, you are stronger and wiser.",
            "Pam Gregory — Pluto transit section",
            "lifeos/knowledge/Ideas/pam-gregory-you-dont-really-believe-in-astrology.md"
        ))

    # --- Neptune transits (from Pam Gregory) ---
    if transit_body == "Neptune":
        readings.append((
            "Neptune can feel like low energy, confusion, or dissolution of identity. "
            "The positive expression is spiritual and creative inspiration — paint, listen to music, meditate.",
            "Pam Gregory — Neptune transit section",
            "lifeos/knowledge/Ideas/pam-gregory-you-dont-really-believe-in-astrology.md"
        ))

    # --- Mercury transits ---
    if transit_body == "Mercury":
        readings.append((
            "Mercury transits affect communication, perception, and mental clarity. "
            "Mercury's archetype is the messenger — what is being communicated through this transit?",
            "Pam Gregory — planetary archetypes table",
            "lifeos/knowledge/Ideas/pam-gregory-you-dont-really-believe-in-astrology.md"
        ))

    # --- Venus transits ---
    if transit_body == "Venus":
        readings.append((
            "Venus transits touch relationships, creativity, and what you value. "
            "Venus in transit asks: what do you love, and how are you expressing it?",
            "Pam Gregory — Venus archetype section",
            "lifeos/knowledge/Ideas/pam-gregory-you-dont-really-believe-in-astrology.md"
        ))

    return readings


def make_card():
    data = get_sky()
    lines = []
    d = data["date"]

    baseline = f"# Sky — {d}"
    lines.append(baseline)
    lines.append("")

    # --- Moon phase ---
    mp = data["moon_phase"]
    lines.append(f"## Moon: {mp['phase']} ({mp['illumination_pct']}% illuminated)")
    lines.append("")

    # --- Natal Big Three ---
    lines.append("### Natal Big Three")
    for k, v in data["natal_big_three"].items():
        lines.append(f"- **{k}**: {v['pos']} → *{v['sabian']}*")
    lines.append("")

    # --- Today's luminaries ---
    lines.append("### Today's Luminaries")
    for k, v in data["luminaries"].items():
        lines.append(f"- **{k}** at {v['pos']} → *{v['sabian']}*")
    lines.append("")

    # --- Transits to natal ---
    lines.append("### Transits to Natal Chart")
    lines.append(f"*{len(data['transits'])} aspects within orb. Showing the tightest 10.*")
    lines.append("")
    for t in data["transits"][:10]:
        heading = f"- **T-{t['transit']}** {t['aspect']} **natal {t['natal']}** (orb {t['orb']:+.2f}°)"
        lines.append(heading)
        lines.append(f"  - Transit {t['transit']} at {t['transit_pos']}: *{t['transit_sabian']}*")
        lines.append(f"  - Natal {t['natal']} at {t['natal_pos']}: *{t['natal_sabian']}*")

        # Corpus reading
        readings = corpus_reading(t['transit'], t['natal'], t['aspect'])
        for reading_text, source, source_path in readings:
            lines.append(f"  - {reading_text}")
            lines.append(f"    *([{source}]({source_path}))*")
        lines.append("")

    # --- Global context ---
    lines.append("### Bigger Frame")
    lines.append("We are in the transition from Pisces to Aquarius (the liminal between ages, per Ensworth).")
    lines.append("Kali Yuga ended March 2025. The ascending half-cycle of consciousness is beginning.")
    lines.append("*(Heather Ensworth, 'Astrological Ages and the Galactic Center' — Part III)*")
    lines.append("*([lifeos/knowledge/Ideas/heather-ensworth-astrological-ages-and-galactic-center.md](lifeos/knowledge/Ideas/heather-ensworth-astrological-ages-and-galactic-center.md))*")
    lines.append("")

    lines.append("---")
    lines.append("*Facts computed from Swiss Ephemeris (JPL DE431). Interpretations cited to source notes. "
                 "No predictive claim is made.*")

    return "\n".join(lines)


if __name__ == "__main__":
    card = make_card()
    print(card)
    out_path = os.path.join(HERE, f"sky-{datetime.now().strftime('%Y-%m-%d')}.md")
    with open(out_path, "w") as f:
        f.write(card)
    print(f"\n[written to {out_path}]")