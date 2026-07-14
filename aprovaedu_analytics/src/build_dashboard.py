# -*- coding: utf-8 -*-
"""
Dashboard - AprovaEdu Analytics
================================
Gera um dashboard HTML interativo (outputs/dashboard.html) a partir do
resumo de indicadores calculado por src/analysis.py. O arquivo é
autocontido (dados embutidos) e usa Chart.js via CDN — basta abrir no
navegador, sem servidor.

Como rodar (depois de etl.py e analysis.py):
    python src/build_dashboard.py
"""

import os
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IND_PATH = os.path.join(BASE_DIR, "outputs", "resumo_indicadores.json")
OUT_PATH = os.path.join(BASE_DIR, "outputs", "dashboard.html")

with open(IND_PATH, encoding="utf-8") as f:
    IND = json.load(f)

TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AprovaEdu Analytics — Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root { --azul:#2E5FA3; --laranja:#E27D60; --verde:#3B8C6E; --cinza:#6b7280; }
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; margin:0; background:#f4f6fa; color:#1f2937; }
  header { background:var(--azul); color:#fff; padding:22px 32px; }
  header h1 { margin:0; font-size:1.35rem; font-weight:600; }
  header p { margin:6px 0 0; opacity:.85; font-size:.9rem; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:18px; padding:24px 32px; max-width:1300px; margin:0 auto; }
  .card { background:#fff; border-radius:10px; padding:18px 20px; box-shadow:0 1px 4px rgba(0,0,0,.08); }
  .card h2 { margin:0 0 4px; font-size:1rem; color:var(--azul); }
  .card p.sub { margin:0 0 12px; font-size:.8rem; color:var(--cinza); }
  .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:14px; padding:20px 32px 0; max-width:1300px; margin:0 auto; }
  .kpi { background:#fff; border-radius:10px; padding:14px 18px; box-shadow:0 1px 4px rgba(0,0,0,.08); border-left:4px solid var(--azul); }
  .kpi.alt { border-left-color:var(--laranja); }
  .kpi.ok { border-left-color:var(--verde); }
  .kpi .v { font-size:1.6rem; font-weight:700; }
  .kpi .l { font-size:.78rem; color:var(--cinza); margin-top:2px; }
  footer { padding:14px 32px 28px; font-size:.78rem; color:var(--cinza); max-width:1300px; margin:0 auto; }
  canvas { max-height:320px; }
</style>
</head>
<body>
<header>
  <h1>AprovaEdu Analytics — Rede de Cursinhos Pré-Vestibular (2021–2025)</h1>
  <p>Dashboard gerado automaticamente pelo pipeline (src/build_dashboard.py). Dados fictícios do desafio técnico.</p>
</header>

<div class="kpis">
  <div class="kpi"><div class="v">__KPI_APROV__</div><div class="l">Aprovações únicas (2021–2025)</div></div>
  <div class="kpi ok"><div class="v">__KPI_CRESC__</div><div class="l">Crescimento de aprovados 2022 → 2023</div></div>
  <div class="kpi alt"><div class="v">__KPI_INGLES__</div><div class="l">Taxa de conclusão em Inglês (menor da rede)</div></div>
  <div class="kpi"><div class="v">__KPI_PRES__</div><div class="l">Presença média: aprovados vs demais</div></div>
</div>

<div class="grid">
  <div class="card">
    <h2>Aprovados por ano</h2>
    <p class="sub">Base de Aprovações completa (sem amostragem)</p>
    <canvas id="chAno"></canvas>
  </div>
  <div class="card">
    <h2>Nota final média no vestibular</h2>
    <p class="sub">Qualidade das aprovações, por ano</p>
    <canvas id="chNota"></canvas>
  </div>
  <div class="card">
    <h2>Taxa de conclusão por matéria</h2>
    <p class="sub">Amostra de 500 matrículas — Inglês em destaque</p>
    <canvas id="chConclusao"></canvas>
  </div>
  <div class="card">
    <h2>Nota de diagnóstico por matéria</h2>
    <p class="sub">Nível de entrada dos alunos (0–100)</p>
    <canvas id="chDiag"></canvas>
  </div>
  <div class="card">
    <h2>Aprovações por universidade</h2>
    <p class="sub">Total 2021–2025</p>
    <canvas id="chUni"></canvas>
  </div>
  <div class="card">
    <h2>Canal de captação dos estudantes</h2>
    <p class="sub">Amostra de 500 estudantes</p>
    <canvas id="chCanal"></canvas>
  </div>
</div>

<footer>
  Limitações de amostragem: 5 das 9 tabelas fornecidas são amostras parciais e independentes —
  ver README.md e relatorio_final.md para o detalhamento da confiança de cada indicador.
</footer>

<script>
const IND = __DATA__;
const AZUL='#2E5FA3', LARANJA='#E27D60', VERDE='#3B8C6E';
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.plugins.legend.display = false;

// Aprovados por ano
const q1 = IND.q1_aprovacoes_por_ano;
new Chart(chAno, { type:'bar',
  data:{ labels:q1.map(r=>r.ano), datasets:[{ data:q1.map(r=>r.alunos_aprovados), backgroundColor:AZUL, borderRadius:6 }] },
  options:{ scales:{ y:{ beginAtZero:true } } } });

// Nota final média
const nf = IND.q1_nota_final_media_por_ano;
new Chart(chNota, { type:'line',
  data:{ labels:Object.keys(nf), datasets:[{ data:Object.values(nf), borderColor:LARANJA, backgroundColor:LARANJA, tension:.3, pointRadius:5 }] },
  options:{ scales:{ y:{ suggestedMin:650, suggestedMax:800 } } } });

// Conclusão por matéria
const q3 = [...IND.q3_por_materia_matriculas].sort((a,b)=>a.taxa_conclusao-b.taxa_conclusao);
new Chart(chConclusao, { type:'bar',
  data:{ labels:q3.map(r=>r.materia_declarada),
         datasets:[{ data:q3.map(r=>+(r.taxa_conclusao*100).toFixed(1)),
                     backgroundColor:q3.map(r=>r.materia_declarada==='Inglês'?LARANJA:AZUL), borderRadius:5 }] },
  options:{ indexAxis:'y', scales:{ x:{ max:100, title:{display:true,text:'% concluídas'} } } } });

// Diagnóstico por matéria
const qd = [...IND.q3_por_materia_matriculas].sort((a,b)=>a.nota_diagnostico_media-b.nota_diagnostico_media);
new Chart(chDiag, { type:'bar',
  data:{ labels:qd.map(r=>r.materia_declarada),
         datasets:[{ data:qd.map(r=>+r.nota_diagnostico_media.toFixed(1)), backgroundColor:AZUL, borderRadius:5 }] },
  options:{ indexAxis:'y', scales:{ x:{ min:0, max:70 } } } });

// Universidades
const uni = IND.analises_adicionais.aprovacoes_por_universidade;
new Chart(chUni, { type:'bar',
  data:{ labels:Object.keys(uni), datasets:[{ data:Object.values(uni), backgroundColor:AZUL, borderRadius:5 }] },
  options:{ indexAxis:'y' } });

// Canal de captação
const canal = IND.analises_adicionais.canal_captacao_estudantes;
new Chart(chCanal, { type:'doughnut',
  data:{ labels:Object.keys(canal),
         datasets:[{ data:Object.values(canal),
                     backgroundColor:[AZUL,VERDE,'#9ca3af',LARANJA,'#7c5cbf','#c9a227'] }] },
  options:{ plugins:{ legend:{ display:true, position:'right' } } } });
</script>
</body>
</html>
"""


def fmt_kpis(ind):
    q1 = ind["q1_aprovacoes_por_ano"]
    total = sum(r["alunos_aprovados"] for r in q1)
    cresc = next(r["variacao_pct"] for r in q1 if r["ano"] == 2023)
    ingles = next(
        r["taxa_conclusao"] for r in ind["q3_por_materia_matriculas"]
        if r["materia_declarada"] == "Inglês"
    )
    p = {r["grupo"]: r["mean"] for r in ind["q2_presenca_por_grupo"]}
    pres = f"{p['Aprovados']*100:.0f}% vs {p['Sem registro de aprovação']*100:.0f}%"
    return {
        "__KPI_APROV__": str(total),
        "__KPI_CRESC__": f"+{cresc:.0f}%",
        "__KPI_INGLES__": f"{ingles*100:.0f}%",
        "__KPI_PRES__": pres,
    }


def main():
    html = TEMPLATE.replace("__DATA__", json.dumps(IND, ensure_ascii=False))
    for k, v in fmt_kpis(IND).items():
        html = html.replace(k, v)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print("Dashboard salvo em:", OUT_PATH)


if __name__ == "__main__":
    main()
