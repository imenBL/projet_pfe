You are a senior expert in data science, machine learning, time-series forecasting, financial modeling, and quantitative analysis, specialized in commodity price prediction.

I am not satisfied with the current results of the modeling phase and would like a rigorous end-to-end review of the entire pipeline.

Please critically assess all previous phases of the project and determine whether we made the right methodological decisions, especially regarding:

### 1. Data Cleaning & Preprocessing

- Review all cleaning decisions that were made.
- Identify any mistakes, risks of data leakage, poor imputation choices, incorrect temporal handling, or preprocessing weaknesses.
- Verify whether missing values, outliers, duplicates, inconsistent frequencies, scaling, and temporal alignment were handled correctly.
- Evaluate whether macroeconomic and financial variables were merged appropriately with gold price data.

### 2. Exploratory Data Analysis (EDA)

- Critically evaluate whether the EDA is sufficiently robust and useful for the modeling phase.
- Identify if needed missing analyses that should have been performed.
- Assess:
    - temporal patterns and trends
    - seasonality and structural breaks
    - stationarity analysis
    - autocorrelation and lag relationships
    - multicollinearity
    - feature correlation (linear and nonlinear)
    - feature importance signals
    - missing data patterns
    - regime changes and volatility shifts
    - distribution analysis and transformations


### 3. Feature Engineering

Evaluate whether the feature engineering strategy is appropriate for forecasting gold prices over medium horizons (T+30, T+60).

Please review:

- lag features
- rolling statistics
- momentum indicators
- volatility indicators
- macroeconomic transformations
- time-based features
- trend/seasonality decomposition features
- interaction features
- feature selection strategy
- risks of leakage

Suggest better feature engineering approaches if needed.

### 4. Forecasting Objective

The objective is to predict the future price of 24k gold in USD for:

- T+30 days (1 month)
- T+60 days (2 months)

### 5. Modeling Phase

I want a scientifically justified modeling strategy using multiple approaches.

Please evaluate and compare the suitability of:

#### Statistical Models

- ARIMA
- SARIMA
- SARIMAX

#### Machine Learning Models

- XGBoost
- LightGBM
- CatBoost
- Random Forest (if relevant)

#### Hybrid Approaches

- SARIMAX + ML residual modeling
- statistical + gradient boosting ensembles

For each model:

- explain whether it is suitable for this dataset size and forecasting horizon
- strengths and weaknesses
- assumptions
- expected risks (overfitting, instability, leakage, feature dependence)
- recommended hyperparameters
- tuning strategy

### 6. Hyperparameter Tuning

I want a robust hyperparameter optimization strategy using proper time-series validation.

Please recommend:

- TimeSeriesSplit / walk-forward validation
- Bayesian optimization vs Grid Search vs Optuna
- search spaces
- evaluation methodology
- overfitting prevention techniques

### 7. Explainability

I want model explainability using SHAP.

Please:

- recommend how to integrate SHAP properly
- explain which model(s) should use SHAP
- identify the most influential features
- explain how to interpret SHAP values for forecasting

### 8. Evaluation Strategy

Recommend a rigorous evaluation framework for forecasting performance.

Include:

- train/validation/test split strategy
- walk-forward backtesting
- metrics (MAE, RMSE, MAPE, SMAPE, directional accuracy, etc.)
- residual diagnostics
- prediction interval evaluation
- benchmark models (naive forecast, persistence model)

### 9. Final Recommendation

After reviewing everything, provide:

1. A critical review of what was done correctly and incorrectly.
2. Recommended changes to previous phases (EDA, cleaning, feature engineering).
3. A prioritized roadmap for the next modeling phase.
4. The best modeling architecture for this project given the dataset size and forecasting objective.

Be critical, rigorous, and scientifically justified. Challenge previous assumptions if necessary and propose better alternatives.