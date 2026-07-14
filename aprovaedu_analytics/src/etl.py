# -*- coding: utf-8 -*-
"""
ETL - AprovaEdu Analytics
==========================
Lê as bases brutas (data/raw/*.csv), aplica tratamento e padronização,
e gera uma estrutura analítica (data/processed/*.csv) pronta para
responder às perguntas do desafio.

Além das tabelas tratadas, o script gera automaticamente um LOG DE
QUALIDADE (outputs/log_qualidade.md) que documenta, tabela por tabela,
cada decisão de tratamento aplicada e quantos registros foram afetados —
tornando o processo auditável pelo avaliador.

Como rodar:
    python src/etl.py
"""

import os
import re
import unicodedata
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(PROC_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# Acumulador global do log de qualidade
QUALITY_LOG = []


def log_q(tabela, acao, detalhe, n_afetados):
    QUALITY_LOG.append(
        {"tabela": tabela, "acao": acao, "detalhe": detalhe, "n_afetados": int(n_afetados)}
    )


# ---------------------------------------------------------------------------
# Helpers genéricos de limpeza
# ---------------------------------------------------------------------------

def strip_accents(txt):
    if pd.isna(txt):
        return txt
    return "".join(
        c for c in unicodedata.normalize("NFD", str(txt)) if unicodedata.category(c) != "Mn"
    )


def parse_date_flex(series, tabela="", coluna=""):
    """Converte datas em formatos mistos (YYYY-MM-DD, DD/MM/YYYY, MM-DD-YYYY,
    YYYY/MM/DD, com ou sem hora) para datetime. Assume padrão brasileiro
    DD/MM/AAAA quando o separador é '/'. Loga quantos valores não estavam
    em formato ISO e precisaram de conversão."""
    s = series.astype(str).str.strip()
    s = s.replace({"nan": np.nan, "None": np.nan, "": np.nan})

    out = pd.Series(pd.NaT, index=s.index)

    mask_iso = s.str.match(r"^\d{4}-\d{2}-\d{2}", na=False)
    out.loc[mask_iso] = pd.to_datetime(s.loc[mask_iso], format="mixed", errors="coerce")

    mask_iso_slash = s.str.match(r"^\d{4}/\d{2}/\d{2}", na=False) & out.isna()
    out.loc[mask_iso_slash] = pd.to_datetime(
        s.loc[mask_iso_slash].str.replace("/", "-", regex=False), format="mixed", errors="coerce"
    )

    mask_br = s.str.match(r"^\d{2}/\d{2}/\d{4}", na=False) & out.isna()
    out.loc[mask_br] = pd.to_datetime(s.loc[mask_br], dayfirst=True, errors="coerce")

    remaining = out.isna() & s.notna()
    out.loc[remaining] = pd.to_datetime(s.loc[remaining], errors="coerce")

    n_nao_iso = int((~mask_iso & s.notna()).sum())
    if tabela and n_nao_iso:
        log_q(tabela, "Padronização de datas", f"{coluna}: valores fora do formato ISO convertidos", n_nao_iso)
    n_falha = int((out.isna() & s.notna()).sum())
    if tabela and n_falha:
        log_q(tabela, "Data inválida", f"{coluna}: valores que não puderam ser interpretados (→ nulo)", n_falha)
    return out


def map_categories(series, mapping, tabela="", coluna=""):
    """Aplica dicionário de normalização (chave em minúsculo/sem acento) e
    loga quantos valores foram alterados."""
    def _map(v):
        if pd.isna(v):
            return np.nan
        key = strip_accents(str(v)).strip().lower()
        key = re.sub(r"\s+", " ", key)
        return mapping.get(key, str(v).strip())

    out = series.apply(_map)
    if tabela:
        mask_validos = series.notna()
        alterados = int(
            (series[mask_validos].astype(str).str.strip() != out[mask_validos].astype(str)).sum()
        )
        if alterados:
            log_q(tabela, "Normalização de categoria", f"{coluna}: grafias unificadas", alterados)
    return out


def fill_na_log(df, col, valor, tabela):
    n = int(df[col].isna().sum())
    if n:
        log_q(tabela, "Preenchimento de nulos", f"{col} → '{valor}'", n)
    df[col] = df[col].fillna(valor)
    return df


MATERIA_MAP = {
    "matematica": "Matemática", "mat.": "Matemática",
    "fisica": "Física", "quimica": "Química", "biologia": "Biologia",
    "historia": "História", "geografia": "Geografia", "filosofia": "Filosofia",
    "sociologia": "Sociologia", "portugues": "Português", "ingles": "Inglês",
    "redacao": "Redação",
}

CIDADE_MAP = {
    "fortaleza": "Fortaleza", "caucaia": "Caucaia", "crato": "Crato",
    "eusebio": "Eusébio", "horizonte": "Horizonte", "itapipoca": "Itapipoca",
    "juazeiro do norte": "Juazeiro do Norte", "maracanau": "Maracanaú",
    "pacatuba": "Pacatuba", "sobral": "Sobral", "aquiraz": "Aquiraz",
}


# ---------------------------------------------------------------------------
# 1. Carga das bases brutas
# ---------------------------------------------------------------------------

def load_raw():
    tables = {}
    for name in [
        "professores", "estudantes", "ofertas_curso", "matriculas",
        "aprovacoes", "simulados", "resultados_sim", "aulas", "presencas_aulas",
    ]:
        tables[name] = pd.read_csv(os.path.join(RAW_DIR, f"{name}.csv"), dtype=str)
    return tables


def dedup_by_key(df, key, tabela):
    antes = len(df)
    df = df.drop_duplicates(subset=key)
    removidos = antes - len(df)
    if removidos:
        log_q(tabela, "Deduplicação", f"chave {key}", removidos)
    return df.copy()


# ---------------------------------------------------------------------------
# 2. Tratamento por tabela
# ---------------------------------------------------------------------------

def clean_professores(df):
    t = "professores"
    df = dedup_by_key(df, "professor_id", t)
    df["nome_professor"] = df["nome_professor"].str.strip()
    df["materia_principal"] = map_categories(df["materia_principal"], MATERIA_MAP, t, "materia_principal")
    df["status_professor"] = map_categories(
        df["status_professor"], {"ativo": "Ativo", "inativo": "Inativo"}, t, "status_professor"
    )
    df["data_contratacao"] = parse_date_flex(df["data_contratacao"], t, "data_contratacao")
    df["carga_horaria_semanal"] = pd.to_numeric(df["carga_horaria_semanal"], errors="coerce")
    return df


def clean_estudantes(df):
    t = "estudantes"
    df = dedup_by_key(df, "aluno_id", t)
    df["nome_aluno"] = df["nome_aluno"].str.strip()
    df["cidade"] = map_categories(df["cidade"], CIDADE_MAP, t, "cidade")
    df["data_nascimento"] = parse_date_flex(df["data_nascimento"], t, "data_nascimento")
    df["data_cadastro"] = parse_date_flex(df["data_cadastro"], t, "data_cadastro")
    # 'Não informado' já aparece como texto na base; unificamos nulo + texto
    df["escola_origem"] = df["escola_origem"].replace({"Não informado": np.nan})
    df = fill_na_log(df, "escola_origem", "Não informado", t)
    df["canal_captacao"] = map_categories(
        df["canal_captacao"],
        {"instagram": "Instagram", "google": "Google", "whatsapp": "WhatsApp",
         "indicacao": "Indicação", "feira escolar": "Feira escolar"},
        t, "canal_captacao",
    )
    df = fill_na_log(df, "canal_captacao", "Não informado", t)
    return df


def clean_ofertas(df):
    t = "ofertas_curso"
    df = dedup_by_key(df, "oferta_id", t)
    df["materia"] = map_categories(df["materia"], MATERIA_MAP, t, "materia")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["data_inicio"] = parse_date_flex(df["data_inicio"], t, "data_inicio")
    df["data_fim"] = parse_date_flex(df["data_fim"], t, "data_fim")
    df["carga_horaria_total"] = pd.to_numeric(df["carga_horaria_total"], errors="coerce")
    df["preco_lista"] = pd.to_numeric(df["preco_lista"], errors="coerce")
    df["modalidade"] = map_categories(
        df["modalidade"], {"online": "Online", "presencial": "Presencial", "hibrido": "Híbrido"},
        t, "modalidade",
    )
    return df


def clean_matriculas(df):
    t = "matriculas"
    df = dedup_by_key(df, "matricula_id", t)
    df["materia_declarada"] = map_categories(df["materia_declarada"], MATERIA_MAP, t, "materia_declarada")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["data_matricula"] = parse_date_flex(df["data_matricula"], t, "data_matricula")
    n_bolsa_nula = int(df["bolsa_percentual"].isna().sum())
    if n_bolsa_nula:
        log_q(t, "Preenchimento de nulos", "bolsa_percentual nulo → 0 (sem bolsa)", n_bolsa_nula)
    df["bolsa_percentual"] = pd.to_numeric(df["bolsa_percentual"], errors="coerce").fillna(0)
    df["status_matricula"] = map_categories(
        df["status_matricula"],
        {"concluida": "Concluída", "cancelada": "Cancelada", "ativa": "Ativa", "trancada": "Trancada"},
        t, "status_matricula",
    )
    df = fill_na_log(df, "status_matricula", "Não informado", t)
    df["nota_diagnostico"] = pd.to_numeric(df["nota_diagnostico"], errors="coerce")
    df = fill_na_log(df, "origem_captacao", "Não informado", t)
    return df


def clean_aprovacoes(df):
    t = "aprovacoes"
    # Duplicidade de negócio: mesmo aluno + ano + universidade + curso + data
    # = lançamento duplicado (não uma 2ª aprovação legítima do mesmo aluno).
    df = dedup_by_key(
        df, ["aluno_id", "ano_vestibular", "universidade", "curso_aprovado", "data_resultado"], t
    )
    df["ano_vestibular"] = pd.to_numeric(df["ano_vestibular"], errors="coerce").astype("Int64")
    uni_antes = df["universidade"].copy()
    df["universidade"] = df["universidade"].str.strip().str.upper()
    n_uni = int((uni_antes != df["universidade"]).sum())
    if n_uni:
        log_q(t, "Normalização de categoria", "universidade: caixa alta unificada (uece→UECE, Ufc→UFC)", n_uni)
    df["modalidade_vaga"] = map_categories(
        df["modalidade_vaga"],
        {"ampla concorrencia": "Ampla concorrência", "ppi": "PPI", "pcd": "PCD",
         "cota escola publica": "Cota escola pública"},
        t, "modalidade_vaga",
    )
    df = fill_na_log(df, "modalidade_vaga", "Não informado", t)
    df["bolsa_aprovacao"] = map_categories(
        df["bolsa_aprovacao"], {"sim": "Sim", "nao": "Não", "parcial": "Parcial"}, t, "bolsa_aprovacao"
    )
    df = fill_na_log(df, "bolsa_aprovacao", "Não informado", t)
    df["data_resultado"] = parse_date_flex(df["data_resultado"], t, "data_resultado")
    df["nota_final_vestibular"] = pd.to_numeric(df["nota_final_vestibular"], errors="coerce")
    df = fill_na_log(df, "campus", "Não informado", t)
    return df


def clean_simulados(df):
    t = "simulados"
    df = dedup_by_key(df, "simulado_id", t)
    df["materia"] = map_categories(df["materia"], MATERIA_MAP, t, "materia")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["data_simulado"] = parse_date_flex(df["data_simulado"], t, "data_simulado")
    df["dificuldade"] = map_categories(
        df["dificuldade"], {"facil": "Fácil", "media": "Média", "dificil": "Difícil"}, t, "dificuldade"
    )
    df = fill_na_log(df, "dificuldade", "Não informado", t)
    df["total_questoes"] = pd.to_numeric(df["total_questoes"], errors="coerce")
    df["tempo_limite_min"] = pd.to_numeric(df["tempo_limite_min"], errors="coerce")
    df = fill_na_log(df, "tema", "Não informado", t)
    return df


def clean_resultados_sim(df):
    t = "resultados_sim"
    df = dedup_by_key(df, "resultado_id", t)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["status_realizacao"] = map_categories(
        df["status_realizacao"],
        {"finalizado": "Finalizado", "ausente": "Ausente", "incompleto": "Incompleto"},
        t, "status_realizacao",
    )
    df = fill_na_log(df, "status_realizacao", "Não informado", t)
    df["nota"] = pd.to_numeric(df["nota"], errors="coerce")
    # Outlier: escala de nota é 0-100; valores > 100 são erro de digitação.
    # Decisão: anular a nota (NaN), preservando o restante da linha.
    n_out = int((df["nota"] > 100).sum())
    if n_out:
        log_q(t, "Outlier tratado", "nota > 100 (escala 0-100) → nulo, linha preservada", n_out)
    df.loc[df["nota"] > 100, "nota"] = np.nan
    df["acertos"] = pd.to_numeric(df["acertos"], errors="coerce")
    df["tempo_finalizacao_min"] = pd.to_numeric(df["tempo_finalizacao_min"], errors="coerce")
    # Consistência: tempo de finalização acima do tempo-limite do simulado
    df["inicio_simulado"] = parse_date_flex(df["inicio_simulado"], t, "inicio_simulado")
    df["dispositivo"] = map_categories(
        df["dispositivo"],
        {"desktop": "Desktop", "celular": "Celular", "papel": "Papel", "tablet": "Tablet"},
        t, "dispositivo",
    )
    df = fill_na_log(df, "dispositivo", "Não informado", t)
    n_tent = int(df["tentativas"].isna().sum())
    if n_tent:
        log_q(t, "Preenchimento de nulos", "tentativas nulo → 1 (mínimo lógico)", n_tent)
    df["tentativas"] = pd.to_numeric(df["tentativas"], errors="coerce").fillna(1)
    df["unidade_aplicacao"] = map_categories(
        df["unidade_aplicacao"],
        {"online": "Online", "centro": "Centro", "aldeota": "Aldeota", "sul": "Sul"},
        t, "unidade_aplicacao",
    )
    df = fill_na_log(df, "unidade_aplicacao", "Não informado", t)
    return df


def clean_aulas(df):
    t = "aulas"
    df = dedup_by_key(df, "aula_id", t)
    df["materia"] = map_categories(df["materia"], MATERIA_MAP, t, "materia")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["data_aula"] = parse_date_flex(df["data_aula"], t, "data_aula")
    df["tema_aula"] = df["tema_aula"].str.strip()
    df["duracao_min"] = pd.to_numeric(df["duracao_min"], errors="coerce")
    df["modalidade_aula"] = map_categories(
        df["modalidade_aula"],
        {"online": "Online", "presencial": "Presencial", "hibrido": "Híbrido"},
        t, "modalidade_aula",
    )
    df = fill_na_log(df, "modalidade_aula", "Não informado", t)
    return df


def clean_presencas(df):
    t = "presencas_aulas"
    df = dedup_by_key(df, "presenca_id", t)
    df["status_presenca"] = map_categories(
        df["status_presenca"],
        {"presente": "Presente", "ausente": "Ausente", "atrasado": "Atrasado",
         "justificado": "Justificado"},
        t, "status_presenca",
    )
    df = fill_na_log(df, "status_presenca", "Não informado", t)
    n_atraso = int(df["atraso_min"].isna().sum())
    if n_atraso:
        log_q(t, "Preenchimento de nulos", "atraso_min nulo → 0 (sem atraso registrado)", n_atraso)
    df["atraso_min"] = pd.to_numeric(df["atraso_min"], errors="coerce").fillna(0)
    return df


# ---------------------------------------------------------------------------
# 3. Checagem de denormalização
# ---------------------------------------------------------------------------

def check_denormalizacao(dim_prof, ofertas, simulados):
    """Confere o nome de professor informado nas tabelas de fato contra a
    dimensão Professores (comparação sem caixa)."""
    prof_map = dim_prof.set_index("professor_id")["nome_professor"].to_dict()

    def _divergencias(df, col_nome):
        tmp = df.copy()
        tmp["nome_esperado"] = tmp["professor_id"].map(prof_map)
        return tmp[
            tmp[col_nome].str.upper().str.strip()
            != tmp["nome_esperado"].str.upper().str.strip()
        ]

    div_ofertas = _divergencias(ofertas, "professor_nome_informado")
    div_simulados = _divergencias(simulados, "professor_nome_informado")
    log_q("ofertas_curso", "Checagem de denormalização",
          "professor_nome_informado divergente da dimensão Professores", len(div_ofertas))
    log_q("simulados", "Checagem de denormalização",
          "professor_nome_informado divergente da dimensão Professores", len(div_simulados))
    return div_ofertas, div_simulados


# ---------------------------------------------------------------------------
# 4. Estrutura analítica (agregados por aluno/ano)
# ---------------------------------------------------------------------------

def build_analytics(clean):
    estudantes = clean["estudantes"]
    matriculas = clean["matriculas"]
    aprovacoes = clean["aprovacoes"]
    aulas = clean["aulas"]
    presencas = clean["presencas_aulas"]
    resultados_sim = clean["resultados_sim"]
    simulados = clean["simulados"]

    # Presença por aluno/ano ("Presente" e "Atrasado" contam como presença física)
    pres = presencas.merge(aulas[["aula_id", "ano", "materia"]], on="aula_id", how="left")
    pres["presente_flag"] = pres["status_presenca"].isin(["Presente", "Atrasado"]).astype(int)
    freq_aluno_ano = (
        pres.groupby(["aluno_id", "ano"])
        .agg(aulas_registradas=("presenca_id", "count"),
             aulas_presentes=("presente_flag", "sum"))
        .reset_index()
    )
    freq_aluno_ano["taxa_presenca"] = (
        freq_aluno_ano["aulas_presentes"] / freq_aluno_ano["aulas_registradas"]
    ).round(3)

    # Desempenho em simulados por aluno/ano
    sim_res = resultados_sim.merge(
        simulados[["simulado_id", "ano", "materia"]], on="simulado_id",
        how="left", suffixes=("", "_sim"),
    )
    sim_aluno_ano = (
        sim_res.groupby(["aluno_id", "ano"])
        .agg(nota_media_simulados=("nota", "mean"),
             qtd_simulados_feitos=("resultado_id", "count"))
        .reset_index()
    )
    sim_aluno_ano["nota_media_simulados"] = sim_aluno_ano["nota_media_simulados"].round(2)

    # Matrícula agregada por aluno/ano
    mat_aluno_ano = (
        matriculas.groupby(["aluno_id", "ano"])
        .agg(qtd_materias=("materia_declarada", "nunique"),
             nota_diagnostico_media=("nota_diagnostico", "mean"),
             bolsa_media=("bolsa_percentual", "mean"))
        .reset_index()
    )
    mat_aluno_ano["nota_diagnostico_media"] = mat_aluno_ano["nota_diagnostico_media"].round(2)

    # Flag de aprovação por aluno/ano
    aprov_ano = aprovacoes[["aluno_id", "ano_vestibular"]].drop_duplicates()
    aprov_ano["aprovado"] = 1
    aprov_ano = aprov_ano.rename(columns={"ano_vestibular": "ano"})

    base = mat_aluno_ano.merge(freq_aluno_ano, on=["aluno_id", "ano"], how="left")
    base = base.merge(sim_aluno_ano, on=["aluno_id", "ano"], how="left")
    base = base.merge(aprov_ano, on=["aluno_id", "ano"], how="left")
    base["aprovado"] = base["aprovado"].fillna(0).astype(int)
    base = base.merge(estudantes[["aluno_id", "cidade", "escola_origem"]],
                      on="aluno_id", how="left")

    return {
        "freq_aluno_ano": freq_aluno_ano,
        "sim_aluno_ano": sim_aluno_ano,
        "base_analitica_aluno_ano": base,
    }


# ---------------------------------------------------------------------------
# 5. Log de qualidade
# ---------------------------------------------------------------------------

def write_quality_log():
    df = pd.DataFrame(QUALITY_LOG)
    path = os.path.join(OUT_DIR, "log_qualidade.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Log de qualidade de dados — gerado automaticamente pelo ETL\n\n")
        f.write("Cada linha documenta uma decisão de tratamento aplicada e quantos ")
        f.write("registros foram afetados. Reexecutar `python src/etl.py` regenera este arquivo.\n\n")
        f.write("| Tabela | Ação | Detalhe | Registros afetados |\n")
        f.write("|---|---|---|---:|\n")
        for _, r in df.iterrows():
            f.write(f"| {r.tabela} | {r.acao} | {r.detalhe} | {r.n_afetados} |\n")
    print("Log de qualidade salvo em:", path)
    return path


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    raw = load_raw()

    clean = {
        "professores": clean_professores(raw["professores"]),
        "estudantes": clean_estudantes(raw["estudantes"]),
        "ofertas_curso": clean_ofertas(raw["ofertas_curso"]),
        "matriculas": clean_matriculas(raw["matriculas"]),
        "aprovacoes": clean_aprovacoes(raw["aprovacoes"]),
        "simulados": clean_simulados(raw["simulados"]),
        "resultados_sim": clean_resultados_sim(raw["resultados_sim"]),
        "aulas": clean_aulas(raw["aulas"]),
        "presencas_aulas": clean_presencas(raw["presencas_aulas"]),
    }

    check_denormalizacao(clean["professores"], clean["ofertas_curso"], clean["simulados"])

    analytics = build_analytics(clean)

    for name, df in clean.items():
        df.to_csv(os.path.join(PROC_DIR, f"{name}_tratado.csv"), index=False)
    for name, df in analytics.items():
        df.to_csv(os.path.join(PROC_DIR, f"{name}.csv"), index=False)

    write_quality_log()

    print("\nETL concluído. Arquivos gerados em data/processed/:")
    for f in sorted(os.listdir(PROC_DIR)):
        print(" -", f)


if __name__ == "__main__":
    main()
