"""The README's charts, drawn as plain SVG from one run record (never from typed numbers).

Every value is read with `report.get`, so a missing key refuses the drawing. Every chart names its run. Only derived
statistics are drawn (monthly errors, monitor states, monthly block values); no hourly price series is published.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from pmcore import runs

from hq_price.report import LABEL, STATE, get

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = {"B0": "#2a78d6", "M1": "#eb6834", "M2": "#1baf7a"}  # fixed order; validated (dataviz validator, light)
STATUS = {"trust": "#0ca30c", "watch": "#fab219", "stop trusting": "#d03b3b", "no verdict (window not full)": "#b5b4ae"}
FONT = "font-family='system-ui, -apple-system, Segoe UI, sans-serif'"
W, H = 720, 300

T = {
    "fr": {"mae": "EAM mensuelle, prix du marché du jour précédent (T1), année réservée", "unit": "$ US/MWh",
           "states": "États du moniteur, chaque jour de l'année réservée", "deal": "Bloc 5×16 de 50 MW : valeur par mois",
           "settled": "Réglé", "musd": "M$ US", "run": "exécution"},
    "en": {"mae": "Monthly MAE, day-ahead price (T1), held-out year", "unit": "US$/MWh",
           "states": "Monitor states, each day of the held-out year", "deal": "50 MW 5×16 block: value by month",
           "settled": "Settled", "musd": "US$ M", "run": "run"},
}


def _svg(body: list[str], title: str, rec: dict, lang: str, h: int = H) -> str:
    foot = f"{T[lang]['run']} {rec['run_id']}, {LABEL[lang][rec['label']]}"
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{h}' viewBox='0 0 {W} {h}' role='img' "
            f"aria-label='{escape(title)}'>\n<title>{escape(title)}</title>\n"
            f"<rect width='{W}' height='{h}' fill='{SURFACE}'/>\n"
            f"<text x='16' y='24' {FONT} font-size='15' font-weight='600' fill='{INK}'>{escape(title)}</text>\n"
            + "\n".join(body) +
            f"\n<text x='16' y='{h - 10}' {FONT} font-size='11' fill='{INK2}'>{escape(foot)}</text>\n</svg>\n")


def _lines(months: list[str], series: dict[str, list[float]], colors: dict[str, str], unit: str, dashed=()) -> list[str]:
    x0, x1, y0, y1 = 64, W - 32, H - 48, 66
    hi = max(max(v) for v in series.values()) * 1.08
    step = 10 ** max(0, len(str(int(hi))) - 1)
    ticks = [k * step for k in range(0, int(hi // step) + 1)]
    if len(ticks) > 6:
        ticks = ticks[::2]
    sx = lambda i: x0 + (x1 - x0) * i / max(1, len(months) - 1)
    sy = lambda v: y0 - (y0 - y1) * v / hi
    out = [f"<text x='16' y='{y1 - 8}' {FONT} font-size='11' fill='{INK2}'>{escape(unit)}</text>"]
    lx = x0 + 60
    for name in series:  # legend row: series names in ink, beside their colour
        dash = " stroke-dasharray='5 4'" if name in dashed else ""
        out.append(f"<line x1='{lx}' x2='{lx + 18}' y1='{y1 - 12}' y2='{y1 - 12}' stroke='{colors[name]}' stroke-width='3'{dash}/>")
        out.append(f"<text x='{lx + 24}' y='{y1 - 8}' {FONT} font-size='12' fill='{INK}'>{escape(name)}</text>")
        lx += 40 + 8 * len(name)
    for t in ticks:
        out.append(f"<line x1='{x0}' x2='{x1}' y1='{sy(t):.1f}' y2='{sy(t):.1f}' stroke='{GRID}' stroke-width='1'/>")
        out.append(f"<text x='{x0 - 8}' y='{sy(t) + 4:.1f}' {FONT} font-size='11' fill='{INK2}' text-anchor='end'>{t:g}</text>")
    for i, m in enumerate(months):
        out.append(f"<text x='{sx(i):.1f}' y='{y0 + 16}' {FONT} font-size='10' fill='{INK2}' text-anchor='middle'>{m[2:]}</text>")
    for name, vals in series.items():
        pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals))
        dash = " stroke-dasharray='5 4'" if name in dashed else ""
        out.append(f"<polyline points='{pts}' fill='none' stroke='{colors[name]}' stroke-width='2' stroke-linejoin='round'{dash}/>")
        for i, v in enumerate(vals):
            out.append(f"<circle cx='{sx(i):.1f}' cy='{sy(v):.1f}' r='3' fill='{colors[name]}' stroke='{SURFACE}' stroke-width='1.5'>"
                       f"<title>{escape(name)} {months[i]}: {v:,.2f}</title></circle>")
    return out


def monthly_mae(rec: dict, lang: str) -> str:
    bm = get(rec, "results", "T1_da_lbmp", "by_month")
    months = sorted(bm)
    series = {m: [get(bm, k, m, "mae") for k in months] for m in ("B0", "M1", "M2")}
    return _svg(_lines(months, series, SERIES, T[lang]["unit"]), T[lang]["mae"], rec, lang)


def deal_by_month(rec: dict, lang: str) -> str:
    bm = get(rec, "deal", "by_month")
    months = sorted(bm)
    settled = T[lang]["settled"]
    series = {settled: [get(bm, k, "settled_total") / 1e6 for k in months]}
    series.update({m: [get(bm, k, m, "forecast_total") / 1e6 for k in months] for m in ("B0", "M1", "M2")})
    colors = {settled: INK, **SERIES}
    return _svg(_lines(months, series, colors, T[lang]["musd"], dashed=(settled,)), T[lang]["deal"], rec, lang)


def monitor_states(rec: dict, lang: str) -> str:
    mon = get(rec, "monitor")
    keys = sorted(mon, key=lambda k: (k.split(":")[1], k))
    x0, top, row = 150, 44, 22
    days = get(mon, keys[0], "daily", "day")
    cw = (W - x0 - 16) / len(days)
    h = top + row * len(keys) + 70
    out = []
    for r, k in enumerate(keys):
        y = top + r * row
        out.append(f"<text x='{x0 - 8}' y='{y + 14}' {FONT} font-size='11' fill='{INK}' text-anchor='end'>{escape(k)}</text>")
        states = get(mon, k, "daily", "state")
        i = 0
        while i < len(states):  # one rect per run of equal states
            j = i
            while j + 1 < len(states) and states[j + 1] == states[i]:
                j += 1
            out.append(f"<rect x='{x0 + i * cw:.2f}' y='{y + 2}' width='{(j - i + 1) * cw:.2f}' height='{row - 6}' "
                       f"fill='{STATUS[states[i]]}'><title>{escape(k)} {days[i][:10]}–{days[j][:10]}: "
                       f"{escape(STATE[lang][states[i]])}</title></rect>")
            i = j + 1
    yl = top + row * len(keys) + 8
    for i in range(0, len(days), 1):
        if days[i][8:10] == "01":
            out.append(f"<text x='{x0 + i * cw:.1f}' y='{yl + 4}' {FONT} font-size='10' fill='{INK2}'>{days[i][2:7]}</text>")
    lx = x0
    for s in ("trust", "watch", "stop trusting"):
        out.append(f"<rect x='{lx}' y='{yl + 16}' width='12' height='12' fill='{STATUS[s]}'/>")
        out.append(f"<text x='{lx + 18}' y='{yl + 26}' {FONT} font-size='12' fill='{INK}'>{escape(STATE[lang][s])}</text>")
        lx += 30 + 8 * len(STATE[lang][s])
    return _svg(out, T[lang]["states"], rec, lang, h)


def write(repo: Path, replay_id: str) -> list[str]:
    rec = runs.read(repo / "runs", replay_id)
    d = repo / "docs" / "figures"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for lang in ("fr", "en"):
        for name, fn in (("mae-t1", monthly_mae), ("monitor", monitor_states), ("block", deal_by_month)):
            p = d / f"{name}.{lang}.svg"
            p.write_text(fn(rec, lang))
            out.append(str(p.relative_to(repo)))
    return out
