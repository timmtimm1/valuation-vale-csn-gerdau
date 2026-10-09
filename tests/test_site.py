"""O modelo em JavaScript da página tem de dar o mesmo resultado que o Python."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from valuation import modelo, premissas, site
from valuation.empresas import FOCO, REPOSITORIO, SITE

RODAR = """
const M = require(process.argv.at(-1));
const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const saida = d.simulacoes.map(([cenario, manual]) => {
  const p = M.premissas(d, { ...M.doCenario(d, cenario), ...manual });
  const proj = M.projetar(d.base, p, d.anos);
  return { proj, v: M.avaliar(d.base, proj, p), s: M.sensibilidade(d.base, proj, p) };
});
console.log(JSON.stringify(saida));
"""

# Os três cenários, um ajuste manual dentro da faixa e um fora, que tem de ficar preso.
SIMULACOES: list[tuple[str, dict[str, float]]] = [
    ("pessimista", {}),
    ("moderado", {}),
    ("otimista", {}),
    ("moderado", {"crescimento_receita": 0.02, "ajuste_wacc": 0.005}),
    ("pessimista", {"margem_ebitda": 0.99}),
]


@pytest.mark.skipif(shutil.which("node") is None, reason="precisa do Node")
@pytest.mark.parametrize("ticker", [e.ticker for e in FOCO])
def test_javascript_bate_com_python(ticker: str) -> None:
    entrada = site._empresa(ticker) | {"simulacoes": SIMULACOES}
    saida = subprocess.run(
        ["node", "-e", RODAR, str(SITE / "modelo.js")],
        input=json.dumps(entrada),
        capture_output=True,
        text=True,
        check=True,
    )
    dados = premissas.carregar(ticker)
    for (cenario, manual), js in zip(SIMULACOES, json.loads(saida.stdout), strict=True):
        r = modelo.rodar(ticker, dados, cenario, manual)
        for linha in r["projecao"].index:
            esperado = list(r["projecao"].loc[linha])
            assert js["proj"][linha] == pytest.approx(esperado, rel=1e-9, abs=1e-6)
        for chave, valor in r["valuation"].items():
            assert js["v"][chave] == pytest.approx(valor, rel=1e-9)
        grade = modelo.sensibilidade(r["base"], r["projecao"], r["premissas"])
        achatado = [preco for linha in js["s"]["precos"] for preco in linha]
        assert achatado == pytest.approx(grade.to_numpy().ravel().tolist(), rel=1e-9)


def test_links_publicos_ficam_so_na_pagina_completa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for nome in ("pagina.html", "modelo.js"):
        shutil.copy(SITE / nome, tmp_path / nome)
    monkeypatch.setattr(site, "SITE", tmp_path)
    pagina = site.construir().read_text(encoding="utf-8")
    artefato = (tmp_path / "artefato.html").read_text(encoding="utf-8")
    planilha = f"{REPOSITORIO}/raw/main/saida/valuation_vale_csn_gerdau.xlsx"
    assert f'href="{planilha}"' in pagina
    assert f'href="{REPOSITORIO}/blob/main/FONTES.md"' in pagina
    assert REPOSITORIO not in artefato
    assert site.LIGACOES not in pagina + artefato


def test_pagina_mostra_a_analise_do_leiame(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for nome in ("pagina.html", "modelo.js"):
        shutil.copy(SITE / nome, tmp_path / nome)
    monkeypatch.setattr(site, "SITE", tmp_path)
    pagina = site.construir().read_text(encoding="utf-8")
    artefato = (tmp_path / "artefato.html").read_text(encoding="utf-8")
    leiame = site.LEIAME.read_text(encoding="utf-8")
    for texto in (pagina, artefato):
        # O resumo com a tabela vem antes das abas; a análise completa, no fim.
        assert texto.index('<div class="rolagem"><table>') < texto.index('id="abas"')
        assert texto.index("Por que a Vale se destaca") > texto.index('id="sensibilidade"')
        assert "Isto não é recomendação de investimento" in texto
        assert "ersão de trabalho" not in texto
        assert not any(marca in texto for marca in site.TRECHOS)
    # Cada parágrafo da análise no README aparece na página, sem os marcadores.
    analise = leiame.split("<!-- analise:inicio -->")[1].split("<!-- analise:fim -->")[0]
    for paragrafo in analise.split("\n\n"):
        linha = " ".join(paragrafo.split())
        if linha and not linha.startswith(("#", "-")):
            assert linha in " ".join(pagina.split()), linha[:60]
