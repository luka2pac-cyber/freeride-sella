"""ARSO automatic station Kanin (2260 m, Slovenian side): snow depth, temp, wind -> kanin.json"""
import json, re, urllib.request, datetime
URL = "https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_KANIN_latest.xml"
def tag(x, n):
    m = re.search(rf"<{n}>([^<]*)</{n}>", x)
    return m.group(1).strip() if m else ""
def num(s):
    try: return float(s)
    except: return None
try:
    req = urllib.request.Request(URL, headers={"User-Agent": "freeride-sella (github pages)"})
    x = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
except Exception as e:
    print("fetch failed:", e); raise SystemExit(0)
out = {
    "station": "Kanin", "alt": int(num(tag(x, "domain_altitude")) or 2260),
    "snow": num(tag(x, "snow")), "t": num(tag(x, "t")),
    "wind": num(tag(x, "ff_val_kmh")), "gust": num(tag(x, "ffmax_val_kmh")),
    "deg": num(tag(x, "dd_val")), "valid_utc": tag(x, "valid_UTC"),
    "checked": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "source": "ARSO", "url": "https://www.vreme.si/podatki/Kanin/sneg",
}
if out["snow"] is None and out["t"] is None:
    print("no data parsed"); raise SystemExit(0)
open("kanin.json", "w").write(json.dumps(out, ensure_ascii=False, indent=1))
print(out)
