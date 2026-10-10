"""A correlação entre ação e minério: dados coerentes e conta conferível."""

import pandas as pd
import pytest

from valuation import commodities
from valuation.empresas import FOCO


@pytest.fixture(scope="module")
def series() -> pd.DataFrame:
    return pd.read_csv(commodities.SERIES_CSV, index_col="mes")


def test_meses_seguidos_e_sem_buraco(series: pd.DataFrame) -> None:
    meses = pd.period_range(series.index[0], series.index[-1], freq="M").strftime("%Y-%m")
    assert list(series.index) == list(meses)
    assert not series.isna().any().any()


def test_minerio_em_reais_e_dolar_vezes_cambio(series: pd.DataFrame) -> None:
    esperado = series["minerio_usd"] * series["dolar"]
    assert (series["minerio_brl"] - esperado).abs().max() < 0.01


def test_bonificacao_da_gerdau_nao_vira_queda(series: pd.DataFrame) -> None:
    # abril de 2024: sem o ajuste, a média do mês cairia mais de 10% por causa da bonificação
    variacao = series["GGBR4"].pct_change()
    assert variacao["2024-04"] > -0.10 and variacao["2024-05"] > -0.10


def test_bonificacao_da_gerdau_de_2023_tambem_e_ajustada() -> None:
    # 22/03/2023, primeiro pregão sem direito à bonificação de 5%: sem o ajuste o
    # fechamento cai 4,4% num dia em que as outras siderúrgicas ficaram paradas.
    from valuation.b3 import PRECOS_CSV, tabela_ajustada

    precos = tabela_ajustada(pd.read_csv(PRECOS_CSV, parse_dates=["data"]))
    variacao = precos[["GGBR4", "GGBR3"]].pct_change().loc["2023-03-22"]
    assert (variacao.abs() < 0.01).all()


def test_correlacao_dentro_dos_limites_e_r2_coerente(series: pd.DataFrame) -> None:
    resultado = commodities.correlacao(series)
    assert len(resultado) == 2 * len(FOCO)
    assert resultado["correlacao"].between(-1, 1).all()
    assert (resultado["r2"] - resultado["correlacao"] ** 2).abs().max() < 1e-12


def test_vale_anda_mais_com_o_minerio_que_a_gerdau(series: pd.DataFrame) -> None:
    r = commodities.correlacao(series).set_index(["ticker", "minerio"])["correlacao"]
    assert r[("VALE3", "minerio_usd")] > r[("GGBR4", "minerio_usd")]
