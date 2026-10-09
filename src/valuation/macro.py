"""Dados de mercado que alimentam o custo de capital.

Três fontes públicas, cada número gravado com a data e o link de onde veio:
- Tesouro Direto: taxa do título prefixado mais longo (juro sem risco em reais).
- Boletim Focus (Banco Central): inflação esperada, base do crescimento perpétuo.
- Damodaran (NYU): prêmio de risco de mercado e prêmio de risco do Brasil.
"""

import io
import json
import urllib.request
from pathlib import Path
from urllib.parse import quote

import openpyxl
import pandas as pd

from valuation.empresas import CACHE, DADOS

MACRO_CSV = DADOS / "macro.csv"

URL_TESOURO = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3"
    "/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
)
URL_FOCUS = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
    "ExpectativasMercadoAnuais"
)
URL_DAMODARAN = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctryprem.xlsx"


def _baixar(url: str, nome: str, atualizar: bool) -> Path:
    destino = CACHE / "macro" / nome
    if atualizar or not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        pedido = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(pedido, timeout=180) as resposta:
            destino.write_bytes(resposta.read())
    return destino


def _tesouro(atualizar: bool) -> list[dict[str, object]]:
    df = pd.read_csv(_baixar(URL_TESOURO, "tesouro.csv", atualizar), sep=";", decimal=",")
    df["data"] = pd.to_datetime(df["Data Base"], format="%d/%m/%Y")
    df["vencimento"] = pd.to_datetime(df["Data Vencimento"], format="%d/%m/%Y")
    hoje = df[df["data"] == df["data"].max()]
    linhas = []
    for indicador, titulo in (
        ("juro_prefixado_longo", "Tesouro Prefixado com Juros Semestrais"),
        ("juro_real_longo", "Tesouro IPCA+ com Juros Semestrais"),
    ):
        # O vencimento mais próximo de dez anos: prazo parecido com o de um DCF.
        candidatos = hoje[hoje["Tipo Titulo"] == titulo]
        alvo = hoje["data"].max() + pd.DateOffset(years=10)
        escolhido = candidatos.loc[(candidatos["vencimento"] - alvo).abs().idxmin()]
        linhas.append(
            {
                "indicador": indicador,
                "valor": escolhido["Taxa Compra Manha"] / 100,
                "data": escolhido["data"].date().isoformat(),
                "detalhe": f"{titulo} {escolhido['vencimento'].year}",
                "fonte": URL_TESOURO,
            }
        )
    return linhas


def _focus(atualizar: bool) -> list[dict[str, object]]:
    filtro = "Indicador eq 'IPCA' and baseCalculo eq 0"
    url = f"{URL_FOCUS}?$top=40&$format=json&$filter={quote(filtro)}&$orderby={quote('Data desc')}"
    valores = json.loads(_baixar(url, "focus_ipca.json", atualizar).read_text("utf-8"))["value"]
    ultima = max(v["Data"] for v in valores)
    return [
        {
            "indicador": f"ipca_{v['DataReferencia']}",
            "valor": v["Mediana"] / 100,
            "data": ultima,
            "detalhe": f"Focus, mediana de {v['numeroRespondentes']} instituições",
            "fonte": URL_FOCUS,
        }
        for v in sorted(valores, key=lambda v: v["DataReferencia"])
        if v["Data"] == ultima
    ]


def _damodaran(atualizar: bool) -> list[dict[str, object]]:
    caminho = _baixar(URL_DAMODARAN, "ctryprem.xlsx", atualizar)
    livro = openpyxl.load_workbook(io.BytesIO(caminho.read_bytes()), data_only=True)
    aba = livro["ERPs by country"]
    cabecalho = next(
        [str(c or "").strip() for c in linha]
        for linha in aba.iter_rows(values_only=True)
        if linha[0] == "Country"
    )
    brasil = next(linha for linha in aba.iter_rows(values_only=True) if linha[0] == "Brazil")
    por_coluna = dict(zip(cabecalho, brasil, strict=False))
    total = float(por_coluna["Total Equity Risk Premium"])
    pais = float(por_coluna["Country Risk Premium"])
    rating = por_coluna["Moody's rating"]
    atualizado = livro.properties.modified.date().isoformat()
    comum = {"data": atualizado, "fonte": URL_DAMODARAN}
    return [
        {
            "indicador": "premio_mercado_maduro",
            "valor": total - pais,
            "detalhe": "Prêmio de risco de mercado maduro (total do Brasil menos risco-país)",
            **comum,
        },
        {
            "indicador": "premio_risco_brasil",
            "valor": pais,
            "detalhe": f"Risco-país pelo rating {rating}",
            **comum,
        },
    ]


def extrair(atualizar: bool = False) -> pd.DataFrame:
    macro = pd.DataFrame([*_tesouro(atualizar), *_focus(atualizar), *_damodaran(atualizar)])
    macro = macro[["indicador", "valor", "data", "detalhe", "fonte"]]
    macro.to_csv(MACRO_CSV, index=False, float_format="%.6f")
    return macro


def carregar() -> dict[str, float]:
    return pd.read_csv(MACRO_CSV).set_index("indicador")["valor"].to_dict()
