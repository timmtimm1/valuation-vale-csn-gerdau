"""O modelo em JavaScript da página tem de dar o mesmo resultado que o Python."""

import json
import shutil
import subprocess

import pytest

from valuation import modelo, premissas, site
from valuation.empresas import FOCO, SITE

RODAR = """
const M = require(process.argv.at(-1));
const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const proj = M.projetar(d.base, d.premissas, d.anos);
console.log(JSON.stringify({
  proj, v: M.avaliar(d.base, proj, d.premissas), s: M.sensibilidade(d.base, proj, d.premissas),
}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="precisa do Node")
@pytest.mark.parametrize("ticker", [e.ticker for e in FOCO])
def test_javascript_bate_com_python(ticker: str) -> None:
    entrada = site._empresa(ticker)
    saida = subprocess.run(
        ["node", "-e", RODAR, str(SITE / "modelo.js")],
        input=json.dumps(entrada),
        capture_output=True,
        text=True,
        check=True,
    )
    js = json.loads(saida.stdout)

    r = modelo.rodar(ticker, premissas.carregar(ticker))
    for linha in r["projecao"].index:
        assert js["proj"][linha] == pytest.approx(
            list(r["projecao"].loc[linha]), rel=1e-9, abs=1e-6
        )
    for chave, valor in r["valuation"].items():
        assert js["v"][chave] == pytest.approx(valor, rel=1e-9)
    grade = modelo.sensibilidade(r["base"], r["projecao"], r["premissas"])
    achatado = [preco for linha in js["s"]["precos"] for preco in linha]
    assert achatado == pytest.approx(grade.to_numpy().ravel().tolist(), rel=1e-9)
