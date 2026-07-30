# -*- coding: utf-8 -*-
"""
Analises obrigatorias - AprovaEdu Analytics
Gera as tabelas/numeros usados nas respostas das 4 perguntas do desafio e
salva os graficos em report/figures/.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE_DIR, "data", "processed")
FIG_DIR = os.path.join(BASE_DIR, "report", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

def load(n):
    return pd.read_csv(os.path.join(PROC, f"{n}.csv"), encoding="utf-8-sig")

estudantes = load("estudantes")
matriculas = load("matriculas")
aulas = load("aulas")
presencas = load("presencas_aulas")
aprovacoes = load("aprovacoes_vestibular")
mart_aluno_ano = load("mart_aluno_ano")
mart_curso_materia = load("mart_curso_materia")

out = open(os.path.join(os.path.dirname(__file__), "analysis_out.txt"), "w", encoding="utf-8")
def p(*a):
    print(*a, file=out)

# ---------------------------------------------------------------------------
# Q1 - Evolucao da taxa de aprovacao ao longo dos anos
# Denominador: alunos unicos com matricula ativa/concluida naquele ano
# (base elegivel de comparacao), numerador: alunos aprovados no vestibular
# naquele ano_vestibular.
# ---------------------------------------------------------------------------
alunos_ano = matriculas.groupby("ano")["aluno_id"].nunique().rename("alunos_matriculados")
aprov_ano = aprovacoes.groupby("ano_vestibular")["aluno_id"].nunique().rename("alunos_aprovados")
q1 = pd.concat([alunos_ano, aprov_ano.rename_axis("ano")], axis=1).fillna(0)
q1["taxa_aprovacao"] = (q1["alunos_aprovados"] / q1["alunos_matriculados"]).round(4)
p("### Q1 - Taxa de aprovacao por ano\n", q1.to_string())

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.bar(q1.index.astype(int).astype(str), q1["taxa_aprovacao"] * 100, color="#3b6fa0")
ax.set_ylabel("Taxa de aprovacao (%)")
ax.set_xlabel("Ano")
ax.set_title("Evolucao da taxa de aprovacao no vestibular")
for i, v in enumerate(q1["taxa_aprovacao"] * 100):
    ax.text(i, v + 0.3, f"{v:.1f}%", ha="center", fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "q1_taxa_aprovacao_por_ano.png"), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------------------
# Q2 - Relacao entre presenca e aprovacao
# Usa mart_aluno_ano: taxa_presenca (aluno-ano) x aprovado (0/1)
# ---------------------------------------------------------------------------
q2 = mart_aluno_ano.dropna(subset=["taxa_presenca"]).copy()
p("\n### Q2 - Presenca media por status de aprovacao\n",
  q2.groupby("aprovado")["taxa_presenca"].describe().to_string())

bins = [0, 0.75, 0.85, 0.90, 0.95, 1.01]
labels = ["<75%", "75-85%", "85-90%", "90-95%", ">=95%"]
q2["faixa_presenca"] = pd.cut(q2["taxa_presenca"], bins=bins, labels=labels, right=False)
faixa = q2.groupby("faixa_presenca")["aprovado"].agg(["mean", "count"])
faixa["mean"] = (faixa["mean"] * 100).round(2)
p("\n### Q2 - Taxa de aprovacao por faixa de presenca\n", faixa.to_string())

corr = q2["taxa_presenca"].corr(q2["aprovado"])
p(f"\n### Q2 - Correlacao (point-biserial) presenca x aprovado: {corr:.4f}")

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.bar(faixa.index.astype(str), faixa["mean"], color="#3b6fa0")
ax.set_ylabel("Taxa de aprovacao (%)")
ax.set_xlabel("Faixa de presenca nas aulas")
ax.set_title("Taxa de aprovacao por faixa de presenca")
for i, (v, c) in enumerate(zip(faixa["mean"], faixa["count"])):
    ax.text(i, v + 0.5, f"{v:.1f}%\n(n={c})", ha="center", fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "q2_presenca_x_aprovacao.png"), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------------------
# Q3 - Desempenho por curso/materia
# nota media em simulados + taxa de conclusao de matricula, por materia
# (media entre os 5 anos)
# ---------------------------------------------------------------------------
q3 = (
    mart_curso_materia.groupby("materia")
    .agg(nota_media_simulados=("nota_media_simulados", "mean"), taxa_conclusao=("taxa_conclusao", "mean"),
         total_matriculas=("total_matriculas", "sum"))
    .round(3)
    .sort_values("nota_media_simulados", ascending=False)
)
p("\n### Q3 - Desempenho medio por materia (todos os anos)\n", q3.to_string())

fig, ax1 = plt.subplots(figsize=(8, 5))
order = q3.index.tolist()
bars1 = ax1.bar(order, q3["nota_media_simulados"], color="#3b6fa0")
ax1.set_ylabel("Nota media em simulados (%)")
ax1.set_xticks(range(len(order)))
ax1.set_xticklabels(order, rotation=40, ha="right")
ax1.set_title("Nota media em simulados por materia")
ax1.bar_label(bars1, labels=[f"{v:.1f}%" if pd.notna(v) else "sem dados" for v in q3["nota_media_simulados"]], padding=3, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "q3_nota_media_por_materia.png"), dpi=140)
plt.close(fig)

fig, ax2 = plt.subplots(figsize=(8, 5))
q3_conc = q3.sort_values("taxa_conclusao", ascending=False)
vals_conc = q3_conc["taxa_conclusao"] * 100
bars2 = ax2.bar(q3_conc.index.tolist(), vals_conc, color="#5a8f4f")
ax2.set_ylabel("Taxa de conclusao de matricula (%)")
ax2.set_xticks(range(len(q3_conc.index)))
ax2.set_xticklabels(q3_conc.index.tolist(), rotation=40, ha="right")
ax2.set_title("Taxa de conclusao de matricula por materia")
ax2.bar_label(bars2, labels=[f"{v:.1f}%" for v in vals_conc], padding=3, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "q3_taxa_conclusao_por_materia.png"), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------------------
# Analises complementares (apoiam Q3 e Q4)
# ---------------------------------------------------------------------------
ofertas = load("ofertas_curso")
resultados = load("resultados_simulados")
simulados = load("simulados")

# conclusao de matricula por modalidade da oferta
matr_of = matriculas.merge(ofertas[["oferta_id", "modalidade", "unidade"]], on="oferta_id", how="left")
matr_of["concluida"] = (matr_of["status_matricula"] == "Concluída").astype(int)
by_modalidade = matr_of.groupby("modalidade")["concluida"].agg(["mean", "count"])
by_modalidade["mean"] = (by_modalidade["mean"] * 100).round(2)
p("\n### Q3b - Taxa de conclusao por modalidade da oferta\n", by_modalidade.to_string())

by_unidade = matr_of.groupby("unidade")["concluida"].agg(["mean", "count"])
by_unidade["mean"] = (by_unidade["mean"] * 100).round(2)
p("\n### Q3b - Taxa de conclusao por unidade\n", by_unidade.to_string())

# aprovacao x faixa media de bolsa do aluno (quase todos tem bolsa_percentual
# > 0 em pelo menos uma matricula, entao comparamos por faixa em vez de um
# flag binario com/sem bolsa, que deixaria o grupo "sem bolsa" com 1 aluno)
bolsa_aluno = matriculas.groupby("aluno_id")["bolsa_percentual"].mean().reset_index()
bolsa_aluno["faixa_bolsa"] = pd.cut(
    bolsa_aluno["bolsa_percentual"], bins=[-0.1, 0, 10, 20, 30, 100],
    labels=["0%", "1-10%", "11-20%", "21-30%", ">30%"]
)
aprov_aluno = aprovacoes.groupby("aluno_id").size().reset_index(name="n_aprovacoes")
bolsa_aprov = bolsa_aluno.merge(aprov_aluno, on="aluno_id", how="left")
bolsa_aprov["aprovado"] = bolsa_aprov["n_aprovacoes"].notna()
p("\n### Q4 apoio - Aprovacao (%) por faixa media de bolsa do aluno\n",
  bolsa_aprov.groupby("faixa_bolsa")["aprovado"].agg(["mean", "count"]).assign(
      mean=lambda d: (d["mean"] * 100).round(2)).to_string())

# aprovacao x escola de origem
est_aprov = estudantes.merge(aprov_aluno, on="aluno_id", how="left")
est_aprov["aprovado"] = est_aprov["n_aprovacoes"].notna()
p("\n### Q4 apoio - Aprovacao (%) por escola de origem\n",
  (est_aprov.groupby("escola_origem")["aprovado"].mean() * 100).round(2).to_string())

# aprovacao x canal de captacao
p("\n### Q4 apoio - Aprovacao (%) por canal de captacao\n",
  (est_aprov.groupby("canal_captacao")["aprovado"].mean() * 100).round(2).to_string())

# nota media de simulados por dificuldade
res_dif = resultados.merge(simulados[["simulado_id", "dificuldade"]], on="simulado_id", how="left")
p("\n### Q3b apoio - Nota media por dificuldade do simulado\n",
  res_dif.groupby("dificuldade")["nota"].mean().round(2).to_string())

out.close()
print("done")
