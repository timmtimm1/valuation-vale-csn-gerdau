"""Propriedades que o modelo tem de respeitar com qualquer premissa."""

import pytest

from valuation import modelo, premissas
from valuation.empresas import FOCO

TICKERS = [e.ticker for e in FOCO]


@pytest.fixture(scope="module", params=TICKERS)
def rodada(request: pytest.FixtureRequest) -> dict:
    ticker = request.param
    dados = premissas.carregar(ticker)
    return {"ticker": ticker, "dados": dados, **modelo.rodar(ticker, dados)}


def test_balanco_fecha_em_todos_os_anos(rodada: dict) -> None:
    assert rodada["projecao"].loc["checagem_balanco"].abs().max() < 1e-6


def test_caixa_anda_pelo_fluxo_do_acionista_menos_dividendos(rodada: dict) -> None:
    proj, base = rodada["projecao"], rodada["base"]
    caixa_final = base.ano["caixa_total"] + (proj.loc["fcfe"] - proj.loc["dividendos"]).sum()
    assert proj.loc["caixa_total"].iloc[-1] == pytest.approx(caixa_final)


def test_ponte_do_valor_da_empresa_ao_preco(rodada: dict) -> None:
    v, base = rodada["valuation"], rodada["base"]
    equity = (
        v["ev"] - v["divida_liquida"] - v["minoritarios"] + v["investimentos"] - v["outros_ajustes"]
    )
    assert v["equity"] == pytest.approx(equity)
    assert v["preco_justo"] == pytest.approx(equity / base.acoes)


def test_wacc_fica_entre_divida_e_capital_proprio(rodada: dict) -> None:
    v = rodada["valuation"]
    assert v["kd_liquido"] < v["wacc"] < v["ke"]


def test_wacc_maior_derruba_o_preco_e_g_maior_sobe(rodada: dict) -> None:
    grade = modelo.sensibilidade(rodada["base"], rodada["projecao"], rodada["premissas"])
    assert grade.iloc[:, 2].is_monotonic_decreasing  # descendo as linhas, o WACC sobe
    assert grade.iloc[2, :].is_monotonic_increasing  # andando nas colunas, o g sobe


def test_preco_mais_alto_vale_mais(rodada: dict) -> None:
    ticker, dados = rodada["ticker"], rodada["dados"]
    precos = [
        modelo.rodar(ticker, dados, c)["valuation"]["preco_justo"] for c in premissas.CENARIOS
    ]
    assert precos == sorted(precos)


def test_desconto_de_um_fluxo_conhecido() -> None:
    # 100 por ano, ano inteiro pela frente, 10% a.a., sem crescimento:
    # fluxos no meio de cada ano e perpetuidade de 100/0,10 descontada 2 anos.
    vp, terminal = modelo._valor_presente([100.0, 100.0], 100.0, 0.10, 0.0, 1.0)
    assert vp == pytest.approx(100 / 1.1**0.5 + 100 / 1.1**1.5)
    assert terminal == pytest.approx(1000 / 1.1**2)
