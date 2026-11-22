import sys, zipfile, json
from pathlib import Path
from datetime import datetime
raw = Path(sys.argv[1]); out = {}
def lags(d):
    L = []
    for z in sorted((raw / d).glob("*.zip")):
        for i in zipfile.ZipFile(z).infolist():
            day = datetime.strptime(i.filename[:8], "%Y%m%d")
            L.append(((datetime(*i.date_time) - day).total_seconds() / 3600, i.filename[:8]))
    return L
for d, lim in (("isolf", 5.0), ("rtlbmp", 29.0), ("damlbmp", 5.0)):
    L = lags(d); bad = [f for h, f in L if h >= lim]
    hs = sorted(h for h, _ in L)
    out[d] = {"files": len(L), "limit_h": lim, "late": len(bad), "late_examples": bad[:8],
              "p50": round(hs[len(hs)//2], 2), "p99": round(hs[int(len(hs)*.99)], 2)}
print(json.dumps(out, indent=1))
