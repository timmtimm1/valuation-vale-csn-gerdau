"""Do plano de contas da CVM para as linhas que o modelo usa.

Entrada: `dados/contas_cvm.csv` (uma linha por conta, como a empresa entregou).
Saída: `dados/historico.csv`, uma linha por empresa e período, com DRE, balanço,
fluxo de caixa e os indicadores derivados (EBITDA, NOPAT, margens, giro, ROIC).

Períodos: cada exercício anual (rótulo "2025") e os últimos doze meses até o
trimestre mais recente (rótulo "LTM 2T26"), que usa o balanço desse trimestre.
"""

import re
import unicodedata

import pandas as pd

from valuation.cvm import CONTAS_CSV
from valuation.empresas import DADOS

HISTORICO_CSV = DADOS / "historico.csv"
ALIQUOTA_IR = 0.34  # IRPJ 25% + CSLL 9%, alíquota nominal das não financeiras

# Os níveis altos do plano da CVM são fixos: o código vale para qualquer empresa.
DRE = {
    "receita": "3.01",
    "custo": "3.02",
    "lucro_bruto": "3.03",
    "despesas_operacionais": "3.04",
    "despesas_vendas": "3.04.01",
    "despesas_ga": "3.04.02",
    "equivalencia": "3.04.06",
    "ebit": "3.05",
    "resultado_financeiro": "3.06",
    "receitas_financeiras": "3.06.01",
    "despesas_financeiras": "3.06.02",
    "lair": "3.07",
    "ir": "3.08",
    "lucro_liquido": "3.11",
    "lucro_controladores": "3.11.01",
}
BALANCO = {
    "ativo_total": "1",
    "ativo_circulante": "1.01",
    "caixa": "1.01.01",
    "aplicacoes": "1.01.02",
    "contas_receber": "1.01.03",
    "estoques": "1.01.04",
    "investimentos": "1.02.02",
    "imobilizado": "1.02.03",
    "intangivel": "1.02.04",
    "passivo_circulante": "2.01",
    "fornecedores": "2.01.02",
    "divida_cp": "2.01.04",
    "passivo_nao_circulante": "2.02",
    "divida_lp": "2.02.01",
    "patrimonio_liquido": "2.03",
    "minoritarios": "2.03.09",
}
FLUXOS_FIXOS = {
    "fco": ("DFC_MI", "6.01"),
    "fci": ("DFC_MI", "6.02"),
    "fcf": ("DFC_MI", "6.03"),
    # A DVA tem código fixo para a depreciação; no fluxo de caixa cada empresa
    # usa uma linha diferente.
    "da": ("DVA", "7.04.01"),
}

# Abaixo do terceiro nível o fluxo de caixa é texto livre: classificamos pela descrição.
_CAPEX = re.compile(r"imobilizado|intangivel")
_CAPEX_ACAO = re.compile(r"aquisic|adic|compra")
_CAPEX_EXCLUI = re.compile(r"venda|alienac|baixa|receb")
_DIVIDENDO = re.compile(r"dividend|juros s(?:obre|/) (?:o )?capital|jcp")
_DIVIDENDO_EXCLUI = re.compile(r"receb")


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def _fluxos_por_descricao(dfc: pd.DataFrame) -> pd.DataFrame:
    """Soma capex e dividendos pagos a partir das linhas de 3º nível do fluxo de caixa."""
    nivel3 = dfc[dfc["cd_conta"].str.fullmatch(r"6\.0[23]\.\d{2}")].copy()
    desc = nivel3["ds_conta"].map(_sem_acento)
    pai = nivel3["cd_conta"].str[:4]
    capex = (
        (pai == "6.02")
        & desc.str.contains(_CAPEX)
        & desc.str.contains(_CAPEX_ACAO)
        & ~desc.str.contains(_CAPEX_EXCLUI)
    )
    dividendos = (
        (pai == "6.03") & desc.str.contains(_DIVIDENDO) & ~desc.str.contains(_DIVIDENDO_EXCLUI)
    )
    nivel3["linha"] = None
    nivel3.loc[capex, "linha"] = "capex"
    nivel3.loc[dividendos, "linha"] = "dividendos_pagos"
    return nivel3.dropna(subset=["linha"])


def _linhas(contas: pd.DataFrame) -> pd.DataFrame:
    """Tabela longa: ticker, doc, dt_refer, dt_ini, linha, valor."""
    partes = []
    for quadro, mapa in (("DRE", DRE), ("BPA", BALANCO), ("BPP", BALANCO)):
        por_codigo = {codigo: linha for linha, codigo in mapa.items()}
        q = contas[(contas["quadro"] == quadro) & contas["cd_conta"].isin(por_codigo)].copy()
        q["linha"] = q["cd_conta"].map(por_codigo)
        partes.append(q)
    for linha, (quadro, codigo) in FLUXOS_FIXOS.items():
        q = contas[(contas["quadro"] == quadro) & (contas["cd_conta"] == codigo)].copy()
        q["linha"] = linha
        partes.append(q)
    partes.append(_fluxos_por_descricao(contas[contas["quadro"] == "DFC_MI"]))
    longa = pd.concat(partes, ignore_index=True)
    return (
        longa.groupby(["ticker", "doc", "dt_refer", "dt_ini", "linha"], dropna=False)["valor"]
        .sum()
        .reset_index()
    )


def _acumulado(longa: pd.DataFrame, doc: str, dt_refer: str) -> pd.Series:
    """Valores de um documento, com os fluxos acumulados desde 1º de janeiro.

    O ITR traz a DRE duas vezes (só o trimestre e o acumulado do ano); o
    acumulado é o que começa em janeiro.
    """
    d = longa[(longa["doc"] == doc) & (longa["dt_refer"] == dt_refer)]
    inicio_do_ano = f"{dt_refer[:4]}-01-01"
    d = d[d["dt_ini"].isna() | (d["dt_ini"] == inicio_do_ano)]
    return d.set_index("linha")["valor"]


def _periodos_de(longa: pd.DataFrame) -> pd.DataFrame:
    """Uma coluna por período para uma empresa: anos fechados e o LTM."""
    fluxos = [*DRE, *FLUXOS_FIXOS, "capex", "dividendos_pagos"]
    colunas: dict[str, pd.Series] = {}
    anuais = sorted(longa.loc[longa["doc"] == "DFP", "dt_refer"].unique())
    for dt in anuais:
        colunas[dt[:4]] = _acumulado(longa, "DFP", dt)

    trimestres = sorted(longa.loc[longa["doc"] == "ITR", "dt_refer"].unique())
    ultimo = trimestres[-1] if trimestres else None
    if ultimo and ultimo > anuais[-1]:
        atual = _acumulado(longa, "ITR", ultimo)
        um_ano_antes = _acumulado(longa, "ITR", f"{int(ultimo[:4]) - 1}{ultimo[4:]}")
        ano_cheio = colunas[anuais[-1][:4]]
        ltm = atual.copy()  # balanço: o do trimestre
        for linha in fluxos:  # fluxos: ano fechado + parcial deste ano - parcial do ano passado
            ltm[linha] = (
                ano_cheio.get(linha, 0.0) + atual.get(linha, 0.0) - um_ano_antes.get(linha, 0.0)
            )
        trimestre = (int(ultimo[5:7]) - 1) // 3 + 1
        colunas[f"LTM {trimestre}T{ultimo[2:4]}"] = ltm
    tabela = pd.DataFrame(colunas).T
    tabela["data_balanco"] = [*anuais, ultimo][: len(tabela)]
    return tabela


def _indicadores(t: pd.DataFrame) -> pd.DataFrame:
    """Medidas derivadas. Custos e despesas ficam negativos, como na DRE da CVM."""
    t = t.copy()
    t["da"] = t["da"].abs()
    t["capex"] = t["capex"].abs()
    t["dividendos_pagos"] = t["dividendos_pagos"].abs()
    # A Vale entregou o custo de 2022 com sinal trocado (positivo) na DFP. Tirar o
    # custo da diferença entre lucro bruto e receita vale para todas e corrige o caso.
    t["custo"] = t["lucro_bruto"] - t["receita"]
    # Tudo que está em despesas operacionais e não é vendas, G&A nem equivalência:
    # provisões, impairment, ganhos e perdas não recorrentes.
    t["outras_operacionais"] = (
        t["despesas_operacionais"] - t["despesas_vendas"] - t["despesas_ga"] - t["equivalencia"]
    )
    t["ebitda"] = t["ebit"] + t["da"]
    # O modelo projeta o custo sem a depreciação, para ela reagir ao capex.
    t["custo_caixa"] = t["custo"] + t["da"]
    t["nopat"] = (t["ebit"] - t["equivalencia"]) * (1 - ALIQUOTA_IR)

    t["divida_bruta"] = t["divida_cp"] + t["divida_lp"]
    t["caixa_total"] = t["caixa"] + t["aplicacoes"]
    t["divida_liquida"] = t["divida_bruta"] - t["caixa_total"]
    t["capital_de_giro"] = t["contas_receber"] + t["estoques"] - t["fornecedores"]
    t["ativo_fixo"] = t["imobilizado"] + t["intangivel"]
    t["capital_investido"] = t["capital_de_giro"] + t["ativo_fixo"]

    receita = t["receita"]
    t["crescimento_receita"] = receita.pct_change()
    t["margem_bruta"] = t["lucro_bruto"] / receita
    t["margem_ebitda"] = t["ebitda"] / receita
    t["margem_ebit"] = t["ebit"] / receita
    t["margem_liquida"] = t["lucro_liquido"] / receita
    t["custo_caixa_pct"] = -t["custo_caixa"] / receita
    t["vendas_pct"] = -t["despesas_vendas"] / receita
    t["ga_pct"] = -t["despesas_ga"] / receita
    t["outras_pct"] = t["outras_operacionais"] / receita
    t["capex_pct"] = t["capex"] / receita
    t["da_pct_ativo_fixo"] = t["da"] / t["ativo_fixo"].shift(1)
    t["aliquota_efetiva"] = -t["ir"] / t["lair"]

    t["prazo_recebimento"] = t["contas_receber"] / receita * 365
    t["prazo_estoque"] = t["estoques"] / -t["custo_caixa"] * 365
    t["prazo_pagamento"] = t["fornecedores"] / -t["custo_caixa"] * 365
    t["ciclo_caixa"] = t["prazo_recebimento"] + t["prazo_estoque"] - t["prazo_pagamento"]

    t["divida_liquida_ebitda"] = t["divida_liquida"] / t["ebitda"]
    t["liquidez_corrente"] = t["ativo_circulante"] / t["passivo_circulante"]
    t["roe"] = t["lucro_controladores"] / (t["patrimonio_liquido"] - t["minoritarios"])
    t["roic"] = t["nopat"] / t["capital_investido"]
    # Juros sobre o saldo médio. Na despesa entram variação cambial e derivativos,
    # então em ano de câmbio forte a taxa implícita não é o custo contratado.
    t["custo_implicito_divida"] = -t["despesas_financeiras"] / t["divida_bruta"].rolling(2).mean()
    t["rendimento_implicito_caixa"] = t["receitas_financeiras"] / t["caixa_total"].rolling(2).mean()
    t["payout"] = t["dividendos_pagos"] / t["lucro_liquido"]
    t["fcl_simples"] = t["fco"] - t["capex"]  # caixa operacional menos investimento
    return t


def construir() -> pd.DataFrame:
    contas = pd.read_csv(CONTAS_CSV, dtype={"cd_conta": str, "dt_ini": str})
    longa = _linhas(contas)
    tabelas = []
    for ticker, da_empresa in longa.groupby("ticker"):
        t = _indicadores(_periodos_de(da_empresa))
        t.insert(0, "periodo", t.index)
        t.insert(0, "ticker", ticker)
        tabelas.append(t.reset_index(drop=True))
    historico = pd.concat(tabelas, ignore_index=True)
    historico.to_csv(HISTORICO_CSV, index=False, float_format="%.4f")
    return historico


def carregar() -> pd.DataFrame:
    return pd.read_csv(HISTORICO_CSV)
