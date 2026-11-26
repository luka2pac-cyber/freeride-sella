"""ARSO automatic station Kanin (2260 m, Slovenian side): latest + 48 h history -> kanin.json"""
import json, re, urllib.request, datetime, html
BASE = "https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/"
UA = {"User-Agent": "freeride-sella (github pages)"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "replace")
def tag(x, n):
    m = re.search(rf"<{n}>([^<]*)</{n}>", x)
    return m.group(1).strip() if m else ""
def num(s):
    try: return float(str(s).replace(",", "."))
    except: return None
try:
    x = get(BASE + "observationAms_KANIN_latest.xml")
except Exception as e:
    print("fetch failed:", e); raise SystemExit(0)
out = {
    "station": "Kanin", "alt": int(num(tag(x, "domain_altitude")) or 2260),
    "snow": num(tag(x, "snow")), "t": num(tag(x, "t")),
    "wind": num(tag(x, "ff_val_kmh")), "gust": num(tag(x, "ffmax_val_kmh")),
    "deg": num(tag(x, "dd_val")), "valid_utc": tag(x, "valid_UTC"),
    "checked": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "source": "ARSO", "url": "https://www.vreme.si/podatki/Kanin/sneg", "series": [],
}
if out["snow"] is None and out["t"] is None:
    print("no data parsed"); raise SystemExit(0)
# 48 h history (HTML table). Columns: time, icon, T, RH, wind, dir, gust, rr, rr_sum, sun, dif_sun, snow
try:
    h = get(BASE + "observationAms_KANIN_history.html")
    hdr = re.search(r"<tr[^>]*>(.*?)</tr>", h, re.S).group(1)
    heads = [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip().lower() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", hdr, re.S)]
    def col(key):
        for i, c in enumerate(heads):
            if key in c: return i
        return None
    iT, iW, iG, iS, iD = col("temperatura"), col("hitrost vetra"), col("sunki"), col("snežne"), col("smer")
    print("heads:", heads, "dir col:", iD)
    ser = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S)[1:]:
        cells = [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)]
        if len(cells) < len(heads): continue
        m = re.search(r"(\d+)\.(\d+)\.(\d{4})\s+(\d+):(\d+)\s*(CEST|CET)?", cells[0])
        if not m: continue
        d, mo, y, hh, mi, tz = m.groups()
        off = 2 if tz == "CEST" else 1
        t = datetime.datetime(int(y), int(mo), int(d), int(hh), int(mi), tzinfo=datetime.timezone.utc) - datetime.timedelta(hours=off)
        g = lambda i: num(cells[i]) if i is not None and cells[i] != "" else None
        md = re.search(r"-?\d+(?:[.,]\d+)?", cells[iD]) if iD is not None else None
        ser.append([t.strftime("%Y-%m-%dT%H:%M:%SZ"), g(iS), g(iT), g(iW), g(iG), num(md.group(0)) if md else None])
    ser.sort()
    out["series"] = ser
    print("history rows:", len(ser))
except Exception as e:
    print("history failed:", e)
open("kanin.json", "w").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print({k: v for k, v in out.items() if k != "series"})
