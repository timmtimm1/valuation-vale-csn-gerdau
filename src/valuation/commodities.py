"""Preço das ações contra o preço do minério de ferro.

Série mensal do minério (Banco Mundial), do dólar (Banco Central) e do preço
médio de cada ação no mês (B3). Daí saem a correlação entre as variações mensais,
quanto a ação costuma andar quando o minério anda 1% e quanto da oscilação da
ação o minério explica.

Tudo é medido em variação mensal, não em nível de preço: duas séries que só sobem
com o tempo parecem correlacionadas mesmo sem ter nada a ver uma com a outra.
"""

import json

import pandas as pd

from valuation.b3 import PRECOS_CSV, tabela_ajustada
from valuation.empresas import DADOS, FOCO
from valuation.macro import _baixar

# O Banco Mundial troca o código da pasta a cada ano; o link atual está na página
# https://www.worldbank.org/en/research/commodity-markets ("Monthly prices").
URL_BANCO_MUNDIAL = (
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026"
    "/related/CMO-Historical-Data-Monthly.xlsx"
)
URL_DOLAR = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.3698/dados?formato=json&dataInicial=01/01/2021"
)
MINERIO = "Iron ore, cfr spot"
INICIO = "2021-01"

SERIES_CSV = DADOS / "commodity_e_acoes.csv"
CORRELACAO_CSV = DADOS / "correlacao.csv"


def _minerio(atualizar: bool) -> pd.Series:
    """Minério de ferro 62% Fe, CFR China, US$ por tonelada, média do mês."""
    caminho = _baixar(URL_BANCO_MUNDIAL, "banco_mundial_mensal.xlsx", atualizar)
    bruto = pd.read_excel(caminho, sheet_name="Monthly Prices", header=4)
    bruto = bruto.rename(columns=lambda c: str(c).strip())
    meses = bruto.iloc[:, 0].astype(str)
    validos = meses.str.fullmatch(r"\d{4}M\d{2}")
    serie = pd.to_numeric(bruto.loc[validos, MINERIO], errors="coerce")
    serie.index = meses[validos].str.replace("M", "-")
    return serie.dropna()


def _dolar(atualizar: bool) -> pd.Series:
    """Dólar PTAX de venda, média do mês."""
    bruto = json.loads(_baixar(URL_DOLAR, "sgs_dolar_mensal.json", atualizar).read_text("utf-8"))
    return pd.Series(
        {f"{v['data'][6:]}-{v['data'][3:5]}": float(v["valor"]) for v in bruto}
    ).sort_index()


def series(atualizar: bool = False) -> pd.DataFrame:
    """Uma linha por mês: minério em dólar e em reais, dólar e preço médio de cada ação."""
    precos = pd.read_csv(PRECOS_CSV, parse_dates=["data"])
    acoes = tabela_ajustada(precos)[[e.ticker for e in FOCO]]
    mensal = acoes.groupby(acoes.index.strftime("%Y-%m")).mean()
    tabela = pd.DataFrame({"minerio_usd": _minerio(atualizar), "dolar": _dolar(atualizar)})
    tabela["minerio_brl"] = tabela["minerio_usd"] * tabela["dolar"]
    # Só os meses em que as três fontes têm dado (o mês corrente fica de fora).
    tabela = tabela.join(mensal, how="inner").loc[INICIO:].dropna()
    tabela.index.name = "mes"
    tabela.to_csv(SERIES_CSV, float_format="%.4f")
    return tabela


def correlacao(tabela: pd.DataFrame | None = None) -> pd.DataFrame:
    """Para cada ação e cada medida do minério: correlação, sensibilidade e R²."""
    if tabela is None:
        tabela = pd.read_csv(SERIES_CSV, index_col="mes")
    variacao = tabela.pct_change().dropna()
    linhas = []
    for e in FOCO:
        for minerio in ("minerio_usd", "minerio_brl"):
            x, y = variacao[minerio], variacao[e.ticker]
            r = x.corr(y)
            linhas.append(
                {
                    "ticker": e.ticker,
                    "minerio": minerio,
                    "meses": len(x),
                    "correlacao": r,
                    # Inclinação da reta: quanto a ação anda, em média, para 1% no minério.
                    "sensibilidade": x.cov(y) / x.var(),
                    "r2": r**2,
                }
            )
    resultado = pd.DataFrame(linhas)
    resultado.to_csv(CORRELACAO_CSV, index=False, float_format="%.4f")
    return resultado
