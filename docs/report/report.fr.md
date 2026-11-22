# Le prix à la frontière : la zone « H Q » de NYISO

_Version française, la référence. [English version](report.en.md)._

Ce dépôt prévoit et valide le prix horaire de l'électricité à la zone que l'opérateur du réseau de New York (NYISO) nomme « H Q », la frontière avec le Québec, et la composante de congestion de ce prix, sur le marché du jour précédent et en temps réel. Ce qui compte ici est la discipline, pas le modèle : chaque prévision a une heure de décision tirée des documents de l'opérateur ; aucun fichier archivé moins de 60 minutes avant cette heure n'est admis ; le plan a été figé par une étiquette git avant tout rejeu de l'année réservée.

## En bref

- Sur l'année réservée, **3 paires sur 10** battent leur référence selon la règle du plan : M1:T1_da_lbmp, M1:T3_rt_lbmp, M2:T3_rt_lbmp.
- Perte plus basse, mais non significative après la correction de Holm : P2:T2_da_mcc.
- Perte plus haute que la référence : M1:T2_da_mcc, M1:T4_rt_mcc, M2:T1_da_lbmp, M2:T2_da_mcc, M2:T4_rt_mcc, P2:T4_rt_mcc.
- Pour la congestion, aucun modèle ne bat la prévision zéro (Z).
- « Pas d'avantage » est un résultat permis, publié aussi nettement qu'un avantage. Aucune ligne de profit : rien dans les règles lues ne montre que la position puisse être prise à cet endroit.
- M1:T1_da_lbmp : EAM plus basse que B0 dans 12 des 12 mois.
- M1:T3_rt_lbmp : EAM plus basse que B0 dans 12 des 12 mois.
- M2:T3_rt_lbmp : EAM plus basse que B0 dans 12 des 12 mois.
- Données manquantes : T3_rt_lbmp, T4_rt_mcc : 456 heures sans résultat (2026-07) ; évaluées sur 8 304 heures. Verdict de P2:T4_rt_mcc indéterminé (défaut de calcul). Voir Limites.
- Écart au plan permis par le propriétaire : un second rejeu, les heures sans résultat comptées comme manquantes : 3 paires sur 10 ; verdicts changés : aucun. Voir « Écart au plan ».

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

## Légende

- **Cibles** : T1 prix du marché du jour précédent (day-ahead) ; T2 sa composante de congestion publiée ; T3 prix horaire intégré en temps réel ; T4 sa congestion publiée. Lieu : la zone « H Q ».
- **Modèles** : B0 = même heure du dernier jour connu du même marché (la veille pour T1, T2 ; l'avant-veille pour T3, T4) ; B1 = même heure sept jours plus tôt ; Z = zéro ; M1 = LASSO par heure sur prix transformés (LEAR) ; M2 = arbres boostés ; M1−LF = M1 sans la prévision de charge ; P0 = part des heures congestionnées sur 28 jours ; P2 = probabilité par arbres boostés. Référence qui décide : B0 pour T1, T3 ; Z pour T2, T4 ; P0 pour P2.
- **Année réservée** (hors échantillon) : jours d'exploitation des mois 2025-11 à 2026-10 inclus.
- **Signes** : biais = prévision − réalisé (négatif = sous-estimation). Prix publié = énergie + pertes − congestion publiée : une congestion publiée positive abaisse le prix à « H Q ».
- **Unités** : dollars américains ; EAM = erreur absolue moyenne (MAE), REQM = racine de l'erreur quadratique moyenne (RMSE), en $ US/MWh.

## L'endroit et ses règles

- « H Q » (PTID 61844) est une zone externe publiée « à titre indicatif seulement » ; son prix est celui de la barre mandataire `HQ_GEN_WHEEL` (Proxy Generator Bus, PTID 23651), qui règle les transactions externes (MST 17.1).
- Toutes les barres mandataires d'Hydro-Québec sont désignées « non concurrentielles » (MST 4.4.4) : en temps réel, une interface congestionnée dans le sens des importations peut fixer le prix à zéro ou moins (MST 17.1.6.3.3).
- Mesures de l'exploration des données, pas d'une exécution suivie ([docs/problem.md](../problem.md) §5) : le prix publié vaut énergie + pertes − congestion publiée (les quinze noms concordent à 0,02 $ US/MWh près au 99e centile, archives de 2016-01 à 2025-10) ; « H Q » suit la zone NORTH (corrélation 0,974).
- Plan figé : [docs/plan.md](../plan.md).

## Discipline

- **Heure de décision** : 5 h, heure de l'Est, la veille du jour d'exploitation, soit la clôture des offres du marché du jour précédent (Manuel 11 de NYISO, §2.2 ; MST 4.2.1.1). La prévision couvre les 23, 24 ou 25 heures du jour, de 19 à 43 heures plus tard.
- **Admission** : aucun fichier dont l'heure d'archivage est postérieure à 60 minutes avant l'heure de décision n'est admis ; sinon, le dernier jour admissible précédent prend sa place.
- **Validation progressive** (walk-forward) : un pli par mois, réestimation au début de chaque pli, purge selon l'heure de publication des cibles, embargo de 7 jours imposé par un contrôle qui refuse toute violation.
- **Plan figé** : étiquette `plan-v1` ; fichiers du plan identiques à l'étiquette lors de la validation et du rejeu : oui.
- **Rejeu de l'année réservée** : 2 rejeu(x) terminé(s) consigné(s) dans `docs/replay-ledger.json` ; rejeu inscrit : commit `3bc75c2`, arbre propre au début et à la fin : oui.
- **Écarts au plan** : voir docs/departures.md. Cibles inscrites non exécutées : aucune. Décisions prises après l'étiquette, avant et après le rejeu : [docs/implementation-notes.md](../implementation-notes.md).
- Avant l'étiquette, un examen a mesuré sur la fenêtre de validation que Z bat B0 pour T2 ; c'est pourquoi Z décide pour la congestion (préambule du plan).

## Résultats sur l'année réservée

| Paire | Perte du modèle | Perte de la référence | Écart | p unilatéral (DM) | p de Holm | Bat la référence |
|---|---|---|---|---|---|---|
| M1:T1_da_lbmp | 10,592 | 14,038 | −3,446 | < 0,001 | < 0,001 | oui |
| M2:T1_da_lbmp | 15,814 | 14,038 | 1,776 | 0,734 | 1,000 | non |
| M1:T2_da_mcc | 1,786 | 1,367 | 0,420 | 1,000 | 1,000 | non |
| M2:T2_da_mcc | 1,370 | 1,367 | 0,003 | 0,946 | 1,000 | non |
| P2:T2_da_mcc | 0,1067 | 0,1115 | −0,0048 | 0,021 | 0,148 | non |
| M1:T3_rt_lbmp | 17,600 | 25,816 | −8,216 | < 0,001 | < 0,001 | oui |
| M2:T3_rt_lbmp | 17,753 | 25,816 | −8,064 | < 0,001 | < 0,001 | oui |
| M1:T4_rt_mcc | 1,238 | 0,674 | 0,564 | 1,000 | 1,000 | non |
| M2:T4_rt_mcc | 0,675 | 0,674 | 0,001 | 0,843 | 1,000 | non |
| P2:T4_rt_mcc ¹ | 0,1001 | 0,0990 | 0,0011 | 0,669 | 1,000 | non |

Pertes : EAM en $ US/MWh ; score de Brier pour P2. Écart = modèle − référence ; négatif = meilleur. Famille de Holm : les 10 paires. ¹ Calculé en comptant les heures sans résultat comme « pas de congestion » : défaut de calcul ; le signe de l'écart peut changer, le verdict est donc indéterminé tant que ces chiffres ne sont pas recalculés. Voir Limites. _(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

### T1, prix du marché du jour précédent

| Modèle | EAM | REQM | Biais | EAM, décile supérieur | Heures |
|---|---|---|---|---|---|
| B0 | 14,04 | 33,23 | 0,04 | 64,58 | 8 760 |
| B1 | 32,92 | 86,10 | 0,28 | 172,46 | 8 760 |
| M1 | 10,59 | 30,91 | −5,19 | 57,84 | 8 760 |
| M2 | 15,81 | 56,07 | −7,28 | 103,02 | 8 760 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_


Par saison et par groupe d'heures (EAM) :

| Saison | B0 | M1 | M2 |
|---|---|---|---|
| DJF | 33,91 | 28,48 | 45,54 |
| MAM | 7,69 | 4,59 | 5,68 |
| JJA | 9,12 | 5,49 | 7,60 |
| SON | 5,78 | 4,12 | 4,96 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

| Heures | B0 | M1 | M2 |
|---|---|---|---|
| 00-06 | 11,08 | 9,25 | 12,10 |
| 07-22 | 15,52 | 11,21 | 17,63 |
| 23 | 11,05 | 10,11 | 12,82 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

### T2, congestion publiée, jour précédent

| Modèle | EAM | REQM | Biais | EAM, décile supérieur | Heures |
|---|---|---|---|---|---|
| B0 | 2,01 | 10,35 | 0,00 | — | 8 760 |
| B1 | 2,57 | 12,41 | 0,00 | — | 8 760 |
| Z | 1,37 | 8,95 | 0,80 | — | 8 760 |
| M1 | 1,79 | 8,87 | 0,76 | — | 8 760 |
| M2 | 1,37 | 8,95 | 0,79 | — | 8 760 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

L'EAM de M2 diffère de celle de Z (prévision zéro) de 0,003 $ US/MWh seulement ; les enregistrements ne gardent pas la taille des prévisions de M2. Sous une perte absolue, la médiane conditionnelle d'une série surtout nulle est zéro.

Par saison et par groupe d'heures (EAM) :

| Saison | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| DJF | 6,48 | 4,60 | 5,00 | 4,60 |
| MAM | 0,33 | 0,18 | 0,58 | 0,18 |
| JJA | 0,78 | 0,45 | 0,96 | 0,45 |
| SON | 0,54 | 0,30 | 0,66 | 0,31 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

| Heures | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 00-06 | 1,32 | 0,87 | 1,18 | 0,87 |
| 07-22 | 2,34 | 1,60 | 2,06 | 1,60 |
| 23 | 1,63 | 1,11 | 1,58 | 1,12 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

### T3, prix horaire intégré en temps réel

| Modèle | EAM | REQM | Biais | EAM, décile supérieur | Heures |
|---|---|---|---|---|---|
| B0 | 25,82 | 59,48 | −0,10 | 94,15 | 8 304 |
| B1 | 31,17 | 66,42 | 0,39 | 115,47 | 8 304 |
| M1 | 17,60 | 45,55 | −10,20 | 86,79 | 8 304 |
| M2 | 17,75 | 46,09 | −8,72 | 85,13 | 8 304 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_


Par saison et par groupe d'heures (EAM) :

| Saison | B0 | M1 | M2 |
|---|---|---|---|
| DJF | 50,51 | 36,31 | 36,34 |
| MAM | 18,94 | 11,62 | 12,19 |
| JJA | 18,26 | 11,24 | 11,46 |
| SON | 14,41 | 10,24 | 10,05 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

| Heures | B0 | M1 | M2 |
|---|---|---|---|
| 00-06 | 18,79 | 12,53 | 11,75 |
| 07-22 | 29,36 | 20,08 | 20,67 |
| 23 | 18,38 | 13,35 | 13,06 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

### T4, congestion publiée, temps réel

| Modèle | EAM | REQM | Biais | EAM, décile supérieur | Heures |
|---|---|---|---|---|---|
| B0 | 1,31 | 10,60 | 0,01 | — | 8 304 |
| B1 | 1,32 | 10,60 | 0,00 | — | 8 304 |
| Z | 0,67 | 7,50 | −0,15 | — | 8 304 |
| M1 | 1,24 | 7,55 | 0,12 | — | 8 304 |
| M2 | 0,67 | 7,50 | −0,15 | — | 8 304 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

L'EAM de M2 diffère de celle de Z (prévision zéro) de 0,001 $ US/MWh seulement ; les enregistrements ne gardent pas la taille des prévisions de M2. Sous une perte absolue, la médiane conditionnelle d'une série surtout nulle est zéro.

Par saison et par groupe d'heures (EAM) :

| Saison | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| DJF | 1,72 | 0,88 | 1,80 | 0,88 |
| MAM | 1,03 | 0,53 | 0,93 | 0,53 |
| JJA | 1,33 | 0,69 | 1,20 | 0,69 |
| SON | 1,18 | 0,60 | 1,02 | 0,60 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

| Heures | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 00-06 | 0,34 | 0,18 | 0,46 | 0,18 |
| 07-22 | 1,74 | 0,90 | 1,60 | 0,90 |
| 23 | 1,16 | 0,61 | 0,85 | 0,61 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

Congestion : chaque modèle contre B0, à titre d'information seulement ; la règle juge contre Z.

| Cible | Modèle | EAM du modèle | EAM de B0 | p unilatéral (DM, sans correction) |
|---|---|---|---|---|
| T2_da_mcc | M1 | 1,786 | 2,012 | 0,132 |
| T2_da_mcc | M2 | 1,370 | 2,012 | 0,001 |
| T4_rt_mcc | M1 | 1,238 | 1,310 | 0,246 |
| T4_rt_mcc | M2 | 0,675 | 1,310 | < 0,001 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

### Où se trouve l'erreur (T1)

EAM par mois ($ US/MWh).

| Mois | B0 | M1 | M2 | Heures |
|---|---|---|---|---|
| 2025-11 | 7,03 | 5,00 | 7,35 | 721 |
| 2025-12 | 21,15 | 16,03 | 17,79 | 744 |
| 2026-01 | 58,05 | 49,90 | 83,97 | 744 |
| 2026-02 | 21,30 | 18,56 | 33,74 | 672 |
| 2026-03 | 8,95 | 4,57 | 6,00 | 743 |
| 2026-04 | 6,80 | 4,62 | 5,43 | 720 |
| 2026-05 | 7,28 | 4,58 | 5,59 | 744 |
| 2026-06 | 6,41 | 4,29 | 5,12 | 720 |
| 2026-07 | 15,11 | 8,41 | 13,75 | 744 |
| 2026-08 | 5,76 | 3,74 | 3,86 | 744 |
| 2026-09 | 5,51 | 3,91 | 3,34 | 720 |
| 2026-10 | 4,83 | 3,46 | 4,21 | 744 |

Biais (prévision − réalisé) par décile du prix réalisé ; 9 = les 10 % d'heures les plus chères.

| Décile | B0 | M1 | M2 |
|---|---|---|---|
| 0 | 3,84 | 1,39 | 3,72 |
| 1 | 2,15 | 0,39 | 1,42 |
| 2 | 1,49 | 0,22 | 0,73 |
| 3 | 0,83 | −0,07 | 0,25 |
| 4 | −0,49 | −0,95 | −0,65 |
| 5 | −0,18 | −1,84 | −1,56 |
| 6 | 1,37 | −1,67 | −1,07 |
| 7 | 0,30 | −2,01 | −1,84 |
| 8 | 0,06 | −6,04 | −6,86 |
| 9 | −9,09 | −41,72 | −67,54 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

## Écart au plan : second rejeu

Raison consignée : « The July 2026 real-time archive as first fetched held 12 of 31 daily files; re-fetched, and the held-out year replayed with missing outcomes scored as missing (post-replay scoring fix, docs/implementation-notes.md). Allowed by the owner on 2026-11-22, answering the card 'May I re-download it and run a second held-out replay, shown in the report beside the first as a recorded departure from the plan?': 'Yes, re-run (Recommended)'. ». Le résultat inscrit reste celui du premier rejeu ; ce second rejeu est montré à côté, jamais à sa place. Paires qui battent leur référence : 3 sur 10 (premier rejeu : 3). Verdicts changés : aucun.

Ses prévisions sont identiques à celles du premier rejeu (mêmes empreintes SHA-256) : seul le calcul des scores diffère.

L'enregistrement marque l'arbre « modifié » au début : c'est l'entrée de registre que la commande écrit avant cet instantané ; la commande refuse un arbre modifié avant de l'écrire (corrigé ensuite, voir docs/implementation-notes.md).

T3_rt_lbmp, T4_rt_mcc : 456 heures sans résultat (2026-07) ; évaluées sur 8 304 heures.

| Paire | Perte du modèle | Perte de la référence | Écart | p unilatéral (DM) | p de Holm | Bat la référence |
|---|---|---|---|---|---|---|
| M1:T1_da_lbmp | 10,592 | 14,038 | −3,446 | < 0,001 | < 0,001 | oui |
| M2:T1_da_lbmp | 15,814 | 14,038 | 1,776 | 0,734 | 1,000 | non |
| M1:T2_da_mcc | 1,786 | 1,367 | 0,420 | 1,000 | 1,000 | non |
| M2:T2_da_mcc | 1,370 | 1,367 | 0,003 | 0,946 | 1,000 | non |
| P2:T2_da_mcc | 0,1067 | 0,1115 | −0,0048 | 0,021 | 0,148 | non |
| M1:T3_rt_lbmp | 17,600 | 25,816 | −8,216 | < 0,001 | < 0,001 | oui |
| M2:T3_rt_lbmp | 17,753 | 25,816 | −8,064 | < 0,001 | < 0,001 | oui |
| M1:T4_rt_mcc | 1,238 | 0,674 | 0,564 | 1,000 | 1,000 | non |
| M2:T4_rt_mcc | 0,675 | 0,674 | 0,001 | 0,843 | 1,000 | non |
| P2:T4_rt_mcc | 0,1012 | 0,1035 | −0,0023 | 0,044 | 0,262 | non |

Pertes : EAM en $ US/MWh ; score de Brier pour P2. Écart = modèle − référence ; négatif = meilleur. Famille de Holm : les 10 paires. _(exécution `20261122T183753Z-replay-38737f`, année réservée)_

| Cible | Modèle | Couverture à 90 % | Heures |
|---|---|---|---|
| T1_da_lbmp | M1 | 88,7 % | 8 760 |
| T1_da_lbmp | M2 | 88,4 % | 8 760 |
| T2_da_mcc | M1 | 88,1 % | 8 760 |
| T2_da_mcc | M2 | 91,4 % | 8 760 |
| T3_rt_lbmp | M1 | 89,3 % | 8 304 |
| T3_rt_lbmp | M2 | 89,1 % | 8 304 |
| T4_rt_mcc | M1 | 92,5 % | 8 304 |
| T4_rt_mcc | M2 | 91,9 % | 8 304 |

_(exécution `20261122T183753Z-replay-38737f`, année réservée)_

## Répétition sur la dernière année de validation (novembre 2024 à octobre 2025, déjà vue)

Le même code que le rejeu, sur une année déjà vue : un signal de stabilité, pas un test.

| Paire | Perte du modèle | Perte de la référence | Écart | p unilatéral (DM) | p de Holm | Bat la référence |
|---|---|---|---|---|---|---|
| M1:T1_da_lbmp | 8,343 | 10,069 | −1,726 | < 0,001 | < 0,001 | oui |
| M2:T1_da_lbmp | 8,409 | 10,069 | −1,660 | < 0,001 | 0,001 | oui |
| M1:T2_da_mcc | 0,708 | 0,483 | 0,225 | 1,000 | 1,000 | non |
| M2:T2_da_mcc | 0,493 | 0,483 | 0,009 | 0,968 | 1,000 | non |
| P2:T2_da_mcc | 0,1048 | 0,1255 | −0,0207 | 0,004 | 0,023 | oui |
| M1:T3_rt_lbmp | 17,241 | 22,944 | −5,703 | < 0,001 | < 0,001 | oui |
| M2:T3_rt_lbmp | 15,777 | 22,944 | −7,166 | < 0,001 | < 0,001 | oui |
| M1:T4_rt_mcc | 1,944 | 1,166 | 0,778 | 1,000 | 1,000 | non |
| M2:T4_rt_mcc | 1,166 | 1,166 | 0,000 | 1,000 | 1,000 | non |
| P2:T4_rt_mcc | 0,1308 | 0,1363 | −0,0055 | 0,005 | 0,024 | oui |

Pertes : EAM en $ US/MWh ; score de Brier pour P2. Écart = modèle − référence ; négatif = meilleur. Famille de Holm : les 10 paires. _(exécution `20261120T231232Z-rehearse-796e3f`, validation (déjà vue))_

## Validation (déjà vue), novembre 2022 à octobre 2025

Ces chiffres ont servi à fixer les seuils et les intervalles ; ils ne décident de rien.

Chaque modèle contre sa référence sur les plis de validation, à titre d'information : la validation ne décide rien.

| Cible | Référence | Modèle | Perte du modèle | Perte de la référence | p unilatéral (DM, sans correction) |
|---|---|---|---|---|---|
| T1_da_lbmp | B0 | M1 | 6,193 | 7,591 | < 0,001 |
| T1_da_lbmp | B0 | M2 | 6,494 | 7,591 | < 0,001 |
| T2_da_mcc | Z | M1 | 0,793 | 0,451 | 1,000 |
| T2_da_mcc | Z | M2 | 0,463 | 0,451 | 0,992 |
| T2_da_mcc | P0 | P2 | Brier 0,1257 | Brier 0,1323 | 0,022 |
| T3_rt_lbmp | B0 | M1 | 12,613 | 17,582 | < 0,001 |
| T3_rt_lbmp | B0 | M2 | 12,200 | 17,582 | < 0,001 |
| T4_rt_mcc | Z | M1 | 2,860 | 1,333 | 1,000 |
| T4_rt_mcc | Z | M2 | 1,333 | 1,333 | 0,920 |
| T4_rt_mcc | P0 | P2 | Brier 0,1211 | Brier 0,1250 | < 0,001 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_

Congestion : chaque modèle contre B0, à titre d'information seulement ; la règle juge contre Z.

| Cible | Modèle | EAM du modèle | EAM de B0 | p unilatéral (DM, sans correction) |
|---|---|---|---|---|
| T2_da_mcc | M1 | 0,793 | 0,728 | 0,960 |
| T2_da_mcc | M2 | 0,463 | 0,728 | < 0,001 |
| T4_rt_mcc | M1 | 2,860 | 2,555 | 0,802 |
| T4_rt_mcc | M2 | 1,333 | 2,555 | < 0,001 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_

### T1, prix du marché du jour précédent

| Modèle | EAM | REQM | Biais | EAM, décile supérieur | Heures |
|---|---|---|---|---|---|
| B0 | 7,59 | 16,49 | −0,01 | 27,57 | 26 304 |
| B1 | 13,38 | 28,28 | −0,12 | 45,77 | 26 304 |
| M1 | 6,19 | 12,85 | −1,39 | 24,55 | 26 304 |
| M2 | 6,49 | 13,75 | −0,42 | 23,12 | 26 304 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_


EAM par année civile des jours de validation (2022 : novembre et décembre ; 2025 : janvier à octobre).

| Année | B0 | M1 | M2 |
|---|---|---|---|
| 2022 | 16,01 | 13,53 | 14,02 |
| 2023 | 6,22 | 4,81 | 5,23 |
| 2024 | 5,40 | 4,55 | 4,70 |
| 2025 | 10,18 | 8,36 | 8,65 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_

Par saison et par groupe d'heures (EAM) :

| Saison | B0 | M1 | M2 |
|---|---|---|---|
| DJF | 13,85 | 11,79 | 12,00 |
| MAM | 4,65 | 3,83 | 3,94 |
| JJA | 6,77 | 5,08 | 5,59 |
| SON | 5,18 | 4,14 | 4,53 |

_(exécution `20261121T002222Z-derive-9213d8`, validation (déjà vue))_

| Heures | B0 | M1 | M2 |
|---|---|---|---|
| 00-06 | 6,10 | 5,00 | 4,57 |
| 07-22 | 8,37 | 6,77 | 7,40 |
| 23 | 5,48 | 5,34 | 5,40 |

_(exécution `20261121T002222Z-derive-9213d8`, validation (déjà vue))_

### T2, congestion publiée, jour précédent

| Modèle | EAM | REQM | Biais | EAM, décile supérieur | Heures |
|---|---|---|---|---|---|
| B0 | 0,73 | 3,40 | 0,00 | — | 26 304 |
| B1 | 0,81 | 3,54 | 0,00 | — | 26 304 |
| Z | 0,45 | 2,58 | −0,31 | — | 26 304 |
| M1 | 0,79 | 2,56 | −0,02 | — | 26 304 |
| M2 | 0,46 | 2,54 | −0,28 | — | 26 304 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_


EAM par année civile des jours de validation (2022 : novembre et décembre ; 2025 : janvier à octobre).

| Année | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 2022 | 0,61 | 0,32 | 0,80 | 0,35 |
| 2023 | 0,58 | 0,37 | 0,83 | 0,39 |
| 2024 | 0,75 | 0,49 | 0,77 | 0,49 |
| 2025 | 0,91 | 0,53 | 0,77 | 0,54 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_

Par saison et par groupe d'heures (EAM) :

| Saison | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| DJF | 0,73 | 0,44 | 0,73 | 0,45 |
| MAM | 0,39 | 0,22 | 0,50 | 0,23 |
| JJA | 1,34 | 0,84 | 1,36 | 0,86 |
| SON | 0,46 | 0,30 | 0,57 | 0,32 |

_(exécution `20261121T002222Z-derive-9213d8`, validation (déjà vue))_

| Heures | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 00-06 | 0,45 | 0,27 | 0,49 | 0,28 |
| 07-22 | 0,87 | 0,54 | 0,94 | 0,55 |
| 23 | 0,44 | 0,29 | 0,56 | 0,31 |

_(exécution `20261121T002222Z-derive-9213d8`, validation (déjà vue))_

### T3, prix horaire intégré en temps réel

| Modèle | EAM | REQM | Biais | EAM, décile supérieur | Heures |
|---|---|---|---|---|---|
| B0 | 17,58 | 45,95 | −0,23 | 59,40 | 26 304 |
| B1 | 18,95 | 47,57 | −0,28 | 61,38 | 26 304 |
| M1 | 12,61 | 34,18 | −4,21 | 56,60 | 26 304 |
| M2 | 12,20 | 33,38 | −2,19 | 47,85 | 26 304 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_


EAM par année civile des jours de validation (2022 : novembre et décembre ; 2025 : janvier à octobre).

| Année | B0 | M1 | M2 |
|---|---|---|---|
| 2022 | 40,42 | 28,65 | 28,32 |
| 2023 | 13,94 | 9,63 | 9,77 |
| 2024 | 12,23 | 8,72 | 8,50 |
| 2025 | 23,81 | 17,66 | 16,34 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_

Par saison et par groupe d'heures (EAM) :

| Saison | B0 | M1 | M2 |
|---|---|---|---|
| DJF | 28,19 | 22,11 | 20,69 |
| MAM | 11,33 | 8,00 | 7,93 |
| JJA | 18,27 | 11,76 | 11,70 |
| SON | 12,68 | 8,71 | 8,59 |

_(exécution `20261121T002222Z-derive-9213d8`, validation (déjà vue))_

| Heures | B0 | M1 | M2 |
|---|---|---|---|
| 00-06 | 11,91 | 9,16 | 8,67 |
| 07-22 | 20,42 | 14,29 | 13,93 |
| 23 | 11,89 | 9,99 | 9,26 |

_(exécution `20261121T002222Z-derive-9213d8`, validation (déjà vue))_

### T4, congestion publiée, temps réel

| Modèle | EAM | REQM | Biais | EAM, décile supérieur | Heures |
|---|---|---|---|---|---|
| B0 | 2,56 | 35,04 | 0,01 | — | 26 304 |
| B1 | 2,58 | 34,77 | −0,01 | — | 26 304 |
| Z | 1,33 | 24,60 | −1,12 | — | 26 304 |
| M1 | 2,86 | 24,69 | −0,53 | — | 26 304 |
| M2 | 1,33 | 24,60 | −1,12 | — | 26 304 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_

L'EAM de M2 diffère de celle de Z (prévision zéro) de 0,000 $ US/MWh seulement ; les enregistrements ne gardent pas la taille des prévisions de M2. Sous une perte absolue, la médiane conditionnelle d'une série surtout nulle est zéro.

EAM par année civile des jours de validation (2022 : novembre et décembre ; 2025 : janvier à octobre).

| Année | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 2022 | 12,77 | 6,67 | 8,20 | 6,67 |
| 2023 | 2,20 | 1,13 | 2,99 | 1,13 |
| 2024 | 1,28 | 0,67 | 2,54 | 0,67 |
| 2025 | 2,47 | 1,31 | 2,02 | 1,31 |

_(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_

Par saison et par groupe d'heures (EAM) :

| Saison | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| DJF | 4,72 | 2,47 | 4,20 | 2,47 |
| MAM | 0,57 | 0,29 | 1,46 | 0,29 |
| JJA | 4,30 | 2,21 | 4,29 | 2,21 |
| SON | 0,65 | 0,37 | 1,50 | 0,37 |

_(exécution `20261121T002222Z-derive-9213d8`, validation (déjà vue))_

| Heures | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 00-06 | 0,82 | 0,47 | 1,46 | 0,47 |
| 07-22 | 3,40 | 1,76 | 3,57 | 1,76 |
| 23 | 1,22 | 0,59 | 1,32 | 0,59 |

_(exécution `20261121T002222Z-derive-9213d8`, validation (déjà vue))_

## Intervalles à 90 %

| Période | Cible | Modèle | Couverture | Largeur moyenne ($ US/MWh) | Heures |
|---|---|---|---|---|---|
| validation (déjà vue) | T1_da_lbmp | M1 | 87,2 % | 23,64 | 18 288 |
| validation (déjà vue) | T1_da_lbmp | M2 | 87,4 % | 23,14 | 18 288 |
| validation (déjà vue) | T2_da_mcc | M1 | 89,1 % | 3,07 | 18 288 |
| validation (déjà vue) | T2_da_mcc | M2 | 89,2 % | 1,96 | 18 288 |
| validation (déjà vue) | T3_rt_lbmp | M1 | 87,0 % | 48,07 | 18 288 |
| validation (déjà vue) | T3_rt_lbmp | M2 | 87,0 % | 44,20 | 18 288 |
| validation (déjà vue) | T4_rt_mcc | M1 | 91,1 % | 9,82 | 18 288 |
| validation (déjà vue) | T4_rt_mcc | M2 | 90,2 % | 1,91 | 18 288 |
| année réservée | T1_da_lbmp | M1 | 88,7 % | 42,38 | 8 760 |
| année réservée | T1_da_lbmp | M2 | 88,4 % | 46,36 | 8 760 |
| année réservée | T2_da_mcc | M1 | 88,1 % | 4,13 | 8 760 |
| année réservée | T2_da_mcc | M2 | 91,4 % | 2,51 | 8 760 |
| année réservée | T3_rt_lbmp | M1 | 84,6 % ¹ | 77,22 | 8 760 |
| année réservée | T3_rt_lbmp | M2 | 84,4 % ¹ | 77,95 | 8 760 |
| année réservée | T4_rt_mcc | M1 | 87,7 % ¹ | 4,79 | 8 760 |
| année réservée | T4_rt_mcc | M2 | 87,1 % ¹ | 1,45 | 8 760 |

La couverture est mesurée, jamais supposée ; les résidus sont autocorrélés, aucune garantie d'échantillon fini n'est revendiquée. Les 11 premiers plis de validation n'ont pas d'intervalle (il faut 330 jours de résidus). ¹ Calculé en comptant les heures sans résultat comme hors de l'intervalle : défaut de calcul qui sous-estime la couverture ; voir Limites. _(exécution `20261121T002222Z-derive-9213d8`, validation (déjà vue))_ _(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

## Valeur d'une variable : la prévision de charge de l'opérateur

M1 avec et sans la prévision de charge (M1−LF) ; test unilatéral « M1 plus bas ». Une valeur p proche de 1 veut dire que la prévision de charge nuit. La prévision admise est celle publiée vers 7 h le jour J−2, à 41 à 65 heures des heures de J : c'est la valeur de cette version, pas celle d'une prévision récente comme en utiliserait un pupitre.

- validation (déjà vue), T1_da_lbmp : M1 6,193 ; M1−LF 6,796 ; la prévision de charge aide ; p < 0,001 _(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_
- validation (déjà vue), T2_da_mcc : M1 0,793 ; M1−LF 0,761 ; la prévision de charge nuit ; « M1−LF plus bas » : p < 0,001, à titre d'information _(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_
- validation (déjà vue), T3_rt_lbmp : M1 12,613 ; M1−LF 12,781 ; la prévision de charge aide ; p = 0,004 _(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_
- validation (déjà vue), T4_rt_mcc : M1 2,860 ; M1−LF 2,742 ; la prévision de charge nuit ; « M1−LF plus bas » : p < 0,001, à titre d'information _(exécution `20261120T221928Z-validate-ba9571`, validation (déjà vue))_
- année réservée, T1_da_lbmp : M1 10,592 ; M1−LF 12,906 ; la prévision de charge aide ; p < 0,001 _(exécution `20261120T233440Z-replay-8359cd`, année réservée)_
- année réservée, T2_da_mcc : M1 1,786 ; M1−LF 1,767 ; la prévision de charge nuit ; « M1−LF plus bas » : p = 0,073, à titre d'information _(exécution `20261120T233440Z-replay-8359cd`, année réservée)_
- année réservée, T3_rt_lbmp : M1 17,600 ; M1−LF 18,587 ; la prévision de charge aide ; p < 0,001 _(exécution `20261120T233440Z-replay-8359cd`, année réservée)_
- année réservée, T4_rt_mcc : M1 1,238 ; M1−LF 1,197 ; la prévision de charge nuit ; « M1−LF plus bas » : p < 0,001, à titre d'information _(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

## Le moniteur

| Modèle : cible | Seuil d'erreur relative | Bande de biais | Bande de régime | Jours par état (année réservée) | Jours de signal : erreur / biais / régime / données | Jours « cesser » qui sont des jours de signal « données » | Premier « cesser » |
|---|---|---|---|---|---|---|---|
| M1:T1_da_lbmp | 1,03 | [−11,41 ; 3,01] | [2,6 % ; 54,4 %] | cesser de faire confiance 1, confiance 328, vigilance 36 | 1 / 37 / 0 / 0 | 0 / 1 | 2026-01-29 |
| M2:T1_da_lbmp | 1,05 | [−5,88 ; 4,81] | [2,6 % ; 54,4 %] | cesser de faire confiance 81, confiance 239, vigilance 45 | 84 / 107 / 0 / 0 | 0 / 81 | 2025-11-01 |
| M1:T2_da_mcc | 8,37 | [−0,73 ; 0,89] | [2,6 % ; 54,4 %] | confiance 291, vigilance 74 | 0 / 74 / 0 / 0 | 0 / 0 | — |
| M2:T2_da_mcc | 1,21 | [−1,32 ; 0,01] | [2,6 % ; 54,4 %] | confiance 186, vigilance 179 | 0 / 179 / 0 / 0 | 0 / 0 | — |
| M1:T3_rt_lbmp | 0,86 | [−33,80 ; 6,43] | [0,0 % ; 18,6 %] | cesser de faire confiance 20, confiance 318, vigilance 27 | 0 / 27 / 0 / 20 | 20 / 20 | 2026-07-06 |
| M2:T3_rt_lbmp | 0,81 | [−18,33 ; 9,54] | [0,0 % ; 18,6 %] | cesser de faire confiance 45, confiance 298, vigilance 22 | 39 / 31 / 0 / 20 | 20 / 45 | 2025-11-27 |
| M1:T4_rt_mcc | 12,52 | [−10,02 ; 1,75] | [0,0 % ; 18,6 %] | cesser de faire confiance 20, confiance 345 | 0 / 0 / 0 / 20 | 20 / 20 | 2026-07-06 |
| M2:T4_rt_mcc | 1,00 | [−11,66 ; 0,01] | [0,0 % ; 18,6 %] | cesser de faire confiance 42, confiance 236, vigilance 87 | 28 / 81 / 0 / 20 | 20 / 42 | 2026-01-24 |

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

« Confiance » veut dire « se comporte comme en validation » ; cela ne dit pas si le modèle bat sa référence. Seuils et bandes viennent des jours de validation (déjà vus) ; les états, de l'année réservée. Le signal « données » s'allume quand une entrée manque ou date de plus de 3 jours ; dans ce rejeu, les heures sans résultat comptaient aussi dans la statistique de régime. Règle : « cesser » quand deux signaux statistiques sont allumés ensemble, quand l'erreur relative dépasse son seuil sept jours de suite, ou quand le signal « données » est allumé. Au premier jour de l'année réservée, la fenêtre de 28 jours ne contient que des erreurs des jours de validation ; « cesser » ce jour-là, avec les signaux allumés : M2:T1_da_lbmp (erreur relative, biais).

Signaux sur les jours de validation, où les seuils ont été fixés (dans l'échantillon) :

| Modèle : cible | Jours par état (validation, dans l'échantillon) |
|---|---|
| M1:T1_da_lbmp | aucun avis (fenêtre incomplète) 28, cesser de faire confiance 22, confiance 959, vigilance 87 |
| M2:T1_da_lbmp | aucun avis (fenêtre incomplète) 28, cesser de faire confiance 30, confiance 954, vigilance 84 |
| M1:T2_da_mcc | aucun avis (fenêtre incomplète) 28, cesser de faire confiance 50, confiance 961, vigilance 57 |
| M2:T2_da_mcc | aucun avis (fenêtre incomplète) 28, cesser de faire confiance 36, confiance 960, vigilance 72 |
| M1:T3_rt_lbmp | aucun avis (fenêtre incomplète) 29, cesser de faire confiance 53, confiance 956, vigilance 58 |
| M2:T3_rt_lbmp | aucun avis (fenêtre incomplète) 29, cesser de faire confiance 42, confiance 949, vigilance 76 |
| M1:T4_rt_mcc | aucun avis (fenêtre incomplète) 29, cesser de faire confiance 48, confiance 932, vigilance 87 |
| M2:T4_rt_mcc | aucun avis (fenêtre incomplète) 29, cesser de faire confiance 58, confiance 929, vigilance 80 |

_(exécution `20261120T233440Z-replay-8359cd`, jours de validation : dans l'échantillon)_

Ce qu'il peut ne pas détecter : un pic bref (la fenêtre de 28 jours le dilue) ; un changement qui dégrade le modèle et la référence ensemble (le ratio reste stable) ; une dérive assez lente pour rester dans les seuils ; tout ce qui survient dans ses 28 premiers jours. Ses seuils viennent d'une période de validation qui chevauche un changement de marché ; ses bandes sont donc larges et peuvent laisser passer un mouvement à l'intérieur de celles-ci.

## Revenu du lendemain d'un bloc 5×16

Transaction énoncée : **50 MW livrés à New York à la barre `HQ_GEN_WHEEL`, de 7 h à 22 h 59 (16 heures), chaque jour ouvrable hors congés NERC (le bloc 5×16), vendus sur le marché du jour précédent, au LBMP qui en résulte.** C'est une prévision du revenu brut du lendemain, pas une évaluation de pupitre contre les prix à terme, ni un résultat de négociation : aucune ligne de profit.

Jours : 255 ; valeur au prix de règlement : 15 561 928 $ US ; part de la congestion publiée dans cette valeur : 192 220 $ US (−50 MW × la congestion publiée ; positive quand la congestion publiée est négative).

| Modèle | Valeur prévue ($ US) | Écart au réglé | Erreur absolue moyenne par jour ($ US) | Biais par jour ($ US) | Couverture de la bande à 90 % |
|---|---|---|---|---|---|
| B0 | 15 318 557 | −1,6 % | 11 361 | −954 | 87,8 % (255 j) |
| M1 | 14 618 270 | −6,1 % | 7 860 | −3 701 | 88,6 % (255 j) |
| M2 | 13 170 798 | −15,4 % | 13 632 | −9 377 | 88,2 % (255 j) |

Par mois (valeur, $ US) :

| Mois | Réglé | B0 | M1 | M2 | Couverture de la bande de M1 | Jours |
|---|---|---|---|---|---|---|
| 2025-11 | 911 244 | 877 956 | 860 615 | 782 033 | 100,0 % | 19 |
| 2025-12 | 1 926 044 | 1 845 620 | 1 783 798 | 1 679 735 | 77,3 % | 22 |
| 2026-01 | 3 647 658 | 3 626 504 | 3 114 221 | 1 930 379 | 52,4 % | 21 |
| 2026-02 | 1 881 414 | 2 044 488 | 1 949 094 | 2 042 696 | 55,0 % | 20 |
| 2026-03 | 887 487 | 885 080 | 878 524 | 878 847 | 100,0 % | 22 |
| 2026-04 | 755 468 | 729 112 | 707 003 | 691 052 | 100,0 % | 22 |
| 2026-05 | 678 508 | 675 507 | 665 188 | 680 667 | 100,0 % | 20 |
| 2026-06 | 919 868 | 850 139 | 916 273 | 864 338 | 100,0 % | 22 |
| 2026-07 | 1 456 198 | 1 329 080 | 1 327 922 | 1 181 558 | 78,3 % | 23 |
| 2026-08 | 926 654 | 894 666 | 891 593 | 927 478 | 100,0 % | 21 |
| 2026-09 | 778 694 | 780 714 | 746 896 | 766 884 | 100,0 % | 21 |
| 2026-10 | 792 692 | 779 690 | 777 142 | 745 131 | 100,0 % | 22 |

Part de la congestion, prévue par les modèles de T2 (total ; erreur absolue moyenne par jour, $ US) : B0 184 770 (877) ; M1 −106 (972) ; M2 1 265 (782) ; réglée : 192 220.

_(exécution `20261120T233440Z-replay-8359cd`, année réservée)_

Hypothèses : le bloc est entièrement accepté, en preneur de prix ; sans frais de transport, de transit ou de compensation (uplift), ni autres frais, d'un côté ou de l'autre de la frontière ; aucune valeur de capacité ; dollars américains. Le rapport n'affirme pas que quiconque puisse programmer ce bloc. Revenu brut : le coût de l'énergie côté Québec et le risque d'équilibrage en temps réel si l'importation est réduite n'y sont pas. L'hypothèse de preneur de prix tient le moins quand l'interface est congestionnée dans le sens des importations, c'est-à-dire quand le prix est bas. M1 et M2 sont des prévisions de type médiane ; sur des prix asymétriques vers le haut, leur somme sous-estime l'espérance. Le prix utilisé est celui de la zone « H Q » ; à quelle barre mandataire (`HQ_GEN_IMPORT` ou `HQ_GEN_WHEEL`) une importation ordinaire est programmée n'a pas été établi.

## Limites

- **Résultats manquants.** T3_rt_lbmp, T4_rt_mcc : 456 heures sans résultat (2026-07) ; évaluées sur 8 304 heures. L'archive mensuelle de l'opérateur pour juillet 2026 (liste P-4A, temps réel), telle que téléchargée, passe le test d'intégrité et ne contient que 12 des 31 fichiers quotidiens (le 19 et du 21 au 31 ; liste des fichiers de l'archive au 2026-11-21, pas une exécution suivie). Téléchargée de nouveau le 2026-11-22 : toujours 12 fichiers ; les jours manquent à la source. Deux calculs du rejeu comptent ces heures à tort : la couverture des intervalles (comptées hors de l'intervalle, ce qui sous-estime la couverture) et le score de Brier de P2 et P0 (comptées « sans congestion »). Le propriétaire a permis un second rejeu avec le calcul corrigé : voir « Écart au plan ».
- **Une rupture dans l'année réservée.** La ligne Champlain Hudson Power Express (CHPE, 1 250 MW, du Québec à New York) est entrée en exploitation commerciale le 2026-05-13 et a été hors service à partir du 2026-07-04 pour la plus grande partie de juillet (S&P Global ; GCN ; MIT Technology Review : sources publiques, pas une exécution suivie). Les données d'entraînement ne l'ont jamais vue. Les jours de juillet sans prix en temps réel recouvrent cette panne : T3 et T4 sont évalués sans les jours de temps réel les plus difficiles de l'été.
- **Ce que les références mesurent.** B0 pour T3 est le prix en temps réel de l'avant-veille ; M1 et M2 ont les prix du jour précédent parmi leurs entrées, donc leur gain sur T3 peut tenir surtout à l'information du marché du jour précédent. Une référence « prix du jour précédent pris comme prévision du temps réel » et l'écart jour précédent − temps réel, la vraie décision entre les deux marchés, n'ont pas été inscrits au plan et ne sont pas évalués. T3 et T4 à 5 h la veille ne prévoient pas ce que voit un programmeur en temps réel, qui décide environ 75 minutes avant l'heure. B0 prend la veille tous les jours (le lundi à partir du dimanche) ; la référence naïve usuelle prend J−7 le lundi, le samedi et le dimanche.
- **Le choix de la perte.** Sous une perte absolue, la prévision zéro est presque imbattable sur une série surtout nulle : « aucun modèle ne bat Z » est en partie une propriété de la perte. Sous l'erreur quadratique, M1 est un peu sous Z sur T2 (REQM 8,87 contre 8,95) _(exécution `20261120T233440Z-replay-8359cd`, année réservée)_, sans test.
- **Les heures d'archivage.** Leur accord avec la colonne « Last Updated » des listes de l'opérateur a été vérifié un seul jour, en heure normale ; l'heure d'été n'a pas été vérifiée. Si l'opérateur reconstruisait une archive mensuelle corrigée en gardant les heures d'origine, une valeur corrigée entrerait sans être vue ; ce cas n'a pas été testé.
- **Aucune ligne de profit.** La formation de NYISO décrit les transactions virtuelles au niveau des zones, avec des exemples de zones internes ; aucun document lu ne montre de point d'offre virtuelle à une barre mandataire externe. Qui peut programmer une importation à `HQ_GEN_WHEEL`, et à quel coût des deux côtés, n'a pas été établi.
- **B0 est un plancher, pas une référence de pupitre.** Aucune donnée météo, de prix du gaz, d'indisponibilités ou de limites d'interface n'est admise ; les modèles sont statistiques, pas fondamentaux.
- **Valeurs corrigées.** L'archive contient les prix corrigés ; un fichier corrigé qui aurait gardé son heure d'origine ferait entrer une valeur corrigée. Le groupe de validation des prix de NYISO n'a déclaré aucune correction du prix du jour précédent de 2007 à septembre 2017, et 78 jours de marché avec corrections du temps réel de 2013 à septembre 2017 (NYISO, MIWG, 2017-11-02) ; les corrections après octobre 2017 ne sont pas connues.
- **Séparation procédurale.** L'année réservée était déjà passée quand ce travail a été fait ; sa séparation tient à une barrière sur le téléchargement, à l'étiquette et au registre. La connaissance générale qu'avaient les auteurs de l'hiver 2025-2026 ne peut pas être exclue. L'ordre des événements (plan, étiquette, rejeu) ne se vérifie que par l'historique de ce dépôt, dont les dates sont fixées par l'auteur ; aucun horodatage externe ne l'atteste.
- **Aucune validation indépendante.** Le modèle, les contrôles et ce rapport viennent d'agents d'IA travaillant pour un seul propriétaire ; les examens par d'autres modèles ne sont pas une validation indépendante. Une seule année réservée ; aucune revue périodique.

## Projet frère

[valiwatt](https://github.com/MrRolie/valiwatt) valide et surveille une prévision de la demande horaire d'électricité du Québec : le côté de la demande. Ce dépôt couvre le prix à la frontière new-yorkaise : le côté du marché.
