# Log de qualidade de dados — gerado automaticamente pelo ETL

Cada linha documenta uma decisão de tratamento aplicada e quantos registros foram afetados. Reexecutar `python src/etl.py` regenera este arquivo.

| Tabela | Ação | Detalhe | Registros afetados |
|---|---|---|---:|
| professores | Normalização de categoria | materia_principal: grafias unificadas | 5 |
| professores | Normalização de categoria | status_professor: grafias unificadas | 1 |
| professores | Padronização de datas | data_contratacao: valores fora do formato ISO convertidos | 2 |
| estudantes | Normalização de categoria | cidade: grafias unificadas | 108 |
| estudantes | Padronização de datas | data_nascimento: valores fora do formato ISO convertidos | 41 |
| estudantes | Padronização de datas | data_cadastro: valores fora do formato ISO convertidos | 53 |
| estudantes | Preenchimento de nulos | escola_origem → 'Não informado' | 129 |
| estudantes | Normalização de categoria | canal_captacao: grafias unificadas | 82 |
| estudantes | Preenchimento de nulos | canal_captacao → 'Não informado' | 74 |
| ofertas_curso | Normalização de categoria | materia: grafias unificadas | 9 |
| ofertas_curso | Padronização de datas | data_inicio: valores fora do formato ISO convertidos | 9 |
| ofertas_curso | Padronização de datas | data_fim: valores fora do formato ISO convertidos | 13 |
| matriculas | Normalização de categoria | materia_declarada: grafias unificadas | 39 |
| matriculas | Padronização de datas | data_matricula: valores fora do formato ISO convertidos | 62 |
| matriculas | Preenchimento de nulos | bolsa_percentual nulo → 0 (sem bolsa) | 45 |
| matriculas | Normalização de categoria | status_matricula: grafias unificadas | 18 |
| matriculas | Preenchimento de nulos | status_matricula → 'Não informado' | 17 |
| matriculas | Preenchimento de nulos | origem_captacao → 'Não informado' | 84 |
| aprovacoes | Deduplicação | chave ['aluno_id', 'ano_vestibular', 'universidade', 'curso_aprovado', 'data_resultado'] | 15 |
| aprovacoes | Normalização de categoria | universidade: caixa alta unificada (uece→UECE, Ufc→UFC) | 50 |
| aprovacoes | Normalização de categoria | modalidade_vaga: grafias unificadas | 57 |
| aprovacoes | Preenchimento de nulos | modalidade_vaga → 'Não informado' | 56 |
| aprovacoes | Normalização de categoria | bolsa_aprovacao: grafias unificadas | 61 |
| aprovacoes | Preenchimento de nulos | bolsa_aprovacao → 'Não informado' | 74 |
| aprovacoes | Padronização de datas | data_resultado: valores fora do formato ISO convertidos | 24 |
| aprovacoes | Preenchimento de nulos | campus → 'Não informado' | 68 |
| simulados | Normalização de categoria | materia: grafias unificadas | 7 |
| simulados | Padronização de datas | data_simulado: valores fora do formato ISO convertidos | 16 |
| simulados | Normalização de categoria | dificuldade: grafias unificadas | 17 |
| simulados | Preenchimento de nulos | dificuldade → 'Não informado' | 2 |
| simulados | Preenchimento de nulos | tema → 'Não informado' | 29 |
| resultados_sim | Normalização de categoria | status_realizacao: grafias unificadas | 9 |
| resultados_sim | Preenchimento de nulos | status_realizacao → 'Não informado' | 7 |
| resultados_sim | Outlier tratado | nota > 100 (escala 0-100) → nulo, linha preservada | 5 |
| resultados_sim | Padronização de datas | inicio_simulado: valores fora do formato ISO convertidos | 68 |
| resultados_sim | Data inválida | inicio_simulado: valores que não puderam ser interpretados (→ nulo) | 2 |
| resultados_sim | Normalização de categoria | dispositivo: grafias unificadas | 78 |
| resultados_sim | Preenchimento de nulos | dispositivo → 'Não informado' | 88 |
| resultados_sim | Preenchimento de nulos | tentativas nulo → 1 (mínimo lógico) | 90 |
| resultados_sim | Normalização de categoria | unidade_aplicacao: grafias unificadas | 97 |
| resultados_sim | Preenchimento de nulos | unidade_aplicacao → 'Não informado' | 75 |
| aulas | Normalização de categoria | materia: grafias unificadas | 36 |
| aulas | Padronização de datas | data_aula: valores fora do formato ISO convertidos | 34 |
| aulas | Normalização de categoria | modalidade_aula: grafias unificadas | 107 |
| aulas | Preenchimento de nulos | modalidade_aula → 'Não informado' | 105 |
| presencas_aulas | Normalização de categoria | status_presenca: grafias unificadas | 4 |
| presencas_aulas | Preenchimento de nulos | status_presenca → 'Não informado' | 5 |
| presencas_aulas | Preenchimento de nulos | atraso_min nulo → 0 (sem atraso registrado) | 139 |
| ofertas_curso | Checagem de denormalização | professor_nome_informado divergente da dimensão Professores | 0 |
| simulados | Checagem de denormalização | professor_nome_informado divergente da dimensão Professores | 0 |
