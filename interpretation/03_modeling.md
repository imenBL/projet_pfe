# Interprétation de la Phase 3 — Modélisation (`models/*.ipynb`)

> **Notebooks sources :** `models/01_preprocessing.ipynb` → `06_comparison.ipynb`
> **Phase CRISP-DM :** Phase 3 — *Modeling* + *Evaluation*
> **Périmètre Stage 1 :** USA · `gold_24k` · USD · cible **t+1** (rendement log reconstruit en prix)
> **Rôle de ce document :** lecture experte (Data Scientist) des sorties des notebooks de modélisation, en français, pour expliquer **pourquoi chaque modèle se comporte ainsi** et **comment choisir un modèle selon le comportement de la série**. Chiffres repris des notebooks exécutés ; tableau de référence : `reports/phase3-modeling/comparison_table.md`.

> **Suite (itération T+30) :** ce document décrit le run **t+1**, conservé tel quel comme **baseline marche-aléatoire**. Donnant suite au point 6 du TL;DR, le projet passe à l'horizon **T+30** (~1 mois) et `gold_reserves` est retiré du jeu de features (co-tendance). Voir `notebooks/01_eda_phase1_copieeee.ipynb` (EDA ré-itérée) et `project_plan.md` (bloc NOTES). Les chiffres ci-dessous ne sont **pas** réécrits.

---

## Synthèse exécutive (TL;DR)

1. **Au pas de temps journalier (h = 1), l'or se comporte comme une marche aléatoire.** L'ARIMA sélectionné par AIC est **(0,1,0)** — c'est-à-dire littéralement une marche aléatoire. Le meilleur modèle (LSTM) ne bat la marche aléatoire que de **+0,3 %** de skill : un écart **dans le bruit**.
2. **La bonne métrique est le *skill vs marche aléatoire*, pas le R².** Tous les modèles affichent un R² ≈ 0,99 sur le prix — un **artefact de la tendance** (le prix d'aujourd'hui explique déjà presque tout celui de demain). Le `skill_vs_RW` révèle la vérité : proche de 0 pour les meilleurs, **négatif** pour les autres.
3. **Plus un modèle a de capacité effective, plus il dégrade** sur cette série. Le classement est inverse de la complexité : arbre de décision très régularisé (profondeur 2) ≈ marche aléatoire ; LightGBM un peu moins bon ; XGBoost (200 arbres) et régression linéaire nettement moins bons ; **Prophet très en dessous**.
4. **La validation croisée a spontanément choisi les configurations les plus régularisées** (arbre profondeur 2, `min_samples_leaf=50`, 200 arbres peu profonds, `learning_rate=0,03`). C'est le signe d'une série **à très faible rapport signal/bruit** : le modèle optimal est celui qui « s'abstient » le plus (prédit ~le rendement moyen ≈ 0).
5. **Décalage de fréquence features ↔ cible.** Six des 14 features exogènes sont mensuelles/trimestrielles, forward-fillées → **quasi constantes au jour le jour**. Elles ne *peuvent pas* expliquer un rendement journalier. Le signal exploitable à h = 1 est donc structurellement faible.
6. **Leçon centrale pour la sélection de modèle :** sur une série fortement tendancielle + quasi-racine-unitaire + autocorrélation des rendements négligeable, **la baseline (marche aléatoire / ARIMA) est l'étalon à battre**, et la sophistication aide peu à un horizon court. La valeur viendra d'un **changement de cadrage** (horizon plus long, features de *variation*), pas d'un modèle plus complexe.

---

## Cadre d'évaluation commun (rappel)

Tous les modèles partagent, via `models/utils.py` :

- **Cible t+1 *return-based* :** prédire le log-rendement du lendemain `r_{t+1} = ln(y_{t+1}/y_t)`, puis reconstruire le prix `ŷ = y_t · e^{r̂}`. Justification : cible stationnaire (cf. notebook 01), pas de fuite (les features de la ligne `t` sont connues en fin de jour `t`), et on évite le piège d'extrapolation des arbres sur une fenêtre de test en plus-hauts historiques.
- **Découpage chronologique 70/15/15** (1 691 / 363 / 363), jamais mélangé. Fenêtre de test = **2024-12-31 → 2026-05-21** (le super-cycle haussier).
- **Métriques sur l'échelle prix ($/g)** : MAE, RMSE, MAPE, R² — plus deux métriques de *skill* : `skill_vs_RW = 1 − MSE_modèle/MSE_marche-aléatoire` et la précision directionnelle.

---

## Section 1 — Prétraitement & analyse (`01_preprocessing.ipynb`)

### Chiffres clés

| Élément | Valeur |
|---|---|
| Période / volume | 2017-02-13 → 2026-05-21 · **2 417 jours** |
| Prix (moy / σ / max) | 65,20 / 28,23 / **173,62** $/g (max non capé — décision Phase 2) |
| STL — part de variance | **trend ≈ 0,98** · seasonal ≈ 0,014 · resid ≈ 0,031 |
| ADF niveau `y` | stat +1,63 · **p = 0,998** → non-stationnaire |
| ADF `log(y)` | stat +1,36 · **p = 0,997** → non-stationnaire |
| ADF log-rendements | stat **−8,79** · **p < 0,0001** → **stationnaire** |
| Rendement journalier | moyenne +0,054 % · **σ ≈ 0,98 %/j** (≈ 1,49 %/j sur la fenêtre de test) |

### Interprétation experte

La série est **massivement tendancielle** : STL attribue ~98 % de la variance au `trend`, contre ~1,4 % à la saisonnalité. C'est l'archétype d'une série financière **quasi intégrée d'ordre 1** (racine unitaire). Les tests ADF le confirment sans ambiguïté : niveau et log-niveau non-stationnaires, **log-rendements stationnaires** → **d = 1**, cible = log-rendement.

**Conséquence directe sur la modélisation :** une série à racine unitaire signifie que *la meilleure prévision naïve de demain est aujourd'hui*. Tout modèle devra **battre cette marche aléatoire** — ce qui est notoirement difficile sur un actif liquide. La faible part de saisonnalité indique aussi que **SARIMA n'apportera rien** par rapport à ARIMA simple (décision confirmée en notebook 02).

---

## Section 2 — ARIMA (`02_arima.ipynb`)

### Chiffres clés

| Élément | Valeur |
|---|---|
| Ordre retenu (AIC) | **(0, 1, 0)** · AIC = −11 305,15 |
| Concurrents proches | (0,1,1) −11 303,47 · (1,1,0) −11 303,46 · (0,1,2) −11 303,07 |
| Test (MAE / RMSE / MAPE / R²) | 1,3554 / 2,1075 / 1,047 % / 0,9923 |
| `skill_vs_RW` / directionnel | **0,000** / 0,36 |

### Interprétation experte

L'AIC tranche pour **(0,1,0)** : aucun terme AR ni MA. Les ordres concurrents sont à **ΔAIC ≈ 1,7** (donc statistiquement équivalents) — l'AIC pénalisant la complexité, il choisit la solution **la plus parcimonieuse**, qui est *exactement* la marche aléatoire. C'est cohérent avec l'ACF/PACF du notebook 01 (peu/pas d'autocorrélation dans les rendements).

ARIMA(0,1,0) **égale donc la marche aléatoire par construction** : `skill_vs_RW = 0`. Sa précision directionnelle (~0,36) est faible précisément parce qu'il **ne s'engage sur aucune direction** (il prédit « pas de changement ») — il ne « gagne » donc jamais les jours où le marché bouge nettement.

> **Verdict.** ARIMA est ici la **baseline honnête** : il formalise le fait que la dynamique linéaire des rendements journaliers de l'or n'est pas exploitable. C'est l'étalon que les modèles ML/DL doivent dépasser.

---

## Section 3 — Modèles simples (`03_simple_model.ipynb`)

### Chiffres clés

| Modèle           | Hyperparamètres retenus (CV temporelle) | MAE    | RMSE   | `skill_vs_RW` |
| ---------------- | --------------------------------------- | ------ | ------ | ------------- |
| LinearRegression | (aucun — standardisation seule)         | 1,7158 | 2,4051 | **−0,30**     |
| DecisionTree     | `max_depth=2`, `min_samples_leaf=50`    | 1,3540 | 2,1089 | −0,001 (≈ RW) |

### Interprétation experte

Deux comportements opposés très instructifs :

- **La régression linéaire dégrade fortement (skill −0,30).** En combinant linéairement les 24 features — dont des variables de **co-tendance** (cf. EDA : `gdp`, `cpi`, `gold_reserves`) et des features de niveau non-stationnaires — elle ajuste des relations **fallacieuses** qui ne tiennent pas hors échantillon (la fenêtre de test est un régime de prix jamais vu). Résultat : un biais systématique.
- **L'arbre de décision retombe sur ≈ la marche aléatoire** parce que la validation croisée temporelle a choisi la configuration **la plus régularisée possible** (profondeur 2, feuilles ≥ 50 observations). Avec si peu de capacité, l'arbre prédit des **moyennes de rendement très grossières ≈ 0** → reconstruit ≈ `y_t`. Sa précision directionnelle (0,57) ne reflète pas une compétence de *timing* : il prédit un petit rendement positif constant (≈ la moyenne d'entraînement), ce qui « a raison » ~57 % du temps **uniquement parce que la période de test est haussière**.

> **Verdict.** Le contraste LinReg vs arbre illustre la règle d'or sur série quasi-efficiente : **la régularisation est reine**. Le modèle qui « s'abstient » (arbre minimal) ≈ marche aléatoire ; celui qui « surinterprète » (linéaire sur features de co-tendance) fait pire.

---

## Section 4 — Ensembles & Prophet (`04_modele_d_ensemble.ipynb`)

### Chiffres clés

| Modèle | Hyperparamètres retenus | MAE | RMSE | `skill_vs_RW` |
|---|---|---|---|---|
| XGBoost | `max_depth=2`, `n_estimators=200`, `lr=0,03`, `subsample=0,8` | 1,7727 | 2,4528 | **−0,35** |
| LightGBM | `num_leaves=15`, `n_estimators=200`, `lr=0,03`, `subsample=0,8` | 1,4872 | 2,1848 | −0,075 |
| Prophet | yearly only, 1-step walk-forward | 4,0509 | 5,9487 | **−6,97** |

### Interprétation experte

- **Le paradoxe du boosting.** XGBoost a pourtant été régularisé (profondeur 2, `lr=0,03`), mais **200 itérations de boosting** accumulent suffisamment de corrections pour **ajuster le bruit** du rendement → skill −0,35 (pire que l'arbre unique de profondeur 2 du notebook 03 !). LightGBM, avec `num_leaves=15` (plus régularisé que le défaut 31), reste plus proche de la marche aléatoire (−0,075). **Le classement OOS est inverse de la capacité effective** : arbre unique > LightGBM > XGBoost. C'est la signature d'une cible **sans signal apprenable** : chaque degré de liberté supplémentaire sert à mémoriser du bruit.
- **Prophet s'effondre (skill −6,97).** Même en *one-step*, son modèle additif tendance + saisonnalité impose une structure (lissage, pente) que la série quasi-efficiente ne respecte pas : à h = 1, cela introduit un **biais important** par rapport à « répéter la dernière valeur ». Prophet est conçu pour des **horizons moyens/longs** avec saisonnalités marquées — pas pour de la prévision journalière sur actif liquide.

> **Verdict.** Les ensembles ne créent pas de signal là où il n'y en a pas ; ils en fabriquent l'illusion sur l'entraînement et le paient sur le test. Prophet est ici un **mauvais outil pour le bon problème** (mauvais horizon).

---

## Section 5 — LSTM (`05_LSTM.ipynb`)

### Chiffres clés

| Élément | Valeur |
|---|---|
| Séquences (train/val/test) | 1 661 / 363 / 363 · fenêtre L = 30 |
| Arrêt anticipé | **époque 18** · meilleure val MSE 1,085 (échelle normalisée) |
| Test (MAE / RMSE / R²) | 1,3498 / **2,1047** / 0,9923 |
| `skill_vs_RW` / directionnel | **+0,0027** / 0,576 |

### Interprétation experte

Le LSTM univarié (sur la seule série de rendements passés) **arrête tôt** (époque 18) grâce à l'early-stopping sur la validation : il **ne sur-apprend pas** et **converge vers une prévision quasi constante** ≈ le rendement moyen. C'est ce qui lui donne le **plus petit RMSE** (2,1047, marginalement sous la marche aléatoire à 2,1075) et une précision directionnelle de 0,576 — encore une fois portée par le **biais haussier** de la période de test, pas par un vrai timing.

> **Verdict.** Le LSTM « gagne » en faisant **le moins de mal** : il dégrade gracieusement vers la marche aléatoire. Son avantage (+0,3 % de skill) est **statistiquement non significatif**. Un LSTM **multivarié** (les 24 features par pas de temps) est l'extension naturelle, mais sans changement d'horizon il est peu probable qu'il dépasse cette limite.

---

## Section 6 — Comparaison finale (`06_comparison.ipynb`)

| modèle | MAE | RMSE | MAPE % | R² | skill vs RW | dir. |
|--------|-----|------|--------|-----|-------------|------|
| **LSTM** | **1,3498** | **2,1047** | 1,0426 | 0,9923 | **+0,003** | 0,576 |
| ARIMA (0,1,0) | 1,3554 | 2,1075 | 1,0472 | 0,9923 | 0,000 | 0,364 |
| RandomWalk (réf.) | 1,3554 | 2,1075 | 1,0472 | 0,9923 | 0,000 | — |
| DecisionTree | 1,3540 | 2,1089 | 1,0455 | 0,9923 | −0,001 | 0,568 |
| LightGBM | 1,4872 | 2,1848 | 1,1478 | 0,9917 | −0,075 | 0,435 |
| LinearRegression | 1,7158 | 2,4051 | 1,2944 | 0,9900 | −0,302 | 0,457 |
| XGBoost | 1,7727 | 2,4528 | 1,3691 | 0,9896 | −0,355 | 0,435 |
| Prophet | 4,0509 | 5,9487 | 3,0677 | 0,9387 | −6,967 | 0,466 |

**Lecture :** le graphe `best_model_pred_vs_actual.png` montre le LSTM qui « colle » à la courbe réelle — mais c'est trompeur : à h = 1, coller au réel ≡ recopier la veille. Le tableau, lui, ordonne les modèles par **proximité à la marche aléatoire**. Le R² (0,94–0,99) ne discrimine quasiment pas ; **`skill_vs_RW` est la seule colonne qui parle**.

> **Modèle retenu (cette itération) : LSTM**, par plus petit RMSE — avec la réserve explicite qu'il est **à égalité avec la marche aléatoire**. ARIMA(0,1,0) reste la baseline de référence.

---

## Section 7 — Pourquoi la marche aléatoire domine (synthèse)

Quatre causes convergentes, toutes diagnostiquables **avant** de modéliser :

1. **Efficience de marché (forme faible).** Sur un actif liquide, les rendements journaliers sont quasi imprévisibles à partir du passé. ADF/ACF du notebook 01 l'annonçaient (rendements stationnaires, autocorrélation négligeable).
2. **Plancher de bruit = volatilité.** L'erreur 1-pas (MAE ≈ 1,35 $/g ≈ 1,2 %) est de l'ordre de la **volatilité journalière** (~1–1,5 %). Aucun modèle ne descend sous ce plancher : la part imprévisible domine.
3. **Décalage de fréquence features ↔ cible.** Macro mensuelle/trimestrielle forward-fillée ⇒ features **constantes intra-mois** ⇒ aucun pouvoir explicatif sur un rendement *journalier*.
4. **Capacité vs régularisation.** Le rapport signal/bruit étant minuscule, toute capacité supplémentaire sert à ajuster du bruit ⇒ **plus de complexité = pire OOS** (XGBoost < LightGBM < arbre minimal ≈ RW).

---

## Section 8 — Guide : choisir le modèle selon le comportement de la série

C'est le livrable demandé pour la phase d'interprétation. La **démarche** : diagnostiquer la série (notebook 01) **avant** de choisir un modèle.

| Comportement diagnostiqué | Diagnostic (outil) | Modèle approprié | Pourquoi |
|---|---|---|---|
| **Tendance forte + racine unitaire + rendements ~ bruit blanc**, horizon court (notre cas) | ADF (niveau non-stat / Δ stat), ACF≈0, STL trend≫saisonnier | **Marche aléatoire / ARIMA(0,1,0)** comme référence ; modèles complexes peu utiles | Rien d'apprenable à h=1 ; la parcimonie l'emporte |
| **Autocorrélation marquée** des rendements (AR/MA) | ACF/PACF significatifs | **ARIMA(p,d,q)** | Capte la mémoire linéaire |
| **Saisonnalité forte** (hebdo/annuelle) | STL part saisonnière élevée ; pics ACF saisonniers | **SARIMA / Prophet** | Modélisent explicitement la périodicité ; Prophet brille à horizon moyen/long |
| **Interactions non-linéaires** entre exogènes, SNR suffisant, **fréquence des features = celle de la cible** | écart Pearson≪Spearman ; importance hors-tendance | **XGBoost / LightGBM** | Capturent les seuils/interactions ; nécessitent un vrai signal |
| **Dépendances temporelles longues**, beaucoup de données, features multivariées | mémoire longue, motifs séquentiels | **LSTM / RNN / TFT** | Apprennent des dynamiques séquentielles ; gourmands en données |

**Règles transversales (leçons de cette phase) :**

- **Choisir la métrique avant le modèle.** Sur série tendancielle, le R²/RMSE en niveau est **saturé** ⇒ juger au `skill_vs_RW`, à la précision directionnelle et au R² *des rendements*.
- **Toujours inclure la marche aléatoire** comme référence : si on ne la bat pas, le modèle complexe ne se justifie pas.
- **Aligner la fréquence des features sur l'horizon de la cible** (sinon les features « lentes » sont du bruit constant).
- **Sous faible SNR, privilégier la régularisation** (modèles peu profonds, peu d'itérations, early-stopping) : ils dégradent proprement vers la baseline plutôt que de sur-apprendre.
- **La précision directionnelle > 0,5 n'est pas une preuve de skill** si elle vient d'un biais de tendance (prédire « hausse » dans un marché haussier).

---

## Section 9 — Limites & recommandations pour la suite

1. **Changer d'horizon** (t+5 / t+21 / mensuel) : c'est le levier le plus prometteur — les features macro/géo « lentes » y reprennent du sens, et la prévisibilité augmente structurellement.
2. **Features de *variation* plutôt que de niveau** pour le journalier : Δfed_rate, surprise CPI, rendement journalier du DXY/VIX, plutôt que les niveaux forward-fillés.
3. **LSTM multivarié** (24 features/pas) et, si souhaité, **TFT** (toujours différé) — mais avec des attentes réalistes à h = 1.
4. **Évaluation économique** : à h = 1, un backtest avec coûts de transaction ou des **intervalles de prédiction** (ARIMA les fournit nativement, conformal pour les arbres) sont plus parlants qu'un point quasi égal à la veille.
5. **SHAP** (réalisé dans l'itération `.py` antérieure) reste pertinent dès que des arbres porteront un vrai signal (horizon plus long) — top features alors : `dxy`, moyennes mobiles, `fed_rate`.

---

## Artefacts référencés

- Notebooks exécutés : `models/01_preprocessing` … `06_comparison.ipynb` (sorties inline).
- Tableau de comparaison : `reports/phase3-modeling/comparison_table.{md,csv}`.
- Graphe meilleur modèle : `reports/phase3-modeling/best_model_pred_vs_actual.png`.
- Prédictions alignées par modèle : `models/predictions/*.csv` (363 jours de test communs).
- Synthèse : `reports/phase3-modeling/SUMMARY.md`.

---

*Document d'interprétation — Phase 3 (Modélisation) du projet PFE. Rédigé en français pour la cohérence avec `interpretation/01_eda_phase1.md`.*
