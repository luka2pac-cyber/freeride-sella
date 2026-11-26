"""Napoved Open-Meteo vsako uro -> data/forecast.json (branch data) + arhiv za primerjavo modelov.
URL-ji se preberejo iz CONFIG.forecast v index.html (ena sama nastavitev).
Arhiv (Luka 25. 11. 2026 – test, kateri model je za Sello Nevea najbolj točen):
  data/archive/fc-YYYY-MM.jsonl  – vsakih ~6 h: sneg (cm) po modelih in dnevih na 1837 m (ista formula kot stran)
  data/archive/obs.json          – po dnevih: izmerjen novi sneg / višina snega, postaja Livinal Lunc (PC FVG 541)"""
import json, re, os, sys, time, urllib.request, datetime

OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
UA = {"User-Agent": "freeride-sella (github pages)"}
src = open("index.html", encoding="utf-8").read()
def cfg(key):
    m = re.search(r'\b' + key + r':\s*"(https://api\.open-meteo\.com[^"]+)"', src)
    return m.group(1)
URL, ENS, PAST = cfg("url"), cfg("ens"), cfg("past")
low = re.search(r'low:\s*\{\s*lat:\s*([\d.]+),\s*lon:\s*([\d.]+),\s*elev:\s*(\d+)', src)
def to_low(u):
    u = re.sub(r"latitude=[\d.]+", "latitude=" + low.group(1), u)
    u = re.sub(r"longitude=[\d.]+", "longitude=" + low.group(2), u)
    return re.sub(r"elevation=\d+", "elevation=" + low.group(3), u)

def get(u, tries=3):
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read())
        except Exception as e:
            print("napaka", u[:80], e); time.sleep(5 * (i + 1))
    return None

now = datetime.datetime.now(datetime.timezone.utc)
top, ens, past = get(URL), get(ENS), get(PAST)
lowj = get(to_low(URL))
lowe = get(to_low(ENS).replace("hourly=temperature_2m,precipitation", "hourly=temperature_2m,precipitation,snowfall"))
if not top or "daily" not in top:
    print("ni napovedi – forecast.json ostane star"); sys.exit(0)
os.makedirs(OUT + "/archive", exist_ok=True)
data = {"generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "top": top, "ens": ens, "past": past, "low": lowj, "lowEns": lowe}
json.dump(data, open(OUT + "/forecast.json", "w"), separators=(",", ":"))
print("forecast.json OK")

# ---------- arhiv napovedi po modelih ----------
def frac(T): return 1 if T <= 0.5 else 0 if T >= 2 else (2 - T) / 1.5
def ratio(T): return 1.0 if T > -2 else 1.2 if T > -6 else 1.4
fcf = OUT + "/archive/fc-" + now.strftime("%Y-%m") + ".jsonl"
last = None
for f in sorted(os.listdir(OUT + "/archive")):
    if f.startswith("fc-"):
        lines = open(OUT + "/archive/" + f).read().strip().splitlines()
        if lines: last = json.loads(lines[-1])["t"]
due = not last or (now - datetime.datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)).total_seconds() > 5.5 * 3600
if ens and "hourly" in ens and due:
    H = ens["hourly"]; by = {}
    models = [k[len("precipitation_"):] for k in H if k.startswith("precipitation_")]
    for m in models:
        P, T = H.get("precipitation_" + m) or [], H.get("temperature_2m_" + m) or []
        d = {}
        for k, t in enumerate(H["time"]):
            if k >= len(P) or P[k] is None or k >= len(T) or T[k] is None: continue
            day = t[:10]; d.setdefault(day, [0.0, 0.0, 0])
            d[day][0] += P[k] * frac(T[k]) * ratio(T[k]); d[day][1] += P[k]; d[day][2] += 1
        by[m] = {day: [round(v[0], 1), round(v[1], 1)] for day, v in d.items() if v[2] >= 20}
    with open(fcf, "a") as fh:
        fh.write(json.dumps({"t": data["generated"], "snow_prec": by}, separators=(",", ":")) + "\n")
    print("arhiv napovedi +1")

# ---------- meritve postaje (PC FVG 541) ----------
API = "https://monitor.protezionecivile.fvg.it/api/stations/541/sensors/{}/measures?from={}&to={}"
def sensor(sid, hours=50):
    f = (now - datetime.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S"); t = now.strftime("%Y-%m-%d %H:%M:%S")
    j = get(API.format(sid, urllib.parse.quote(f), urllib.parse.quote(t)))
    if not j or j.get("result") != "OK": return []
    return sorted({m["dt"]: m["value"] for m in j["measures"] if m.get("value") is not None}.items())
import urllib.parse
obsf = OUT + "/archive/obs.json"
obs = json.load(open(obsf)) if os.path.exists(obsf) else {}
try:
    off = datetime.timedelta(seconds=top.get("utc_offset_seconds", 3600))
    snow, temp = sensor(23), sensor(2)
    days = {}
    for dt, v in snow:
        day = (datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S") + off).strftime("%Y-%m-%d")
        days.setdefault(day, {"hs": []})["hs"].append(v)
    for dt, v in temp:
        day = (datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S") + off).strftime("%Y-%m-%d")
        days.setdefault(day, {"hs": []}).setdefault("t", []).append(v)
    for day, x in days.items():
        hs = x["hs"]
        if len(hs) < 8: continue
        sm = [sorted(hs[max(0, i - 2):i + 3])[len(hs[max(0, i - 2):i + 3]) // 2] for i in range(len(hs))]
        rec = {"new": round(max(0, sm[-1] - min(sm)), 1), "hs": round(sm[-1], 1), "n": len(hs)}
        if x.get("t"): rec.update(tmin=min(x["t"]), tmax=max(x["t"]))
        obs[day] = rec
    json.dump(dict(sorted(obs.items())), open(obsf, "w"), indent=0)
    print("obs OK", len(days))
except Exception as e:
    print("obs napaka", e)

# ---------- surove meritve postaj 541 (Livinal Lunc) in 542 (Sella Nevea paese) za preverjanje strani (E2E test) ----------
try:
    API2 = "https://monitor.protezionecivile.fvg.it/api/stations/{}/sensors/{}/measures?from={}&to={}"
    f = (now - datetime.timedelta(hours=170)).strftime("%Y-%m-%d %H:%M:%S"); t = now.strftime("%Y-%m-%d %H:%M:%S")
    st = {"generated": data["generated"]}
    for sid, sens in ((541, (23, 2, 6, 7, 5)), (542, (23, 2))):
        for s in sens:
            j = get(API2.format(sid, s, urllib.parse.quote(f), urllib.parse.quote(t)))
            st[f"{sid}_{s}"] = j if j and j.get("result") == "OK" else None
    json.dump(st, open(OUT + "/stations.json", "w"), separators=(",", ":"))
    print("stations.json OK")
except Exception as e:
    print("stations napaka", e)
