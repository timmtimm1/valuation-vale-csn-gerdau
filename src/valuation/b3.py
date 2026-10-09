"""Cotações da B3 (arquivo COTAHIST) e o que o valuation tira delas.

O COTAHIST é o histórico oficial de pregões, em texto de largura fixa, um zip por
ano. Daqui saem o preço atual, a faixa de 52 semanas, o valor de mercado e o beta.

O arquivo não traz o Ibovespa, então o beta usa o BOVA11 (ETF que replica o
índice) como carteira de mercado. Os preços são ajustados por bonificação, mas não
por dividendos: em retornos semanais o efeito de um dividendo é pequeno, mas existe.
"""

import io
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from valuation.cvm import ACOES_CSV
from valuation.empresas import CACHE, DADOS, EMPRESAS, EVENTOS

URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP"
MERCADO = "BOVA11"
ANOS = range(2021, 2027)
PRECOS_CSV = DADOS / "precos.csv"
MERCADO_CSV = DADOS / "mercado.csv"


def baixar(ano: int, atualizar: bool = False) -> Path:
    """Baixa o zip do ano para o cache. `atualizar` troca o que já estava lá."""
    destino = CACHE / "b3" / f"COTAHIST_A{ano}.ZIP"
    if atualizar or not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        # O servidor da B3 recusa o agente padrão do Python.
        pedido = urllib.request.Request(URL.format(ano=ano), headers={"User-Agent": "curl/8"})
        parcial = destino.with_suffix(".parcial")
        with urllib.request.urlopen(pedido, timeout=300) as resposta:
            parcial.write_bytes(resposta.read())
        parcial.replace(destino)  # só troca o arquivo antigo com o download completo
    return destino


def _ler_ano(caminho: Path, tickers: set[str]) -> pd.DataFrame:
    """Lê as linhas do mercado à vista dos tickers pedidos.

    Layout do COTAHIST: data nas posições 3-10, código de negociação em 13-24,
    tipo de mercado em 25-27 (010 = à vista), último preço em 109-121 (centavos).
    """
    linhas = []
    with zipfile.ZipFile(caminho) as z, z.open(z.namelist()[0]) as bruto:
        for linha in io.TextIOWrapper(bruto, encoding="latin1"):
            if linha[:2] != "01" or linha[24:27] != "010":
                continue
            ticker = linha[12:24].strip()
            if ticker in tickers:
                linhas.append((linha[2:10], ticker, int(linha[108:121]) / 100))
    df = pd.DataFrame(linhas, columns=["data", "ticker", "fechamento"])
    df["data"] = pd.to_datetime(df["data"], format="%Y%m%d")
    return df


def extrair_precos(atualizar: bool = False) -> pd.DataFrame:
    """Fechamentos diários de todos os papéis do estudo e do BOVA11."""
    tickers = {MERCADO}
    for e in EMPRESAS:
        tickers |= {e.ticker, *e.outros_tickers}
    ultimo = max(ANOS)
    precos = pd.concat(
        [_ler_ano(baixar(a, atualizar and a == ultimo), tickers) for a in ANOS],
        ignore_index=True,
    ).sort_values(["ticker", "data"])
    precos.to_csv(PRECOS_CSV, index=False, date_format="%Y-%m-%d")
    return precos


def tabela_ajustada(precos: pd.DataFrame) -> pd.DataFrame:
    """Fechamentos, uma coluna por ticker, com o passado corrigido pelas bonificações."""
    tabela = precos.pivot(index="data", columns="ticker", values="fechamento")
    for ticker, data_ex, fator in EVENTOS:
        if ticker in tabela:
            tabela.loc[tabela.index < pd.Timestamp(data_ex), ticker] /= fator
    return tabela


def _retornos_semanais(precos: pd.DataFrame) -> pd.DataFrame:
    """Retorno semanal (sexta a sexta) de cada papel, uma coluna por ticker."""
    semanal = tabela_ajustada(precos).resample("W-FRI").last()
    return np.log(semanal / semanal.shift(1))


def beta(retornos: pd.DataFrame, ticker: str, semanas: int) -> float:
    """Inclinação da regressão do retorno do papel contra o do mercado."""
    par = retornos[[ticker, MERCADO]].dropna().tail(semanas)
    covariancia = par.cov().loc[ticker, MERCADO]
    return float(covariancia / par[MERCADO].var())


def construir_mercado(precos: pd.DataFrame | None = None) -> pd.DataFrame:
    """Uma linha por empresa: preço, faixa de 52 semanas, valor de mercado e betas."""
    if precos is None:
        precos = pd.read_csv(PRECOS_CSV, parse_dates=["data"])
    acoes = pd.read_csv(ACOES_CSV).sort_values("dt_refer").groupby("ticker").last()
    retornos = _retornos_semanais(precos)
    por_ticker = {t: g.set_index("data")["fechamento"] for t, g in precos.groupby("ticker")}

    linhas = []
    for e in EMPRESAS:
        serie = por_ticker[e.ticker]
        data = serie.index[-1]
        ano = serie[serie.index > data - pd.Timedelta(days=365)]
        a = acoes.loc[e.ticker]
        # Tesouraria sai proporcionalmente de cada classe: a CVM só informa o total.
        emitidas = a["ordinarias"] + a["preferenciais"]
        em_circulacao = a["em_circulacao"] / emitidas
        # Valor de mercado: cada classe pelo seu próprio preço.
        if a["preferenciais"] > 0:
            on = next(t for t in (e.ticker, *e.outros_tickers) if t.endswith("3"))
            pn = next(t for t in (e.ticker, *e.outros_tickers) if not t.endswith("3"))
            bruto = (
                a["ordinarias"] * por_ticker[on].iloc[-1]
                + a["preferenciais"] * por_ticker[pn].iloc[-1]
            )
        else:
            bruto = a["ordinarias"] * serie.iloc[-1]
        linhas.append(
            {
                "ticker": e.ticker,
                "data_preco": data.date().isoformat(),
                "preco": serie.iloc[-1],
                "minimo_52s": ano.min(),
                "maximo_52s": ano.max(),
                "acoes_em_circulacao": a["em_circulacao"],
                "data_acoes": a["dt_refer"],
                "valor_de_mercado": bruto * em_circulacao,
                "beta_5a": beta(retornos, e.ticker, 260),
                "beta_2a": beta(retornos, e.ticker, 104),
            }
        )
    mercado = pd.DataFrame(linhas)
    mercado.to_csv(MERCADO_CSV, index=False, float_format="%.4f")
    return mercado
