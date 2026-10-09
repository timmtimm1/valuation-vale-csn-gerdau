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
    assert v["kd_liquido"] < v["wacc_capm"] < v["ke"]
    assert v["wacc"] == pytest.approx(v["wacc_capm"] + v["ajuste_wacc"])


def test_wacc_maior_derruba_o_preco_e_g_maior_sobe(rodada: dict) -> None:
    grade = modelo.sensibilidade(rodada["base"], rodada["projecao"], rodada["premissas"])
    assert grade.iloc[:, 2].is_monotonic_decreasing  # descendo as linhas, o WACC sobe
    assert grade.iloc[2, :].is_monotonic_increasing  # andando nas colunas, o g sobe


def test_pessimista_moderado_otimista_em_ordem(rodada: dict) -> None:
    ticker, dados = rodada["ticker"], rodada["dados"]
    precos = [
        modelo.rodar(ticker, dados, c)["valuation"]["preco_justo"] for c in premissas.CENARIOS
    ]
    assert precos == sorted(precos)


def test_ajuste_manual_fica_preso_na_faixa(rodada: dict) -> None:
    dados = rodada["dados"]
    minimo, maximo = premissas.faixa(dados, "margem_ebitda")
    assert premissas.escolha(dados, "moderado", {"margem_ebitda": 0.99})["margem_ebitda"] == maximo
    assert premissas.escolha(dados, "moderado", {"margem_ebitda": -1.0})["margem_ebitda"] == minimo
    meio = (minimo + maximo) / 2
    assert premissas.escolha(dados, "moderado", {"margem_ebitda": meio})["margem_ebitda"] == meio


def test_2026_e_igual_nos_tres_cenarios(rodada: dict) -> None:
    # o primeiro ano parte do realizado: receita e margem não dependem do cenário
    ticker, dados = rodada["ticker"], rodada["dados"]
    primeiro = dados["anos"][0]
    receitas, margens = set(), set()
    for c in premissas.CENARIOS:
        proj = modelo.rodar(ticker, dados, c)["projecao"]
        receitas.add(round(proj.loc["receita", primeiro], 6))
        margens.add(round(proj.loc["margem_ebitda", primeiro], 9))
    assert len(receitas) == 1 and len(margens) == 1


def test_margem_projetada_e_a_do_cenario(rodada: dict) -> None:
    dados, proj = rodada["dados"], rodada["projecao"]
    ultimo = dados["anos"][-1]
    assert proj.loc["margem_ebitda", ultimo] == pytest.approx(
        dados["cenarios"]["margem_ebitda"]["moderado"]
    )


def test_desconto_de_um_fluxo_conhecido() -> None:
    # 100 por ano, ano inteiro pela frente, 10% a.a., sem crescimento:
    # fluxos no meio de cada ano e perpetuidade de 100/0,10 descontada 2 anos.
    vp, terminal = modelo._valor_presente([100.0, 100.0], 100.0, 0.10, 0.0, 1.0)
    assert vp == pytest.approx(100 / 1.1**0.5 + 100 / 1.1**1.5)
    assert terminal == pytest.approx(1000 / 1.1**2)


def test_juros_pagos_da_csn_vem_do_fluxo_de_caixa_da_cvm() -> None:
    # o valor digitado em premissas/divida_divulgada.yaml tem de ser o da linha da CVM
    import pandas as pd
    import yaml

    from valuation.cvm import CONTAS_CSV

    divulgado = yaml.safe_load(premissas.DIVIDA_YAML.read_text(encoding="utf-8"))["CSNA3"]
    contas = pd.read_csv(CONTAS_CSV, dtype={"cd_conta": str})
    ano = divulgado["juros_pagos"]["ano"]
    linha = contas[
        (contas["ticker"] == "CSNA3")
        & (contas["doc"] == "DFP")
        & (contas["dt_refer"] == f"{ano}-12-31")
        & (contas["ds_conta"] == "Juros pagos")
    ]
    assert len(linha) == 1
    assert divulgado["juros_pagos"]["valor"] == pytest.approx(-linha["valor"].iloc[0])


def test_custo_da_divida_em_reais_nao_fica_abaixo_dos_juros_pagos(rodada: dict) -> None:
    # a parte em dólar ganha a diferença de inflação ao vir para reais: nunca reduz o custo
    p = rodada["premissas"]
    assert p["custo_divida"] >= p["juros_divida"]
    assert 0.03 < p["juros_divida"] < 0.20
