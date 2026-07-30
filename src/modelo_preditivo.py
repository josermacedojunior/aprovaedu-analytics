# -*- coding: utf-8 -*-
"""
Modelo preditivo (diferencial) - AprovaEdu Analytics
=======================================================
Regressao logistica simples para estimar a probabilidade de aprovacao no
vestibular a partir de sinais disponiveis durante o ano de preparacao
(presenca, nota de diagnostico, nota media em simulados, bolsa, perfil do
aluno). Nao e o foco do desafio (que pede analise descritiva), mas atende ao
item de diferencial "criacao de score, segmentacao ou modelo preditivo".

Rodar: python src/modelo_preditivo.py
"""
import os

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, confusion_matrix, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE_DIR, "data", "processed")


def load(name):
    return pd.read_csv(os.path.join(PROC, f"{name}.csv"), encoding="utf-8-sig")


def build_features():
    mart = load("mart_aluno_ano")
    matriculas = load("matriculas")
    estudantes = load("estudantes")
    resultados = load("resultados_simulados")

    # nota de diagnostico e bolsa media, por aluno-ano (media entre as matriculas daquele ano)
    matr_agg = (
        matriculas.groupby(["aluno_id", "ano"])
        .agg(nota_diagnostico_media=("nota_diagnostico", "mean"), bolsa_percentual_media=("bolsa_percentual", "mean"))
        .reset_index()
    )

    # nota media em simulados validos, por aluno-ano
    res_valid = resultados[resultados["nota_valida"]]
    res_agg = (
        res_valid.groupby(["aluno_id", "ano"])
        .agg(nota_simulados_media=("nota", "mean"), n_simulados=("resultado_id", "count"))
        .reset_index()
    )

    df = mart.merge(matr_agg, on=["aluno_id", "ano"], how="left")
    df = df.merge(res_agg, on=["aluno_id", "ano"], how="left")
    df = df.merge(estudantes[["aluno_id", "canal_captacao"]], on="aluno_id", how="left")

    return df


NUMERIC_FEATURES = ["taxa_presenca", "nota_diagnostico_media", "bolsa_percentual_media", "nota_simulados_media"]
CATEGORICAL_FEATURES = ["escola_origem", "canal_captacao", "cidade"]
TARGET = "aprovado"


def main():
    df = build_features()

    out = open(os.path.join(os.path.dirname(__file__), "modelo_out.txt"), "w", encoding="utf-8")
    def p(*a):
        print(*a, file=out)

    p("Linhas antes de remover nulos nas features numericas:", len(df))
    modelo_df = df.dropna(subset=NUMERIC_FEATURES + CATEGORICAL_FEATURES).copy()
    p("Linhas apos remover nulos:", len(modelo_df))
    p("Taxa de aprovacao na base do modelo:", modelo_df[TARGET].mean().round(4))

    X = modelo_df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = modelo_df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    preprocess = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])

    modelo = Pipeline([
        ("prep", preprocess),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])

    modelo.fit(X_train, y_train)

    proba_test = modelo.predict_proba(X_test)[:, 1]
    pred_test = modelo.predict(X_test)

    p("\n=== Avaliacao no conjunto de teste (25% dos dados, nunca vistos no treino) ===")
    p("Baseline (sempre prever a classe majoritaria 'nao aprovado'): acuracia =",
      round(1 - y_test.mean(), 4))
    p("Acuracia do modelo:", round(accuracy_score(y_test, pred_test), 4))
    p("AUC-ROC do modelo:", round(roc_auc_score(y_test, proba_test), 4))
    p("\nMatriz de confusao (linhas=real, colunas=previsto) [0=nao aprovado, 1=aprovado]:\n",
      confusion_matrix(y_test, pred_test))
    p("\nRelatorio de classificacao:\n", classification_report(y_test, pred_test, digits=3))

    # Importancia das features (coeficientes padronizados, features numericas)
    feat_names = (
        NUMERIC_FEATURES
        + list(modelo.named_steps["prep"].named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES))
    )
    coefs = modelo.named_steps["clf"].coef_[0]
    coef_df = pd.DataFrame({"feature": feat_names, "coeficiente": coefs}).sort_values(
        "coeficiente", ascending=False
    )
    p("\n=== Coeficientes do modelo (positivo = aumenta chance de aprovacao) ===")
    p(coef_df.to_string(index=False))

    # Cross-validation simples (5-fold) para estabilidade do AUC
    from sklearn.model_selection import cross_val_score
    cv_scores = cross_val_score(modelo, X, y, cv=5, scoring="roc_auc")
    p("\nAUC-ROC em 5-fold cross-validation:", np.round(cv_scores, 4).tolist())
    p("Media:", round(cv_scores.mean(), 4), "Desvio padrao:", round(cv_scores.std(), 4))

    out.close()

    modelo_df["proba_aprovacao"] = modelo.predict_proba(X)[:, 1]
    modelo_df[["aluno_id", "ano", "aprovado", "proba_aprovacao"]].to_csv(
        os.path.join(PROC, "scores_predicao_aprovacao.csv"), index=False, encoding="utf-8-sig"
    )
    print("Modelo treinado. Detalhes em src/modelo_out.txt")
    print("Scores salvos em data/processed/scores_predicao_aprovacao.csv")


if __name__ == "__main__":
    main()
