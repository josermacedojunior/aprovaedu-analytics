# AprovaEdu Analytics — Desafio Técnico (Analista de Dados)

Solução analítica para o desafio proposto pela Logap, a partir da base fictícia
de um cursinho pré-vestibular (2021–2025).

**Entregáveis principais:**
- `src/etl.py` — tratamento completo dos dados + log de qualidade automático
- `src/analysis.py` — indicadores das 4 perguntas obrigatórias + análises adicionais + teste estatístico
- `src/build_dashboard.py` — dashboard HTML interativo (Chart.js)
- `relatorio_final.md` — respostas, achados e recomendações
- `outputs/log_qualidade.md` — cada decisão de tratamento documentada com nº de registros afetados
- `outputs/dashboard.html` — abrir direto no navegador

## 1. Como rodar o projeto

Requisitos: Python 3.10+.

```bash
pip install -r requirements.txt

# Pipeline completo (ETL -> análises -> dashboard):
bash run_all.sh

# Ou passo a passo:
python src/etl.py              # gera data/processed/ e outputs/log_qualidade.md
python src/analysis.py         # gera outputs/figures/ e outputs/resumo_indicadores.json
python src/build_dashboard.py  # gera outputs/dashboard.html
```

Os scripts rodam do início ao fim sem intervenção manual e são idempotentes
(sempre recriam os arquivos de saída). Todos os números citados no relatório
vêm de `outputs/resumo_indicadores.json` — nada é digitado à mão.

## 2. Ferramentas utilizadas

- **Python 3** com **pandas**/**numpy** (tratamento e agregação)
- **scipy** (teste de hipótese Mann-Whitney na pergunta 2)
- **matplotlib** (gráficos estáticos do relatório)
- **Chart.js** via CDN (dashboard interativo, sem servidor)
- **openpyxl** (extração inicial do `.xlsx` de origem → CSVs brutos)

## 3. Estrutura do projeto

```
aprovaedu_analytics/
├── data/
│   ├── raw/          # bases originais extraídas 1:1 do Excel fornecido (1 tabela = 1 CSV)
│   └── processed/    # saída do ETL: tabelas tratadas + estrutura analítica
├── src/
│   ├── etl.py               # leitura, limpeza e padronização (com log de qualidade)
│   ├── analysis.py          # indicadores, teste estatístico e gráficos
│   └── build_dashboard.py   # dashboard HTML autocontido
├── outputs/
│   ├── figures/                 # gráficos (.png) usados no relatório
│   ├── log_qualidade.md         # decisões de tratamento, geradas pelo ETL
│   ├── resumo_indicadores.json  # todos os números do relatório
│   └── dashboard.html           # visualização interativa
├── relatorio_final.md
├── requirements.txt
├── run_all.sh
└── README.md
```

## 4. Origem dos dados e uma decisão importante

O arquivo fornecido (`base_pre_vestibular_dicionario_amostras.xlsx`) traz, para
cada tabela, uma **amostra de até 500 linhas**, junto com uma aba "Resumo" que
informa quantas linhas existem no *CSV completo* de cada tabela. Comparando a
amostra com o total informado:

| Tabela            | Linhas na amostra | Linhas no total (Resumo) | Situação |
|-------------------|------------------:|--------------------------:|----------|
| Professores       | 35                | 35                        | **Base completa** |
| Ofertas_Curso     | 220               | 220                       | **Base completa** |
| Simulados         | 165               | 165                       | **Base completa** |
| Aprovações        | 354               | 354                       | **Base completa** |
| Estudantes        | 500               | 812                       | Amostra parcial |
| Matrículas        | 500               | 9.452                     | Amostra parcial |
| Resultados_Sim    | 500               | 21.510                    | Amostra parcial |
| Aulas             | 500               | 2.418                     | Amostra parcial |
| Presenças_Aulas   | 500               | 74.997                    | Amostra parcial |

**Não recebemos os CSVs completos** (apenas o dicionário com amostras), então
o projeto foi construído com o que estava disponível — de forma transparente,
não escondida. O pipeline foi desenhado para funcionar igualmente com os CSVs
completos: basta colocá-los em `data/raw/` com os mesmos nomes de coluna e
reexecutar `run_all.sh`.

Consequência prática: como as 5 tabelas parciais são **amostras independentes
entre si** (não recortadas para manter os mesmos alunos), a interseção de
`aluno_id` entre elas é pequena. Isso limita o tamanho (n) de algumas análises
cruzadas — o grau de confiança de cada resposta é sinalizado no relatório.

## 5. Principais decisões de tratamento

Todas as decisões estão **quantificadas em `outputs/log_qualidade.md`**
(gerado automaticamente a cada execução do ETL). Resumo:

- **Datas em formatos mistos** (`2021-09-22`, `2021/04/02`, `06-07-2021`,
  `28/05/2021 12:00`...): convertidas para `datetime` priorizando ISO, depois
  padrão brasileiro (`dayfirst=True` com separador "/"), e por fim parser
  genérico. Valores não interpretáveis viram nulo (2 casos, logados).
- **Categorias inconsistentes** (matéria `MATEMÁTICA`/`Mat.`/`matematica`,
  status `concluida`/`Concluída`, universidade `uece`/`UECE`, cidade
  `fortaleza`/`Fortaleza`, canal `instagram`/`Instagram` etc.): normalizadas
  para um rótulo canônico único via dicionários de mapeamento (comparação
  sem acento/caixa).
- **Valores faltantes**: campos de identificação pessoal (e-mail, telefone,
  CPF) permanecem nulos — não interferem nas análises. Campos categóricos
  usados em agrupamentos recebem `"Não informado"` para não perder linhas.
  Campos numéricos com nulo semanticamente igual a zero (`bolsa_percentual`,
  `atraso_min`) recebem 0; `tentativas` nulo recebe 1 (mínimo lógico).
- **Outliers**: 5 notas de simulado acima de 100 (escala 0–100) tratadas como
  erro de digitação — a nota vira nula, mas a linha é preservada.
- **Duplicidades**: 15 registros de Aprovações com o mesmo aluno + ano +
  universidade + curso + data de resultado — interpretados como lançamento
  duplicado (não uma segunda aprovação legítima) e deduplicados. Restam 339
  aprovações únicas.
- **Denormalização**: `professor_nome_informado` das tabelas de fato conferido
  contra a dimensão Professores — **0 divergências** (checagem roda a cada
  execução e aparece no log).

## 6. Estrutura analítica gerada

- `*_tratado.csv`: versão limpa de cada tabela original.
- `freq_aluno_ano.csv`: taxa de presença por aluno/ano ("Presente" e
  "Atrasado" contam como presença física).
- `sim_aluno_ano.csv`: nota média em simulados por aluno/ano.
- `base_analitica_aluno_ano.csv`: quadro único — 1 linha por aluno/ano com
  matrícula, presença, simulados e flag de aprovação.

## 7. Relatório final e dashboard

- Respostas às 4 perguntas obrigatórias: [`relatorio_final.md`](./relatorio_final.md)
- Visualização interativa: abrir `outputs/dashboard.html` no navegador
  (autocontido; requer internet apenas para o CDN do Chart.js).
