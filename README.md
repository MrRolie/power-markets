# power-markets

_Français d'abord, la référence ; [English below](#english)._

Construit avec Claude Code sous ma direction.

Peut-on se fier à une prévision du prix horaire de l'électricité à la frontière Québec–New York ? Ce dépôt la
prévoit, la rejoue sur une année mise de côté, et conclut sans détour : 3 des 10 paires modèle-cible battent leur référence, et pour la
congestion, aucun modèle ne bat une prévision de zéro.

Dans les graphiques : **B0** est la référence naïve (le prix de la même heure d'un jour précédent) ; **M1** et **M2** sont deux
modèles concurrents (une régression LASSO et des arbres à gradient boosté) ; **T1** est le prix du marché du jour
précédent, **T3** le prix en temps réel et **T4** la congestion en temps réel (T2 est celle du jour précédent) ;
**EAM** est l'erreur absolue moyenne (MAE en anglais), en dollars américains par MWh : plus elle est basse, meilleure
est la prévision.

![EAM mensuelle de T1 : B0, M1, M2](docs/figures/mae-t1.fr.svg)

L'erreur de M1 est sous celle de la référence B0 chaque mois ; M2 décroche en janvier et février 2026.

**En bref.** Sur l'année réservée (novembre 2025 à octobre 2026), 3 paires modèle-cible sur 10 battent leur
référence ; aucun modèle ne bat la prévision zéro de la congestion. 19 jours de juillet 2026 manquent à l'archive du
temps réel, et une nouvelle ligne Québec–New York (CHPE) est entrée en service pendant l'année : voir les limites du
rapport. Le rapport : [français](docs/report/report.fr.md), [anglais](docs/report/report.en.md). Chaque chiffre vient
d'une exécution consignée dans `runs/`.

L'**année réservée** (hors échantillon) est une année de données tenue à l'écart : aucun prix n'en a été lu avant
que le plan soit figé. Un **bloc 5×16** est une livraison d'électricité de 16
heures par jour, les 5 jours de semaine.

**Première pièce : le prix à la frontière** (`pieces/hq-price`). Prévoir et valider le prix horaire du marché du
jour précédent (day-ahead) et du temps réel à la zone que l'opérateur du réseau de New York (NYISO) nomme « H Q », et la
composante de congestion de chacun, sous une discipline sans anticipation :

- chaque prévision a une heure de décision tirée des documents de l'opérateur, cités ([problème](docs/problem.md)) ;
- un fichier n'est admis que si son heure d'archivage précède l'heure de décision d'au moins 60 minutes ;
- le [plan](docs/plan.md), avec chaque modèle évalué et la règle qui décide « meilleur », est figé par l'étiquette
  `plan-v1` (dans l'historique de travail privé, voir Provenance) avant tout rejeu de l'année réservée ; le résultat
  inscrit est celui du premier rejeu, et un second rejeu, permis par le propriétaire comme écart au plan, est montré
  à côté ;
- une référence naïve et des modèles concurrents ; un moniteur qui dit quand cesser de faire confiance à la
  prévision, avec ce qu'il peut ne pas détecter ; le revenu du lendemain d'un bloc 5×16 énoncé ;
- aucune ligne de profit : rien dans les règles de l'opérateur lues ne montre qu'on puisse prendre la position à
  cet endroit. « Pas d'avantage » est un résultat permis.

Le projet est organisé en pièces : chacune a son dossier sous `pieces/`, et le code partagé vit dans un seul paquet,
`packages/pmcore`.

### Autres graphiques

Chaque graphique est tracé à partir de l'enregistrement du rejeu de l'année réservée qu'il nomme
(`uv run hq-price figures --replay-run <id>`), jamais à partir de chiffres tapés. Seules des statistiques dérivées
sont tracées ; aucune série horaire de prix n'est publiée.

![États du moniteur chaque jour de l'année réservée](docs/figures/monitor.fr.svg)

Les arrêts de juillet sur T3 et T4 sont des jours où des prix en temps réel manquaient à la source, pas une dérive
des modèles.

![Bloc 5×16 de 50 MW : valeur réglée et prévue par mois](docs/figures/block.fr.svg)

**Projet frère** : [valiwatt](https://github.com/MrRolie/valiwatt) valide et surveille une prévision de la demande
horaire d'électricité du Québec, le côté de la demande ; ce dépôt couvre le côté du marché.

## English

Built with Claude Code under my direction.

Can a forecast of the hourly electricity price at the Québec–New York border be trusted? This repository forecasts
it, replays a year set aside, and concludes plainly: 3 of 10
model-target pairs beat their baseline, and on congestion no model beats a forecast of zero.

In the charts: **B0** is the naive baseline (the price of the same hour on an earlier day); **M1** and **M2** are two
competing models (a LASSO regression and gradient-boosted trees); **T1** is the day-ahead price, **T3** the
real-time price and **T4** the real-time congestion (T2 is the day-ahead congestion); **MAE** is the mean absolute
error, in US dollars per MWh: the lower it is, the better the forecast.

![Monthly MAE of T1: B0, M1, M2](docs/figures/mae-t1.en.svg)

M1's error is below the B0 baseline's in every month; M2 breaks away in January and February 2026.

**In short.** On the held-out year (November 2025 to October 2026), 3 of 10 model-target pairs beat their baseline;
no model beats the zero forecast of congestion. 19 days of July 2026 are missing from the real-time archive, and a
new Québec–New York line (CHPE) entered service during the year: see the report's limits. The report:
[French](docs/report/report.fr.md), [English](docs/report/report.en.md). Every number comes from a run recorded in
`runs/`.

The **held-out year** is a year of data kept aside: no price from it was read before the plan was frozen. A **5×16 block** is a delivery of electricity for 16 hours a day on the 5 weekdays.

**First piece: the price at the border** (`pieces/hq-price`). Forecast and validate the hourly day-ahead and
real-time price at the zone New York's grid operator (NYISO) names "H Q", and the congestion component of each,
under a no-lookahead discipline:

- each forecast has a decision time taken from the operator's documents, cited ([problem](docs/problem.md));
- a file is admitted only if its archive stamp is at least 60 minutes before the decision time;
- the [plan](docs/plan.md), with every model scored and the rule that decides "better", is frozen by the tag
  `plan-v1` (in the private working history, see Provenance) before any replay of the held-out year; the result
  of record is the first replay, and a second replay, allowed by the owner as a departure from the plan, is shown
  beside it;
- a naive baseline and competing models; a monitor that says when to stop trusting the forecast, with what it can
  miss; the next-day revenue of a stated 5×16 block;
- no profit line: nothing in the operator's rules read shows the position can be taken at that location. "No
  edge" is a legal result.

The project is organised in pieces: each has its folder under `pieces/`, and shared code lives in one package,
`packages/pmcore`.

### More charts

Each chart is drawn from the held-out replay record it names (`uv run hq-price figures --replay-run <id>`), never
from typed numbers. Only derived statistics are drawn; no hourly price series is published.

![Monitor states on each day of the held-out year](docs/figures/monitor.en.svg)

The July stops on T3 and T4 are days when real-time prices were missing at the source, not model drift.

![50 MW 5×16 block: settled and forecast value by month](docs/figures/block.en.svg)

**Sibling project**: [valiwatt](https://github.com/MrRolie/valiwatt) validates and monitors a forecast of Québec's
hourly electricity demand, the demand side; this repository covers the market side.

### Run it

Python 3.12 and [uv](https://docs.astral.sh/uv/). Every command prints one JSON document.

```sh
uv sync --all-packages
uv run hq-price fetch --product damlbmp --start 2016-01 --end 2025-10   # also rtlbmp, isolf; refuses the held-out year
uv run hq-price validate                                                # walk-forward validation, writes runs/<id>.json
uv run hq-price rehearse --prior-run <validate id>                      # the replay's code path on the last validation year
uv run hq-price replay --prior-run <validate id>                        # once: tag check, ledger, held-out fetch, scores
uv run hq-price derive --from-run <validation id>   # robustness and outcome counts from the saved validation forecasts
uv run hq-price figures --replay-run <id>                              # the README's charts
uv run hq-price report --validate-run <id> --derived-run <id> --rehearse-run <id> --replay-run <id>
uv run pytest
```

### Data

NYISO's public files (`mis.nyiso.com/public`), downloaded by the fetch command into `data/raw/`, never committed
and never redistributed. Terms read and recorded in [docs/data-licences.md](docs/data-licences.md).

## Provenance / Provenance

Ce dépôt public est une copie à historique neuf d'un dépôt de travail privé. Les enregistrements de `runs/` et
`docs/replay-ledger.json` citent des commits de cet historique privé. Le plan a été figé avant le rejeu de l'année
réservée ; l'ordre « plan figé, puis rejeu » repose sur ces enregistrements et sur la confiance, et l'historique
privé peut être montré sur demande. Les données brutes de NYISO ne sont pas redistribuées : `uv run hq-price fetch`
les télécharge.

This public repository is a fresh-history copy of a private working repository. The records in `runs/` and
`docs/replay-ledger.json` cite commits of that private history. The plan was frozen before the held-out year was
replayed; the order "plan frozen, then replay" rests on these records and on trust, and the private history can be
shown on request. NYISO's raw data is not redistributed: `uv run hq-price fetch` downloads it.
