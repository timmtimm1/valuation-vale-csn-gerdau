"""Valuation relativo: quanto o mercado paga pelas comparáveis.

Calcula os múltiplos das cinco empresas com os últimos doze meses e aplica a
mediana das outras quatro aos números de cada empresa do estudo. É uma segunda
opinião para o DCF, não um preço-alvo: o grupo é pequeno e mistura mineração
com siderurgia.
"""

import pandas as pd

from valuation import historico
from valuation.b3 import MERCADO_CSV
from valuation.empresas import DADOS, EMPRESAS, FOCO

MULTIPLOS_CSV = DADOS / "multiplos.csv"
IMPLICITOS_CSV = DADOS / "multiplos_implicitos.csv"
MULTIPLOS = ("ev_ebitda", "ev_ebit", "p_l", "p_vp")


def calcular() -> pd.DataFrame:
    """Uma linha por empresa, com as bases (R$ milhões) e os múltiplos."""
    h = historico.carregar()
    ltm = h[h["periodo"].str.startswith("LTM")].set_index("ticker")
    mercado = pd.read_csv(MERCADO_CSV).set_index("ticker")
    t = pd.DataFrame(index=[e.ticker for e in EMPRESAS])
    t["empresa"] = [e.nome for e in EMPRESAS]
    t["setor"] = [e.setor for e in EMPRESAS]
    t["preco"] = mercado["preco"]
    t["acoes"] = mercado["acoes_em_circulacao"]
    t["valor_de_mercado"] = mercado["valor_de_mercado"]
    t["divida_liquida"] = ltm["divida_liquida"]
    t["minoritarios"] = ltm["minoritarios"]
    t["ev"] = t["valor_de_mercado"] + t["divida_liquida"] + t["minoritarios"]
    # Sem as perdas por recuperabilidade, nas cinco: a baixa de um ano não diz quanto a
    # operação gera, e com ela a Usiminas aparecia a 66 vezes o EBITDA. O lucro e o
    # patrimônio ficam como divulgados, porque a baixa reduziu os dois de verdade.
    t["ebitda"] = ltm["ebitda_recorrente"]
    t["ebit"] = ltm["ebit"] - ltm["perdas_recuperabilidade"]
    t["lucro"] = ltm["lucro_controladores"]
    t["patrimonio"] = ltm["patrimonio_liquido"] - ltm["minoritarios"]
    t["ev_ebitda"] = t["ev"] / t["ebitda"]
    t["ev_ebit"] = t["ev"] / t["ebit"]
    # Múltiplo de lucro não tem sentido com prejuízo.
    t["p_l"] = (t["valor_de_mercado"] / t["lucro"]).where(t["lucro"] > 0)
    t["p_vp"] = t["valor_de_mercado"] / t["patrimonio"]
    t.index.name = "ticker"
    return t


def implicitos(t: pd.DataFrame) -> pd.DataFrame:
    """Preço por ação de cada empresa do estudo pela mediana das comparáveis."""
    linhas = []
    for e in FOCO:
        alvo = t.loc[e.ticker]
        pares = t.drop(index=e.ticker)
        for m in MULTIPLOS:
            mediana = pares[m].median()
            if m.startswith("ev_"):
                base = alvo[m.removeprefix("ev_")]
                valor = mediana * base - alvo["divida_liquida"] - alvo["minoritarios"]
            else:
                base = alvo["lucro"] if m == "p_l" else alvo["patrimonio"]
                valor = mediana * base
            # Lucro ou EBIT negativo: o múltiplo não se aplica.
            preco = valor / alvo["acoes"] if base > 0 else float("nan")
            linhas.append(
                {
                    "ticker": e.ticker,
                    "multiplo": m,
                    "mediana_pares": mediana,
                    "base": base,
                    "preco_implicito": preco,
                }
            )
    return pd.DataFrame(linhas)


def construir() -> tuple[pd.DataFrame, pd.DataFrame]:
    t = calcular()
    imp = implicitos(t)
    t.to_csv(MULTIPLOS_CSV, float_format="%.4f")
    imp.to_csv(IMPLICITOS_CSV, index=False, float_format="%.4f")
    return t, imp
