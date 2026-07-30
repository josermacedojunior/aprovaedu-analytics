# -*- coding: utf-8 -*-
"""
ETL - AprovaEdu Analytics
==========================
Le as 9 bases brutas (data/raw), aplica as regras de tratamento documentadas
no README, e grava:
  - CSVs tratados em data/processed/
  - um banco SQLite (data/processed/aprovaedu.db) com as mesmas tabelas
    + duas marts analiticas (mart_aluno_ano, mart_curso_materia)

Rodar:  python src/etl.py
"""
import os
import re
import sqlite3
import unicodedata

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
DB_PATH = os.path.join(PROCESSED_DIR, "aprovaedu.db")

os.makedirs(PROCESSED_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers genericos
# ---------------------------------------------------------------------------
def strip_accents(text):
    if pd.isna(text):
        return text
    text = str(text)
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def build_mapper(canonical_values):
    """Cria um dicionario {chave_normalizada: valor_canonico} a partir de uma
    lista de valores 'corretos'. A chave normalizada remove acentos, espacos
    nas bordas e coloca em maiusculo, permitindo casar variantes como
    'presente' / 'Presente' / 'PRESENTE' com o mesmo valor canonico."""
    return {strip_accents(v).strip().upper(): v for v in canonical_values}


def apply_mapper(series, mapper, extra_aliases=None, default_unmapped="manter"):
    """Normaliza uma coluna categorica usando o mapper. extra_aliases permite
    tratar abreviacoes/erros especificos (ex.: 'MAT.' -> 'Matematica').
    Valores nao mapeados sao mantidos como estao (e reportados)."""
    aliases = dict(mapper)
    if extra_aliases:
        aliases.update({strip_accents(k).strip().upper(): v for k, v in extra_aliases.items()})

    def _map(v):
        if pd.isna(v):
            return v
        key = strip_accents(str(v)).strip().upper()
        key = re.sub(r"\.$", "", key)  # remove ponto final (ex.: "MAT.")
        return aliases.get(key, v if default_unmapped == "manter" else np.nan)

    return series.map(_map)


_DATE_PATTERNS = [
    (re.compile(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$"), "%Y-%m-%d %H:%M", "%Y-%m-%d"),
    (re.compile(r"^\d{4}/\d{2}/\d{2}( \d{2}:\d{2})?$"), "%Y/%m/%d %H:%M", "%Y/%m/%d"),
    (re.compile(r"^\d{2}/\d{2}/\d{4}( \d{2}:\d{2})?$"), "%d/%m/%Y %H:%M", "%d/%m/%Y"),
    (re.compile(r"^\d{2}-\d{2}-\d{4}( \d{2}:\d{2})?$"), "%m-%d-%Y %H:%M", "%m-%d-%Y"),
]


def parse_date_flex(value):
    """Parser tolerante a multiplos formatos de data encontrados na base:
      - YYYY-MM-DD[ HH:MM]           (ISO)
      - YYYY/MM/DD[ HH:MM]           (ano na frente -> ano-mes-dia)
      - DD/MM/YYYY[ HH:MM]           (barra, ano no final -> formato BR)
      - MM-DD-YYYY[ HH:MM]           (traco, ano no final -> formato US)
    A regra de desambiguacao usada foi: quando o ano vem primeiro, a ordem e
    sempre ano-mes-dia; quando o ano vem por ultimo, o separador indica a
    convencao (barra = BR dia/mes/ano, traco = US mes-dia/ano), com base no
    padrao observado nos dados brutos."""
    if pd.isna(value):
        return pd.NaT
    s = str(value).strip()
    if not s:
        return pd.NaT
    for pattern, fmt_dt, fmt_d in _DATE_PATTERNS:
        if pattern.match(s):
            fmt = fmt_dt if " " in s else fmt_d
            try:
                return pd.to_datetime(s, format=fmt)
            except ValueError:
                return pd.NaT
    return pd.NaT


def parse_date_col(series):
    return series.map(parse_date_flex)


def normalize_cpf(series):
    return series.astype(str).str.replace(r"\D", "", regex=True).where(series.notna())


# ---------------------------------------------------------------------------
# Dicionarios de padronizacao (baseados nos valores unicos observados na
# exploracao dos dados brutos - ver src/explore.py e src/explore2_out.txt)
# ---------------------------------------------------------------------------
MAP_MATERIA = build_mapper(
    ["Matemática", "Português", "Redação", "Física", "Química", "Biologia",
     "História", "Geografia", "Filosofia", "Sociologia", "Inglês"]
)
MATERIA_ALIASES = {"MAT": "Matemática", "MAT.": "Matemática"}

MAP_CIDADE = build_mapper(
    ["Fortaleza", "Crato", "Horizonte", "Juazeiro do Norte", "Caucaia",
     "Maracanaú", "Itapipoca", "Sobral", "Aquiraz", "Eusébio", "Pacatuba"]
)
CIDADE_ALIASES = {"MARACANAU": "Maracanaú"}

MAP_ESCOLA_ORIGEM = build_mapper(["Federal", "Pública", "Privada", "Não informado"])
MAP_CANAL = build_mapper(["Feira escolar", "Google", "Indicação", "Instagram", "WhatsApp"])
MAP_STATUS_MATRICULA = build_mapper(["Ativa", "Cancelada", "Concluída", "Trancada"])
MAP_STATUS_PRESENCA = build_mapper(["Presente", "Ausente", "Atrasado", "Justificado"])
MAP_STATUS_REALIZACAO = build_mapper(["Finalizado", "Ausente", "Incompleto"])
MAP_DISPOSITIVO = build_mapper(["Celular", "Desktop", "Tablet", "Papel"])
MAP_BOLSA_APROVACAO = build_mapper(["Sim", "Não", "Parcial"])
MAP_STATUS_PROFESSOR = build_mapper(["Ativo", "Inativo"])
MAP_UNIDADE = build_mapper(["Online", "Aldeota", "Sul", "Centro"])
MAP_MODALIDADE = build_mapper(["Online", "Presencial", "Híbrido"])
MAP_DIFICULDADE = build_mapper(["Fácil", "Média", "Difícil"])


# ---------------------------------------------------------------------------
# Loaders / transform por tabela
# ---------------------------------------------------------------------------
def load_raw(name):
    return pd.read_csv(os.path.join(RAW_DIR, f"{name}.csv"), encoding="utf-8-sig")


def clean_estudantes():
    df = load_raw("estudantes")
    df["cidade"] = apply_mapper(df["cidade"], MAP_CIDADE, CIDADE_ALIASES)
    df["escola_origem"] = apply_mapper(df["escola_origem"], MAP_ESCOLA_ORIGEM)
    df["escola_origem"] = df["escola_origem"].fillna("Não informado")
    df["canal_captacao"] = apply_mapper(df["canal_captacao"], MAP_CANAL)
    df["canal_captacao"] = df["canal_captacao"].fillna("Não informado")
    df["cpf_ficticio"] = normalize_cpf(df["cpf_ficticio"])
    df["data_nascimento"] = parse_date_col(df["data_nascimento"])
    df["data_cadastro"] = parse_date_col(df["data_cadastro"])
    # CPFs ficticios duplicados nao indicam aluno duplicado: aluno_id e a
    # chave primaria real (unica, sem furos nas FKs de todas as outras
    # tabelas), entao mantemos o registro como esta e apenas documentamos.
    return df


def clean_professores():
    df = load_raw("professores")
    df["status_professor"] = apply_mapper(df["status_professor"], MAP_STATUS_PROFESSOR)
    df["unidade_base"] = apply_mapper(df["unidade_base"], MAP_UNIDADE)
    df["data_contratacao"] = parse_date_col(df["data_contratacao"])
    df["materia_principal"] = apply_mapper(df["materia_principal"], MAP_MATERIA, MATERIA_ALIASES)
    # P_DUP_001 e um cadastro duplicado de Diego Rocha Lima (mesmo nome de
    # P004) sem nenhuma referencia em ofertas/aulas/simulados -> removido.
    df = df[df["professor_id"] != "P_DUP_001"].copy()
    return df


def clean_ofertas():
    df = load_raw("ofertas_curso")
    df["materia"] = apply_mapper(df["materia"], MAP_MATERIA, MATERIA_ALIASES)
    df["unidade"] = apply_mapper(df["unidade"], MAP_UNIDADE)
    df["modalidade"] = apply_mapper(df["modalidade"], MAP_MODALIDADE)
    df["data_inicio"] = parse_date_col(df["data_inicio"])
    df["data_fim"] = parse_date_col(df["data_fim"])
    return df


def clean_matriculas():
    df = load_raw("matriculas")
    df["materia_declarada"] = apply_mapper(df["materia_declarada"], MAP_MATERIA, MATERIA_ALIASES)
    df["status_matricula"] = apply_mapper(df["status_matricula"], MAP_STATUS_MATRICULA)
    df["status_matricula"] = df["status_matricula"].fillna("Não informado")
    df["origem_captacao"] = apply_mapper(df["origem_captacao"], MAP_CANAL)
    df["origem_captacao"] = df["origem_captacao"].fillna("Não informado")
    df["data_matricula"] = parse_date_col(df["data_matricula"])
    # bolsa_percentual ausente = aluno sem bolsa registrada -> 0
    df["bolsa_percentual"] = df["bolsa_percentual"].fillna(0)
    return df


def clean_aulas():
    df = load_raw("aulas")
    df["materia"] = apply_mapper(df["materia"], MAP_MATERIA, MATERIA_ALIASES)
    df["modalidade_aula"] = apply_mapper(df["modalidade_aula"], MAP_MODALIDADE)
    df["modalidade_aula"] = df["modalidade_aula"].fillna("Não informado")
    df["data_aula"] = parse_date_col(df["data_aula"])
    return df


def clean_presencas():
    df = load_raw("presencas_aulas")
    df["status_presenca"] = apply_mapper(df["status_presenca"], MAP_STATUS_PRESENCA)
    # ausencia de registro de presenca e tratada como categoria propria, para
    # nao ser confundida com "Ausente" (falta) nem descartada da contagem de
    # aulas do aluno.
    df["status_presenca"] = df["status_presenca"].fillna("Não registrado")
    return df


def clean_simulados():
    df = load_raw("simulados")
    df["materia"] = apply_mapper(df["materia"], MAP_MATERIA, MATERIA_ALIASES)
    df["data_simulado"] = parse_date_col(df["data_simulado"])
    df["dificuldade"] = apply_mapper(df["dificuldade"], MAP_DIFICULDADE)
    df["dificuldade"] = df["dificuldade"].fillna("Não informado")
    return df


def clean_resultados_simulados():
    df = load_raw("resultados_simulados")
    df["status_realizacao"] = apply_mapper(df["status_realizacao"], MAP_STATUS_REALIZACAO)
    df["status_realizacao"] = df["status_realizacao"].fillna("Não informado")
    df["dispositivo"] = apply_mapper(df["dispositivo"], MAP_DISPOSITIVO)
    df["dispositivo"] = df["dispositivo"].fillna("Não informado")
    df["unidade_aplicacao"] = apply_mapper(df["unidade_aplicacao"], MAP_UNIDADE)
    df["unidade_aplicacao"] = df["unidade_aplicacao"].fillna("Não informado")
    df["inicio_simulado"] = parse_date_col(df["inicio_simulado"])
    # nota deve estar entre 0 e 100 (escala de 0 a 100 usada em toda a base,
    # confirmada por nota_final_vestibular e nota_diagnostico). Valores fora
    # da faixa (ex.: -3.5, 1005) sao erros de digitacao/importacao: marcamos
    # como invalidos (NaN) e sinalizamos na coluna nota_valida para
    # transparencia, em vez de tentar adivinhar uma correcao.
    invalid = (df["nota"] < 0) | (df["nota"] > 100)
    df["nota_valida"] = ~invalid.fillna(False) & df["nota"].notna()
    df.loc[invalid, "nota"] = np.nan
    return df


def clean_aprovacoes():
    df = load_raw("aprovacoes_vestibular")
    df["bolsa_aprovacao"] = apply_mapper(df["bolsa_aprovacao"], MAP_BOLSA_APROVACAO)
    df["bolsa_aprovacao"] = df["bolsa_aprovacao"].fillna("Não informado")
    df["modalidade_vaga"] = df["modalidade_vaga"].fillna("Não informado")
    df["campus"] = df["campus"].fillna("Não informado")
    df["data_resultado"] = parse_date_col(df["data_resultado"])
    return df


# ---------------------------------------------------------------------------
# Marts analiticas (agregados usados nas respostas do desafio)
# ---------------------------------------------------------------------------
def build_mart_aluno_ano(estudantes, matriculas, presencas, aulas, aprovacoes):
    """Uma linha por (aluno, ano) com frequencia media e status de aprovacao
    no vestibular naquele ano."""
    pres = presencas.merge(aulas[["aula_id", "ano", "materia"]], on="aula_id", how="left")
    pres["presente_flag"] = pres["status_presenca"].isin(["Presente", "Atrasado", "Justificado"]).astype(int)
    freq = (
        pres.dropna(subset=["ano"])
        .groupby(["aluno_id", "ano"])
        .agg(aulas_registradas=("presenca_id", "count"), aulas_presente=("presente_flag", "sum"))
        .reset_index()
    )
    freq["ano"] = freq["ano"].astype(int)
    freq["taxa_presenca"] = (freq["aulas_presente"] / freq["aulas_registradas"]).round(4)

    aprov = aprovacoes.copy()
    aprov["aprovado"] = 1
    aprov_ano = aprov.groupby(["aluno_id", "ano_vestibular"], as_index=False)["aprovado"].max()
    aprov_ano = aprov_ano.rename(columns={"ano_vestibular": "ano"})

    matr_anos = matriculas[["aluno_id", "ano"]].drop_duplicates()

    mart = matr_anos.merge(freq, on=["aluno_id", "ano"], how="left")
    mart = mart.merge(aprov_ano, on=["aluno_id", "ano"], how="left")
    mart["aprovado"] = mart["aprovado"].fillna(0).astype(int)
    mart = mart.merge(estudantes[["aluno_id", "cidade", "escola_origem"]], on="aluno_id", how="left")
    return mart


def build_mart_curso_materia(ofertas, matriculas, resultados, simulados, aprovacoes):
    """Uma linha por (ano, materia) com metricas de desempenho: nota media em
    simulados, taxa de conclusao de matricula e numero de aprovados na
    materia (proxy: alunos aprovados que cursaram a materia naquele ano)."""
    sim_full = resultados.merge(simulados[["simulado_id", "materia"]], on="simulado_id", how="left")
    nota_media = (
        sim_full.dropna(subset=["nota"])
        .groupby(["ano", "materia"], as_index=False)["nota"]
        .mean()
        .rename(columns={"nota": "nota_media_simulados"})
    )

    matr = matriculas.copy()
    matr["concluida_flag"] = (matr["status_matricula"] == "Concluída").astype(int)
    conclusao = (
        matr.groupby(["ano", "materia_declarada"], as_index=False)
        .agg(total_matriculas=("matricula_id", "count"), matriculas_concluidas=("concluida_flag", "sum"))
        .rename(columns={"materia_declarada": "materia"})
    )
    conclusao["taxa_conclusao"] = (conclusao["matriculas_concluidas"] / conclusao["total_matriculas"]).round(4)

    mart = conclusao.merge(nota_media, on=["ano", "materia"], how="left")
    return mart


# ---------------------------------------------------------------------------
# Validacao de integridade (roda a cada execucao do pipeline; falha alto e
# rapido se uma mudanca futura no ETL quebrar uma premissa dos dados)
# ---------------------------------------------------------------------------
def validate_tables(t):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    # chaves primarias unicas
    pk = {
        "estudantes": "aluno_id", "professores": "professor_id", "ofertas_curso": "oferta_id",
        "matriculas": "matricula_id", "aulas": "aula_id", "presencas_aulas": "presenca_id",
        "simulados": "simulado_id", "resultados_simulados": "resultado_id",
        "aprovacoes_vestibular": "aprovacao_id",
    }
    for name, key in pk.items():
        dups = t[name][key].duplicated().sum()
        check(dups == 0, f"{name}.{key} tem {dups} chave(s) duplicada(s)")

    # chaves estrangeiras sem orfaos
    fks = [
        ("matriculas", "aluno_id", "estudantes", "aluno_id"),
        ("matriculas", "oferta_id", "ofertas_curso", "oferta_id"),
        ("ofertas_curso", "professor_id", "professores", "professor_id"),
        ("aulas", "oferta_id", "ofertas_curso", "oferta_id"),
        ("aulas", "professor_id", "professores", "professor_id"),
        ("presencas_aulas", "aula_id", "aulas", "aula_id"),
        ("presencas_aulas", "aluno_id", "estudantes", "aluno_id"),
        ("simulados", "professor_id", "professores", "professor_id"),
        ("resultados_simulados", "simulado_id", "simulados", "simulado_id"),
        ("resultados_simulados", "aluno_id", "estudantes", "aluno_id"),
        ("aprovacoes_vestibular", "aluno_id", "estudantes", "aluno_id"),
    ]
    for tbl, col, ref_tbl, ref_col in fks:
        orphans = (~t[tbl][col].isin(t[ref_tbl][ref_col])).sum()
        check(orphans == 0, f"{tbl}.{col} tem {orphans} valor(es) sem correspondencia em {ref_tbl}.{ref_col}")

    # dominios categoricos: apos o tratamento, so podem existir os valores
    # canonicos esperados (+ "Nao informado"/"Nao registrado" onde aplicavel)
    domains = {
        ("estudantes", "cidade"): set(MAP_CIDADE.values()),
        ("estudantes", "escola_origem"): set(MAP_ESCOLA_ORIGEM.values()) | {"Não informado"},
        ("estudantes", "canal_captacao"): set(MAP_CANAL.values()) | {"Não informado"},
        ("matriculas", "materia_declarada"): set(MAP_MATERIA.values()),
        ("matriculas", "status_matricula"): set(MAP_STATUS_MATRICULA.values()) | {"Não informado"},
        ("presencas_aulas", "status_presenca"): set(MAP_STATUS_PRESENCA.values()) | {"Não registrado"},
        ("resultados_simulados", "status_realizacao"): set(MAP_STATUS_REALIZACAO.values()) | {"Não informado"},
        ("resultados_simulados", "dispositivo"): set(MAP_DISPOSITIVO.values()) | {"Não informado"},
        ("simulados", "dificuldade"): set(MAP_DIFICULDADE.values()) | {"Não informado"},
        ("professores", "status_professor"): set(MAP_STATUS_PROFESSOR.values()),
        ("ofertas_curso", "modalidade"): set(MAP_MODALIDADE.values()),
    }
    for (tbl, col), allowed in domains.items():
        found = set(t[tbl][col].dropna().unique())
        unexpected = found - allowed
        check(not unexpected, f"{tbl}.{col} tem valor(es) fora do dominio esperado: {unexpected}")

    # nota de simulado deve estar em 0-100 (ou nula, quando invalidada)
    nota = t["resultados_simulados"]["nota"]
    check(((nota >= 0) & (nota <= 100) | nota.isna()).all(), "resultados_simulados.nota tem valor fora de 0-100 apos o tratamento")

    # datas: o parser deve ter conseguido converter 100% dos valores nao-nulos originais
    for tbl, col in [("estudantes", "data_nascimento"), ("matriculas", "data_matricula"),
                       ("aulas", "data_aula"), ("resultados_simulados", "inicio_simulado"),
                       ("aprovacoes_vestibular", "data_resultado")]:
        check(t[tbl][col].notna().all(), f"{tbl}.{col} tem data(s) nao reconhecida(s) pelo parser (NaT)")

    if errors:
        raise AssertionError("Validacao de integridade falhou:\n- " + "\n- ".join(errors))
    print(f"Validacao de integridade: OK ({len(pk)} chaves primarias, {len(fks)} FKs, "
          f"{len(domains)} dominios categoricos checados)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    estudantes = clean_estudantes()
    professores = clean_professores()
    ofertas = clean_ofertas()
    matriculas = clean_matriculas()
    aulas = clean_aulas()
    presencas = clean_presencas()
    simulados = clean_simulados()
    resultados = clean_resultados_simulados()
    aprovacoes = clean_aprovacoes()

    mart_aluno_ano = build_mart_aluno_ano(estudantes, matriculas, presencas, aulas, aprovacoes)
    mart_curso_materia = build_mart_curso_materia(ofertas, matriculas, resultados, simulados, aprovacoes)

    tables = {
        "estudantes": estudantes,
        "professores": professores,
        "ofertas_curso": ofertas,
        "matriculas": matriculas,
        "aulas": aulas,
        "presencas_aulas": presencas,
        "simulados": simulados,
        "resultados_simulados": resultados,
        "aprovacoes_vestibular": aprovacoes,
        "mart_aluno_ano": mart_aluno_ano,
        "mart_curso_materia": mart_curso_materia,
    }

    validate_tables(tables)

    for name, df in tables.items():
        df.to_csv(os.path.join(PROCESSED_DIR, f"{name}.csv"), index=False, encoding="utf-8-sig")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    for name, df in tables.items():
        df.to_sql(name, conn, index=False)
    conn.close()

    print("ETL concluido. Tabelas geradas:")
    for name, df in tables.items():
        print(f"  - {name}: {df.shape[0]} linhas, {df.shape[1]} colunas")
    print(f"\nCSV tratados em: {PROCESSED_DIR}")
    print(f"Banco SQLite em: {DB_PATH}")


if __name__ == "__main__":
    main()
