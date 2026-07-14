# -*- coding: utf-8 -*-
"""
Análise - AprovaEdu Analytics
==============================
Lê as tabelas tratadas (data/processed/*.csv) e produz:
  1. Os indicadores que respondem às 4 perguntas obrigatórias.
  2. Análises adicionais (universidades, cursos, notas do vestibular,
     dificuldade de simulados, canais de captação).
  3. Gráficos em outputs/figures/ e um resumo numérico completo em
     outputs/resumo_indicadores.json (todos os números do relatório
     vêm desse JSON — nada é digitado à mão).

Como rodar (depois do etl.py):
    python src/analysis.py
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:  # o teste estatístico vira opcional se scipy não existir
    HAS_SCIPY = False

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
FIG_DIR = os.path.join(BASE_DIR, "outputs", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 120,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "font.size": 10,
})
COLOR_MAIN = "#2E5FA3"
COLOR_ALT = "#E27D60"
COLOR_OK = "#3B8C6E"


def load(name):
    return pd.read_csv(os.path.join(PROC_DIR, f"{name}.csv"))


def savefig(fig, name):
    path = os.path.join(FIG_DIR, name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("Figura salva:", path)


# ---------------------------------------------------------------------------
# Pergunta 1 — Evolução da taxa de aprovação ao longo dos anos
# ---------------------------------------------------------------------------

def pergunta_1():
    apr = load("aprovacoes_tratado")
    mat = load("matriculas_tratado")

    aprov_ano = apr.groupby("ano_vestibular").aluno_id.nunique().rename("alunos_aprovados")
    mat_ano = mat.groupby("ano").aluno_id.nunique().rename("alunos_matriculados_amostra")

    tabela = pd.concat([mat_ano, aprov_ano.rename_axis("ano")], axis=1).reset_index()
    tabela["variacao_pct"] = (tabela["alunos_aprovados"].pct_change() * 100).round(1)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.bar(tabela["ano"].astype(str), tabela["alunos_aprovados"], color=COLOR_MAIN)
    ax.set_title("Alunos aprovados no vestibular por ano\n(base de Aprovações completa: 339 aprovações únicas)")
    ax.set_xlabel("Ano do vestibular")
    ax.set_ylabel("Alunos aprovados")
    for b, y in zip(bars, tabela["alunos_aprovados"]):
        ax.text(b.get_x() + b.get_width() / 2, y + 1, str(int(y)), ha="center", fontsize=10)
    savefig(fig, "q1_aprovacoes_por_ano.png")

    # Nota final média do vestibular por ano (qualidade das aprovações)
    nota_ano = apr.groupby("ano_vestibular")["nota_final_vestibular"].mean().round(1)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.plot(nota_ano.index.astype(str), nota_ano.values, marker="o", color=COLOR_ALT, lw=2)
    for x, y in zip(nota_ano.index.astype(str), nota_ano.values):
        ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(0, 8), ha="center")
    ax.set_title("Nota final média no vestibular dos aprovados, por ano")
    ax.set_ylabel("Nota média")
    savefig(fig, "q1_nota_final_media_por_ano.png")

    return tabela, nota_ano


# ---------------------------------------------------------------------------
# Pergunta 2 — Relação entre presença nas aulas e aprovação
# ---------------------------------------------------------------------------

def pergunta_2():
    pres = load("presencas_aulas_tratado")
    aulas = load("aulas_tratado")
    apr = load("aprovacoes_tratado")

    pres2 = pres.merge(aulas[["aula_id", "ano"]], on="aula_id", how="left")
    pres2["presente_flag"] = pres2["status_presenca"].isin(["Presente", "Atrasado"]).astype(int)

    por_aluno = (
        pres2.groupby("aluno_id")
        .agg(aulas_registradas=("presenca_id", "count"),
             aulas_presentes=("presente_flag", "sum"))
        .reset_index()
    )
    por_aluno["taxa_presenca"] = por_aluno["aulas_presentes"] / por_aluno["aulas_registradas"]

    alunos_aprovados = set(apr.aluno_id.unique())
    por_aluno["grupo"] = np.where(
        por_aluno.aluno_id.isin(alunos_aprovados),
        "Aprovados", "Sem registro de aprovação",
    )

    resumo = (
        por_aluno.groupby("grupo")["taxa_presenca"]
        .agg(["mean", "median", "std", "count"]).round(3)
    )

    # Teste de hipótese: Mann-Whitney U (não assume normalidade; adequado
    # a amostras pequenas e taxas limitadas em [0,1]).
    teste = {}
    if HAS_SCIPY:
        g1 = por_aluno.loc[por_aluno.grupo == "Aprovados", "taxa_presenca"]
        g0 = por_aluno.loc[por_aluno.grupo == "Sem registro de aprovação", "taxa_presenca"]
        u, p = stats.mannwhitneyu(g1, g0, alternative="greater")
        teste = {"teste": "Mann-Whitney U (unilateral: aprovados > demais)",
                 "estatistica_U": float(u), "p_valor": round(float(p), 4),
                 "n_aprovados": int(len(g1)), "n_demais": int(len(g0))}

    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    grupos = list(resumo.index)
    dados = [por_aluno.loc[por_aluno.grupo == g, "taxa_presenca"] for g in grupos]
    bp = ax.boxplot(dados, tick_labels=[g.replace(" ", "\n", 1) for g in grupos],
                    patch_artist=True, medianprops={"color": "black"})
    for patch, c in zip(bp["boxes"], [COLOR_OK, COLOR_MAIN]):
        patch.set_facecolor(c)
        patch.set_alpha(0.6)
    ax.set_title("Distribuição da taxa de presença por grupo")
    ax.set_ylabel("Taxa de presença nas aulas")
    savefig(fig, "q2_presenca_vs_aprovacao.png")

    return resumo, teste


# ---------------------------------------------------------------------------
# Pergunta 3 — Cursos/matérias com melhor desempenho
# ---------------------------------------------------------------------------

def pergunta_3():
    mat = load("matriculas_tratado")
    res = load("resultados_sim_tratado")
    sim = load("simulados_tratado")

    mat["concluida"] = (mat["status_matricula"] == "Concluída").astype(int)
    por_materia_mat = (
        mat.groupby("materia_declarada")
        .agg(nota_diagnostico_media=("nota_diagnostico", "mean"),
             taxa_conclusao=("concluida", "mean"),
             qtd_matriculas=("matricula_id", "count"))
        .round(3)
        .sort_values("nota_diagnostico_media", ascending=False)
    )

    res2 = res.merge(sim[["simulado_id", "materia", "dificuldade"]],
                     on="simulado_id", how="left")
    por_materia_sim = (
        res2.groupby("materia")
        .agg(nota_media_simulado=("nota", "mean"), qtd_resultados=("resultado_id", "count"))
        .round(1)
        .sort_values("nota_media_simulado", ascending=False)
    )

    fig, ax = plt.subplots(figsize=(7, 4.6))
    ordered = por_materia_mat.sort_values("nota_diagnostico_media")
    ax.barh(ordered.index, ordered["nota_diagnostico_media"], color=COLOR_MAIN)
    for i, v in enumerate(ordered["nota_diagnostico_media"]):
        ax.text(v + 0.4, i, f"{v:.1f}", va="center", fontsize=9)
    ax.set_title("Nota média de diagnóstico por matéria")
    ax.set_xlabel("Nota média de diagnóstico (0–100)")
    ax.set_xlim(0, 70)
    savefig(fig, "q3_nota_diagnostico_por_materia.png")

    fig, ax = plt.subplots(figsize=(7, 4.6))
    ordered2 = por_materia_mat.sort_values("taxa_conclusao")
    cores = [COLOR_ALT if m == "Inglês" else COLOR_MAIN for m in ordered2.index]
    ax.barh(ordered2.index, ordered2["taxa_conclusao"] * 100, color=cores)
    for i, v in enumerate(ordered2["taxa_conclusao"] * 100):
        ax.text(v + 0.6, i, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_title("Taxa de conclusão da matrícula por matéria\n(Inglês em destaque: menor conclusão da rede)")
    ax.set_xlabel("% de matrículas concluídas")
    ax.set_xlim(0, 85)
    savefig(fig, "q3_taxa_conclusao_por_materia.png")

    # Nota do simulado por dificuldade (validação de coerência da régua)
    por_dificuldade = (
        res2.groupby("dificuldade")["nota"].agg(["mean", "count"]).round(1)
        .reindex(["Fácil", "Média", "Difícil", "Não informado"]).dropna()
    )

    return por_materia_mat, por_materia_sim, por_dificuldade


# ---------------------------------------------------------------------------
# Análises adicionais (diferenciais)
# ---------------------------------------------------------------------------

def analises_adicionais():
    apr = load("aprovacoes_tratado")
    est = load("estudantes_tratado")

    # Aprovações por universidade
    por_uni = apr.universidade.value_counts()
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.barh(por_uni.index[::-1], por_uni.values[::-1], color=COLOR_MAIN)
    for i, v in enumerate(por_uni.values[::-1]):
        ax.text(v + 0.5, i, str(v), va="center", fontsize=9)
    ax.set_title("Aprovações por universidade (2021–2025)")
    ax.set_xlabel("Nº de aprovações")
    savefig(fig, "extra_aprovacoes_por_universidade.png")

    # Top cursos aprovados
    top_cursos = apr.curso_aprovado.value_counts().head(10)

    # Modalidade de vaga
    por_modalidade = apr.modalidade_vaga.value_counts()

    # Canal de captação dos estudantes
    por_canal = est.canal_captacao.value_counts()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh(por_canal.index[::-1], por_canal.values[::-1], color=COLOR_OK)
    ax.set_title("Canal de captação dos estudantes (amostra de 500)")
    ax.set_xlabel("Nº de alunos")
    savefig(fig, "extra_canal_captacao.png")

    return {
        "aprovacoes_por_universidade": por_uni.to_dict(),
        "top10_cursos_aprovados": top_cursos.to_dict(),
        "aprovacoes_por_modalidade_vaga": por_modalidade.to_dict(),
        "canal_captacao_estudantes": por_canal.to_dict(),
    }


def main():
    resultados = {}

    t1, nota_ano = pergunta_1()
    resultados["q1_aprovacoes_por_ano"] = t1.to_dict(orient="records")
    resultados["q1_nota_final_media_por_ano"] = nota_ano.to_dict()

    resumo2, teste2 = pergunta_2()
    resultados["q2_presenca_por_grupo"] = resumo2.reset_index().to_dict(orient="records")
    resultados["q2_teste_hipotese"] = teste2

    por_materia_mat, por_materia_sim, por_dif = pergunta_3()
    resultados["q3_por_materia_matriculas"] = por_materia_mat.reset_index().to_dict(orient="records")
    resultados["q3_por_materia_simulados"] = por_materia_sim.reset_index().to_dict(orient="records")
    resultados["q3_nota_por_dificuldade_simulado"] = por_dif.reset_index().to_dict(orient="records")

    resultados["analises_adicionais"] = analises_adicionais()

    out_path = os.path.join(BASE_DIR, "outputs", "resumo_indicadores.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)

    print("\nResumo de indicadores salvo em:", out_path)


if __name__ == "__main__":
    main()
