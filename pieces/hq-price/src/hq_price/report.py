"""The report, French first (the reference) then English, rendered only from run records (docs/plan.md §10).

Every number is read from a record by `get`; a missing key raises `Untraceable`, so the report refuses to render
rather than print a number it cannot trace. Every table names the run it comes from and that run's label.
Prose that states a result is derived from the records, never a fixed string.
"""

from __future__ import annotations

import json
from pathlib import Path

from pmcore import runs

from hq_price.monitor import REGIME

TNAME = {
    "fr": {"T1_da_lbmp": "T1, prix du marché du jour précédent", "T2_da_mcc": "T2, congestion publiée, jour précédent",
           "T3_rt_lbmp": "T3, prix horaire intégré en temps réel", "T4_rt_mcc": "T4, congestion publiée, temps réel"},
    "en": {"T1_da_lbmp": "T1, day-ahead price", "T2_da_mcc": "T2, day-ahead posted congestion",
           "T3_rt_lbmp": "T3, real-time integrated hourly price", "T4_rt_mcc": "T4, real-time posted congestion"},
}
LABEL = {"fr": {"validation (seen)": "validation (déjà vue)", "held out": "année réservée", "in sample": "dans l'échantillon"},
         "en": {"validation (seen)": "validation (seen)", "held out": "held out", "in sample": "in sample"}}
STATE = {"fr": {"trust": "confiance", "watch": "vigilance", "stop trusting": "cesser de faire confiance",
                "no verdict (window not full)": "aucun avis (fenêtre incomplète)"},
         "en": {"trust": "trust", "watch": "watch", "stop trusting": "stop trusting",
                "no verdict (window not full)": "no verdict (window not full)"}}
NBSP = " "


class Untraceable(KeyError):
    pass


def get(rec: dict, *path):
    cur = rec
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, dict) and str(k) in cur:
            cur = cur[str(k)]
        else:
            raise Untraceable(f"run {rec.get('run_id')}: no value at {'/'.join(map(str, path))}")
    if cur is None:
        raise Untraceable(f"run {rec.get('run_id')}: null at {'/'.join(map(str, path))}")
    return cur


def _num(s: str, lang: str) -> str:
    s = s.replace("-", "−")
    if s.startswith("−") and not s.strip("−0.,"):
        s = s[1:]  # negative zero
    if lang == "fr":
        s = s.replace(",", NBSP).replace(".", ",")
    return s


def f2(x, lang):
    return _num(f"{x:,.2f}", lang)


def f3(x, lang):
    return _num(f"{x:,.3f}", lang)


def f4(x, lang):
    return _num(f"{x:.4f}", lang)


def f0(x, lang):
    return _num(f"{x:,.0f}", lang)


def pct(x, lang, d=1):
    s = _num(f"{100 * x:.{d}f}", lang)
    return s + (f"{NBSP}%" if lang == "fr" else " %")


def pval(x, lang):
    s = "< 0.001" if x < 0.001 else f"{x:.3f}"
    return s.replace(".", ",") if lang == "fr" else s


def peq(x, lang):
    v = pval(x, lang)
    return f"p {v}" if v.startswith("<") else f"p = {v}"


def L(lang, fr, en):
    return fr if lang == "fr" else en


def stamp(rec, lang):
    lab = LABEL[lang][rec["label"]]
    return L(lang, f"_(exécution `{rec['run_id']}`, {lab})_", f"_(run `{rec['run_id']}`, {lab})_")


def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(r) + " |" for r in rows])


def models_in(sc, order=("B0", "B1", "Z", "M1", "M2")):
    return [m for m in order if m in sc]


def gaps(rec) -> dict:
    """Per target, the months scored on fewer hours than the fullest target scored in that month: {t: {month: (k, full)}}."""
    bm = {t: get(rec, "results", t, "by_month") for t in get(rec, "targets")}
    months = sorted(set().union(*bm.values()))
    full = {k: max(get(b, k, "B0", "n_hours") for b in bm.values() if k in b) for k in months}
    out = {}
    for t, b in bm.items():
        g = {k: (get(b, k, "B0", "n_hours") if k in b else 0, full[k]) for k in months
             if (get(b, k, "B0", "n_hours") if k in b else 0) < full[k]}
        if g:
            out[t] = g
    return out


# What the operator's monthly archives held, as listed on 2026-11-21: an observation of files, not a tracked run.
ARCHIVE_LISTING = {
    "2026-07": {"fr": "L'archive mensuelle de l'opérateur pour juillet 2026 (liste P-4A, temps réel), telle que téléchargée, "
                      "passe le test d'intégrité et ne contient que 12 des 31 fichiers quotidiens (le 19 et du 21 au 31 ; liste "
                      "des fichiers de l'archive au 2026-11-21, pas une exécution suivie). Téléchargée de nouveau le 2026-11-22 : "
                      "toujours 12 fichiers ; les jours manquent à la source.",
                "en": "The operator's monthly archive for July 2026 (list P-4A, real time), as fetched, passes an integrity test "
                      "and holds only 12 of 31 daily files (the 19th and the 21st to the 31st; archive file listing on 2026-11-21, "
                      "not a tracked run). Fetched again on 2026-11-22: still 12 files; the days are missing at the source."},
}


def miscounted(rec) -> tuple:
    """Targets with missing outcomes scored by the old code, which counted them as misses or "no congestion".
    Records scored by the fixed code carry `scores._outcomes`."""
    return tuple(t for t in gaps(rec) if "_outcomes" not in get(rec, "results", t, "scores"))


def gap_text(rec, lang):
    g = gaps(rec)
    if not g:
        return ""
    ts = ", ".join(g)
    first = next(iter(g.values()))
    miss = sum(full - k for k, full in first.values())
    ms = ", ".join(first)
    n = get(rec, "results", next(iter(g)), "scores", "B0", "n_hours")
    return L(lang, f"{ts} : {f0(miss, lang)} heures sans résultat ({ms}) ; évaluées sur {f0(n, lang)} heures.",
             f"{ts}: {f0(miss, lang)} hours with no outcome ({ms}); scored on {f0(n, lang)} hours.")


# ------------------------------------------------------------------ tables


def scores_table(rec, target, lang):
    sc = get(rec, "results", target, "scores")
    head = L(lang, ["Modèle", "EAM", "REQM", "Biais", "EAM, décile supérieur", "Heures"],
             ["Model", "MAE", "RMSE", "Bias", "MAE, top decile", "Hours"])
    rows = []
    for m in models_in(sc):
        s = sc[m]
        top = f2(get(s, "mae_top_decile"), lang) if target.endswith("lbmp") else "—"
        rows.append([m, f2(get(s, "mae"), lang), f2(get(s, "rmse"), lang), f2(get(s, "bias"), lang), top,
                     f0(get(s, "n_hours"), lang)])
    return table(head, rows) + "\n\n" + stamp(rec, lang)


def near_zero_note(rec, target, lang):
    """M2 against Z on a congestion target: say it when their MAEs agree within 0.01 $/MWh."""
    sc = get(rec, "results", target, "scores")
    if "Z" not in sc:
        return ""
    d = abs(get(sc, "M2", "mae") - get(sc, "Z", "mae"))
    if d < 0.01:
        return L(lang, f"L'EAM de M2 diffère de celle de Z (prévision zéro) de {f3(d, lang)} $ US/MWh seulement ; les enregistrements ne gardent pas la taille des prévisions de M2. Sous une perte absolue, la médiane conditionnelle d'une série surtout nulle est zéro.\n",
                 f"M2's MAE differs from Z's (the zero forecast) by only {f3(d, lang)} US$/MWh; the records do not keep the size of M2's forecasts. Under absolute loss, the conditional median of a mostly zero series is zero.\n")
    return ""


def rule_table(rec, lang, flagged=()):
    r = get(rec, "rule")
    head = L(lang, ["Paire", "Perte du modèle", "Perte de la référence", "Écart", "p unilatéral (DM)", "p de Holm", "Bat la référence"],
             ["Pair", "Model loss", "Baseline loss", "Difference", "one-sided p (DM)", "Holm p", "Beats baseline"])
    yes, no = L(lang, "oui", "yes"), L(lang, "non", "no")
    rows, marked = [], False
    for k in sorted(r, key=lambda k: (k.split(":")[1], k)):
        v = r[k]
        fm = f4 if k.startswith("P2") else f3
        mark = k.startswith("P2") and k.split(":")[1] in flagged
        marked |= mark
        rows.append([k + (" ¹" if mark else ""), fm(get(v, "loss_model"), lang), fm(get(v, "loss_baseline"), lang),
                     fm(get(v, "loss_model") - get(v, "loss_baseline"), lang), pval(get(v, "dm", "p_one_sided"), lang),
                     pval(get(v, "holm", "p_holm"), lang), yes if get(v, "beats_baseline") else no])
    note = L(lang, f"Pertes : EAM en $ US/MWh ; score de Brier pour P2. Écart = modèle − référence ; négatif = meilleur. Famille de Holm : les {len(r)} paires.",
             f"Losses: MAE in US$/MWh; Brier score for P2. Difference = model − baseline; negative = better. Holm family: the {len(r)} pairs.")
    if marked:
        note += L(lang, " ¹ Calculé en comptant les heures sans résultat comme « pas de congestion » : défaut de calcul ; le signe de l'écart peut changer, le verdict est donc indéterminé tant que ces chiffres ne sont pas recalculés. Voir Limites.",
                  " ¹ Computed counting hours with no outcome as \"no congestion\": a scoring defect; the sign of the difference could change, so the verdict is undetermined until these numbers are recomputed. See Limits.")
    return table(head, rows) + "\n\n" + note + " " + stamp(rec, lang)


def versus_b0_table(rec, lang):
    rows = []
    for t in get(rec, "targets"):
        if not t.endswith("mcc"):
            continue
        r = get(rec, "results", t)
        for m in ("M1", "M2"):
            rows.append([t, m, f3(get(r, "scores", m, "mae"), lang), f3(get(r, "scores", "B0", "mae"), lang),
                         pval(get(r, "versus_B0", m, "p_one_sided"), lang)])
    head = L(lang, ["Cible", "Modèle", "EAM du modèle", "EAM de B0", "p unilatéral (DM, sans correction)"],
             ["Target", "Model", "Model MAE", "B0 MAE", "one-sided p (DM, uncorrected)"])
    lead = L(lang, "Congestion : chaque modèle contre B0, à titre d'information seulement ; la règle juge contre Z.",
             "Congestion: each model against B0, for information only; the rule judges against Z.")
    return lead + "\n\n" + table(head, rows) + "\n\n" + stamp(rec, lang)


def seen_comparisons(rec, lang):
    rows = []
    for t in get(rec, "targets"):
        r = get(rec, "results", t)
        b = get(r, "baseline")
        for m in ("M1", "M2"):
            rows.append([t, b, m, f3(get(r, "scores", m, "mae"), lang), f3(get(r, "scores", b, "mae"), lang),
                         pval(get(r, "versus_baseline", m, "p_one_sided"), lang)])
        if "prob_scores" in r:
            rows.append([t, "P0", "P2", "Brier " + f4(get(r, "prob_scores", "P2", "brier"), lang),
                         "Brier " + f4(get(r, "prob_scores", "P0", "brier"), lang), pval(get(r, "P2_versus_P0", "p_one_sided"), lang)])
    head = L(lang, ["Cible", "Référence", "Modèle", "Perte du modèle", "Perte de la référence", "p unilatéral (DM, sans correction)"],
             ["Target", "Baseline", "Model", "Model loss", "Baseline loss", "one-sided p (DM, uncorrected)"])
    lead = L(lang, "Chaque modèle contre sa référence sur les plis de validation, à titre d'information : la validation ne décide rien.",
             "Each model against its deciding baseline on the validation folds, for information: validation decides nothing.")
    return lead + "\n\n" + table(head, rows) + "\n\n" + stamp(rec, lang)


def by_year_table(rec, target, lang):
    by = get(rec, "results", target, "by_year")
    ms = [m for m in ("B0", "Z", "M1", "M2") if m in by[sorted(by)[0]]]
    rows = [[str(y)] + [f2(get(by, y, m, "mae"), lang) for m in ms] for y in sorted(by)]
    note = L(lang, "EAM par année civile des jours de validation (2022 : novembre et décembre ; 2025 : janvier à octobre).",
             "MAE by calendar year of the validation days (2022: November and December; 2025: January to October).")
    return note + "\n\n" + table([L(lang, "Année", "Year")] + ms, rows) + "\n\n" + stamp(rec, lang)


def robustness_table(rec, target, lang, key):
    rb = get(rec, "results", target, "robustness", key)
    first = rb[sorted(rb)[0]]
    ms = [m for m in ("B0", "Z", "M1", "M2") if m in first]
    order = {"season": ["DJF", "MAM", "JJA", "SON"], "hour_group": ["00-06", "07-22", "23"]}[key]
    rows = [[g] + [f2(get(rb, g, m, "mae"), lang) for m in ms] for g in order if g in rb]
    lab = {"season": L(lang, "Saison", "Season"), "hour_group": L(lang, "Heures", "Hours")}[key]
    return table([lab] + ms, rows) + "\n\n" + stamp(rec, lang)


def where_error(rec, target, lang):
    r = get(rec, "results", target)
    bm = get(r, "by_month")
    ms = ("B0", "M1", "M2")
    rows = [[k] + [f2(get(bm, k, m, "mae"), lang) for m in ms] + [f0(get(bm, k, "B0", "n_hours"), lang)] for k in sorted(bm)]
    out = L(lang, "EAM par mois ($ US/MWh).", "MAE by month (US$/MWh).") + "\n\n" + table([L(lang, "Mois", "Month"), *ms, L(lang, "Heures", "Hours")], rows)
    dec = get(r, "robustness", "price_decile")
    rows = [[k] + [f2(get(dec, k, m, "bias"), lang) for m in ms] for k in sorted(dec, key=int)]
    out += "\n\n" + L(lang, "Biais (prévision − réalisé) par décile du prix réalisé ; 9 = les 10 % d'heures les plus chères.",
                      "Bias (forecast − realised) by realised price decile; 9 = the 10 % most expensive hours.") + "\n\n" + \
        table([L(lang, "Décile", "Decile"), *ms], rows)
    return out + "\n\n" + stamp(rec, lang)


# ------------------------------------------------------------------ sections


def glance(replay, lang, departure=None):
    r = get(replay, "rule")
    beats = [k for k, v in r.items() if v["beats_baseline"]]
    worse = [k for k, v in r.items() if v["loss_model"] > v["loss_baseline"]]
    lower_ns = [k for k, v in r.items() if v["loss_model"] < v["loss_baseline"] and not v["beats_baseline"]]
    cong = [k for k in r if k.split(":")[1].endswith("mcc") and not k.startswith("P2")]
    cong_beats = [k for k in cong if r[k]["beats_baseline"]]
    p = []
    p.append(L(lang, f"Sur l'année réservée, **{len(beats)} paires sur {len(r)}** battent leur référence selon la règle du plan",
               f"On the held-out year, **{len(beats)} of {len(r)} pairs** beat their baseline under the plan's rule")
             + (f"{L(lang, ' : ', ': ')}{', '.join(beats)}." if beats else "."))
    if lower_ns:
        p.append(L(lang, "Perte plus basse, mais non significative après la correction de Holm : ",
                   "Lower loss, but not significant after the Holm correction: ") + ", ".join(lower_ns) + ".")
    if worse:
        p.append(L(lang, "Perte plus haute que la référence : ", "Higher loss than the baseline: ") + ", ".join(worse) + ".")
    p.append(L(lang, "Pour la congestion, ", "For congestion, ")
             + (", ".join(cong_beats) + L(lang, " bat la prévision zéro (Z).", " beats the zero forecast (Z).") if cong_beats
                else L(lang, "aucun modèle ne bat la prévision zéro (Z).", "no model beats the zero forecast (Z).")))
    p.append(L(lang, "« Pas d'avantage » est un résultat permis, publié aussi nettement qu'un avantage. Aucune ligne de profit : rien dans les règles lues ne montre que la position puisse être prise à cet endroit.",
               "\"No edge\" is a legal result, published as plainly as an edge would be. No profit line: nothing in the rules read shows the position can be taken at this location."))
    for k in beats:
        m, t = k.split(":")
        bm = get(replay, "results", t, "by_month")
        base = get(replay, "results", t, "baseline")
        n = sum(get(bm, mo, m, "mae") < get(bm, mo, base, "mae") for mo in bm)
        p.append(L(lang, f"{k} : EAM plus basse que {base} dans {n} des {len(bm)} mois.",
                   f"{k}: lower MAE than {base} in {n} of {len(bm)} months."))
    gt = gap_text(replay, lang)
    if gt:
        und = [k for k in r if k.startswith("P2") and k.split(":")[1] in miscounted(replay)]
        p.append(L(lang, "Données manquantes : ", "Missing data: ") + gt
                 + (L(lang, f" Verdict de {', '.join(und)} indéterminé (défaut de calcul).", f" Verdict of {', '.join(und)} undetermined (scoring defect).") if und else "")
                 + L(lang, " Voir Limites.", " See Limits."))
    if departure is not None:
        r1 = get(departure, "rule")
        changed = [k for k in r1 if k in r and r[k]["beats_baseline"] != r1[k]["beats_baseline"]]
        n1 = sum(v["beats_baseline"] for v in r1.values())
        p.append(L(lang, f"Écart au plan permis par le propriétaire : un second rejeu, les heures sans résultat comptées comme "
                         f"manquantes : {n1} paires sur {len(r1)} ; verdicts changés : {', '.join(changed) if changed else 'aucun'}. "
                         "Voir « Écart au plan ».",
                   f"Departure allowed by the owner: a second replay, hours with no outcome scored as missing: {n1} of {len(r1)} "
                   f"pairs; verdicts changed: {', '.join(changed) if changed else 'none'}. See \"Departure from the plan\"."))
    return L(lang, "## En bref\n\n", "## At a glance\n\n") + "\n".join("- " + x for x in p) + "\n\n" + stamp(replay, lang) + "\n"


def legend(replay, lang):
    first, last = get(replay, "period")
    if lang == "fr":
        return ("## Légende\n\n"
                "- **Cibles** : T1 prix du marché du jour précédent (day-ahead) ; T2 sa composante de congestion publiée ; T3 prix horaire "
                "intégré en temps réel ; T4 sa congestion publiée. Lieu : la zone « H Q ».\n"
                "- **Modèles** : B0 = même heure du dernier jour connu du même marché (la veille pour T1, T2 ; l'avant-veille pour T3, T4) ; "
                "B1 = même heure sept jours plus tôt ; Z = zéro ; M1 = LASSO par heure sur prix transformés (LEAR) ; M2 = arbres "
                "boostés ; M1−LF = M1 sans la prévision de charge ; P0 = part des heures congestionnées sur 28 jours ; P2 = probabilité "
                "par arbres boostés. Référence qui décide : B0 pour T1, T3 ; Z pour T2, T4 ; P0 pour P2.\n"
                f"- **Année réservée** (hors échantillon) : jours d'exploitation des mois {first} à {last} inclus.\n"
                "- **Signes** : biais = prévision − réalisé (négatif = sous-estimation). Prix publié = énergie + pertes − congestion publiée : "
                "une congestion publiée positive abaisse le prix à « H Q ».\n"
                "- **Unités** : dollars américains ; EAM = erreur absolue moyenne (MAE), REQM = racine de l'erreur quadratique moyenne "
                "(RMSE), en $ US/MWh.\n")
    return ("## Legend\n\n"
            "- **Targets**: T1 day-ahead price; T2 its posted congestion component; T3 real-time integrated hourly price; T4 its "
            "posted congestion. Location: the \"H Q\" zone.\n"
            "- **Models**: B0 = same hour of the latest known day of the same market (the day before for T1, T2; two days before "
            "for T3, T4); B1 = same hour seven days earlier; Z = zero; M1 = per-hour LASSO on transformed prices (LEAR); M2 = "
            "boosted trees; M1−LF = M1 without the load forecast; P0 = share of congested hours over 28 days; P2 = boosted-tree "
            "probability. Deciding baseline: B0 for T1, T3; Z for T2, T4; P0 for P2.\n"
            f"- **Held-out year**: operating days of months {first} to {last}, inclusive.\n"
            "- **Signs**: bias = forecast − realised (negative = under-forecast). Posted price = energy + losses − posted "
            "congestion: a positive posted congestion lowers the price at \"H Q\".\n"
            "- **Units**: US dollars; MAE = mean absolute error, RMSE = root mean squared error, in US$/MWh.\n")


def location(lang):
    if lang == "fr":
        return ("## L'endroit et ses règles\n\n"
                "- « H Q » (PTID 61844) est une zone externe publiée « à titre indicatif seulement » ; son prix est celui de la barre "
                "mandataire `HQ_GEN_WHEEL` (Proxy Generator Bus, PTID 23651), qui règle les transactions externes (MST 17.1).\n"
                "- Toutes les barres mandataires d'Hydro-Québec sont désignées « non concurrentielles » (MST 4.4.4) : en temps réel, "
                "une interface congestionnée dans le sens des importations peut fixer le prix à zéro ou moins (MST 17.1.6.3.3).\n"
                "- Mesures de l'exploration des données, pas d'une exécution suivie ([docs/problem.md](../problem.md) §5) : le prix "
                "publié vaut énergie + pertes − congestion publiée (les quinze noms concordent à 0,02 $ US/MWh près au 99e centile, "
                "archives de 2016-01 à 2025-10) ; « H Q » suit la zone NORTH (corrélation 0,974).\n"
                "- Plan figé : [docs/plan.md](../plan.md).\n")
    return ("## The location and its rules\n\n"
            "- \"H Q\" (PTID 61844) is an external zone posted \"for informational purposes only\"; its price is that of the proxy "
            "generator bus `HQ_GEN_WHEEL` (PTID 23651), which settles external transactions (MST 17.1).\n"
            "- Every Hydro-Québec proxy bus is designated non-competitive (MST 4.4.4): in real time, an import-constrained "
            "interface can pin the price at or below zero (MST 17.1.6.3.3).\n"
            "- Measurements from the data spike, not a tracked run ([docs/problem.md](../problem.md) §5): the posted price is "
            "energy + losses − posted congestion (the fifteen names agree within 0.02 US$/MWh at the 99th percentile, archives "
            "2016-01 to 2025-10); \"H Q\" tracks the NORTH zone (correlation 0.974).\n"
            "- Frozen plan: [docs/plan.md](../plan.md).\n")


def discipline(validate, replay, ledger, departures_exist, lang):
    finished = [e for e in ledger if e.get("status") == "finished"]
    g = get(replay, "git")
    ge = replay.get("git_at_end", g)
    yes, no = L(lang, "oui", "yes"), L(lang, "non", "no")
    tag_ok = yes if get(validate, "plan_tag", "match") and get(replay, "plan_tag", "match") else no
    clean = yes if not g["dirty"] and not ge["dirty"] else no
    if lang == "fr":
        return ("## Discipline\n\n"
                "- **Heure de décision** : 5 h, heure de l'Est, la veille du jour d'exploitation, soit la clôture des offres du marché "
                "du jour précédent (Manuel 11 de NYISO, §2.2 ; MST 4.2.1.1). La prévision couvre les 23, 24 ou 25 heures du jour, "
                "de 19 à 43 heures plus tard.\n"
                "- **Admission** : aucun fichier dont l'heure d'archivage est postérieure à 60 minutes avant l'heure de décision "
                "n'est admis ; sinon, le dernier jour admissible précédent prend sa place.\n"
                "- **Validation progressive** (walk-forward) : un pli par mois, réestimation au début de chaque pli, purge selon "
                "l'heure de publication des cibles, embargo de 7 jours imposé par un contrôle qui refuse toute violation.\n"
                f"- **Plan figé** : étiquette `plan-v1` (historique de travail privé, voir la Provenance du README) ; fichiers du plan identiques à l'étiquette lors de la validation et du rejeu : {tag_ok}.\n"
                f"- **Rejeu de l'année réservée** : {len(finished)} rejeu(x) terminé(s) consigné(s) dans `docs/replay-ledger.json` ; rejeu inscrit : "
                f"commit `{g['commit'][:7]}`, arbre propre au début et à la fin : {clean}.\n"
                f"- **Écarts au plan** : {'voir docs/departures.md' if departures_exist else 'aucun'}. Cibles inscrites non exécutées : "
                "aucune. Décisions prises après l'étiquette, avant et après le rejeu : [docs/implementation-notes.md](../implementation-notes.md).\n"
                "- Avant l'étiquette, un examen a mesuré sur la fenêtre de validation que Z bat B0 pour T2 ; c'est pourquoi Z décide "
                "pour la congestion (préambule du plan).\n")
    return ("## Discipline\n\n"
            "- **Decision time**: 05:00 Eastern on the day before the operating day, the day-ahead bid deadline (NYISO Manual 11, "
            "§2.2; MST 4.2.1.1). The forecast covers the 23, 24 or 25 hours of the day, 19 to 43 hours ahead.\n"
            "- **Admission**: no file whose archive stamp is later than 60 minutes before the decision time is admitted; "
            "otherwise the latest earlier qualifying day takes its slot.\n"
            "- **Walk-forward validation**: one fold per month, refit at each fold start, purge by the targets' posting time, a "
            "7-day embargo enforced by a check that refuses any violation.\n"
            f"- **Frozen plan**: tag `plan-v1` (private working history, see the README's Provenance); plan files identical to the tag at validation and at the replay: {tag_ok}.\n"
            f"- **Held-out replay**: {len(finished)} finished replay(s) recorded in `docs/replay-ledger.json`; registered replay: commit "
            f"`{g['commit'][:7]}`, tree clean at start and end: {clean}.\n"
            f"- **Departures from the plan**: {'see docs/departures.md' if departures_exist else 'none'}. Registered targets not "
            "run: none. Decisions taken after the tag, before and after the replay: [docs/implementation-notes.md](../implementation-notes.md).\n"
            "- Before the tag, a review measured on the validation window that Z beats B0 on T2; that is why Z decides for "
            "congestion (plan preamble).\n")


def intervals(derived, replay, lang):
    flagged = miscounted(replay)
    rows = []
    for rec in (derived, replay):
        for t in get(rec, "targets"):
            for m in ("M1", "M2"):
                iv = get(rec, "results", t, "intervals", m)
                mark = " ¹" if rec is replay and t in flagged else ""
                rows.append([LABEL[lang][rec["label"]], t, m, pct(get(iv, "coverage"), lang) + mark,
                             f2(get(iv, "mean_width"), lang), f0(get(iv, "n_hours"), lang)])
    head = L(lang, ["Période", "Cible", "Modèle", "Couverture", "Largeur moyenne ($ US/MWh)", "Heures"],
             ["Period", "Target", "Model", "Coverage", "Mean width (US$/MWh)", "Hours"])
    note = L(lang, "La couverture est mesurée, jamais supposée ; les résidus sont autocorrélés, aucune garantie d'échantillon fini "
                   "n'est revendiquée. Les 11 premiers plis de validation n'ont pas d'intervalle (il faut 330 jours de résidus).",
             "Coverage is measured, never assumed; residuals are autocorrelated, so no finite-sample guarantee is claimed. The "
             "first 11 validation folds have no interval (330 days of residuals are required).")
    if flagged:
        note += L(lang, " ¹ Calculé en comptant les heures sans résultat comme hors de l'intervalle : défaut de calcul qui sous-estime la couverture ; voir Limites.",
                  " ¹ Computed counting hours with no outcome as outside the interval: a scoring defect that understates coverage; see Limits.")
    return (L(lang, "## Intervalles à 90 %\n\n", "## 90 % intervals\n\n") + table(head, rows) + "\n\n" + note + " "
            + stamp(derived, lang) + " " + stamp(replay, lang) + "\n")


def load_forecast(validate, replay, lang):
    out = [L(lang, "## Valeur d'une variable : la prévision de charge de l'opérateur\n",
             "## Value of a variable: the operator's load forecast\n"),
           L(lang, "M1 avec et sans la prévision de charge (M1−LF) ; test unilatéral « M1 plus bas ». Une valeur p proche de 1 veut dire que la prévision de charge nuit. La prévision admise est celle publiée vers 7 h le jour J−2, à 41 à 65 heures des heures de J : c'est la valeur de cette version, pas celle d'une prévision récente comme en utiliserait un pupitre.",
             "M1 with and without the load forecast (M1−LF); one-sided test \"M1 lower\". A p near 1 means the load forecast hurts. The admitted forecast is the one issued about 07:00 on D−2, 41 to 65 hours before the hours of D: this is the value of that vintage, not of a recent forecast as a desk would use.") + "\n"]
    for rec in (validate, replay):
        for t in get(rec, "targets"):
            c = get(rec, "results", t, "M1_versus_M1_noLF")
            sc = get(rec, "results", t, "scores")
            m1, nl = get(sc, "M1", "mae"), get(sc, "M1_noLF", "mae")
            verdict = (L(lang, "la prévision de charge aide", "the load forecast helps") if m1 < nl
                       else L(lang, "la prévision de charge nuit", "the load forecast hurts") if m1 > nl
                       else L(lang, "aucun effet", "no effect"))
            if c.get("stat") is None:
                p = L(lang, "sans objet", "not applicable")
            elif m1 > nl:  # the reverse one-sided test, 1 − p of the registered direction; information only
                p = L(lang, f"« M1−LF plus bas » : {peq(1 - get(c, 'p_one_sided'), lang)}, à titre d'information",
                      f"\"M1−LF lower\": {peq(1 - get(c, 'p_one_sided'), lang)}, for information")
            else:
                p = peq(get(c, "p_one_sided"), lang)
            sep = L(lang, " : ", ": ")
            out.append(f"- {LABEL[lang][rec['label']]}, {t}{sep}M1 {f3(m1, lang)} ; M1−LF {f3(nl, lang)} ; {verdict} ; {p} {stamp(rec, lang)}"
                       .replace(" ; ", " ; " if lang == "fr" else "; "))
    return "\n".join(out) + "\n"


def regime_band(th, k, lang):
    lo, hi = th[REGIME[k.split(":")[1]]]
    return f"[{pct(lo, lang)} ; {pct(hi, lang)}]" if lang == "fr" else f"[{pct(lo, lang)}, {pct(hi, lang)}]"


def monitor(replay, lang):
    mon = get(replay, "monitor")
    head = L(lang, ["Modèle : cible", "Seuil d'erreur relative", "Bande de biais", "Bande de régime", "Jours par état (année réservée)",
                    "Jours de signal : erreur / biais / régime / données", "Jours « cesser » qui sont des jours de signal « données »", "Premier « cesser »"],
             ["Model: target", "Relative-error threshold", "Bias band", "Regime band", "Days per state (held out)",
              "Signal days: error / bias / regime / data", "\"Stop\" days on data-signal days", "First \"stop\""])
    rows, ins, day_one = [], [], []
    names = L(lang, ("erreur relative", "biais", "régime", "données"), ("relative error", "bias", "regime", "data"))
    for k in sorted(mon, key=lambda k: (k.split(":")[1], k)):
        v = mon[k]
        th = get(v, "thresholds")
        d = get(v, "daily")
        sig = [sum(bool(x) for x in d[c]) for c in ("sig_rel", "sig_bias", "sig_regime", "sig_data")]
        st = ", ".join(f"{STATE[lang][s]} {n}" for s, n in sorted(get(v, "states_period").items()))
        sti = ", ".join(f"{STATE[lang][s]} {n}" for s, n in sorted(get(v, "states_prior_in_sample").items()))
        b0, b1 = get(th, "bias")
        band = f"[{f2(b0, lang)} ; {f2(b1, lang)}]" if lang == "fr" else f"[{f2(b0, lang)}, {f2(b1, lang)}]"
        stops = [st_ == "stop trusting" for st_ in d["state"]]
        on_data = sum(a and b for a, b in zip(stops, d["sig_data"]))
        rows.append([k, f2(get(th, "rel_mae_hi"), lang), band, regime_band(th, k, lang), st, " / ".join(map(str, sig)),
                     f"{on_data} / {sum(stops)}", str(v["first_stop_day"] or "—")[:10]])
        if d["state"][0] == "stop trusting":
            on = [n for n, c in zip(names, ("sig_rel", "sig_bias", "sig_regime", "sig_data")) if d[c][0]]
            day_one.append(f"{k} ({', '.join(on)})")
        ins.append([k, sti])
    trust = L(lang, "« Confiance » veut dire « se comporte comme en validation » ; cela ne dit pas si le modèle bat sa référence. "
                    "Seuils et bandes viennent des jours de validation (déjà vus) ; les états, de l'année réservée. Le signal "
                    "« données » s'allume quand une entrée manque ou date de plus de 3 jours ; dans ce rejeu, les heures sans "
                    "résultat comptaient aussi dans la statistique de régime.",
                  "\"Trust\" means \"behaving as in validation\"; it says nothing about whether the model beats its baseline. "
                  "Thresholds and bands come from the validation days (seen); the states from the held-out year. The \"data\" signal "
                  "is on when an input is missing or more than 3 days old; in this replay, hours with no outcome also counted in the regime statistic.")
    rule = L(lang, "Règle : « cesser » quand deux signaux statistiques sont allumés ensemble, quand l'erreur relative dépasse son seuil "
                   "sept jours de suite, ou quand le signal « données » est allumé.",
             "Rule: \"stop\" when two statistical signals are on together, when the relative error exceeds its threshold seven days "
             "running, or when the data signal is on.")
    first_day = ""
    if day_one:
        first_day = L(lang, " Au premier jour de l'année réservée, la fenêtre de 28 jours ne contient que des erreurs des jours de "
                            "validation ; « cesser » ce jour-là, avec les signaux allumés : " + " ; ".join(day_one) + ".",
                      " On the first held-out day, the 28-day window holds only errors of validation days; \"stop\" that day, "
                      "with the signals on: " + "; ".join(day_one) + ".")
    miss = L(lang, "Ce qu'il peut ne pas détecter : un pic bref (la fenêtre de 28 jours le dilue) ; un changement qui dégrade le modèle "
                   "et la référence ensemble (le ratio reste stable) ; une dérive assez lente pour rester dans les seuils ; tout ce qui "
                   "survient dans ses 28 premiers jours. Ses seuils viennent d'une période de validation qui chevauche un changement de "
                   "marché ; ses bandes sont donc larges et peuvent laisser passer un mouvement à l'intérieur de celles-ci.",
             "What it can miss: a short spike (the 28-day window dilutes it); a change that degrades the model and the baseline "
             "alike (the ratio stays flat); drift slow enough to stay inside the thresholds; anything in its first 28 days. Its "
             "thresholds come from a validation period that straddles a change in the market, so its bands are wide and can miss "
             "a move inside them.")
    ins_t = (L(lang, "Signaux sur les jours de validation, où les seuils ont été fixés (dans l'échantillon) :",
               "Signals on the validation days, where the thresholds were fixed (in sample):") + "\n\n" +
             table([head[0], L(lang, "Jours par état (validation, dans l'échantillon)", "Days per state (validation, in sample)")], ins))
    return (L(lang, "## Le moniteur\n\n", "## The monitor\n\n") + table(head, rows) + "\n\n" + stamp(replay, lang) + "\n\n"
            + trust + " " + rule + first_day + "\n\n" + ins_t + "\n\n"
            + L(lang, f"_(exécution `{replay['run_id']}`, jours de validation : {LABEL[lang]['in sample']})_",
                f"_(run `{replay['run_id']}`, validation days: {LABEL[lang]['in sample']})_") + "\n\n" + miss + "\n")


def deal(replay, lang):
    s = get(replay, "deal", "summary")
    c = get(replay, "deal", "congestion")
    settled = get(s, "settled_total")
    if lang == "fr":
        txt = ("## Revenu du lendemain d'un bloc 5×16\n\n"
               "Transaction énoncée : **50 MW livrés à New York à la barre `HQ_GEN_WHEEL`, de 7 h à 22 h 59 (16 heures), chaque jour "
               "ouvrable hors congés NERC (le bloc 5×16), vendus sur le marché du jour précédent, au LBMP qui en résulte.** C'est une "
               "prévision du revenu brut du lendemain, pas une évaluation de pupitre contre les prix à terme, ni un résultat de négociation : aucune ligne de profit.\n\n"
               f"Jours : {f0(get(s, 'days'), lang)} ; valeur au prix de règlement : {f0(settled, lang)} $ US ; part de la congestion "
               f"publiée dans cette valeur : {f0(get(s, 'congestion_settled_total'), lang)} $ US (−50 MW × la congestion publiée ; "
               "positive quand la congestion publiée est négative).\n\n")
    else:
        txt = ("## Next-day revenue of a 5×16 block\n\n"
               "Stated deal: **50 MW delivered into New York at the `HQ_GEN_WHEEL` bus, hours beginning 07:00 to 22:00 (16 hours), each "
               "weekday that is not a NERC holiday (the 5×16 block), sold day-ahead at the resulting LBMP.** This is a "
               "forecast of next-day gross revenue, not a desk valuation against forward prices, nor a trading result: no profit line.\n\n"
               f"Days: {f0(get(s, 'days'), lang)}; value at the settled price: US${f0(settled, lang)}; posted congestion's part of that "
               f"value: US${f0(get(s, 'congestion_settled_total'), lang)} (−50 MW × posted congestion; positive when posted congestion is "
               "negative).\n\n")
    head = L(lang, ["Modèle", "Valeur prévue ($ US)", "Écart au réglé", "Erreur absolue moyenne par jour ($ US)", "Biais par jour ($ US)", "Couverture de la bande à 90 %"],
             ["Model", "Forecast value (US$)", "Versus settled", "Mean absolute daily error (US$)", "Daily bias (US$)", "90 % band coverage"])
    rows = []
    for m in ("B0", "M1", "M2"):
        v = get(s, m)
        cov = (pct(v["band_coverage"], lang) + f" ({v['band_days']} {L(lang, 'j', 'd')})") if "band_coverage" in v else "—"
        rows.append([m, f0(get(v, "forecast_total"), lang), pct(get(v, "forecast_total") / settled - 1, lang),
                     f0(get(v, "mae_daily"), lang), f0(get(v, "bias_daily"), lang), cov])
    bm = get(replay, "deal", "by_month")
    mrows = [[k, f0(get(bm, k, "settled_total"), lang)] + [f0(get(bm, k, m, "forecast_total"), lang) for m in ("B0", "M1", "M2")]
             + [pct(get(bm, k, "M1", "band_coverage"), lang) if "band_coverage" in bm[k]["M1"] else "—", f0(get(bm, k, "days"), lang)]
             for k in sorted(bm)]
    mhead = L(lang, ["Mois", "Réglé", "B0", "M1", "M2", "Couverture de la bande de M1", "Jours"],
              ["Month", "Settled", "B0", "M1", "M2", "M1 band coverage", "Days"])
    cong = L(lang, "Part de la congestion, prévue par les modèles de T2 (total ; erreur absolue moyenne par jour, $ US) : ",
             "Congestion part as forecast by the T2 models (total; mean absolute daily error, US$): ") + \
        L(lang, " ; ", "; ").join(f"{m} {f0(get(c, m, 'forecast_total'), lang)} ({f0(get(c, m, 'mae_daily'), lang)})" for m in ("B0", "M1", "M2")) + \
        L(lang, f" ; réglée : {f0(get(c, 'settled_total'), lang)}.", f"; settled: {f0(get(c, 'settled_total'), lang)}.")
    assume = L(lang, "Hypothèses : le bloc est entièrement accepté, en preneur de prix ; sans frais de transport, de transit ou de "
                     "compensation (uplift), ni autres frais, d'un côté ou de l'autre de la frontière ; aucune valeur de capacité ; "
                     "dollars américains. Le rapport n'affirme pas que quiconque puisse programmer ce bloc. Revenu brut : le coût de l'énergie côté "
                     "Québec et le risque d'équilibrage en temps réel si l'importation est réduite n'y sont pas. L'hypothèse de preneur de "
                     "prix tient le moins quand l'interface est congestionnée dans le sens des importations, c'est-à-dire quand le prix est bas. "
                     "M1 et M2 sont des prévisions de type médiane ; sur des prix asymétriques vers le haut, leur somme sous-estime l'espérance. "
                     "Le prix utilisé est celui de la zone « H Q » ; à quelle barre mandataire (`HQ_GEN_IMPORT` ou `HQ_GEN_WHEEL`) une "
                     "importation ordinaire est programmée n'a pas été établi.",
               "Assumptions: the block clears in full as a price taker; no transmission, wheeling, uplift or other charges on either "
               "side of the border; no capacity value; US dollars. The report does not claim that anyone can schedule this block. Gross revenue: the cost of energy on the Québec "
               "side and the real-time balancing risk if the import is cut are not in it. The price-taker assumption holds least when "
               "the interface binds for imports, which is when the price is low. M1 and M2 are median-type forecasts; on prices "
               "skewed upward, their sum understates the expected value. The price used is the \"H Q\" zone price; which proxy bus "
               "(`HQ_GEN_IMPORT` or `HQ_GEN_WHEEL`) an ordinary import is scheduled at was not established.")
    return (txt + table(head, rows) + "\n\n" + L(lang, "Par mois (valeur, $ US) :", "By month (value, US$):") + "\n\n"
            + table(mhead, mrows) + "\n\n" + cong + "\n\n" + stamp(replay, lang) + "\n\n" + assume + "\n")


def limits(replay, lang, departure=None):
    out = [L(lang, "## Limites\n", "## Limits\n")]
    gt = gap_text(replay, lang)
    if gt:
        months = sorted(set().union(*(g.keys() for g in gaps(replay).values())))
        listing = " ".join(ARCHIVE_LISTING[k][lang] if k in ARCHIVE_LISTING else
                           L(lang, f"{k} : cause non établie.", f"{k}: cause not established.") for k in months)
        after_fr = ("Le propriétaire a permis un second rejeu avec le calcul corrigé : voir « Écart au plan »."
                    if departure is not None else "Le code est corrigé pour les exécutions futures ; recalculer ces chiffres de "
                    "l'année réservée relève du propriétaire et serait un écart au plan, consigné et montré.")
        after_en = ("The owner allowed a second replay with the fixed scoring: see \"Departure from the plan\"."
                    if departure is not None else "The code is fixed for future runs; recomputing these held-out numbers is the "
                    "owner's call and would be a departure from the plan, recorded and shown.")
        out.append(L(lang,
            f"- **Résultats manquants.** {gt} {listing} Deux calculs du rejeu comptent ces heures à tort : la couverture des "
            "intervalles (comptées hors de l'intervalle, ce qui sous-estime la couverture) et le score de Brier de P2 et P0 (comptées "
            "« sans congestion »). " + after_fr,
            f"- **Missing outcomes.** {gt} {listing} Two of the replay's computations count these hours wrongly: interval coverage (counted as outside the "
            "interval, which understates coverage) and the Brier score of P2 and P0 (counted as \"no congestion\"). " + after_en))
    rm = {m: get(replay, "results", "T2_da_mcc", "scores", m, "rmse") for m in ("Z", "M1")}
    out.append(L(lang,
        "- **Une rupture dans l'année réservée.** La ligne Champlain Hudson Power Express (CHPE, 1 250 MW, du Québec à New York) "
        "est entrée en exploitation commerciale le 2026-05-13 et a été hors service à partir du 2026-07-04 pour la plus grande "
        "partie de juillet (S&P Global ; GCN ; MIT Technology Review : sources publiques, pas une exécution suivie). Les données "
        "d'entraînement ne l'ont jamais vue. Les jours de juillet sans prix en temps réel recouvrent cette panne : T3 et T4 sont "
        "évalués sans les jours de temps réel les plus difficiles de l'été.",
        "- **A break inside the held-out year.** The Champlain Hudson Power Express line (CHPE, 1,250 MW, Québec to New York City) "
        "entered commercial operation on 2026-05-13 and was out from 2026-07-04 for most of July (S&P Global; GCN; MIT Technology "
        "Review: public sources, not a tracked run). The training data never saw it. The July days without real-time prices overlap "
        "that outage: T3 and T4 are scored without the summer's hardest real-time days."))
    out.append(L(lang,
        "- **Ce que les références mesurent.** B0 pour T3 est le prix en temps réel de l'avant-veille ; M1 et M2 ont les prix du "
        "jour précédent parmi leurs entrées, donc leur gain sur T3 peut tenir surtout à l'information du marché du jour précédent. "
        "Une référence « prix du jour précédent pris comme prévision du temps réel » et l'écart jour précédent − temps réel, la "
        "vraie décision entre les deux marchés, n'ont pas été inscrits au plan et ne sont pas évalués. T3 et T4 à 5 h la veille ne "
        "prévoient pas ce que voit un programmeur en temps réel, qui décide environ 75 minutes avant l'heure. B0 prend la veille "
        "tous les jours (le lundi à partir du dimanche) ; la référence naïve usuelle prend J−7 le lundi, le samedi et le dimanche.",
        "- **What the baselines measure.** B0 for T3 is the real-time price two days earlier; M1 and M2 have day-ahead prices among "
        "their inputs, so their gain on T3 may be mostly day-ahead information. A \"day-ahead price as the real-time forecast\" "
        "baseline and the day-ahead − real-time spread, the actual decision between the two markets, were not registered and are "
        "not scored. T3 and T4 at 05:00 the day before do not forecast what a real-time scheduler sees, who decides about 75 minutes "
        "before the hour. B0 takes the previous day every day (Monday from Sunday); the usual naive benchmark takes D−7 on Monday, "
        "Saturday and Sunday."))
    out.append(L(lang,
        f"- **Le choix de la perte.** Sous une perte absolue, la prévision zéro est presque imbattable sur une série surtout nulle : "
        f"« aucun modèle ne bat Z » est en partie une propriété de la perte. Sous l'erreur quadratique, M1 est un peu sous Z sur T2 "
        f"(REQM {f2(rm['M1'], lang)} contre {f2(rm['Z'], lang)}) {stamp(replay, lang)}, sans test.",
        f"- **The choice of loss.** Under absolute loss, the zero forecast is nearly unbeatable on a mostly zero series: \"no model "
        f"beats Z\" is partly a property of the loss. Under squared error, M1 is slightly below Z on T2 (RMSE {f2(rm['M1'], lang)} "
        f"against {f2(rm['Z'], lang)}) {stamp(replay, lang)}, untested."))
    out.append(L(lang,
        "- **Les heures d'archivage.** Leur accord avec la colonne « Last Updated » des listes de l'opérateur a été vérifié un seul "
        "jour, en heure normale ; l'heure d'été n'a pas été vérifiée. Si l'opérateur reconstruisait une archive mensuelle corrigée "
        "en gardant les heures d'origine, une valeur corrigée entrerait sans être vue ; ce cas n'a pas été testé.",
        "- **Archive stamps.** Their agreement with the operator's \"Last Updated\" column was checked on one day, in standard "
        "time; summer time was not checked. If the operator rebuilt a monthly archive with corrected values while keeping the "
        "original stamps, a corrected value would enter unseen; that case was not tested."))
    out.append(L(lang,
        "- **Aucune ligne de profit.** La formation de NYISO décrit les transactions virtuelles au niveau des zones, avec des "
        "exemples de zones internes ; aucun document lu ne montre de point d'offre virtuelle à une barre mandataire externe. Qui peut "
        "programmer une importation à `HQ_GEN_WHEEL`, et à quel coût des deux côtés, n'a pas été établi.",
        "- **No profit line.** NYISO's training material describes virtual bidding at the zonal level, with internal-zone examples; no "
        "document read shows a virtual bid point at an external proxy bus. Who can schedule an import at `HQ_GEN_WHEEL`, and at what "
        "cost on both sides, was not established."))
    out.append(L(lang,
        "- **B0 est un plancher, pas une référence de pupitre.** Aucune donnée météo, de prix du gaz, d'indisponibilités ou de limites "
        "d'interface n'est admise ; les modèles sont statistiques, pas fondamentaux.",
        "- **B0 is a floor, not a desk benchmark.** No weather, gas prices, outages or interface limits are admitted; the models are "
        "statistical, not fundamental."))
    out.append(L(lang,
        "- **Valeurs corrigées.** L'archive contient les prix corrigés ; un fichier corrigé qui aurait gardé son heure d'origine ferait "
        "entrer une valeur corrigée. Le groupe de validation des prix de NYISO n'a déclaré aucune correction du prix du jour précédent "
        "de 2007 à septembre 2017, et 78 jours de marché avec corrections du temps réel de 2013 à septembre 2017 (NYISO, MIWG, "
        "2017-11-02) ; les corrections après octobre 2017 ne sont pas connues.",
        "- **Corrected values.** The archive holds corrected prices; a corrected file that kept its original stamp would let a "
        "corrected value in. NYISO's price-validation group reported no day-ahead price correction from 2007 to September 2017, and "
        "78 market days with real-time corrections from 2013 to September 2017 (NYISO, MIWG, 2017-11-02); corrections after October "
        "2017 are not known."))
    out.append(L(lang,
        "- **Séparation procédurale.** L'année réservée était déjà passée quand ce travail a été fait ; sa séparation tient à une "
        "barrière sur le téléchargement, à l'étiquette et au registre. La connaissance générale qu'avaient les auteurs de l'hiver "
        "2025-2026 ne peut pas être exclue. L'ordre des événements (plan, étiquette, rejeu) ne se vérifie que par l'historique de "
        "ce dépôt, dont les dates sont fixées par l'auteur ; aucun horodatage externe ne l'atteste.",
        "- **Procedural separation.** The held-out year was already past when this work was done; its separation rests on a fence on "
        "the fetch, the tag and the ledger. The authors' general knowledge of the 2025–26 winter cannot be excluded. The order of "
        "events (plan, tag, replay) can be checked only through this repository's history, whose dates the author sets; no external "
        "timestamp attests it."))
    out.append(L(lang,
        "- **Aucune validation indépendante.** Le modèle, les contrôles et ce rapport viennent d'agents d'IA travaillant pour un seul "
        "propriétaire ; les examens par d'autres modèles ne sont pas une validation indépendante. Une seule année réservée ; aucune "
        "revue périodique.",
        "- **No independent validation.** The model, the checks and this report come from AI agents working for one owner; reviews "
        "by other models are not independent validation. One held-out year; no periodic review."))
    return "\n".join(out) + "\n"


def sibling(lang):
    return L(lang,
        "## Projet frère\n\n[valiwatt](https://github.com/MrRolie/valiwatt) valide et surveille une prévision de la demande horaire "
        "d'électricité du Québec : le côté de la demande. Ce dépôt couvre le prix à la frontière new-yorkaise : le côté du marché.\n",
        "## Sibling project\n\n[valiwatt](https://github.com/MrRolie/valiwatt) validates and monitors a forecast of Québec's hourly "
        "electricity demand: the demand side. This repository covers the price at the New York border: the market side.\n")


def departure_section(replay, dep, ledger, lang):
    """A second replay is a departure (plan §10): shown beside the registered result, never in its place."""
    e = [x for x in ledger if x.get("run_id") == dep["run_id"]]
    if not e or not e[0].get("departure") or e[0].get("status") != "finished":
        raise Untraceable(f"run {dep['run_id']}: no finished departure entry in the replay ledger")
    r0, r1 = get(replay, "rule"), get(dep, "rule")
    n0, n1 = sum(v["beats_baseline"] for v in r0.values()), sum(v["beats_baseline"] for v in r1.values())
    changed = [k for k in sorted(r1) if k in r0 and r0[k]["beats_baseline"] != r1[k]["beats_baseline"]]
    out = [L(lang, "## Écart au plan : second rejeu\n", "## Departure from the plan: a second replay\n"),
           L(lang, f"Raison consignée : « {e[0]['departure']} ». Le résultat inscrit reste celui du premier rejeu ; ce "
                   f"second rejeu est montré à côté, jamais à sa place. Paires qui battent leur référence : {n1} sur {len(r1)} "
                   f"(premier rejeu : {n0}). Verdicts changés : {', '.join(changed) if changed else 'aucun'}.",
             f"Recorded reason: \"{e[0]['departure']}\". The registered result stays the first replay's; this second replay "
             f"is shown beside it, never in its place. Pairs that beat their baseline: {n1} of {len(r1)} (first replay: {n0}). "
             f"Verdicts changed: {', '.join(changed) if changed else 'none'}.") + "\n"]
    same = all(get(replay, "results", t, "forecasts_sha256") == get(dep, "results", t, "forecasts_sha256") for t in get(dep, "targets"))
    if same:
        out.append(L(lang, "Ses prévisions sont identiques à celles du premier rejeu (mêmes empreintes SHA-256) : seul le calcul des "
                           "scores diffère.", "Its forecasts are identical to the first replay's (same SHA-256 hashes): only the "
                           "scoring differs.") + "\n")
    if get(dep, "git", "dirty"):
        out.append(L(lang, "L'enregistrement marque l'arbre « modifié » au début : c'est l'entrée de registre que la commande écrit "
                           "avant cet instantané ; la commande refuse un arbre modifié avant de l'écrire (corrigé ensuite, voir "
                           "docs/implementation-notes.md).",
                     "The record marks the tree dirty at the start: that is the ledger entry the command writes before this "
                     "snapshot; the command refuses a dirty tree before writing it (fixed afterwards, see "
                     "docs/implementation-notes.md).") + "\n")
    gt = gap_text(dep, lang)
    out.append(gt + "\n" if gt else L(lang, "Aucune heure sans résultat.\n", "No hour without an outcome.\n"))
    out.append(rule_table(dep, lang, miscounted(dep)) + "\n")
    rows = []
    for t in get(dep, "targets"):
        for m in ("M1", "M2"):
            iv = get(dep, "results", t, "intervals", m)
            rows.append([t, m, pct(get(iv, "coverage"), lang), f0(get(iv, "n_hours"), lang)])
    out.append(table(L(lang, ["Cible", "Modèle", "Couverture à 90 %", "Heures"], ["Target", "Model", "90 % coverage", "Hours"]), rows)
               + "\n\n" + stamp(dep, lang) + "\n")
    return "\n".join(out)


def render(validate: dict, derived: dict, rehearse: dict, replay: dict, ledger: list, departures_exist: bool, lang: str,
           departure: dict | None = None) -> str:
    T = TNAME[lang]
    flagged = miscounted(replay)
    out = []
    w = out.append
    w(L(lang, "# Le prix à la frontière : la zone « H Q » de NYISO\n\n_Version française, la référence. [English version](report.en.md)._\n",
        "# The price at the border: NYISO's \"H Q\" zone\n\n_English version. [Version française, la référence](report.fr.md)._\n"))
    w(L(lang, "Ce dépôt prévoit et valide le prix horaire de l'électricité à la zone que l'opérateur du réseau de New York (NYISO) "
              "nomme « H Q », la frontière avec le Québec, et la composante de congestion de ce prix, sur le marché du jour précédent et "
              "en temps réel. Ce qui compte ici est la discipline, pas le modèle : chaque prévision a une heure de décision tirée des "
              "documents de l'opérateur ; aucun fichier archivé moins de 60 minutes avant cette heure n'est admis ; le plan a été figé "
              "par une étiquette git avant tout rejeu de l'année réservée.\n",
        "This repository forecasts and validates the hourly electricity price at the zone New York's grid operator (NYISO) names "
        "\"H Q\", the border with Québec, and the congestion component of that price, day-ahead and real-time. What matters here is "
        "the discipline, not the model: each forecast has a decision time taken from the operator's documents; no file archived less "
        "than 60 minutes before that time is admitted; the plan was frozen by a git tag before any replay of the held-out year.\n"))
    w(glance(replay, lang, departure))
    w(legend(replay, lang))
    w(location(lang))
    w(discipline(validate, replay, ledger, departures_exist, lang))
    w(L(lang, "## Résultats sur l'année réservée\n", "## Results on the held-out year\n"))
    w(rule_table(replay, lang, flagged) + "\n")
    for t in get(replay, "targets"):
        w(f"### {T[t]}\n")
        w(scores_table(replay, t, lang) + "\n")
        w(near_zero_note(replay, t, lang))
        w(L(lang, "Par saison et par groupe d'heures (EAM) :", "By season and hour group (MAE):") + "\n")
        w(robustness_table(replay, t, lang, "season") + "\n")
        w(robustness_table(replay, t, lang, "hour_group") + "\n")
    w(versus_b0_table(replay, lang) + "\n")
    w(L(lang, "### Où se trouve l'erreur (T1)\n", "### Where the error lies (T1)\n"))
    w(where_error(replay, "T1_da_lbmp", lang) + "\n")
    if departure is not None:
        w(departure_section(replay, departure, ledger, lang))
    w(L(lang, "## Répétition sur la dernière année de validation (novembre 2024 à octobre 2025, déjà vue)\n",
        "## Rehearsal on the last validation year (November 2024 to October 2025, seen)\n"))
    w(L(lang, "Le même code que le rejeu, sur une année déjà vue : un signal de stabilité, pas un test.",
        "The same code as the replay, on a seen year: a stability signal, not a test.") + "\n")
    w(rule_table(rehearse, lang) + "\n")
    w(L(lang, "## Validation (déjà vue), novembre 2022 à octobre 2025\n", "## Validation (seen), November 2022 to October 2025\n"))
    w(L(lang, "Ces chiffres ont servi à fixer les seuils et les intervalles ; ils ne décident de rien.",
        "These numbers set the thresholds and the intervals; they decide nothing.") + "\n")
    w(seen_comparisons(validate, lang) + "\n")
    w(versus_b0_table(validate, lang) + "\n")
    for t in get(validate, "targets"):
        w(f"### {T[t]}\n")
        w(scores_table(validate, t, lang) + "\n")
        w(near_zero_note(validate, t, lang))
        w(by_year_table(validate, t, lang) + "\n")
        w(L(lang, "Par saison et par groupe d'heures (EAM) :", "By season and hour group (MAE):") + "\n")
        w(robustness_table(derived, t, lang, "season") + "\n")
        w(robustness_table(derived, t, lang, "hour_group") + "\n")
    w(intervals(derived, replay, lang))
    w(load_forecast(validate, replay, lang))
    w(monitor(replay, lang))
    w(deal(replay, lang))
    w(limits(replay, lang, departure))
    w(sibling(lang))
    return "\n".join(out)


def write(repo: Path, validate_id: str, derived_id: str, rehearse_id: str, replay_id: str,
          departure_id: str | None = None) -> list[str]:
    rd = repo / "runs"
    v, dv, rh, rp = (runs.read(rd, x) for x in (validate_id, derived_id, rehearse_id, replay_id))
    dp = runs.read(rd, departure_id) if departure_id else None
    if dv.get("source_run") != validate_id:
        raise Untraceable(f"derived run {derived_id} is not derived from {validate_id}")
    ledger = json.loads((repo / "docs" / "replay-ledger.json").read_text())
    dep = (repo / "docs" / "departures.md").exists()
    (repo / "docs" / "report").mkdir(parents=True, exist_ok=True)
    out = []
    for lang in ("fr", "en"):
        p = repo / "docs" / "report" / f"report.{lang}.md"
        p.write_text(render(v, dv, rh, rp, ledger, dep, lang, dp))
        out.append(str(p.relative_to(repo)))
    return out
