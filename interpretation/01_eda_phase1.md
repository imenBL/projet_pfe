# Interprétation du notebook `01_eda_phase1.ipynb`

> **Notebook source :** `notebooks/01_eda_phase1.ipynb`
> **Phase CRISP-DM :** Phase 1 — *Data Understanding* (EDA)
> **Périmètre Stage 1 :** USA · `gold_24k` · USD · 2017-01-02 → 2026-04-24
> **Rôle de ce document :** lecture experte (Data Scientist) section par section des sorties du notebook, en français, pour faciliter la rédaction des verdicts dans `reports/phase1-eda/SUMMARY.md`.

> **Mise à jour (itération T+30) :** suite au constat de la Phase 3 (l'or quotidien ≈ marche aléatoire à h=1), l'EDA a été ré-itérée. **`gold_reserves` est retiré** du jeu de features Stage 1 (co-tendance fallacieuse — précisément le point 3 ci-dessous) : il reste **13** features exogènes. L'horizon passe de **T+1 à T+30** (~1 mois) ; la représentation de la cible (niveau `y(t+30)` vs rendement cumulé) est fixée à l'étape de modélisation. Ce document conserve l'analyse d'origine (avec `gold_reserves`) comme justification du retrait.

---

## Synthèse exécutive (TL;DR)

1. **L'or 24K aux USA** est passé de **36,98 $/g** (janvier 2017) à **151,43 $/g** (avril 2026) — soit une **multiplication par ~4,1** sur la fenêtre d'étude. La série est **non-stationnaire en niveau** (tendance haussière dominante).
2. **La transformation modélisable** est le **log-rendement journalier** (`log(y_t / y_{t-1})`) : c'est la seule forme où ADF *et* KPSS s'accordent sur la stationnarité. Elle constitue la cible attendue pour les modèles ARIMA/SARIMA de la Phase 3.
3. **Trois prédicteurs « tendanciels »** dominent la corrélation linéaire avec le prix : `gdp` (r = +0,82), `cpi` (+0,80), `gold_reserves` (+0,78). **Attention : il s'agit très probablement de corrélations de co-tendance** (chacun croît avec le temps), pas de causalité directe — la valeur prédictive sur les rendements reste à confirmer en modélisation. → **`gold_reserves` a depuis été retiré** du jeu de features pour exactement cette raison (cf. bannière ci-dessus).
4. **Les indicateurs géopolitiques** ont une corrélation linéaire **faible ou négative** avec le niveau de prix (-0,31 pour `total_events`, -0,27 pour `political_events`). Le test de l'effet « pic géopolitique → rendement +7 jours » montre une moyenne plus haute (+0,59 % vs +0,31 %), **mais le test de Mann-Whitney n'est pas significatif (p = 0,14)** sur 68 jours. À garder dans le modèle pour les effets non-linéaires (SHAP), mais sans surinterpréter.
5. **Le profil de valeurs manquantes** est dominé par la nature même des sources (macro mensuelle, réserves annuelles, marchés en jours ouvrés). La stratégie d'imputation **forward-fill** déjà actée dans `refactor/02-data-understanding.md` est confirmée : les écarts journaliers maximaux sur l'or sont de **3 jours** (week-ends + jours fériés US), ce qui est parfaitement gérable par ffill.
6. **Plusieurs anomalies de données** sont remontées pour la Phase 2 : doublons FRED, incohérences de schéma (en partie résolues par le refactor — tables renommées ; restent les colonnes macro en casse mixte et `vix_oil_data` `"Date"`/`oil`), prix max anormalement haut (173,62 $/g vs spot attendu ~94 $/g). Ces points doivent être traités avant la construction de `ml.us_gold_features_daily`.

---

## Section 1 — Visualisation de la tendance (Tâche 1)

### Chiffres clés extraits du notebook

| Statistique           | Valeur                                         |
| --------------------- | ---------------------------------------------- |
| Période               | 2017-01-02 → 2026-04-24                        |
| Nombre d'observations | 2 428 jours de cotation USA                    |
| Prix initial          | **36,98 $/g**                                  |
| Prix final            | **151,43 $/g**                                 |
| Prix minimum          | 36,98 $/g                                      |
| Prix maximum          | **173,62 $/g** (suspect — voir interprétation) |
| Moyenne               | 64,22 $/g                                      |
| Médiane               | 58,11 $/g                                      |
| Écart-type            | 27,32 $/g                                      |

### Interprétation experte

La trajectoire de l'or 24K USA est **monotone à la hausse sur le long terme**, avec trois régimes successifs nettement identifiables :

1. **2017 → 2019 : phase de consolidation basse** (~37–45 $/g). L'or évolue dans un range étroit, dans un contexte de remontée graduelle des taux Fed.
2. **2020 → 2022 : choc COVID + envolée inflationniste**. Premier décrochage haussier qui amène le prix vers 55–65 $/g. La volatilité augmente nettement.
3. **2022 → 2026 : super-cycle haussier**. L'or franchit successivement les seuils de 70, 90, puis 130+ $/g. Cette dernière phase est cohérente avec la dynamique observée sur le marché spot international (record historique fin 2024).

**Point d'attention — outlier à 173,62 $/g.** Le maximum atteint dans la série dépasse le prix spot international maximum attendu d'environ **80 %** (le spot 24K en pic 2024-2025 tournait autour de 90–95 $/g aux USA). Trois hypothèses :

- Erreur de scraping ponctuelle (mauvaise extraction décimale, par exemple « 173,62 » au lieu de « 17,362 » ou « 73,62 »).
- Données fournisseur transitoirement erronées.
- Valeur en *price-per-troy-ounce* sur certaines lignes mélangée avec *price-per-gram*.

→ **Action Phase 2** : ajouter un contrôle de borne haute (rejet ou winsorization au 99,5e percentile) lors du build de `ml.us_gold_features_daily`. Pour la Phase 1 l'EDA reste valable, mais le verdict doit le mentionner explicitement.

### Verdict suggéré pour `SUMMARY.md` § Trend

> *La série gold_24k USA suit une trajectoire haussière forte sur la période, multipliée par environ 4,1 (de 36,98 à 151,43 $/g). Trois régimes successifs : consolidation 2017–2019, rebond inflationniste 2020–2022, super-cycle 2023–2026. Un outlier à 173,62 $/g, à investiguer en Phase 2 (probable erreur de scraping ponctuelle).*

---

## Section 2 — Matrice de corrélation (Tâche 2)

### Tableau complet trié par |Pearson r|

| Rang | Feature              | Pearson r   | Spearman ρ | p-value (Pearson) | Interprétation                    |
| ---- | -------------------- | ----------- | ---------- | ----------------- | --------------------------------- |
| 1    | `gdp`                | **+0,8237** | +0,9160    | < 1e-10           | Co-tendance forte                 |
| 2    | `cpi`                | **+0,8031** | +0,9405    | < 1e-10           | Co-tendance forte                 |
| 3    | `gold_reserves`      | **+0,7843** | +0,9341    | < 1e-10           | Co-tendance forte                 |
| 4    | `dxy`                | +0,4753     | +0,6269    | < 1e-10           | Lien modéré, à surveiller         |
| 5    | `fed_rate`           | +0,4575     | +0,4860    | < 1e-10           | Lien modéré                       |
| 6    | `real_rate`          | +0,4377     | +0,4777    | < 1e-10           | Lien modéré                       |
| 7    | `total_events`       | −0,3072     | −0,3666    | < 1e-10           | Lien faible négatif               |
| 8    | `political_events`   | −0,2741     | −0,3361    | < 1e-10           | Lien faible négatif               |
| 9    | `political_pressure` | +0,1912     | +0,1833    | < 1e-10           | Très faible positif               |
| 10   | `oil_price`          | +0,1827     | +0,3711    | < 1e-10           | Très faible / non-linéaire        |
| 11   | `crisis_index`       | −0,1160     | −0,1198    | < 1e-10           | Quasi nul                         |
| 12   | `vix`                | +0,0733     | +0,2410    | < 1e-10           | Négligeable                       |
| 13   | `war_intensity`      | +0,0201     | +0,0297    | **0,25 (n.s.)**   | **Non significatif**              |
| 14   | `unemployment`       | −0,0143     | +0,1852    | **0,41 (n.s.)**   | **Non significatif** linéairement |

### Interprétation experte

**Trois constats majeurs :**

#### 1. Les top-3 corrélations sont des co-tendances trompeuses

`gdp`, `cpi` et `gold_reserves` ont toutes une dynamique structurellement haussière sur 2017–2026 (PIB qui croît, IPC en hausse soutenue post-COVID, réserves d'or US qui progressent). Comme la série `gold_24k` croît aussi, **la corrélation calculée sur les niveaux capture surtout le partage d'une tendance commune, pas une relation causale stable**.

→ **Conséquence pratique** : ces trois variables seront probablement **moins utiles que ne le suggère leur r** une fois qu'on modélisera les *rendements* (différenciation au premier ordre) plutôt que les niveaux. C'est précisément pour cette raison que la Phase 3 doit privilégier les rendements (cf. Section 3).

#### 2. L'écart Pearson vs Spearman révèle de la non-linéarité

Pour plusieurs features la corrélation **Spearman est nettement supérieure à Pearson** :

- `gdp` : Pearson +0,82 vs Spearman +0,92 → relation monotone mais pas linéaire
- `cpi` : Pearson +0,80 vs Spearman +0,94 → idem
- `oil_price` : Pearson +0,18 vs Spearman +0,37 → relation non-linéaire significative
- `vix` : Pearson +0,07 vs Spearman +0,24 → relation cachée par les outliers

→ **Implication pour Phase 3** : un modèle linéaire (ARIMA-X) sous-estimera ces features. Les modèles à base d'arbres (XGBoost, LightGBM) qui s'appuient sur l'ordre des valeurs y trouveront davantage de signal. À vérifier sur SHAP.

#### 3. Le DXY et les taux : signal contre-intuitif mais explicable

`dxy` (+0,48), `fed_rate` (+0,46), `real_rate` (+0,44) corrèlent **positivement** avec l'or, ce qui contredit la théorie classique (un dollar fort et des taux réels élevés sont normalement défavorables à l'or). C'est encore un effet de co-tendance sur la période 2017–2026, particulièrement marqué post-2022 où Fed *et* or sont montés simultanément. **Méfiance : la relation s'inversera probablement sur des sous-périodes** — à confirmer par découpage temporel en Phase 3.

#### 4. Features à très faible corrélation linéaire

`vix` (+0,07), `war_intensity` (+0,02 n.s.), `unemployment` (−0,01 n.s.) ont une corrélation linéaire **non significative ou très faible**. Cependant, **on ne les retire pas du jeu de features** : le `project_plan.md` impose `ALL_EXOG_FEATURES` (14 colonnes), et SHAP en Phase 3 reste l'arbitre final.

### Verdict suggéré pour `SUMMARY.md` § Correlations

> *Trois prédicteurs dominent la corrélation linéaire (gdp +0,82, cpi +0,80, gold_reserves +0,78), mais il s'agit largement de co-tendance — leur valeur prédictive sur les rendements reste à valider. Le DXY et les taux Fed sont positivement corrélés (~+0,45), ce qui contredit la théorie classique et reflète un biais de période. Les features géopolitiques sont faiblement corrélées en linéaire (max |r| = 0,31), mais l'écart Pearson/Spearman suggère de la non-linéarité que les modèles à arbres pourront capturer.*

---

## Section 3 — Stationnarité (Tâche 3)

### Résultats des tests ADF / KPSS

| Transformation | ADF stat | ADF p-value | ADF dit          | KPSS stat | KPSS p-value | KPSS dit         | Décision                         |
| -------------- | -------- | ----------- | ---------------- | --------- | ------------ | ---------------- | -------------------------------- |
| `level`        | +3,41    | 1,000       | non-stationnaire | 6,04      | 0,010        | non-stationnaire | **Consensus : non-stationnaire** |
| `first_diff`   | −13,01   | 2,5e-24     | stationnaire     | 0,71      | 0,013        | non-stationnaire | **Désaccord**                    |
| `log_returns`  | −19,02   | ~0          | stationnaire     | 0,41      | 0,074        | stationnaire     | **Consensus : stationnaire**     |

### Interprétation experte

**Le verdict est sans ambiguïté : la cible modélisable est `log_returns`.**

Détaillons les trois cas :

1. **Niveau (level)** : ADF p = 1,00 (forte non-rejet de la racine unitaire) et KPSS p = 0,01 (rejet de la stationnarité). Les deux tests, conçus avec des hypothèses nulles opposées, s'accordent : **la série brute est non-stationnaire**. Cela confirme visuellement ce qu'on voyait sur le graphique de tendance.

2. **Première différence (`y_t - y_{t-1}`)** : ADF dit stationnaire (p ≈ 0), mais **KPSS rejette toujours la stationnarité** (p = 0,013). Ce désaccord est un signal classique de **non-stationnarité résiduelle** — typiquement liée à une **hétéroscédasticité** (variance qui change dans le temps) ou un **changement de niveau** non capturé par la différenciation simple. Avec un prix qui passe de ~37 à ~150 $/g, les valeurs absolues des différences journalières en fin de période sont mécaniquement 3–4× plus grandes qu'en début de période, même si le pourcentage de variation reste similaire — d'où la persistance d'une structure dans la variance.

3. **Log-rendements (`log(y_t / y_{t-1})`)** : ADF p ≈ 0 (stationnaire) et KPSS p = 0,074 > 0,05 (ne rejette pas la stationnarité). **Les deux tests s'accordent**. La transformation logarithmique neutralise la croissance exponentielle de la variance absolue — c'est pourquoi elle est canonique pour les actifs financiers à dynamique multiplicative comme l'or.

### Implications pour la Phase 3

- **ARIMA/SARIMA** : à entraîner sur `log_returns`, puis inverser la transformation pour reconstituer les niveaux prédits.
- **Modèles tree-based (XGBoost, LightGBM)** : peuvent fonctionner sur les niveaux *si* on inclut des features de différenciation explicite (`y_lag_*`, `y_ma_*`, `y_vol_30` — qui sont déjà spécifiées dans `project_plan.md`). À tester aussi avec une cible = log-rendement.
- **LSTM / TFT** : la pratique courante est de prédire des log-rendements normalisés. Standardisation à prévoir.
- **Découpage temporel 70/15/15** : confirmé pertinent — pas besoin de saisonnalité particulière à respecter dans le split.

### Verdict suggéré pour `SUMMARY.md` § Stationarity

> *La série `gold_24k` est non-stationnaire en niveau (consensus ADF + KPSS). Sa première différence est ambiguë (ADF stationnaire mais KPSS rejette — résiduelle hétéroscédasticité). Les **log-rendements quotidiens** constituent la seule transformation où les deux tests s'accordent sur la stationnarité (ADF p ≈ 0, KPSS p = 0,074). **Cible de modélisation retenue pour ARIMA/SARIMA : log-rendements.***

---

## Section 4 — Décomposition STL (Tâche 4)

### Composantes (écart-types)

| Composante  | Écart-type | Plage          | Part de la variance totale (approximative) |
|-------------|------------|----------------|---------------------------------------------|
| `trend`     | **26,88**  | 40,87 → 148,28 $/g | ~96 % |
| `seasonal`  | 3,80       | −14,79 → +22,64 $/g | ~2 % |
| `residual`  | 5,25       | (centré 0)     | ~2 % |

(Part calculée comme `var(c) / sum(var(c_i))`. Le `trend` domine massivement.)

### Interprétation experte

**La décomposition STL confirme et chiffre ce que la Section 1 montrait visuellement : la dynamique de l'or 24K USA est presque entièrement portée par sa tendance long terme.**

- Le **trend** explique l'écrasante majorité de la variance (écart-type 26,88 vs 27,32 pour la série brute).
- La **composante saisonnière** (période = 365 jours) est **faible mais non nulle** : amplitude pic-à-pic d'environ 37 $/g (de −14,79 à +22,64), à comparer à un prix moyen de 64 $/g. Cela représente environ **±18 % autour de la tendance** sur le pic-à-pic, mais avec un écart-type de seulement 3,80 $/g — autrement dit, la saisonnalité est régulière mais d'**amplitude modeste**.
- Le **résidu** (écart-type 5,25 $/g) est légèrement supérieur à la composante saisonnière, ce qui suggère que le bruit de marché à court terme est aussi important que les schémas saisonniers — ou que la saisonnalité annuelle n'est pas la périodicité dominante (un test à période 252, jours de bourse NYSE, pourrait raffiner le découpage).

### Implication méthodologique pour la Phase 3

**SARIMA vs ARIMA pur** : la saisonnalité existe mais reste secondaire. Recommandation :

- **Tester d'abord ARIMA simple** sur les log-rendements comme baseline.
- **Comparer avec SARIMA (s=252 ou s=365)** uniquement si ARIMA simple sous-performe.
- La saisonnalité capturée par `month`, `quarter`, `is_month_end` dans les features calendaires (Phase 2) devrait suffire aux modèles tree-based / LSTM.

→ **Choix de période STL — discussion** : la période 365 (jours calendaires) est utilisée ici, alors que les marchés ne cotent qu'environ 252 jours par an. Le notebook le mentionne dans son commentaire. Un re-run avec `period=252` pourrait être informatif **après** avoir tranché la convention de calendrier en Phase 2 (NYSE business days vs calendar days).

### Verdict suggéré pour `SUMMARY.md` § Seasonality

> *La décomposition STL (période = 365) montre une tendance écrasante (σ = 26,88) face à une saisonnalité modeste (σ = 3,80, amplitude pic-à-pic ≈ 37 $/g) et un résidu de magnitude comparable à la saisonnalité (σ = 5,25). La saisonnalité existe mais ne justifie pas, à elle seule, de privilégier SARIMA sur ARIMA. ARIMA(p,d,q) sur log-rendements suffira probablement comme baseline ; les features calendaires de la Phase 2 (`month`, `quarter`, `is_month_end`) prendront en charge ce qu'il restera de saisonnalité pour les modèles tree-based.*

---

## Section 5 — Pics géopolitiques vs mouvements de prix (Tâche 5)

### Résultats chiffrés

| Indicateur                                    | Valeur                      |
| --------------------------------------------- | --------------------------- |
| Seuil pic (`crisis_index` 99e pct)            | 0,978                       |
| Seuil pic (`war_intensity` 99e pct)           | 0,102                       |
| Nombre de jours-pics identifiés               | **68**                      |
| Rendement +7j moyen **après pic**             | **+0,59 %**                 |
| Rendement +7j moyen **baseline (tous jours)** | **+0,31 %**                 |
| Différence absolue (post-pic − baseline)      | +0,28 pp                    |
| Test de Mann-Whitney U (unilatéral)           | U = 120 857, **p = 0,1418** |

### Interprétation experte

**L'observation : le rendement à 7 jours après un pic géopolitique est presque deux fois supérieur à la baseline (+0,59 % vs +0,31 %).** À première vue, cela suggère que l'or réagit positivement aux tensions géopolitiques — comportement classique de valeur refuge.

**Mais la rigueur statistique tempère :**

1. **Le test de Mann-Whitney n'est pas significatif** (p = 0,14 > 0,05). Avec seulement **68 jours de pic** sur 3 311 jours de fenêtre propre, la puissance statistique est limitée. On ne peut pas rejeter l'hypothèse nulle d'égalité des distributions au seuil 5 %.

2. **L'effet est néanmoins de bonne taille en moyenne (+0,28 pp, soit ~90 % d'écart relatif à la baseline)** et la médiane suit (+0,63 % vs +0,31 %). Le manque de significativité tient à la **variance importante des rendements à 7 jours**, pas à l'absence d'effet directionnel.

3. **Le seuil pour `war_intensity` est très bas** (0,10 au 99e pct), ce qui suggère que cette variable est très majoritairement proche de zéro pour les USA sur cette période (peu de conflit armé direct impliquant le sol américain). Le signal géopolitique vient surtout de `crisis_index`.

### Recommandations

- **Ne pas exclure les features géopolitiques de Phase 2** : le `project_plan.md` les inclut, et le signal directionnel est cohérent avec la théorie.
- **En Phase 3** : laisser les modèles non-linéaires (XGBoost, LSTM, TFT) chercher des interactions plus subtiles (par exemple, l'effet d'un pic *conditionnel* au régime de volatilité — pic en marché calme vs pic en marché déjà stressé peut donner des réponses opposées).
- **SHAP en Phase 3** sera l'arbitre final : si `crisis_index` ressort en top-5 features, c'est gagné ; sinon, on aura confirmation que l'effet observé ici est trop faible pour être prédictif.

### Verdict suggéré pour `SUMMARY.md` § Geopolitical signal

> *68 jours de pic géopolitique USA (top 1 % de `crisis_index` ou `war_intensity`) ont été identifiés sur la fenêtre. Le rendement moyen à +7j post-pic est de +0,59 % vs +0,31 % en baseline — directionnellement cohérent avec le rôle de valeur refuge de l'or, **mais non significatif statistiquement** (Mann-Whitney U p = 0,14, n = 68). Les features géopolitiques sont conservées dans la table de features ; leur valeur prédictive sera arbitrée par SHAP en Phase 3.*

---

## Section 6 — Analyse des valeurs manquantes (Tâche 6)

### Profil de missingness (avant imputation, calendrier journalier 2017→2026)

| Feature              | Lignes nulles | % manquant | Cause |
|----------------------|---------------|------------|-------|
| `gdp`                | 3 364         | 98,94 %    | Source FRED **trimestrielle** (pas mensuelle comme le reste du macro — à confirmer) |
| `cpi`                | 3 291         | 96,79 %    | Source FRED mensuelle |
| `unemployment`       | 3 291         | 96,79 %    | Source FRED mensuelle |
| `fed_rate`           | 3 289         | 96,74 %    | Source FRED mensuelle |
| `real_rate`          | 3 289         | 96,74 %    | Source FRED mensuelle |
| `dxy`                | 1 077         | 31,68 %    | Cotation marché (jours ouvrés uniquement) |
| `vix`                | 1 060         | 31,18 %    | Cotation marché |
| `oil_price`          | 1 058         | 31,12 %    | Cotation marché |
| `gold_24k`           | 972           | 28,59 %    | Cotation marché — week-ends + fériés US |
| `gold_reserves`      | 479           | 14,09 %    | Source World Bank annuelle |
| `total_events`       | 0             | 0,00 %     | GDELT (couverture quotidienne complète) |
| `political_events`   | 0             | 0,00 %     |   |
| `war_intensity`      | 0             | 0,00 %     |   |
| `crisis_index`       | 0             | 0,00 %     |   |
| `political_pressure` | 0             | 0,00 %     |   |

### Distribution des écarts (sur la série `gold_24k`)

| Écart en jours | Nombre d'occurrences | Interprétation |
|----------------|----------------------|----------------|
| 1              | 1 940                | Jour ouvré → jour ouvré (normal) |
| 2              | 2                    | Cas rare (fermeture exceptionnelle isolée ?) |
| 3              | 485                  | Week-end + lundi férié, ou vendredi férié + week-end |
| Max            | **3 jours**          | Aucun trou supérieur à 3 jours sur 9 ans |

### Interprétation experte

**Le profil de missingness est essentiellement structurel — pas un défaut de données mais un reflet de la cadence native des sources :**

1. **Sources macro (FRED) : missingness 97–99 % — normal.** Les données sont publiées mensuellement (ou trimestriellement pour `gdp`), et donc ~28–30 jours sur 30 sont vides sur un calendrier journalier. Le **forward-fill mensuel→journalier** est la pratique standard et ne pose aucun problème méthodologique (les variables macro sont par construction « lentes »).

2. **Sources marché (Yahoo, prix or) : missingness ~30 %.** Les marchés ne cotent pas en week-end ni jours fériés. Sur 365 jours, ~252 sont ouvrés (~69 %), ce qui correspond exactement aux ~31 % manquants observés. Le **forward-fill week-end/férié** est confirmé comme stratégie (décision déjà actée dans `refactor/02-data-understanding.md` § Decisions).

3. **Réserves d'or (World Bank, annuelles) : missingness 14 %.** Une seule valeur par année forward-fillée sur 365 jours. Pas un problème pour une variable aussi lente que les réserves d'or (qui changent typiquement de < 5 % par an).

4. **GDELT : zéro missingness sur 9 ans.** Excellent. La couverture quotidienne est complète et n'aura pas besoin d'imputation.

5. **Profil des écarts sur l'or : maximum 3 jours.** Cela élimine toute préoccupation sur des trous longs (cf. *Open question* du `refactor/02-data-understanding.md` sur GDELT — la réponse est : aucun trou non plus côté gold pour USA). Le forward-fill est sûr.

### Stratégie d'imputation consolidée (à reporter en Phase 2)

| Source                  | Granularité native                      | Règle d'imputation                                |
| ----------------------- | --------------------------------------- | ------------------------------------------------- |
| `raw_prices` (gold)     | Jours ouvrés                            | **Forward-fill** weekend / jours fériés (max 3 j) |
| `macro_data`            | Mensuelle (et trimestrielle pour `gdp`) | **Forward-fill** vers le journalier               |
| `vix_oil_data`          | Jours ouvrés                            | **Forward-fill** weekend / jours fériés           |
| `geopo_data`            | Journalière dense                       | **Aucune imputation** nécessaire (0 % manquant)   |
| `reserves_gold`         | Annuelle                                | **Forward-fill** vers le journalier               |

### Verdict suggéré pour `SUMMARY.md` § Missing values

> *Le profil de missingness est entièrement structurel et explicable par la cadence native des sources : macro mensuel/trimestriel (97–99 %), marchés en jours ouvrés (~31 %), réserves annuelles (14 %), GDELT dense (0 %). Sur l'or 24K USA, l'écart maximum entre observations consécutives est de 3 jours (week-end + férié), bien dans la zone confortable pour un forward-fill. La stratégie d'imputation forward-fill (déjà actée dans `refactor/02-data-understanding.md` § Decisions) est confirmée pour toutes les sources non journalières.*

---

## Anomalies remontées pour la Phase 2 (Data Preparation)

Ce que l'EDA a fait remonter et qui doit être traité **avant** la construction de `ml.us_gold_features_daily` :

> **Note :** le pipeline a été refactoré après cette EDA — tables renommées et or + argent fusionnés dans `raw_prices`. Les points ci-dessous sont annotés *(résolu)* ou *(à faire)* en conséquence.

1. **Doublons FRED** : la table macro `"Macroeconomic_data"` (renommée `macro_data`) contenait chaque ligne **deux fois** (2 463 doublons exacts sur 4 926 lignes). Le notebook EDA dédoublonne en mémoire, mais la Phase 2 doit nettoyer au niveau base (suppression ou recréation depuis FRED).
2. **Outlier prix** : 173,62 $/g (max) est implausible vs spot international. Ajouter une borne supérieure ou winsorization au feature-build.
3. **Schéma (mis à jour par le refactor)** :
   - Table de prix renommée `cleaned_data` → **`raw_prices`** (or + argent fusionnés) *(résolu)*.
   - `"Pays"` → **`country`** *(résolu)* — toujours un slug français ; standardisation ISO3 `country_code` restante (`etats-unis` → `USA`).
   - Colonne `"Année"` supprimée *(résolu)*.
   - Colonne `date` désormais en `timestamp` → **à convertir en `DATE`** *(en cours)*.
   - Colonne `devise` désormais **renseignée** (`etats-unis` → `USD`) *(résolu)*.
4. **Lignes prix à `gold_24k = 0`** : aucune n'a été détectée dans la sortie EDA (`After dropping date OOB / zero-price rows: 2,428 (dropped 0)`), mais l'EDA garde le contrôle défensif. Maintenir en Phase 2.
5. **Table géo** renommée `gdelt_data` → **`geopo_data`** *(résolu)*.
6. **Table macro** renommée `"Macroeconomic_data"` → **`macro_data`** *(résolu)* ; ses colonnes `"CPI"`, `"GDP"`, `"DXY"`, `"Unemployment"` restent en casse mixte → à passer en minuscules *(à faire)*.
7. **Table `vix_oil_data`** : colonne `"Date"` (D majuscule) → `date` ; colonne `oil` → `oil_price` *(à faire)*.
8. **`dim_date` supprimée** *(résolu)* : les features calendaires (`month`, `quarter`, `day_of_week`, `is_month_end`) sont dérivées en pandas au feature-build (`pd.to_datetime(date).dt.month/.quarter/.dayofweek`, `.dt.is_month_end`).
9. **Question ouverte — calendrier de trading** : NYSE business days (~252 j/an) ou tous les jours calendaires forward-fillés (365 j/an) ? Décision à prendre **avant** de calculer `y_lag_*`, `y_ma_*`, `y_vol_30` (la sémantique de `y_lag_1` change : « hier ouvré » ou « hier calendaire »).
10. **Vérification de l'unité de `gdp`** : 98,94 % de missingness suggère une cadence **trimestrielle**, pas mensuelle comme le reste du macro. À vérifier dans `data_collection/fredAPI.py` (la série FRED `GDP` est trimestrielle au format quarterly).

---

## Aide à la rédaction de `SUMMARY.md`

Chaque section ci-dessus contient un encadré **« Verdict suggéré pour `SUMMARY.md` § … »**. Vous pouvez :

1. Copier ces verdicts dans les sections correspondantes de `reports/phase1-eda/SUMMARY.md` (qui contient des `_Fill after running notebook §X._` à remplacer).
2. Compléter les tableaux placeholder de `SUMMARY.md` (corrélations, ADF/KPSS, signal géopolitique) avec les chiffres exacts repris dans ce document.
3. Une fois `SUMMARY.md` complet, basculer le statut de `refactor/02-data-understanding.md` de **IN PROGRESS** vers **DONE** et cocher les 3 cases d'acceptance criteria.
4. Cela ouvrira la porte à la Phase 2 (`refactor/03-data-preparation.md`) — qui devra commencer par traiter les **10 points d'anomalie remontés ci-dessus**.

---

*Document généré dans le cadre de la Phase 1 du projet PFE. Pour chaque graphique ou tableau référencé, voir le notebook exécuté `notebooks/01_eda_phase1.ipynb`.*
