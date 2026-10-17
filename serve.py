#!/usr/bin/env python3
"""
serve.py — the Daily Sky browser surface.

A tiny local HTTP server that renders the sky card as a page, the way durable-pi
and odysseus-factory serve their dashboards. The browser is the right surface:
it renders the markdown, shows the Sabian artwork, and links the sources.

  sky.py serve [--port 4782] [--no-open]

Routes:
  /                 today's card
  /natal            Paul's chart
  /day/YYYY-MM-DD   the card for a date (computed on demand)
  /raw              the plain-text card
"""
import http.server, socketserver, sys, os, json, subprocess, webbrowser, html
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 4782
SIGN_NUM = {"Aries":1,"Taurus":2,"Gemini":3,"Cancer":4,"Leo":5,"Virgo":6,"Libra":7,
            "Scorpio":8,"Sagittarius":9,"Capricorn":10,"Aquarius":11,"Pisces":12}
SIGN_GLYPH = {"Aries":"♈","Taurus":"♉","Gemini":"♊","Cancer":"♋","Leo":"♌","Virgo":"♍",
              "Libra":"♎","Scorpio":"♏","Sagittarius":"♐","Capricorn":"♑",
              "Aquarius":"♒","Pisces":"♓"}

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
</style></head><body><div class="wrap">
 <h1>Sky · {date}</h1>
 <div class="phase">{emoji} {phase}</div>
 <div class="sunline"><span class="glyph">{glyph}</span> {sign}</div>
 <div class="sym">“{sun_sabian}”</div>

 <h2>Today's Moon</h2>
 <div class="card"><div class="imgrow">
   <img src="{moon_img}" alt="{moon_sabian}">
   <div><div style="font-size:18px">{moon_pos}</div>
        <div class="sym" style="font-size:17px;margin-top:4px">“{moon_sabian}”</div></div>
 </div></div>

 <h2>Your Chart</h2>
 <div class="card big3">{big3}</div>

 <h2>Active Transits — tightest first</h2>
 {transits}

 <div class="foot">
  Facts computed from Swiss Ephemeris (JPL DE431). Sabian symbols looked up from a fixed 360 table
  (Sabian Calculator / Ruby Fumizki). <b>No predictive claim is made.</b><br>
  <a href="/natal">natal chart</a> · <a href="/raw">plain text</a>
 </div>
</div></body></html>"""

def transit_html(t, i):
    t_img = sabian_img(*_sign_n(t["transit_pos"]))
    n_img = sabian_img(*_sign_n(t["natal_pos"]))
    feel = {"sextile":"stirring","conjunction":"merging","trine":"flowing",
            "square":"pressing","opposition":"facing"}.get(t["aspect"], t["aspect"])
    return f"""<div class="card"><div class="imgrow">
 <img src="{t_img}" alt="{t['transit_sabian']}">
 <div style="flex:1">
  <div style="font-size:18px"><span class="feel">{feel}</span> · {t['transit']} {t['aspect']} your {t['natal']}
   <span style="color:#6f6f7d;font-size:14px">({t['orb']:+.2f}°)</span></div>
  <div class="sym" style="font-size:16px;margin:6px 0 8px">“{t['transit_sabian']}”</div>
  <div class="src">transit {t['transit_pos']} · natal {t['natal_pos']} — “{t['natal_sabian']}”</div>
 </div></div></div>"""

def _sign_n(pos):
    """('Libra 23°53\'') -> ('Libra', 24)."""
    sign = pos.split()[0]
    deg = int(''.join(c for c in pos.split()[1].split('°')[0] if c.isdigit()))
    return sign, deg + 1

def render(route):
    d = engine_json()
    mp, sun, moon = d["moon_phase"], d["luminaries"]["Sun"], d["luminaries"]["Moon"]
    sign = sun["pos"].split()[0]
    big3 = " · ".join(f"<b>{k}</b> {v['sabian']}" for k, v in d["natal_big_three"].items())
    transits = "".join(transit_html(t, i) for i, t in enumerate(d["transits"][:6]))
    body = PAGE.format(
        date=d["date"], emoji=mp["emoji"], phase=mp["phase"],
        glyph=SIGN_GLYPH.get(sign, ""), sign=sign, sun_sabian=html.escape(sun["sabian"]),
        moon_pos=moon["pos"], moon_sabian=html.escape(moon["sabian"]),
        moon_img=sabian_img(*_sign_n(moon["pos"])),
        big3=big3, transits=transits,
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
            body, ctype = f"<pre>sky serve error: {html.escape(str(e))}</pre>", "text/html"
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
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    main()
