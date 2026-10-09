"""Extração dos demonstrativos no portal de dados abertos da CVM.

A CVM publica um .zip por ano com todas as companhias abertas: DFP (anual) e ITR
(trimestral). Cada zip traz um CSV por quadro (balanço, DRE, fluxo de caixa...).
Aqui baixamos os zips, filtramos as empresas do estudo e gravamos tudo num CSV
só, em R$ milhões, sem interpretar conta nenhuma: a leitura fica em `historico.py`.
"""

import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from valuation.empresas import CACHE, DADOS, EMPRESAS, POR_CNPJ

URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{pasta}/DADOS/{tipo}_cia_aberta_{ano}.zip"
# Só o consolidado: é o que o mercado usa para avaliar o grupo.
QUADROS = ("BPA_con", "BPP_con", "DRE_con", "DFC_MI_con", "DVA_con")
ANOS_DFP = range(2018, 2026)
ANOS_ITR = (2025, 2026)
ESCALA = {"MIL": 1e-3, "UNIDADE": 1e-6}  # para R$ milhões

CONTAS_CSV = DADOS / "contas_cvm.csv"
ACOES_CSV = DADOS / "acoes.csv"


def baixar(tipo: str, ano: int) -> Path:
    """Baixa o zip do ano para o cache, se ainda não estiver lá."""
    destino = CACHE / "cvm" / f"{tipo}_cia_aberta_{ano}.zip"
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        url = URL.format(pasta=tipo.upper(), tipo=tipo, ano=ano)
        with urllib.request.urlopen(url, timeout=120) as resposta:
            destino.write_bytes(resposta.read())
    return destino


def _ler_csv(caminho_zip: Path, nome: str) -> pd.DataFrame:
    """Lê um CSV de dentro do zip já filtrando as empresas do estudo.

    Os arquivos passam de 100 MB; ler em pedaços mantém a memória baixa.
    """
    cnpjs = set(POR_CNPJ)
    with zipfile.ZipFile(caminho_zip) as z, z.open(nome) as bruto:
        texto = io.TextIOWrapper(bruto, encoding="latin1")
        pedacos = [
            p[p["CNPJ_CIA"].isin(cnpjs)]
            for p in pd.read_csv(texto, sep=";", dtype=str, chunksize=200_000)
        ]
    return pd.concat(pedacos, ignore_index=True)


def _ultima_versao(df: pd.DataFrame) -> pd.DataFrame:
    """Fica com a reapresentação mais recente de cada documento."""
    versao = df["VERSAO"].astype(int)
    return df[versao == versao.groupby([df["CNPJ_CIA"], df["DT_REFER"]]).transform("max")]


def ler_quadro(tipo: str, ano: int, quadro: str) -> pd.DataFrame:
    df = _ler_csv(baixar(tipo, ano), f"{tipo}_cia_aberta_{quadro}_{ano}.csv")
    # Cada documento repete o período anterior para comparação; fica só o do próprio.
    df = _ultima_versao(df[df["ORDEM_EXERC"] == "ÚLTIMO"])
    # Balanço é foto de uma data: não tem início de período.
    dt_ini = df["DT_INI_EXERC"] if "DT_INI_EXERC" in df else pd.Series("", index=df.index)
    return pd.DataFrame(
        {
            "ticker": df["CNPJ_CIA"].map(lambda c: POR_CNPJ[c].ticker),
            "doc": tipo.upper(),
            "dt_refer": df["DT_REFER"],
            "dt_ini": dt_ini,
            "dt_fim": df["DT_FIM_EXERC"],
            "quadro": quadro.removesuffix("_con"),
            "cd_conta": df["CD_CONTA"],
            "ds_conta": df["DS_CONTA"].str.strip(),
            "valor": df["VL_CONTA"].astype(float) * df["ESCALA_MOEDA"].map(ESCALA),
        }
    )


def ler_acoes(tipo: str, ano: int) -> pd.DataFrame:
    """Quantidade de ações emitidas e em tesouraria, em milhões."""
    nome = f"{tipo}_cia_aberta_composicao_capital_{ano}.csv"
    with zipfile.ZipFile(baixar(tipo, ano)) as z:
        if nome not in z.namelist():  # a CVM só publica esse quadro de 2020 em diante
            return pd.DataFrame()
    df = _ler_csv(baixar(tipo, ano), nome)
    df = _ultima_versao(df)
    escala = df["CNPJ_CIA"].map(lambda c: POR_CNPJ[c].escala_acoes) / 1e6
    saida = pd.DataFrame(
        {
            "ticker": df["CNPJ_CIA"].map(lambda c: POR_CNPJ[c].ticker),
            "dt_refer": df["DT_REFER"],
        }
    )
    for coluna, origem in (
        ("ordinarias", "QT_ACAO_ORDIN_CAP_INTEGR"),
        ("preferenciais", "QT_ACAO_PREF_CAP_INTEGR"),
        ("tesouraria", "QT_ACAO_TOTAL_TESOURO"),
    ):
        saida[coluna] = df[origem].astype(float) * escala
    saida["em_circulacao"] = saida["ordinarias"] + saida["preferenciais"] - saida["tesouraria"]
    return saida


def extrair() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Baixa, filtra e grava `dados/contas_cvm.csv` e `dados/acoes.csv`."""
    documentos = [("dfp", a) for a in ANOS_DFP] + [("itr", a) for a in ANOS_ITR]
    contas = pd.concat(
        [ler_quadro(tipo, ano, q) for tipo, ano in documentos for q in QUADROS],
        ignore_index=True,
    ).sort_values(["ticker", "dt_refer", "quadro", "cd_conta", "dt_ini"])
    acoes = pd.concat(
        [ler_acoes(tipo, ano) for tipo, ano in documentos], ignore_index=True
    ).sort_values(["ticker", "dt_refer"])

    faltando = {e.ticker for e in EMPRESAS} - set(contas["ticker"])
    if faltando:
        raise RuntimeError(f"sem dados na CVM para: {sorted(faltando)}")

    DADOS.mkdir(exist_ok=True)
    contas.to_csv(CONTAS_CSV, index=False, float_format="%.3f")
    acoes.to_csv(ACOES_CSV, index=False, float_format="%.6f")
    return contas, acoes
