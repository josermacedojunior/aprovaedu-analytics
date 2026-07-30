# Dicionário de Dados

Descreve as tabelas em `data/processed/` (mesmo schema do banco `aprovaedu.db`).
As colunas marcadas com 🔧 foram padronizadas/tratadas pelo ETL (ver
`notebooks/01_etl_tratamento.ipynb` para o antes/depois); as demais vieram
inalteradas do dado bruto.

## estudantes (812 linhas — chave: `aluno_id`)

| Coluna | Tipo | Descrição |
|---|---|---|
| aluno_id | string | Identificador único do aluno (ex.: `A00001`) |
| nome_aluno | string | Nome completo (dado fictício) |
| cpf_ficticio 🔧 | string | CPF fictício, normalizado para apenas dígitos. Duplicatas de CPF não indicam aluno duplicado — `aluno_id` é a chave real |
| email_aluno | string | E-mail do aluno (pode ser nulo) |
| telefone | string | Telefone de contato (pode ser nulo) |
| data_nascimento 🔧 | date | Data de nascimento, convertida para formato único |
| cidade 🔧 | string | Cidade de origem, padronizada (removida variação de caixa/acento) |
| escola_origem 🔧 | string | `Federal`, `Pública`, `Privada` ou `Não informado` |
| data_cadastro 🔧 | date | Data de cadastro no cursinho |
| canal_captacao 🔧 | string | Canal de captação: `Instagram`, `Google`, `WhatsApp`, `Indicação`, `Feira escolar` ou `Não informado` |

## professores (34 linhas — chave: `professor_id`)

| Coluna | Tipo | Descrição |
|---|---|---|
| professor_id | string | Identificador único (o registro duplicado `P_DUP_001` foi removido no tratamento — era uma cópia de `P004`, sem uso em outras tabelas) |
| nome_professor | string | Nome do professor |
| email_professor | string | E-mail (pode ser nulo) |
| materia_principal 🔧 | string | Matéria principal lecionada, padronizada |
| materias_ensina | string | Lista de matérias que também leciona (texto livre, separado por `;`) |
| data_contratacao 🔧 | date | Data de contratação |
| status_professor 🔧 | string | `Ativo` ou `Inativo` |
| unidade_base 🔧 | string | Unidade onde atua: `Online`, `Aldeota`, `Sul` ou `Centro` |
| carga_horaria_semanal | float | Horas semanais contratadas |
| observacoes | string | Texto livre (pode ser nulo) |

## ofertas_curso (220 linhas — chave: `oferta_id`)

| Coluna | Tipo | Descrição |
|---|---|---|
| oferta_id | string | Identificador único de uma turma/oferta (ex.: `O20210001`) |
| ano | int | Ano letivo da oferta |
| turma | string | Nome da turma (ex.: `Extensivo A`) |
| turno | string | Turno (Manhã/Tarde/Noite) |
| unidade 🔧 | string | Unidade física ou `Online` |
| materia 🔧 | string | Matéria da oferta, padronizada |
| professor_id | string | FK para `professores` |
| professor_nome_informado | string | Nome do professor conforme informado na oferta (pode divergir do cadastro) |
| modalidade 🔧 | string | `Online`, `Presencial` ou `Híbrido` |
| carga_horaria_total | int | Carga horária total do curso |
| preco_lista | int | Preço de tabela (sem desconto/bolsa) |
| data_inicio 🔧 / data_fim 🔧 | date | Período da oferta |

## matriculas (9.452 linhas — chave: `matricula_id`)

| Coluna | Tipo | Descrição |
|---|---|---|
| matricula_id | string | Identificador único da matrícula |
| aluno_id | string | FK para `estudantes` |
| oferta_id | string | FK para `ofertas_curso` |
| ano | int | Ano da matrícula |
| materia_declarada 🔧 | string | Matéria declarada na matrícula, padronizada |
| data_matricula 🔧 | date | Data da matrícula |
| bolsa_percentual 🔧 | float | % de bolsa concedida (nulo tratado como `0`, i.e. sem bolsa registrada) |
| status_matricula 🔧 | string | `Ativa`, `Concluída`, `Cancelada`, `Trancada` ou `Não informado` |
| nota_diagnostico | float | Nota do diagnóstico de entrada (0–100, aprox.) |
| origem_captacao 🔧 | string | Mesmo domínio de `canal_captacao` |

## aulas (2.418 linhas — chave: `aula_id`)

| Coluna | Tipo | Descrição |
|---|---|---|
| aula_id | string | Identificador único da aula |
| oferta_id | string | FK para `ofertas_curso` |
| ano | int | Ano da aula |
| data_aula 🔧 | date | Data da aula |
| materia 🔧 | string | Matéria, padronizada |
| professor_id | string | FK para `professores` |
| turma | string | Nome da turma |
| tema_aula | string | Tema/assunto da aula |
| duracao_min | float | Duração em minutos (pode ser nulo) |
| modalidade_aula 🔧 | string | `Online`, `Presencial`, `Híbrido` ou `Não informado` |

## presencas_aulas (74.997 linhas — chave: `presenca_id`)

| Coluna | Tipo | Descrição |
|---|---|---|
| presenca_id | string | Identificador único do registro de presença |
| aula_id | string | FK para `aulas` |
| aluno_id | string | FK para `estudantes` |
| status_presenca 🔧 | string | `Presente`, `Ausente`, `Atrasado`, `Justificado` ou `Não registrado` (ausência de registro — não confundir com falta) |
| atraso_min | float | Minutos de atraso (nulo quando não se aplica) |
| justificativa | string | Texto livre (majoritariamente nulo) |

## simulados (165 linhas — chave: `simulado_id`)

| Coluna | Tipo | Descrição |
|---|---|---|
| simulado_id | string | Identificador único do simulado |
| ano | int | Ano de aplicação |
| data_simulado 🔧 | date | Data de aplicação |
| materia 🔧 | string | Matéria do simulado, padronizada |
| professor_id | string | FK para `professores` |
| professor_nome_informado | string | Nome informado na aplicação |
| dificuldade 🔧 | string | `Fácil`, `Média`, `Difícil` ou `Não informado` |
| tipo_simulado | string | Ex.: `ENEM`, `Revisão` |
| total_questoes | int | Total de questões |
| tempo_limite_min | int | Tempo limite em minutos |
| tema | string | Tema do simulado (pode ser nulo) |

## resultados_simulados (21.510 linhas — chave: `resultado_id`)

| Coluna | Tipo | Descrição |
|---|---|---|
| resultado_id | string | Identificador único do resultado |
| simulado_id | string | FK para `simulados` |
| aluno_id | string | FK para `estudantes` |
| ano | int | Ano do simulado |
| status_realizacao 🔧 | string | `Finalizado`, `Ausente`, `Incompleto` ou `Não informado` |
| nota 🔧 | float | Nota obtida (0–100). Valores originalmente fora dessa faixa foram anulados — ver `nota_valida` |
| nota_valida 🔧 (nova) | bool | `True` se a nota original estava dentro de 0–100; `False` se foi anulada por estar fora da faixa (erro de digitação/importação) |
| acertos | float | Nº de acertos |
| tempo_finalizacao_min | float | Tempo total gasto |
| inicio_simulado 🔧 | datetime | Início da tentativa, convertido para formato único |
| dispositivo 🔧 | string | `Desktop`, `Celular`, `Tablet`, `Papel` ou `Não informado` |
| tentativas | float | Nº de tentativas (pode ser nulo) |
| unidade_aplicacao 🔧 | string | Mesmo domínio de `unidade` |

## aprovacoes_vestibular (354 linhas — chave: `aprovacao_id`)

| Coluna | Tipo | Descrição |
|---|---|---|
| aprovacao_id | string | Identificador único da aprovação |
| ano_vestibular | int | Ano do vestibular |
| aluno_id | string | FK para `estudantes` (um aluno pode aparecer em mais de um ano — 44 alunos aprovaram 2x e 2 alunos 3x no período, indicando reingresso/reclassificação) |
| universidade | string | Universidade de aprovação |
| curso_aprovado | string | Curso de aprovação |
| modalidade_vaga | string | Ex.: cota, ampla concorrência (pode ser nulo → `Não informado`) |
| chamada | string | Ex.: SISU, vestibular próprio |
| bolsa_aprovacao 🔧 | string | `Sim`, `Não`, `Parcial` ou `Não informado` |
| data_resultado 🔧 | date | Data do resultado |
| nota_final_vestibular | float | Nota final no vestibular |
| campus | string | Campus de aprovação (pode ser nulo → `Não informado`) |

---

## Marts analíticas (geradas pelo ETL, não vêm do dado bruto)

### mart_aluno_ano (1.022 linhas — chave: `aluno_id` + `ano`)

Uma linha por combinação (aluno, ano) em que o aluno teve pelo menos uma matrícula naquele ano.

| Coluna | Descrição |
|---|---|
| aluno_id, ano | Chave composta |
| aulas_registradas | Nº de registros de presença do aluno naquele ano |
| aulas_presente | Nº desses registros com status `Presente`, `Atrasado` ou `Justificado` (i.e., aluno esteve na aula) |
| taxa_presenca | `aulas_presente / aulas_registradas` |
| aprovado | `1` se o aluno aparece em `aprovacoes_vestibular` com `ano_vestibular` igual a `ano`; `0` caso contrário |
| cidade, escola_origem | Copiados de `estudantes`, para segmentação |

**Limitação conhecida**: a coluna `aprovado` assume que o ano da matrícula corresponde ao ano em que o aluno presta o vestibular. Na prática, um aluno matriculado em determinado ano pode prestar (e ser aprovado) em um ano seguinte, ou ainda estar cursando outro ano do cursinho no momento da aprovação. Essa aproximação é razoável para uma leitura agregada, mas pode diluir levemente o efeito de presença sobre aprovação — ver observação no relatório final.

### mart_curso_materia (55 linhas — chave: `ano` + `materia`)

| Coluna | Descrição |
|---|---|
| ano, materia | Chave composta |
| total_matriculas | Nº de matrículas naquela matéria/ano |
| matriculas_concluidas | Nº dessas com `status_matricula = "Concluída"` |
| taxa_conclusao | `matriculas_concluidas / total_matriculas` |
| nota_media_simulados | Nota média (`resultados_simulados.nota`, apenas `nota_valida=True`) dos simulados daquela matéria/ano |
