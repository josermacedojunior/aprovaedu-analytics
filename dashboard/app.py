# -*- coding: utf-8 -*-
"""Dashboard AprovaEdu Analytics (Streamlit).

Rodar:  python -m streamlit run dashboard/app.py
"""
import os

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE_DIR, "data", "processed")


@st.cache_data
def load(name):
    return pd.read_csv(os.path.join(PROC, f"{name}.csv"), encoding="utf-8-sig")


st.set_page_config(page_title="AprovaEdu Analytics", layout="wide")
st.title("AprovaEdu Analytics — Painel do Cursinho Pré-vestibular")
st.caption("Dados tratados de 2021 a 2025 · gerado a partir de data/processed/")

estudantes = load("estudantes")
matriculas = load("matriculas")
aprovacoes = load("aprovacoes_vestibular")
mart_aluno_ano = load("mart_aluno_ano")
mart_curso_materia = load("mart_curso_materia")

anos = sorted(matriculas["ano"].unique().tolist())
ano_sel = st.sidebar.multiselect("Filtrar por ano", anos, default=anos)

matriculas_f = matriculas[matriculas["ano"].isin(ano_sel)]
aprovacoes_f = aprovacoes[aprovacoes["ano_vestibular"].isin(ano_sel)]
mart_aluno_ano_f = mart_aluno_ano[mart_aluno_ano["ano"].isin(ano_sel)]
mart_curso_materia_f = mart_curso_materia[mart_curso_materia["ano"].isin(ano_sel)]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Alunos matriculados (período)", f"{matriculas_f['aluno_id'].nunique():,}".replace(",", "."))
col2.metric("Aprovações no vestibular", f"{len(aprovacoes_f):,}".replace(",", "."))
taxa_geral = (
    aprovacoes_f["aluno_id"].nunique() / matriculas_f["aluno_id"].nunique()
    if matriculas_f["aluno_id"].nunique() else 0
)
col3.metric("Taxa de aprovação (período)", f"{taxa_geral*100:.1f}%")
presenca_media = mart_aluno_ano_f["taxa_presenca"].mean()
col4.metric("Presença média nas aulas", f"{presenca_media*100:.1f}%" if pd.notna(presenca_media) else "—")

st.markdown("---")

# --- Q1: evolucao da taxa de aprovacao -------------------------------------
st.subheader("1. Evolução da taxa de aprovação por ano")
alunos_ano = matriculas.groupby("ano")["aluno_id"].nunique().rename("alunos_matriculados")
aprov_ano = aprovacoes.groupby("ano_vestibular")["aluno_id"].nunique().rename("alunos_aprovados")
q1 = pd.concat([alunos_ano, aprov_ano.rename_axis("ano")], axis=1).fillna(0)
q1["taxa_aprovacao_pct"] = (q1["alunos_aprovados"] / q1["alunos_matriculados"] * 100).round(2)
q1 = q1.reset_index()
q1 = q1[q1["ano"].isin(ano_sel)]
fig1 = px.bar(q1, x="ano", y="taxa_aprovacao_pct", text="taxa_aprovacao_pct",
              labels={"ano": "Ano", "taxa_aprovacao_pct": "Taxa de aprovação (%)"})
fig1.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
st.plotly_chart(fig1, use_container_width=True)

# --- Q2: presenca x aprovacao -----------------------------------------------
st.subheader("2. Presença nas aulas x aprovação no vestibular")
q2 = mart_aluno_ano_f.dropna(subset=["taxa_presenca"]).copy()
bins = [0, 0.75, 0.85, 0.90, 0.95, 1.01]
labels = ["<75%", "75-85%", "85-90%", "90-95%", ">=95%"]
q2["faixa_presenca"] = pd.cut(q2["taxa_presenca"], bins=bins, labels=labels, right=False)
faixa = q2.groupby("faixa_presenca", as_index=False)["aprovado"].mean()
faixa["aprovado_pct"] = (faixa["aprovado"] * 100).round(2)
fig2 = px.bar(faixa, x="faixa_presenca", y="aprovado_pct", text="aprovado_pct",
              labels={"faixa_presenca": "Faixa de presença", "aprovado_pct": "Taxa de aprovação (%)"})
fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
st.plotly_chart(fig2, use_container_width=True)
corr = q2["taxa_presenca"].corr(q2["aprovado"]) if len(q2) else float("nan")
st.caption(f"Correlação (presença x aprovado) no recorte selecionado: {corr:.3f}")

# --- Q3: desempenho por materia ---------------------------------------------
st.subheader("3. Desempenho por matéria")
q3 = (
    mart_curso_materia_f.groupby("materia", as_index=False)
    .agg(nota_media_simulados=("nota_media_simulados", "mean"), taxa_conclusao=("taxa_conclusao", "mean"))
)
q3["taxa_conclusao_pct"] = (q3["taxa_conclusao"] * 100).round(2)
q3["nota_media_simulados"] = q3["nota_media_simulados"].round(2)
c1, c2 = st.columns(2)
with c1:
    q3a = q3.sort_values("nota_media_simulados", ascending=False, na_position="last").copy()
    q3a["label"] = q3a["nota_media_simulados"].apply(lambda v: f"{v:.1f}%" if pd.notna(v) else "sem dados")
    fig3a = px.bar(q3a, x="materia", y="nota_media_simulados", text="label",
                    labels={"materia": "Matéria", "nota_media_simulados": "Nota média em simulados (%)"})
    fig3a.update_traces(textposition="outside")
    st.plotly_chart(fig3a, use_container_width=True)
with c2:
    fig3b = px.bar(q3.sort_values("taxa_conclusao_pct", ascending=False), x="materia", y="taxa_conclusao_pct",
                    text="taxa_conclusao_pct",
                    labels={"materia": "Matéria", "taxa_conclusao_pct": "Taxa de conclusão (%)"})
    fig3b.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig3b, use_container_width=True)

# --- Analises complementares: canal de captacao e bolsa ---------------------
st.subheader("Análises complementares (apoiam as recomendações)")
aprov_aluno_id = aprovacoes.groupby("aluno_id").size().reset_index(name="n_aprovacoes")
est_aprov = estudantes.merge(aprov_aluno_id, on="aluno_id", how="left")
est_aprov["aprovado"] = est_aprov["n_aprovacoes"].notna()

c3, c4 = st.columns(2)
with c3:
    canal = (est_aprov.groupby("canal_captacao", as_index=False)["aprovado"].mean())
    canal["aprovado_pct"] = (canal["aprovado"] * 100).round(2)
    fig4 = px.bar(canal.sort_values("aprovado_pct", ascending=False), x="canal_captacao", y="aprovado_pct",
                  text="aprovado_pct", labels={"canal_captacao": "Canal de captação", "aprovado_pct": "Taxa de aprovação (%)"})
    fig4.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig4, use_container_width=True)
with c4:
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
                  labels={"faixa_bolsa": "Faixa média de bolsa", "aprovado_pct": "Taxa de aprovação (%)"})
    fig5.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig5, use_container_width=True)

st.markdown("---")
st.subheader("4. Recomendações")
st.markdown("""
1. **Realocar parte do investimento de captação para o canal Indicação e revisar a
   estratégia via WhatsApp.** Maior efeito encontrado na análise: 43,4% de aprovação
   via Indicação contra 31,1% via WhatsApp (12,3 p.p. de diferença).
2. **Revisar o critério de concessão de bolsas acima de 20%.** Alunos com bolsa
   21–30% aprovam menos (29,1%) que os com 11–20% (40,8%) — cruzar com indicadores
   socioeconômicos e oferecer suporte pedagógico complementar, não só financeiro.
3. **Recalibrar os critérios de dificuldade dos simulados** junto aos professores:
   notas médias praticamente idênticas entre simulados "Fácil", "Média" e "Difícil"
   (todas ~61%) indicam que o rótulo não reflete dificuldade real.
4. **Não usar frequência isolada como sinal de risco de reprovação** — a correlação
   encontrada é praticamente nula (-0,01). Combine com nota em simulados e sua
   evolução ao longo do curso.
5. **Padronizar a avaliação de Redação em nota numérica estruturada** — hoje a
   matéria não tem simulados com nota na base, o que impede comparação com as demais.
6. **Investigar a queda de conclusão de matrícula na modalidade Online** (69,1% vs.
   70,5% Presencial e 70,2% Híbrido) — oportunidade de melhorar suporte remoto.
7. **Padronizar a captura de dados na origem** (formulários/planilhas), reduzindo o
   retrabalho de tratamento e o risco de erros silenciosos como os encontrados nesta
   base (notas de simulado fora da faixa 0–100, formatos de data inconsistentes).
""")
