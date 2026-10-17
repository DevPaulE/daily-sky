#!/usr/bin/env python3
"""
serve.py — the Daily Sky browser surface.

A tiny local HTTP server that renders the sky card as a page, the way durable-pi
and odysseus-factory serve their dashboards. The browser is the right surface:
it renders the markdown, shows the Sabian artwork, links the sources.

  .venv/bin/python serve.py [--port 4782] [--no-open]

Routes:
  /                 today's card (with Burgess companion content)
  /natal            Paul's chart
  /raw              the plain-text card
"""
import http.server, socketserver, sys, os, json, subprocess, webbrowser, html
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 4782
DEGREE_VID_URL = "https://www.youtube.com/watch?v={id}"

SIGN_NUM = {"Aries":1,"Taurus":2,"Gemini":3,"Cancer":4,"Leo":5,"Virgo":6,"Libra":7,
            "Scorpio":8,"Sagittarius":9,"Capricorn":10,"Aquarius":11,"Pisces":12}
NUM_SIGN = {v:k for k,v in SIGN_NUM.items()}
SIGN_GLYPH = {"Aries":"♈","Taurus":"♉","Gemini":"♊","Cancer":"♋","Leo":"♌","Virgo":"♍",
              "Libra":"♎","Scorpio":"♏","Sagittarius":"♐","Capricorn":"♑",
              "Aquarius":"♒","Pisces":"♓"}

# --- Sabian symbols lookup ---
with open(os.path.join(HERE, "sabian-symbols.json")) as f:
    _ss = json.load(f)["symbols"]  # _ss[sign][str(deg)] = symbol name

def sabian(sign: str, deg: int) -> str:
    """Get the Sabian symbol name for a sign and degree (1-30)."""
    return _ss.get(sign, {}).get(str(deg), "")

def prev_degree(sign: str, deg: int) -> tuple:
    """(prev_sign, prev_deg) — the degree immediately before this one."""
    if deg > 1:
        return sign, deg - 1
    # wrap to previous sign
    nums = sorted(SIGN_NUM.values())
    prev_n = SIGN_NUM[sign] - 1 if SIGN_NUM[sign] > 1 else 12
    return NUM_SIGN[prev_n], 30

def next_degree(sign: str, deg: int) -> tuple:
    """(next_sign, next_deg) — the degree immediately after this one."""
    if deg < 30:
        return sign, deg + 1
    next_n = SIGN_NUM[sign] + 1 if SIGN_NUM[sign] < 12 else 1
    return NUM_SIGN[next_n], 1

# --- Burgess video lookup ---
BURGESS = {}
try:
    with open(os.path.join(HERE, "burgess-video-lookup.json")) as f:
        _bv = json.load(f).get("series", {})
    for s, degs in _bv.items():
        BURGESS[s] = {int(k): v for k, v in degs.items()}
except FileNotFoundError:
    pass

def burgess_video(sign: str, deg: int) -> dict | None:
    """Return {id, title, url} for a Burgess per-degree video, or None."""
    entry = BURGESS.get(sign.upper(), {}).get(deg)
    if entry:
        return {**entry, "url": DEGREE_VID_URL.format(id=entry["id"])}
    return None

# --- Curated Burgess quotes ---
BURGESS_QUOTES = [
    # Reverse process (V1)
    ("reverse process", "J. Burgess, V1",
     "To understand any degree, look at the previous degree. "
     "To master Taurus 16, you've got to master Taurus 15 first. "
     "The sequence runs backwards — different from Rudhyar's forward progression."),
    # Seven words (V5)
    ("seven words", "J. Burgess, V5",
     "NO (identity), HELLO (expansion), THANK YOU (felt-sense of the degree), "
     "GOODBYE (what changes by following this wisdom), PLEASE (life vision), "
     "SORRY (pitfalls, shadow side), YES (allow it all to flow)."),
    # Sun (V5)
    ("sun", "J. Burgess, V5",
     "The sun's position is the essence of who we really are — our self-identity. "
     "1/360th specificity is the point. One degree is not 'ok, I'm Taurus,' "
     "a twelfth of the world. You want it very specific indeed."),
    # Moon (V5)
    ("moon", "J. Burgess, V5",
     "The moon represents unconsciousness — familiarity. Our family, our hometown, our "
     "habits. We feel them but we don't really know why. The moon sign answers: why? "
     "Bringing what was unconscious into consciousness moves us closer to realization."),
    # Study method (V5)
    ("study", "J. Burgess, V5",
     "Study the exact words that have been used, the strangeness of the image. "
     "Does this image appear in your life? How did you respond — positively or negatively? "
     "Did you deny it or accept it open-heartedly?"),
    # Speaking (V5)
    ("speak", "J. Burgess, V5",
     "It is not enough to know that something applies to you intuitively as a feeling. "
     "You have to be able to speak about it using the Sabian symbol. "
     "To be able to explain it to somebody else, to talk about it clearly."),
    # Seek (V9)
    ("seek", "J. Burgess, V9",
     "Seek and ye shall find. Seeking is active engagement — different from noticing "
     "or observing. Spend most of your time on the question, not the answer. "
     "If the question is right, the answer is inherent."),
    # Saturn three levels (V5)
    ("saturn", "J. Burgess, V5",
     "Saturn has three operating levels: asleep (lower), aware but struggling (middle), "
     "integrated and healed (higher). The Sabian symbol shows you which level you're on "
     "for that degree."),
    # Wisdom (V10)
    ("wisdom", "J. Burgess, V10",
     "Wisdom is not only truth, it is also loving. It is not only love, it is truthful. "
     "To find a way to live, discover where these two paths are one."),
    # Common sense (V10)
    ("common-sense", "J. Burgess, V10",
     "The secret of life is not a secret at all. It is simply a series of common-sense "
     "realizations backed up with reasonable self-discipline and moderation of impulses. "
     "Do what you feel — unless those feelings are inappropriate."),
]

def burgess_quote(tag: str) -> str:
    """Pick the quote closest to the given tag."""
    for t, src, q in BURGESS_QUOTES:
        if t == tag:
            return f"“{q}” — <b>{src}</b>"
    # fallback: the general reverse-process quote
    return burgess_quote("reverse process")


# --- Engine bridge ---

def run_engine(mode):
    args = mode.split()
    return subprocess.run([sys.executable, os.path.join(HERE, "sky.py"), *args],
                          capture_output=True, text=True, timeout=30).stdout

def engine_json():
    return json.loads(run_engine("today --json"))

def sabian_img(sign, n):
    """Ruby Fumizki's artwork for a degree: /{sign_num}/{degree}.jpg"""
    sn = SIGN_NUM.get(sign, 1)
    return f"https://s3-ap-northeast-1.amazonaws.com/sabian-symbols/{sn:02d}/{n:02d}.jpg"


# --- HTML rendering ---

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sky — {date}</title>
<style>
 :root {{ color-scheme: dark; }}
 body {{ margin:0; background:#0d0d12; color:#e8e6e3;
        font:16px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
 .wrap {{ max-width:760px; margin:0 auto; padding:36px 22px 80px; }}
 h1 {{ font-size:15px; font-weight:600; letter-spacing:.14em; text-transform:uppercase;
       color:#7a7a88; margin:0 0 24px; }}
 .phase {{ font-size:34px; font-weight:600; margin:0 0 4px; }}
 .sunline {{ font-size:30px; font-weight:700; line-height:1.25; margin:14px 0 6px; }}
 .sunline .glyph {{ color:#c9a96a; }}
 .sym {{ font-size:21px; font-style:italic; color:#d8cbb0; margin:6px 0 26px; }}
 .card {{ background:#14141b; border:1px solid #23232e; border-radius:14px;
          padding:20px 22px; margin:16px 0; }}
 .imgrow {{ display:flex; gap:18px; align-items:flex-start; }}
 .imgrow img {{ width:120px; height:120px; border-radius:10px; object-fit:cover;
                border:1px solid #2a2a38; flex:0 0 auto; }}
 h2 {{ font-size:12px; letter-spacing:.13em; text-transform:uppercase; color:#7a7a88;
       margin:34px 0 12px; font-weight:600; }}
 .row {{ display:flex; gap:14px; padding:11px 0; border-bottom:1px solid #1e1e28; }}
 .row:last-child {{ border-bottom:0; }}
 .row .lbl {{ flex:0 0 130px; color:#9a97a3; font-size:14px; }}
 .row .val {{ flex:1; }}
 .feel {{ color:#c9a96a; }}
 .big3 {{ font-size:15px; }}
 .big3 b {{ color:#d8cbb0; font-weight:600; }}
 a {{ color:#8fb3d9; text-decoration:none; }}
 a:hover {{ text-decoration:underline; }}
 .foot {{ margin-top:44px; font-size:12px; color:#5c5c68; line-height:1.6; }}
 .read {{ color:#b9b6c0; font-size:14.5px; margin:8px 0 4px; }}
 .src {{ font-size:12.5px; color:#6f6f7d; }}
 .prev {{ color:#6f6f7d; font-size:13px; margin:6px 0 2px; }}
 .prev .dir {{ color:#8fb3d9; font-size:12px; }}
 .burgess {{ background:#0d0d1a; border:1px solid #a89a5e; border-radius:10px;
             padding:16px 20px; margin:14px 0; font-size:14px; color:#d8cbb0; }}
 .burgess .tag {{ color:#7a7a88; font-size:11px; text-transform:uppercase; letter-spacing:.1em; }}
 .burgess .src {{ color:#8fb3d9; }}
 .channel-link {{ font-size:12px; color:#5c5c68; display:block; margin-top:4px; }}
</style></head><body><div class="wrap">
 <h1>Sky · {date}</h1>
 <div class="phase">{emoji} {phase}</div>
 <div class="sunline"><span class="glyph">{glyph}</span> {sign}</div>
 <div class="sym">“{sun_sabian}”</div>
 {sun_prev}

 <h2>Today's Moon</h2>
 <div class="card"><div class="imgrow">
   <img src="{moon_img}" alt="{moon_sabian}">
   <div><div style="font-size:18px">{moon_pos}</div>
        <div class="sym" style="font-size:17px;margin-top:4px">“{moon_sabian}”</div>
        {moon_prev}</div>
 </div></div>

 <h2>Your Chart</h2>
 <div class="card big3">{big3}</div>

 <h2>Active Transits — tightest first</h2>
 {transits}

 <div class="burgess"><span class="tag">Burgess companion</span><br>
  {burgess_quote}
  <span class="channel-link">← J. Burgess / Sabian Mysteries · <a href="https://www.youtube.com/playlist?list=PLiuvrHKLLymJ8MsYl2TRj_XvFgTYxU_yc">onboarding playlist</a></span>
 </div>

 <div class="foot">
  Facts computed from Swiss Ephemeris (JPL DE431). Sabian symbols looked up from a fixed 360 table
  (Sabian Calculator / Ruby Fumizki). Burgess companion content from the 10-video onboarding playlist
  and per-degree video series.<br>
  <b>No predictive claim is made.</b> Astrology is a mirror, not evidence.<br>
  <a href="/raw">plain text</a>
 </div>
</div></body></html>"""


def _parse_pos(pos: str):
    """('Libra 23°53\\'') -> ('Libra', 24)."""
    sign = pos.split()[0]
    deg = int(''.join(c for c in pos.split()[1].split('°')[0] if c.isdigit()))
    return sign, deg + 1  # +1 because degree number is 1..30, not 0..29


def _prev_block(sign: str, deg: int) -> str:
    """HTML for the 'previous degree' block with Burgess video link."""
    ps, pd = prev_degree(sign, deg)
    prev_name = sabian(ps, pd)
    if not prev_name:
        return ""

    # Burgess video for previous degree
    vid = burgess_video(ps, pd)
    vid_link = f'· <a href="{vid["url"]}">video</a>' if vid else ""

    # Burgess video for this degree
    this_vid = burgess_video(sign, deg)
    this_link = ""
    if this_vid:
        this_link = f'🎬 <a href="{this_vid["url"]}">Burgess: {sign} {deg}</a>'

    prev_glyph = SIGN_GLYPH.get(ps, "")
    return (f'<div class="prev dir">← previous: {prev_glyph} {ps} {pd} — '
            f'“{html.escape(prev_name)}” {vid_link}</div>'
            f'<div class="prev">{this_link}</div>')


def transit_html(t, i):
    t_img = sabian_img(*_parse_pos(t["transit_pos"]))
    n_img = sabian_img(*_parse_pos(t["natal_pos"]))
    feel = {"sextile":"stirring","conjunction":"merging","trine":"flowing",
            "square":"pressing","opposition":"facing"}.get(t["aspect"], t["aspect"])
    ts, td = _parse_pos(t["transit_pos"])
    ns, nd = _parse_pos(t["natal_pos"])
    t_prev = _prev_block(ts, td)
    n_prev = _prev_block(ns, nd)
    return f"""<div class="card"><div class="imgrow">
 <img src="{t_img}" alt="{t['transit_sabian']}">
 <div style="flex:1">
  <div style="font-size:18px"><span class="feel">{feel}</span> · {t['transit']} {t['aspect']} your {t['natal']}
   <span style="color:#6f6f7d;font-size:14px">({t['orb']:+.2f}°)</span></div>
  <div class="sym" style="font-size:16px;margin:6px 0 8px">“{t['transit_sabian']}”</div>
  <div class="src">transit {t['transit_pos']} · natal {t['natal_pos']} — “{t['natal_sabian']}”</div>
  {t_prev}
  {n_prev}
 </div></div></div>"""


def render(path):
    d = engine_json()
    mp, sun, moon = d["moon_phase"], d["luminaries"]["Sun"], d["luminaries"]["Moon"]
    sign = sun["pos"].split()[0]
    sun_sign, sun_deg = _parse_pos(sun["pos"])
    moon_sign, moon_deg = _parse_pos(moon["pos"])

    big3 = " · ".join(f"<b>{k}</b> {v['sabian']}" for k, v in d["natal_big_three"].items())
    transits = "".join(transit_html(t, i) for i, t in enumerate(d["transits"][:6]))

    body = PAGE.format(
        date=d["date"], emoji=mp["emoji"], phase=mp["phase"],
        glyph=SIGN_GLYPH.get(sign, ""), sign=sign,
        sun_sabian=html.escape(sun["sabian"]),
        sun_prev=_prev_block(sun_sign, sun_deg),
        moon_pos=moon["pos"], moon_sabian=html.escape(moon["sabian"]),
        moon_img=sabian_img(*_parse_pos(moon["pos"])),
        moon_prev=_prev_block(moon_sign, moon_deg),
        big3=big3, transits=transits,
        burgess_quote=burgess_quote("reverse process"),
    )
    return body


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == "/raw":
                out = run_engine("today")
                body, ctype = f"<pre>{html.escape(out)}</pre>", "text/html"
            elif self.path == "/natal":
                out = run_engine("natal")
                body, ctype = f"<pre style='font-size:13px'>{html.escape(out)}</pre>", "text/html"
            else:
                body, ctype = render(self.path), "text/html"
        except Exception as e:
            err = html.escape(str(e))
            body, ctype = f"<pre>sky serve error: {err}</pre>", "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
    def log_message(self, *a): pass


def main():
    port = PORT
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port")+1])
    # If already serving, just open it
    import socket
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            url = f"http://localhost:{port}"
            print(f"sky: already serving at {url}")
            if "--no-open" not in sys.argv:
                webbrowser.open(url)
            return
    url = f"http://localhost:{port}"
    print(f"sky: serving at {url}  (Ctrl-C to stop)")
    if "--no-open" not in sys.argv:
        webbrowser.open(url)
    # Use SO_REUSEADDR to prevent binding conflicts after restart
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    httpd.allow_reuse_address = True
    httpd.serve_forever()


if __name__ == "__main__":
    main()