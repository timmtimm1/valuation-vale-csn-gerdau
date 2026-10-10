"""O histórico precisa fechar com as identidades contábeis da própria CVM."""

import pandas as pd
import pytest

from valuation import historico


@pytest.fixture(scope="module")
def h() -> pd.DataFrame:
    return historico.carregar()


def test_todas_as_empresas_tem_ano_base_e_ltm(h: pd.DataFrame) -> None:
    for _, da_empresa in h.groupby("ticker"):
        periodos = set(da_empresa["periodo"])
        assert "2025" in periodos
        assert any(p.startswith("LTM") for p in periodos)


def test_custo_sempre_negativo(h: pd.DataFrame) -> None:
    # pega o sinal trocado da Vale em 2022
    assert (h["custo"] < 0).all()


def test_ebit_fecha_com_as_linhas_da_dre(h: pd.DataFrame) -> None:
    recomposto = h["lucro_bruto"] + h["despesas_operacionais"]
    assert (recomposto - h["ebit"]).abs().max() < 1.0  # R$ 1 milhão de arredondamento


def test_ebitda_e_ebit_mais_depreciacao(h: pd.DataFrame) -> None:
    assert ((h["ebit"] + h["da"]) - h["ebitda"]).abs().max() < 1e-6
    assert (h["da"] > 0).all()


def test_capex_encontrado_em_todo_periodo(h: pd.DataFrame) -> None:
    # a regra por descrição não pode deixar empresa sem investimento
    assert (h["capex"] > 0).all()


def test_ltm_da_gerdau_bate_com_a_soma_dos_trimestres(h: pd.DataFrame) -> None:
    # 2025 (69.858,5) + 1S26 (34.586,3) - 1S25 (34.901,1), em R$ milhões
    ltm = h[(h["ticker"] == "GGBR4") & h["periodo"].str.startswith("LTM")].iloc[0]
    assert ltm["receita"] == pytest.approx(69_858.532 + 34_586.293 - 34_901.086, abs=0.01)


def _linha(h: pd.DataFrame, ticker: str, periodo: str) -> pd.Series:
    return h[(h["ticker"] == ticker) & (h["periodo"] == periodo)].iloc[0]


def test_capex_soma_o_intangivel_escrito_no_plural(h: pd.DataFrame) -> None:
    # Gerdau 2025: "Adições de imobilizado" (6.681,6) + "Adições de outros ativos
    # intangíveis" (171,2). A regra antiga só achava "intangível" no singular.
    assert _linha(h, "GGBR4", "2025")["capex"] == pytest.approx(6_681.6 + 171.2, abs=0.1)
    # Usiminas 2025: imobilizado (1.050,3) + ativos intangíveis (120,6).
    assert _linha(h, "USIM5", "2025")["capex"] == pytest.approx(1_050.3 + 120.6, abs=0.1)


def test_dividendo_antecipado_recebido_nao_conta_como_pago(h: pd.DataFrame) -> None:
    # A CSN não pagou dividendo no 1S25 nem no 1S26: os doze meses são os R$ 695,2
    # milhões de 2025. A linha "antecipados" é entrada de caixa e ficava somada.
    ltm = h[(h["ticker"] == "CSNA3") & h["periodo"].str.startswith("LTM")].iloc[0]
    assert ltm["dividendos_pagos"] == pytest.approx(695.2, abs=0.1)


def test_baixa_da_usiminas_vem_do_fluxo_de_caixa(h: pd.DataFrame) -> None:
    # A Usiminas não usa a linha 3.04.03 da DRE. Os R$ 2.214,4 milhões de 2025 estão em
    # "outras despesas operacionais" e aparecem só nos ajustes do fluxo de caixa.
    ano = _linha(h, "USIM5", "2025")
    assert ano["perdas_recuperabilidade"] == pytest.approx(-2_214.4, abs=0.1)
    assert ano["ebitda"] < 0 < ano["ebitda_recorrente"]


def test_quem_usa_a_linha_da_dre_continua_com_ela(h: pd.DataFrame) -> None:
    assert _linha(h, "VALE3", "2025")["perdas_recuperabilidade"] == pytest.approx(-25_147.0)
    assert _linha(h, "GGBR4", "2025")["perdas_recuperabilidade"] == pytest.approx(-1_964.5, abs=0.1)
    assert (h.loc[h["ticker"] == "CSNA3", "perdas_recuperabilidade"] == 0).all()


def test_alavancagem_usa_o_ebitda_sem_baixas(h: pd.DataFrame) -> None:
    ano = _linha(h, "VALE3", "2025")
    assert ano["divida_liquida_ebitda"] == pytest.approx(61_828 / 74_422, abs=1e-4)


def test_obrigacoes_fora_da_divida_saem_das_contas_do_balanco(h: pd.DataFrame) -> None:
    ltm = h[h["periodo"].str.startswith("LTM")].set_index("ticker")["obrigacoes_extras"]
    # Vale, junho de 2026: Brumadinho (4.178 + 5.007) e Mariana (3.424 + 7.429).
    assert ltm["VALE3"] == pytest.approx(4_178 + 5_007 + 3_424 + 7_429)
    # CSN: passivos de contratos, circulante e não circulante.
    assert ltm["CSNA3"] == pytest.approx(13_101.3, abs=0.1)
    assert ltm["GGBR4"] == 0 and ltm["USIM5"] == 0
