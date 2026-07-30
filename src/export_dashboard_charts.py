# -*- coding: utf-8 -*-
"""Exporta os mesmos graficos Plotly usados no dashboard (dashboard/app.py)
como imagens PNG, para servir de 'Demonstracao' no repositorio sem depender
de rodar o Streamlit. Usa a mesma logica de calculo do app.py.

Rodar: python src/export_dashboard_charts.py
"""
import os

import pandas as pd
import plotly.express as px
import plotly.io as pio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE_DIR, "data", "processed")
OUT_DIR = os.path.join(BASE_DIR, "report", "dashboard_screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

pio.templates.default = "plotly_white"


def load(name):
    return pd.read_csv(os.path.join(PROC, f"{name}.csv"), encoding="utf-8-sig")


estudantes = load("estudantes")
matriculas = load("matriculas")
aprovacoes = load("aprovacoes_vestibular")
mart_aluno_ano = load("mart_aluno_ano")
mart_curso_materia = load("mart_curso_materia")

# --- Q1 ---
alunos_ano = matriculas.groupby("ano")["aluno_id"].nunique().rename("alunos_matriculados")
aprov_ano = aprovacoes.groupby("ano_vestibular")["aluno_id"].nunique().rename("alunos_aprovados")
q1 = pd.concat([alunos_ano, aprov_ano.rename_axis("ano")], axis=1).fillna(0)
q1["taxa_aprovacao_pct"] = (q1["alunos_aprovados"] / q1["alunos_matriculados"] * 100).round(2)
q1 = q1.reset_index()
fig1 = px.bar(q1, x="ano", y="taxa_aprovacao_pct", text="taxa_aprovacao_pct",
              labels={"ano": "Ano", "taxa_aprovacao_pct": "Taxa de aprovação (%)"},
              title="1. Evolução da taxa de aprovação por ano")
fig1.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig1.write_image(os.path.join(OUT_DIR, "01_taxa_aprovacao_por_ano.png"), width=1000, height=550, scale=2)

# --- Q2 ---
q2 = mart_aluno_ano.dropna(subset=["taxa_presenca"]).copy()
bins = [0, 0.75, 0.85, 0.90, 0.95, 1.01]
labels = ["<75%", "75-85%", "85-90%", "90-95%", ">=95%"]
q2["faixa_presenca"] = pd.cut(q2["taxa_presenca"], bins=bins, labels=labels, right=False)
faixa = q2.groupby("faixa_presenca", as_index=False)["aprovado"].mean()
faixa["aprovado_pct"] = (faixa["aprovado"] * 100).round(2)
fig2 = px.bar(faixa, x="faixa_presenca", y="aprovado_pct", text="aprovado_pct",
              labels={"faixa_presenca": "Faixa de presença", "aprovado_pct": "Taxa de aprovação (%)"},
              title="2. Presença nas aulas x aprovação no vestibular")
fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig2.write_image(os.path.join(OUT_DIR, "02_presenca_x_aprovacao.png"), width=1000, height=550, scale=2)

# --- Q3 ---
q3 = (
    mart_curso_materia.groupby("materia", as_index=False)
    .agg(nota_media_simulados=("nota_media_simulados", "mean"), taxa_conclusao=("taxa_conclusao", "mean"))
)
q3["taxa_conclusao_pct"] = (q3["taxa_conclusao"] * 100).round(2)
q3["nota_media_simulados"] = q3["nota_media_simulados"].round(2)

q3a = q3.sort_values("nota_media_simulados", ascending=False, na_position="last").copy()
q3a["label"] = q3a["nota_media_simulados"].apply(lambda v: f"{v:.1f}%" if pd.notna(v) else "sem dados")
fig3a = px.bar(q3a, x="materia", y="nota_media_simulados", text="label",
               labels={"materia": "Matéria", "nota_media_simulados": "Nota média em simulados (%)"},
               title="3a. Nota média em simulados por matéria")
fig3a.update_traces(textposition="outside")
fig3a.write_image(os.path.join(OUT_DIR, "03a_nota_media_por_materia.png"), width=900, height=550, scale=2)

fig3b = px.bar(q3.sort_values("taxa_conclusao_pct", ascending=False), x="materia", y="taxa_conclusao_pct",
               text="taxa_conclusao_pct",
               labels={"materia": "Matéria", "taxa_conclusao_pct": "Taxa de conclusão (%)"},
               title="3b. Taxa de conclusão de matrícula por matéria")
fig3b.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig3b.write_image(os.path.join(OUT_DIR, "03b_taxa_conclusao_por_materia.png"), width=900, height=550, scale=2)

# --- Analises complementares ---
aprov_aluno_id = aprovacoes.groupby("aluno_id").size().reset_index(name="n_aprovacoes")
est_aprov = estudantes.merge(aprov_aluno_id, on="aluno_id", how="left")
est_aprov["aprovado"] = est_aprov["n_aprovacoes"].notna()

canal = est_aprov.groupby("canal_captacao", as_index=False)["aprovado"].mean()
canal["aprovado_pct"] = (canal["aprovado"] * 100).round(2)
fig4 = px.bar(canal.sort_values("aprovado_pct", ascending=False), x="canal_captacao", y="aprovado_pct",
              text="aprovado_pct", labels={"canal_captacao": "Canal de captação", "aprovado_pct": "Taxa de aprovação (%)"},
              title="Complementar: taxa de aprovação por canal de captação")
fig4.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig4.write_image(os.path.join(OUT_DIR, "04_aprovacao_por_canal.png"), width=900, height=550, scale=2)

bolsa_aluno = matriculas.groupby("aluno_id")["bolsa_percentual"].mean().reset_index()
bolsa_aluno["faixa_bolsa"] = pd.cut(
    bolsa_aluno["bolsa_percentual"], bins=[-0.1, 0, 10, 20, 30, 100],
    labels=["0%", "1-10%", "11-20%", "21-30%", ">30%"]
)
bolsa_aprov = bolsa_aluno.merge(aprov_aluno_id, on="aluno_id", how="left")
bolsa_aprov["aprovado"] = bolsa_aprov["n_aprovacoes"].notna()
fx = bolsa_aprov.groupby("faixa_bolsa", as_index=False)["aprovado"].mean()
fx["aprovado_pct"] = (fx["aprovado"] * 100).round(2)
fig5 = px.bar(fx, x="faixa_bolsa", y="aprovado_pct", text="aprovado_pct",
              labels={"faixa_bolsa": "Faixa média de bolsa", "aprovado_pct": "Taxa de aprovação (%)"},
              title="Complementar: taxa de aprovação por faixa de bolsa")
fig5.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig5.write_image(os.path.join(OUT_DIR, "05_aprovacao_por_bolsa.png"), width=900, height=550, scale=2)

print("Imagens exportadas em", OUT_DIR)
