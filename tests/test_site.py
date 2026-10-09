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
