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
