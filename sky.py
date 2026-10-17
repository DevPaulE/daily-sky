#!/usr/bin/env python3
"""
sky.py — the Daily Sky engine.

Computes, from REAL ephemeris data (Swiss Ephemeris / JPL DE-derived):
  1. Natal chart (Paul's, fixed)
  2. Today's transiting positions
  3. Aspects between today's transits and the natal chart
  4. Moon phase
  5. The Sabian symbol for each significant degree

Three layers, kept separate on purpose:
  - FACT: positions, aspects, moon phase (computed, never interpreted)
  - SYMBOL: the Sabian image for a degree (a fixed lookup, not a reading)
  - (interpretation from the corpus is added by the caller, with citations)

Usage:
  python3 sky.py natal          # print natal chart + symbols
  python3 sky.py today          # print today's sky (transits, aspects, symbols)
  python3 sky.py today --json   # machine-readable artifact
  python3 sky.py brief          # 3-line widget card
"""
import json, sys, os
from datetime import datetime, timezone, timedelta
import swisseph as swe

HERE = os.path.dirname(os.path.abspath(__file__))
SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio",
         "Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_GLYPHS = {"Aries":"♈","Taurus":"♉","Gemini":"♊","Cancer":"♋","Leo":"♌",
               "Virgo":"♍","Libra":"♎","Scorpio":"♏","Sagittarius":"♐",
               "Capricorn":"♑","Aquarius":"♒","Pisces":"♓"}

# Paul's birth data (confirmed 2026-10-14). Manila, Philippines, UTC+8, no DST.
NATAL = {
    "date": (1997, 8, 6),
    "local_time": (14, 3),      # 2:03 PM
    "utc_offset": 8.0,
    "lat": 14.5995,
    "lon": 120.9842,
    "place": "Manila, Philippines",
}

BODIES = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
    "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN,
    "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO,
    "NorthNode": swe.TRUE_NODE,
}

# Major aspects: name, angle, orb
ASPECTS = [("conjunction",0,8),("sextile",60,4),("square",90,6),
           ("trine",120,6),("opposition",180,8)]

with open(os.path.join(HERE, "sabian-symbols.json")) as f:
    SYMBOLS = json.load(f)["symbols"]


def sign_of(lon):
    return SIGNS[int(lon // 30) % 12]


def deg_in_sign(lon):
    return lon % 30


def sabian_index(lon):
    """Sabian symbols are 1-indexed and rounded UP within the sign.
    Degree 0.0–1.0 = the 1st symbol. So Leo 13.82 -> Leo 14."""
    import math
    sign = sign_of(lon)
    n = math.floor(deg_in_sign(lon)) + 1
    if n > 30:
        n = 30
    return sign, n, SYMBOLS[sign][str(n)]


def fmt(lon):
    s = sign_of(lon)
    d = deg_in_sign(lon)
    return f"{s} {int(d):02d}°{int((d%1)*60):02d}'"


def jd_ut(y, mo, d, h, mi, utc_offset):
    """Julian Day from local civil time and UTC offset."""
    ut = h + mi/60.0 - utc_offset
    return swe.julday(y, mo, d, ut)


def positions(jd):
    out = {}
    for name, body in BODIES.items():
        pos, _ = swe.calc_ut(jd, body)
        out[name] = pos[0]
    return out


def natal_chart():
    y, mo, d = NATAL["date"]
    h, mi = NATAL["local_time"]
    jd = jd_ut(y, mo, d, h, mi, NATAL["utc_offset"])
    pos = positions(jd)
    cusps, ascmc = swe.houses(jd, NATAL["lat"], NATAL["lon"], b'P')
    pos["Ascendant"] = ascmc[0]
    pos["Midheaven"] = ascmc[1]
    return jd, pos


def today_jd(now=None):
    now = now or datetime.now(timezone.utc)
    return swe.julday(now.year, now.month, now.day,
                      now.hour + now.minute/60.0 + now.second/3600.0)


def moon_phase(jd):
    """Illumination fraction and phase name from Sun-Moon elongation."""
    import math
    sun, _ = swe.calc_ut(jd, swe.SUN)
    moon, _ = swe.calc_ut(jd, swe.MOON)
    elong = (moon[0] - sun[0]) % 360
    illum = (1 - math.cos(math.radians(elong))) / 2 * 100
    emoji_phases = [("New Moon","🌑"),("Waxing Crescent","🌒"),("First Quarter","🌓"),
                    ("Waxing Gibbous","🌔"),("Full Moon","🌕"),("Waning Gibbous","🌖"),
                    ("Last Quarter","🌗"),("Waning Crescent","🌘")]
    if elong < 22.5 or elong >= 337.5: idx = 0
    elif elong < 67.5: idx = 1
    elif elong < 112.5: idx = 2
    elif elong < 157.5: idx = 3
    elif elong < 202.5: idx = 4
    elif elong < 247.5: idx = 5
    elif elong < 292.5: idx = 6
    else: idx = 7
    phase, emoji = emoji_phases[idx]
    return {"phase": phase, "emoji": emoji, "elongation": round(elong,2), "illumination_pct": round(illum,1)}


def aspect_between(a, b):
    """Return aspect name or None, and orb."""
    diff = abs((a - b) % 360)
    if diff > 180: diff = 360 - diff
    for name, angle, orb in ASPECTS:
        if abs(diff - angle) <= orb:
            return name, round(diff - angle, 2)
    return None, None


def compute_today(now=None):
    # The moment is absolute (JD); the date LABEL is Paul's local day.
    jd = today_jd(now)
    local_date = datetime.now().strftime("%Y-%m-%d")
    tpos = positions(jd)
    njd, npos = natal_chart()

    phase = moon_phase(jd)

    # Natal Big Three
    big3 = {k: {"pos": fmt(npos[k]), "lon": round(npos[k],4),
                "sabian": sabian_index(npos[k])[2]}
            for k in ("Sun","Moon","Ascendant")}

    # Today's luminaries with their symbols
    lights = {k: {"pos": fmt(tpos[k]), "lon": round(tpos[k],4),
                  "sabian": sabian_index(tpos[k])[2]}
              for k in ("Sun","Moon")}

    # Transits: today's bodies aspecting natal points
    transits = []
    for tb, tlon in tpos.items():
        for nb, nlon in npos.items():
            asp, orb = aspect_between(tlon, nlon)
            if asp:
                transits.append({
                    "transit": tb, "natal": nb, "aspect": asp, "orb": orb,
                    "transit_pos": fmt(tlon), "natal_pos": fmt(nlon),
                    "transit_sabian": sabian_index(tlon)[2],
                    "natal_sabian": sabian_index(nlon)[2],
                })
    # Sort: tightest orb first
    transits.sort(key=lambda x: abs(x["orb"]))

    return {
        "date": local_date,
        "natal_big_three": big3,
        "moon_phase": phase,
        "luminaries": lights,
        "transits": transits,
        "positions_today": {k: {"pos": fmt(v), "lon": round(v,4)} for k,v in tpos.items()},
    }


def print_natal():
    jd, pos = natal_chart()
    print(f"Paul's natal chart — {NATAL['place']}, {NATAL['date']} "
          f"{NATAL['local_time'][0]}:{NATAL['local_time'][1]:02d} UTC+{int(NATAL['utc_offset'])}")
    print(f"JD(UT) = {jd:.6f}\n")
    print(f"{'Body':11} {'Position':16} {'Sabian symbol'}")
    print("-"*90)
    for name in ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn",
                 "Uranus","Neptune","Pluto","NorthNode","Ascendant","Midheaven"]:
        lon = pos[name]
        sign, n, sym = sabian_index(lon)
        print(f"{name:11} {fmt(lon):16} {sign} {n}: {sym}")


def print_today(as_json=False):
    data = compute_today()
    if as_json:
        print(json.dumps(data, indent=1, ensure_ascii=False))
        return
    print(f"THE SKY — {data['date']}")
    print("="*90)
    mp = data["moon_phase"]
    print(f"Moon: {mp['phase']} ({mp['illumination_pct']}% illuminated, elongation {mp['elongation']}°)")
    print()
    print("Natal Big Three:")
    for k, v in data["natal_big_three"].items():
        print(f"  {k:10} {v['pos']:14}  {v['sabian']}")
    print()
    print("Today's luminaries:")
    for k, v in data["luminaries"].items():
        print(f"  {k:10} {v['pos']:14}  {v['sabian']}")
    print()
    print(f"Transits to natal ({len(data['transits'])} within orb), tightest first:")
    for t in data["transits"][:12]:
        print(f"  T-{t['transit']:10} {t['aspect']:12} natal {t['natal']:10} orb {t['orb']:+.2f}°")
        print(f"       transit at {t['transit_pos']} — {t['transit_sabian']}")


def print_hermes():
    """One Hermes line: <=240 chars, plain words, the one thing that matters first."""
    data = compute_today()
    mp = data["moon_phase"]
    sun = data["luminaries"]["Sun"]
    sun_sign = sun['pos'].split()[0]
    parts = [ f"{mp['emoji']} {mp['phase']}", f"Sun in {sun_sign}: {sun['sabian']}." ]
    if data["transits"]:
        t = data["transits"][0]
        feel = {"sextile":"stirring","conjunction":"merging","trine":"flowing",
                "square":"pressing","opposition":"facing"}
        parts.append(f"{feel.get(t['aspect'],t['aspect'])}: {t['transit']}+{t['natal']}.")
    line = " ".join(parts)
    if len(line) > 240:
        line = line[:237] + "..."
    print(line)


def print_brief():
    """The 3-line widget card: moon phase, the day's Sabian symbol, the tightest transit.
    Facts + lookup only. No interpretation."""
    data = compute_today()
    mp = data["moon_phase"]
    # The day's symbol = the Sun's current degree symbol (it moves ~1/day)
    sun = data["luminaries"]["Sun"]
    # Phase with emoji — feel first
    l1 = f"{mp['emoji']} {mp['phase']}"
    # Sign glyph + sign name + Sabian symbol (the day's image)
    sun_sign = sun['pos'].split()[0]
    glyph = SIGN_GLYPHS.get(sun_sign, "")
    l2 = f"{glyph} {sun_sign} — {sun['sabian']}"
    lines = [l1, l2]
    # Transit: feel-word + both planetary bodies shown clearly
    if data["transits"]:
        t = data["transits"][0]
        feel = {"sextile":"stirring","conjunction":"merging","trine":"flowing",
                "square":"pressing","opposition":"facing"}
        feelword = feel.get(t['aspect'], t['aspect'])
        l3 = f"↻ {t['transit']} {t['aspect']} your {t['natal']}"
        lines.append(l3)
    print("\n".join(lines))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "today"
    if cmd == "natal":
        print_natal()
    elif cmd == "today":
        print_today(as_json="--json" in sys.argv)
    elif cmd == "brief":
        print_brief()
    elif cmd == "hermes":
        print_hermes()
    else:
        print(__doc__)
