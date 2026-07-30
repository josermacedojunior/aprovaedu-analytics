# -*- coding: utf-8 -*-
"""Gera os notebooks 01_etl_tratamento.ipynb e 02_analise.ipynb a partir de
celulas markdown/codigo definidas aqui. Rodar e depois executar com:
    python -m jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
"""
import os
import nbformat as nbf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NB_DIR = os.path.join(BASE_DIR, "notebooks")
os.makedirs(NB_DIR, exist_ok=True)


def nb_from_cells(cells):
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3.8 (aprovaedu)", "language": "python", "name": "aprovaedu-py38"},
        "language_info": {"name": "python", "version": "3.8"},
    }
    return nb


def md(text):
    return nbf.v4.new_markdown_cell(text)


def code(text):
    return nbf.v4.new_code_cell(text)


# ===========================================================================
# 01 - ETL e tratamento
# ===========================================================================
etl_cells = [
md("""# AprovaEdu Analytics — ETL e Tratamento de Dados

Este notebook documenta, passo a passo, o diagnóstico dos dados brutos e as
decisões de tratamento aplicadas antes da análise. A implementação reutilizável
está em `src/etl.py`; aqui reproduzimos o mesmo pipeline célula a célula,
mostrando **antes/depois** de cada tratamento, para deixar as decisões
transparentes para quem avaliar.
"""),

code("""import sys, os
sys.path.insert(0, os.path.abspath(os.path.join("..", "src")))
import pandas as pd
import etl

pd.set_option("display.max_columns", 50)
"""),

md("""## 1. Diagnóstico dos dados brutos

As 9 bases fornecidas (`data/raw/`) vêm de fontes internas diferentes e chegam
com inconsistências típicas de integração manual: variação de
maiúsculas/minúsculas, acentuação, abreviações, formatos de data distintos e
alguns valores fora de faixa. Alguns exemplos:"""),

code("""raw_estudantes = etl.load_raw("estudantes")
print("cidade (bruto):", sorted(raw_estudantes["cidade"].dropna().unique()))
print("escola_origem (bruto):", sorted(raw_estudantes["escola_origem"].dropna().unique()))
"""),

code("""raw_matriculas = etl.load_raw("matriculas")
print("materia_declarada (bruto):", sorted(raw_matriculas["materia_declarada"].dropna().unique()))
print("status_matricula (bruto):", sorted(raw_matriculas["status_matricula"].dropna().unique()))
"""),

code("""raw_resultados = etl.load_raw("resultados_simulados")
print("Formatos de data distintos em inicio_simulado (amostra):")
print(raw_resultados["inicio_simulado"].dropna().sample(8, random_state=1).tolist())
print("\\nValores de nota fora da faixa 0-100:", ((raw_resultados["nota"] < 0) | (raw_resultados["nota"] > 100)).sum())
"""),

md("""## 2. Decisões de tratamento

As regras abaixo foram aplicadas de forma consistente em todas as tabelas
(implementadas em `src/etl.py`):

1. **Padronização de categorias**: cada coluna categórica (cidade, matéria,
   status de presença/matrícula/simulado, dispositivo, modalidade, etc.) é
   normalizada removendo acentuação/caixa para achar a chave e mapeada para
   um valor canônico único (ex.: `"presente"`, `"Presente"`, `"PRESENTE"` →
   `"Presente"`). Abreviações conhecidas (ex.: `"Mat."` → `"Matemática"`)
   também são tratadas.
2. **Valores ausentes em categorias**: preenchidos com `"Não informado"`
   (ou `"Não registrado"` para presença, para não confundir com a categoria
   `"Ausente"`, que representa falta efetiva).
3. **Datas em múltiplos formatos**: a base mistura `YYYY-MM-DD`,
   `YYYY/MM/DD`, `DD/MM/YYYY` e `MM-DD-YYYY` (com e sem hora). Um parser
   tolerante (`parse_date_flex`) identifica o padrão pela posição do ano e
   pelo separador e converte tudo para `datetime`.
4. **CPF fictício**: normalizado para apenas dígitos. Duplicatas de CPF
   fictício **não** foram tratadas como aluno duplicado, pois `aluno_id` é a
   chave primária real da base (sem duplicatas e sem chaves estrangeiras
   órfãs em nenhuma outra tabela).
5. **Notas de simulado fora da faixa 0–100** (ex.: `-3.5`, `1005`): tratadas
   como erro de digitação/importação. Em vez de tentar adivinhar uma correção,
   o valor é anulado e sinalizado na coluna `nota_valida=False`, preservando a
   linha (o aluno realizou o simulado) mas excluindo o valor da média.
6. **Professor duplicado**: o registro `P_DUP_001` ("Diego Rocha Lima") é uma
   duplicata de `P004` (mesmo nome) sem nenhuma referência em ofertas, aulas
   ou simulados — foi removido do cadastro de professores.
7. **Bolsa (`bolsa_percentual`) ausente**: preenchida com `0` (assume-se
   matrícula sem bolsa registrada)."""),

code("""estudantes = etl.clean_estudantes()
professores = etl.clean_professores()
ofertas = etl.clean_ofertas()
matriculas = etl.clean_matriculas()
aulas = etl.clean_aulas()
presencas = etl.clean_presencas()
simulados = etl.clean_simulados()
resultados = etl.clean_resultados_simulados()
aprovacoes = etl.clean_aprovacoes()
print("OK - todas as tabelas tratadas")
"""),

md("## 3. Verificação: antes → depois"),

code("""print("cidade (tratado):", sorted(estudantes["cidade"].dropna().unique()))
print("escola_origem (tratado):", sorted(estudantes["escola_origem"].dropna().unique()))
print("materia_declarada (tratado):", sorted(matriculas["materia_declarada"].dropna().unique()))
print("status_matricula (tratado):", sorted(matriculas["status_matricula"].dropna().unique()))
"""),

code("""print("professores: 35 brutos ->", professores.shape[0], "após remover duplicata")
print("\\nnotas de simulado invalidadas (fora de 0-100):", (~resultados["nota_valida"]).sum(), "de", len(resultados))
print("datas nao reconhecidas (NaT) em inicio_simulado:", resultados["inicio_simulado"].isna().sum())
"""),

md("""## 4. Base estruturada para análise (marts)

Além das 9 tabelas tratadas, geramos duas tabelas agregadas (*marts*) que
alimentam diretamente as perguntas obrigatórias:

- **`mart_aluno_ano`**: uma linha por (aluno, ano), com taxa de presença nas
  aulas registradas naquele ano e indicador binário de aprovação no
  vestibular naquele ano — usada na pergunta 2.
- **`mart_curso_materia`**: uma linha por (ano, matéria), com nota média em
  simulados e taxa de conclusão de matrícula — usada na pergunta 3."""),

code("""mart_aluno_ano = etl.build_mart_aluno_ano(estudantes, matriculas, presencas, aulas, aprovacoes)
mart_curso_materia = etl.build_mart_curso_materia(ofertas, matriculas, resultados, simulados, aprovacoes)
mart_aluno_ano.head()
"""),

code("""mart_curso_materia.head()
"""),

md("""## 5. Exportação

As tabelas tratadas e as marts são exportadas para `data/processed/` em CSV
e também consolidadas em um banco SQLite (`data/processed/aprovaedu.db`),
reutilizável por qualquer ferramenta de BI/SQL."""),

code("""etl.main()
"""),
]

# ===========================================================================
# 02 - Analise
# ===========================================================================
analysis_cells = [
md("""# AprovaEdu Analytics — Análises Obrigatórias

Responde às 4 perguntas obrigatórias do desafio a partir dos dados tratados
em `data/processed/` (gerados pelo notebook `01_etl_tratamento.ipynb` /
`src/etl.py`)."""),

code("""import sys, os
sys.path.insert(0, os.path.abspath(os.path.join("..", "src")))
import pandas as pd
import matplotlib.pyplot as plt
%matplotlib inline

PROC = os.path.abspath(os.path.join("..", "data", "processed"))

def load(n):
    return pd.read_csv(os.path.join(PROC, f"{n}.csv"), encoding="utf-8-sig")

estudantes = load("estudantes")
matriculas = load("matriculas")
aulas = load("aulas")
presencas = load("presencas_aulas")
aprovacoes = load("aprovacoes_vestibular")
ofertas = load("ofertas_curso")
resultados = load("resultados_simulados")
simulados = load("simulados")
mart_aluno_ano = load("mart_aluno_ano")
mart_curso_materia = load("mart_curso_materia")
"""),

md("""## Pergunta 1 — Qual foi a evolução da taxa de aprovação ao longo dos anos?

**Definição da métrica**: `taxa_aprovacao(ano) = alunos aprovados no vestibular
naquele ano / alunos com pelo menos uma matrícula naquele ano.` Usamos alunos
matriculados no ano como base de comparação (denominador), já que é a
população elegível/atendida pelo cursinho naquele ciclo."""),

code("""alunos_ano = matriculas.groupby("ano")["aluno_id"].nunique().rename("alunos_matriculados")
aprov_ano = aprovacoes.groupby("ano_vestibular")["aluno_id"].nunique().rename("alunos_aprovados")
q1 = pd.concat([alunos_ano, aprov_ano.rename_axis("ano")], axis=1).fillna(0)
q1["taxa_aprovacao"] = (q1["alunos_aprovados"] / q1["alunos_matriculados"]).round(4)
q1
"""),

code("""fig, ax = plt.subplots(figsize=(7, 4.5))
ax.bar(q1.index.astype(int).astype(str), q1["taxa_aprovacao"] * 100, color="#3b6fa0")
ax.set_ylabel("Taxa de aprovação (%)")
ax.set_xlabel("Ano")
ax.set_title("Evolução da taxa de aprovação no vestibular")
for i, v in enumerate(q1["taxa_aprovacao"] * 100):
    ax.text(i, v + 0.3, f"{v:.1f}%", ha="center", fontsize=9)
fig.tight_layout()
plt.show()
"""),

md("""**Leitura**: a taxa de aprovação oscila entre ~30% e ~36% ao longo dos 5
anos, sem uma tendência clara de crescimento ou queda — o valor de 2025
(34,3%) é praticamente igual ao de 2021 (36,2%). Os anos de 2022 (31,2%) e
2024 (30,0%) foram os mais baixos do período. Não há, portanto, evidência de
melhora consistente na efetividade do cursinho ao longo do tempo nesta
métrica agregada — o que por si só já é um achado relevante para a
coordenação."""),

md("""## Pergunta 2 — Existe relação entre presença nas aulas e aprovação no vestibular?

Usamos a mart `mart_aluno_ano` (uma linha por aluno-ano, com taxa de presença
nas aulas registradas e indicador de aprovação naquele ano)."""),

code("""q2 = mart_aluno_ano.dropna(subset=["taxa_presenca"]).copy()
q2.groupby("aprovado")["taxa_presenca"].describe()
"""),

code("""bins = [0, 0.75, 0.85, 0.90, 0.95, 1.01]
labels = ["<75%", "75-85%", "85-90%", "90-95%", ">=95%"]
q2["faixa_presenca"] = pd.cut(q2["taxa_presenca"], bins=bins, labels=labels, right=False)
faixa = q2.groupby("faixa_presenca")["aprovado"].agg(["mean", "count"])
faixa["mean"] = (faixa["mean"] * 100).round(2)
faixa
"""),

code("""corr = q2["taxa_presenca"].corr(q2["aprovado"])
print(f"Correlacao (point-biserial) presenca x aprovado: {corr:.4f}")

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.bar(faixa.index.astype(str), faixa["mean"], color="#3b6fa0")
ax.set_ylabel("Taxa de aprovação (%)")
ax.set_xlabel("Faixa de presença nas aulas")
ax.set_title("Taxa de aprovação por faixa de presença")
for i, (v, c) in enumerate(zip(faixa["mean"], faixa["count"])):
    ax.text(i, v + 0.5, f"{v:.1f}%\\n(n={c})", ha="center", fontsize=8)
fig.tight_layout()
plt.show()
"""),

md("""**Leitura**: a correlação entre presença e aprovação é praticamente nula
(≈ -0,01) e a taxa de aprovação fica entre 32% e 35% em todas as faixas de
presença — inclusive na faixa acima de 95%. Duas explicações prováveis: (1) a
maior parte dos alunos já tem presença alta e homogênea (mediana ~88%, desvio
padrão de apenas ~4 pontos percentuais — quase não há alunos com frequência
realmente baixa na base para comparar), o que restringe a variabilidade
observável; e (2) a aprovação no vestibular depende de muitos outros fatores
(desempenho em simulados, base de conhecimento prévia, concorrência da vaga)
que não estão sendo capturados só pela frequência. **Não encontramos, nesta
base, evidência de associação relevante entre presença e aprovação.**"""),

md("""## Pergunta 3 — Quais cursos ou matérias parecem apresentar melhor desempenho?

Combinamos dois indicadores por matéria: nota média em simulados e taxa de
conclusão de matrícula (proxy de "efetividade"/engajamento no curso)."""),

code("""q3 = (
    mart_curso_materia.groupby("materia")
    .agg(nota_media_simulados=("nota_media_simulados", "mean"),
         taxa_conclusao=("taxa_conclusao", "mean"),
         total_matriculas=("total_matriculas", "sum"))
    .round(3)
    .sort_values("nota_media_simulados", ascending=False)
)
q3
"""),

code("""fig, ax = plt.subplots(figsize=(8, 5))
order = q3.index.tolist()
bars = ax.bar(order, q3["nota_media_simulados"], color="#3b6fa0")
ax.set_ylabel("Nota média em simulados (%)")
ax.set_xticks(range(len(order)))
ax.set_xticklabels(order, rotation=40, ha="right")
ax.set_title("Nota média em simulados por matéria")
ax.bar_label(bars, labels=[f"{v:.1f}%" if pd.notna(v) else "sem dados" for v in q3["nota_media_simulados"]], padding=3, fontsize=8)
fig.tight_layout()
plt.show()
"""),

code("""fig, ax = plt.subplots(figsize=(8, 5))
q3_conc = q3.sort_values("taxa_conclusao", ascending=False)
order2 = q3_conc.index.tolist()
vals2 = q3_conc["taxa_conclusao"] * 100
bars2 = ax.bar(order2, vals2, color="#5a8f4f")
ax.set_ylabel("Taxa de conclusão de matrícula (%)")
ax.set_xticks(range(len(order2)))
ax.set_xticklabels(order2, rotation=40, ha="right")
ax.set_title("Taxa de conclusão de matrícula por matéria")
ax.bar_label(bars2, labels=[f"{v:.1f}%" for v in vals2], padding=3, fontsize=8)
fig.tight_layout()
plt.show()
"""),

md("""**Leitura**: as notas médias em simulados são muito próximas entre as
matérias (variação de apenas ~1 ponto, entre 60,8 e 61,9 — Português,
Filosofia e História levemente à frente; Geografia, Sociologia e Matemática
levemente atrás). **Redação** não aparece no gráfico de notas porque não há
simulados objetivos dessa matéria na base (é avaliada de outra forma,
provavelmente por correção manual não capturada aqui) — um gap de dados a
sinalizar para a coordenação. A taxa de conclusão de matrícula também é
bastante homogênea entre matérias (63%–74%), sem nenhuma se destacar
isoladamente. Olhando por outro corte, a taxa de conclusão por **modalidade
de oferta** é ligeiramente menor no Online (69,1%) frente a Presencial
(70,5%) e Híbrido (70,2%) — uma diferença pequena, mas consistente."""),

md("""### Nota sobre ambiguidade: "cursos" também pode significar cursos universitários

A pergunta fala em "cursos ou matérias". Interpretamos "cursos" acima como as
**ofertas do cursinho** (turmas por matéria), que é a leitura mais direta e
a que a coordenação pedagógica mais usaria no dia a dia. Mas existe uma
segunda leitura válida: `curso_aprovado`, em `aprovacoes_vestibular`, guarda
o **curso universitário** de destino (Medicina, Direito, etc.) — ou seja,
"em quais cursos os alunos do cursinho são aprovados com melhor
desempenho?". Trazemos essa segunda leitura como complemento, não como
substituição."""),

code("""curso_uni = (
    aprovacoes.groupby("curso_aprovado")
    .agg(n_aprovacoes=("aprovacao_id", "count"), nota_media=("nota_final_vestibular", "mean"))
    .round(2)
    .sort_values("nota_media", ascending=False)
)
curso_uni
"""),

md("""**Leitura**: os 354 aprovados se distribuem de forma relativamente
equilibrada entre 14 cursos universitários (16 a 30 aprovações cada). A nota
final média de entrada varia mais aqui (701 a 754) do que entre as matérias
do cursinho: **Ciência da Computação** (754,4) e **Administração** (753,6)
têm a maior nota média entre os aprovados, enquanto **Engenharia Civil**
(701,7) e **Engenharia de Software** (713,0) têm a menor — possivelmente
refletindo a nota de corte de cada curso/universidade, não necessariamente a
qualidade da preparação do cursinho nessa área. Por isso tratamos isso como
leitura complementar e não como resposta principal à pergunta 3."""),

md("""## Análises complementares (apoiam as recomendações)

Antes das recomendações, cruzamos três variáveis adicionais que não estavam
nas 4 perguntas obrigatórias, mas ajudam a explicar o que pode estar por trás
da estagnação da taxa de aprovação: **canal de captação**, **faixa de bolsa**
e **calibração de dificuldade dos simulados**."""),

code("""aprov_aluno = aprovacoes.groupby("aluno_id").size().reset_index(name="n_aprovacoes")
est_aprov = estudantes.merge(aprov_aluno, on="aluno_id", how="left")
est_aprov["aprovado"] = est_aprov["n_aprovacoes"].notna()

canal = (est_aprov.groupby("canal_captacao")["aprovado"].mean() * 100).round(2).sort_values(ascending=False)
canal
"""),

code("""bolsa_aluno = matriculas.groupby("aluno_id")["bolsa_percentual"].mean().reset_index()
bolsa_aluno["faixa_bolsa"] = pd.cut(
    bolsa_aluno["bolsa_percentual"], bins=[-0.1, 0, 10, 20, 30, 100],
    labels=["0%", "1-10%", "11-20%", "21-30%", ">30%"]
)
bolsa_aprov = bolsa_aluno.merge(aprov_aluno, on="aluno_id", how="left")
bolsa_aprov["aprovado"] = bolsa_aprov["n_aprovacoes"].notna()
bolsa_aprov.groupby("faixa_bolsa")["aprovado"].agg(taxa_aprovacao_pct=lambda s: round(s.mean() * 100, 2), n="count")
"""),

code("""res_dif = resultados.merge(simulados[["simulado_id", "dificuldade"]], on="simulado_id", how="left")
res_dif.groupby("dificuldade")["nota"].mean().round(2)
"""),

md("""**Leitura**:

- **Canal de captação**: Indicação tem a maior taxa de aprovação entre os
  alunos captados (43,4%), enquanto WhatsApp tem a menor (31,1%) — uma
  diferença de 12,3 pontos percentuais, a maior encontrada em qualquer corte
  desta análise.
- **Faixa de bolsa**: alunos com bolsa média entre 11–20% aprovam mais
  (40,8%, n=557) do que os com bolsa entre 21–30% (29,1%, n=117). É um
  padrão a investigar com cautela (n menor no grupo de bolsa mais alta), mas
  levanta a hipótese de que bolsas maiores podem estar concentradas em
  alunos com mais vulnerabilidade e que precisariam de apoio pedagógico
  adicional, não só financeiro.
- **Dificuldade do simulado**: a nota média é praticamente igual entre
  simulados marcados como "Fácil" (61,3%), "Média" (61,1%) e "Difícil"
  (61,3%) — ou seja, o rótulo de dificuldade não se traduz em desempenho
  diferente dos alunos, sugerindo que o critério de classificação não está
  calibrado."""),

md("""## Pergunta 4 — Recomendações para a coordenação

1. **Realocar parte do investimento de captação para o canal Indicação e
   revisar a estratégia via WhatsApp.** É o maior efeito encontrado em toda a
   análise (43,4% x 31,1% de aprovação, 12,3 p.p. de diferença). Próximo
   passo concreto: comparar custo de aquisição por canal com a taxa de
   aprovação resultante (não só matrícula) para decidir realocação de verba,
   e revisar o script/abordagem de conversão usado no WhatsApp.
2. **Revisar o critério de concessão de bolsas acima de 20%.** Alunos com
   bolsa 21–30% aprovam menos (29,1%) que os com 11–20% (40,8%). Recomenda-se
   cruzar esse grupo com indicadores socioeconômicos e oferecer suporte
   pedagógico complementar (não só desconto financeiro) a quem recebe bolsa
   mais alta.
3. **Recalibrar os critérios de dificuldade dos simulados junto aos
   professores.** Notas médias praticamente idênticas entre simulados
   "Fácil", "Média" e "Difícil" indicam que a classificação atual não reflete
   dificuldade real — isso compromete o uso de simulados como termômetro de
   preparo do aluno por nível.
4. **Não usar frequência isolada como sinal de risco de reprovação.** A
   correlação encontrada é praticamente nula (-0,01); um alerta baseado só em
   presença geraria muitos falsos negativos. Combine com nota em simulados e
   sua evolução ao longo do curso.
5. **Padronizar a avaliação de Redação em nota numérica estruturada.** Hoje
   a matéria não tem simulados com nota na base, o que impede comparação com
   as demais e é uma lacuna relevante dado o peso da Redação em vários
   vestibulares.
6. **Investigar a queda de conclusão de matrícula na modalidade Online**
   (69,1% vs. 70,5% Presencial e 70,2% Híbrido) — oportunidade de melhorar
   suporte/engajamento ao aluno remoto.
7. **Padronizar a captura de dados na origem.** Boa parte deste desafio foi
   tratar inconsistências de digitação (maiúsculas, acentos, abreviações,
   formatos de data, notas de simulado fora da faixa 0–100). Validar esses
   campos na entrada reduz retrabalho analítico e risco de erro silencioso."""),
]

# ===========================================================================
# 03 - Modelo preditivo (diferencial)
# ===========================================================================
modelo_cells = [
md("""# AprovaEdu Analytics — Modelo Preditivo (diferencial)

Este notebook não faz parte das 4 perguntas obrigatórias — atende ao item de
diferencial "criação de score, segmentação ou modelo preditivo" do desafio.

**Pergunta**: dado o que sabemos sobre um aluno durante o ano de preparação
(presença, nota de diagnóstico, nota média em simulados, bolsa, perfil de
captação/origem), conseguimos estimar a probabilidade de aprovação no
vestibular?"""),

code("""import sys, os
sys.path.insert(0, os.path.abspath(os.path.join("..", "src")))
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, confusion_matrix, classification_report
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import modelo_preditivo as mp

df = mp.build_features()
df.head()
"""),

md("""## Preparação da base de modelagem

Cada linha é um (aluno, ano). O alvo é `aprovado` (0/1, aprovação no
vestibular naquele ano — com a mesma limitação de correspondência ano a ano
já discutida no relatório final). As features usam apenas informação
disponível **durante** o ano de preparação (não usam `nota_final_vestibular`
nem qualquer coluna de `aprovacoes_vestibular`, para evitar vazamento de
dados)."""),

code("""NUMERIC = mp.NUMERIC_FEATURES
CATEG = mp.CATEGORICAL_FEATURES
TARGET = mp.TARGET
print("Features numericas:", NUMERIC)
print("Features categoricas:", CATEG)

modelo_df = df.dropna(subset=NUMERIC + CATEG).copy()
print(f"\\n{len(modelo_df)} linhas (de {len(df)}) apos remover nulos nas features")
print(f"Taxa de aprovacao na base do modelo: {modelo_df[TARGET].mean():.1%}")
"""),

md("## Treino (regressão logística) e avaliação em conjunto de teste (25%, nunca visto no treino)"),

code("""X = modelo_df[NUMERIC + CATEG]
y = modelo_df[TARGET]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

preprocess = ColumnTransformer([
    ("num", StandardScaler(), NUMERIC),
    ("cat", OneHotEncoder(handle_unknown="ignore"), CATEG),
])
modelo = Pipeline([("prep", preprocess), ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))])
modelo.fit(X_train, y_train)

proba_test = modelo.predict_proba(X_test)[:, 1]
pred_test = modelo.predict(X_test)

print("Baseline (sempre prever a classe majoritaria):", round(1 - y_test.mean(), 4))
print("Acuracia do modelo:", round(accuracy_score(y_test, pred_test), 4))
print("AUC-ROC do modelo:", round(roc_auc_score(y_test, proba_test), 4))
"""),

code("""print(confusion_matrix(y_test, pred_test))
print()
print(classification_report(y_test, pred_test, digits=3))
"""),

md("## Validação cruzada (5-fold) — para checar se o resultado é estável e não um artefato do split"),

code("""cv_scores = cross_val_score(modelo, X, y, cv=5, scoring="roc_auc")
print("AUC por fold:", np.round(cv_scores, 4))
print(f"Media: {cv_scores.mean():.4f}  Desvio padrao: {cv_scores.std():.4f}")
"""),

md("""## Leitura honesta do resultado

O modelo tem **AUC-ROC ≈ 0,49** (média em 5-fold, desvio-padrão baixo — ou
seja, o resultado é estável, não é ruído do split). Um AUC de 0,5 equivale a
previsão aleatória; portanto, **o modelo não consegue prever aprovação melhor
que o acaso** usando presença, nota de diagnóstico, nota média em simulados,
bolsa, escola de origem, canal de captação e cidade.

Isso não é uma falha do modelo — é, na verdade, o mesmo achado da Pergunta 2
(correlação presença × aprovação ≈ 0) generalizado: **nesta base, os sinais
operacionais disponíveis não explicam quem é aprovado**. Duas leituras
possíveis para a coordenação:

1. **Os dados operacionais capturados hoje não incluem os fatores que
   realmente determinam a aprovação** (ex.: desempenho no dia da prova,
   preparo anterior ao ingresso no cursinho, concorrência específica da
   vaga/curso escolhido, fatores pessoais). Recomenda-se, se o objetivo for
   um modelo preditivo funcional, capturar sinais adicionais — por exemplo,
   a **evolução da nota do aluno ao longo do tempo** (tendência, não só
   média) e a **nota de simulados específicos ENEM** próximos à data da
   prova, que tendem a ser mais preditivos que a média geral.
2. **Reportar esse resultado à coordenação como achado, não como
   entrega de "score pronto".** Entregar um modelo com falso senso de
   precisão (ex.: dizendo "os alunos com nota X têm Y% de chance de
   aprovação" sem essa ressalva) seria enganoso e poderia levar a decisões
   ruins — por isso a abordagem correta aqui é reportar a ausência de sinal
   de forma transparente, em vez de forçar uma métrica de acurácia mais
   bonita sem validade real."""),

md("## Coeficientes do modelo (apenas para referência — sem poder preditivo real, ver conclusão acima)"),

code("""feat_names = NUMERIC + list(
    modelo.named_steps["prep"].named_transformers_["cat"].get_feature_names_out(CATEG)
)
coefs = modelo.named_steps["clf"].coef_[0]
coef_df = pd.DataFrame({"feature": feat_names, "coeficiente": coefs}).sort_values("coeficiente", ascending=False)
coef_df
"""),
]

nbf.write(nb_from_cells(etl_cells), os.path.join(NB_DIR, "01_etl_tratamento.ipynb"))
nbf.write(nb_from_cells(analysis_cells), os.path.join(NB_DIR, "02_analise.ipynb"))
nbf.write(nb_from_cells(modelo_cells), os.path.join(NB_DIR, "03_modelo_preditivo.ipynb"))
print("Notebooks gerados em", NB_DIR)
