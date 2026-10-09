"""O modelo: projeção das três demonstrações e o fluxo de caixa descontado.

Esta é a versão de referência. A planilha (`planilha.py`) e a página (`site/`)
repetem as mesmas contas em fórmulas do Excel e em JavaScript, e os testes
exigem que as três cheguem ao mesmo preço.

Convenções: R$ milhões; custos e despesas positivos; o ano-base é o último
exercício fechado; a data-base do valuation é o último balanço trimestral.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from valuation import historico
from valuation.b3 import MERCADO_CSV
from valuation.premissas import valores

# Saldos e fluxos do ano-base que a projeção usa como ponto de partida.
SALDOS_BASE = (
    "receita",
    "contas_receber",
    "estoques",
    "fornecedores",
    "ativo_fixo",
    "investimentos",
    "caixa_total",
    "divida_bruta",
    "ativo_total",
    "patrimonio_liquido",
)


@dataclass(frozen=True)
class Base:
    """O que o modelo lê do histórico e do mercado."""

    ano: dict[str, float]  # ano-base (último exercício fechado)
    ponte: dict[str, float]  # balanço da data-base, para ir do EV ao valor do acionista
    acoes: float  # em circulação, milhões
    preco: float
    valor_de_mercado: float
    data_base: date
    fracao_ano1: float  # parte do primeiro ano projetado que ainda não aconteceu


def carregar_base(ticker: str, dados: dict[str, Any]) -> Base:
    h = historico.carregar()
    h = h[h["ticker"] == ticker].set_index("periodo")
    ano = h.loc[str(dados["ano_base"])]
    ltm = h.loc[next(p for p in h.index if p.startswith("LTM"))]
    mercado = pd.read_csv(MERCADO_CSV).set_index("ticker").loc[ticker]
    data_base = date.fromisoformat(dados["data_base"])
    saldos = {k: abs(float(ano[k])) for k in SALDOS_BASE}
    # Tudo que o modelo não projeta linha a linha fica constante.
    saldos["outros_ativos"] = saldos["ativo_total"] - sum(
        saldos[k]
        for k in ("caixa_total", "contas_receber", "estoques", "ativo_fixo", "investimentos")
    )
    saldos["outros_passivos"] = saldos["ativo_total"] - (
        saldos["fornecedores"] + saldos["divida_bruta"] + saldos["patrimonio_liquido"]
    )
    return Base(
        ano=saldos,
        ponte={
            k: float(ltm[k])
            for k in ("divida_bruta", "caixa_total", "minoritarios", "investimentos")
        },
        acoes=float(mercado["acoes_em_circulacao"]),
        preco=float(mercado["preco"]),
        valor_de_mercado=float(mercado["valor_de_mercado"]),
        data_base=data_base,
        fracao_ano1=(date(data_base.year, 12, 31) - data_base).days / 365,
    )


def projetar(base: Base, p: dict[str, Any], anos: list[int]) -> pd.DataFrame:
    """DRE, balanço e fluxo de caixa de cada ano projetado (uma coluna por ano)."""
    a = dict(base.ano)
    colunas: dict[int, dict[str, float]] = {}
    t_ir = p["aliquota_ir"]
    for i, ano in enumerate(anos):
        c: dict[str, float] = {}

        # --- DRE
        c["receita"] = a["receita"] * (1 + p["crescimento_receita"][i])
        # A margem EBITDA é premissa do cenário. As despesas operacionais seguem a receita
        # e o custo dos produtos é o que sobra para a margem fechar.
        c["ebitda"] = c["receita"] * p["margem_ebitda"][i]
        c["despesas"] = c["receita"] * p["despesas_pct"][i]
        c["equivalencia"] = p["equivalencia"][i]
        c["custo_caixa"] = c["receita"] - c["despesas"] + c["equivalencia"] - c["ebitda"]
        c["da"] = a["ativo_fixo"] * p["depreciacao_pct"][i]
        c["ebit"] = c["ebitda"] - c["da"]
        # Juros sobre os saldos do início do ano: evita referência circular.
        c["receita_financeira"] = a["caixa_total"] * p["rendimento_caixa"]
        c["despesa_financeira"] = a["divida_bruta"] * p["custo_divida"]
        c["resultado_financeiro"] = c["receita_financeira"] - c["despesa_financeira"]
        c["lair"] = c["ebit"] + c["resultado_financeiro"]
        # Equivalência já vem líquida de imposto da investida.
        c["ir"] = max(0.0, c["lair"] - c["equivalencia"]) * t_ir
        c["lucro_liquido"] = c["lair"] - c["ir"]
        c["nopat"] = (c["ebit"] - c["equivalencia"]) * (1 - t_ir)

        # --- Investimento e capital de giro
        c["capex"] = c["receita"] * p["capex_pct"][i]
        c["ativo_fixo"] = a["ativo_fixo"] + c["capex"] - c["da"]
        c["contas_receber"] = c["receita"] * p["prazo_recebimento"][i] / 365
        c["estoques"] = c["custo_caixa"] * p["prazo_estoque"][i] / 365
        c["fornecedores"] = c["custo_caixa"] * p["prazo_pagamento"][i] / 365
        c["capital_de_giro"] = c["contas_receber"] + c["estoques"] - c["fornecedores"]
        giro_anterior = a["contas_receber"] + a["estoques"] - a["fornecedores"]
        c["variacao_giro"] = c["capital_de_giro"] - giro_anterior

        # --- Fluxos de caixa livres
        c["fcff"] = c["nopat"] + c["da"] - c["capex"] - c["variacao_giro"]
        c["captacao_liquida"] = p["captacao_liquida"][i]
        c["fcfe"] = (
            c["lucro_liquido"]
            - c["equivalencia"]
            + c["da"]
            - c["capex"]
            - c["variacao_giro"]
            + c["captacao_liquida"]
        )
        c["dividendos"] = max(0.0, c["lucro_liquido"]) * p["payout"]

        # --- Balanço: o caixa fecha a conta
        c["variacao_caixa"] = c["fcfe"] - c["dividendos"]
        c["caixa_total"] = a["caixa_total"] + c["variacao_caixa"]
        c["investimentos"] = a["investimentos"] + c["equivalencia"]
        c["outros_ativos"] = a["outros_ativos"]
        c["divida_bruta"] = a["divida_bruta"] + c["captacao_liquida"]
        c["outros_passivos"] = a["outros_passivos"]
        c["patrimonio_liquido"] = a["patrimonio_liquido"] + c["lucro_liquido"] - c["dividendos"]
        c["ativo_total"] = (
            c["caixa_total"]
            + c["contas_receber"]
            + c["estoques"]
            + c["ativo_fixo"]
            + c["investimentos"]
            + c["outros_ativos"]
        )
        c["passivo_e_pl"] = (
            c["fornecedores"] + c["divida_bruta"] + c["outros_passivos"] + c["patrimonio_liquido"]
        )
        c["checagem_balanco"] = c["ativo_total"] - c["passivo_e_pl"]

        # --- Indicadores
        c["margem_ebitda"] = c["ebitda"] / c["receita"]
        c["divida_liquida"] = c["divida_bruta"] - c["caixa_total"]
        c["divida_liquida_ebitda"] = c["divida_liquida"] / c["ebitda"]
        c["roic"] = c["nopat"] / (giro_anterior + a["ativo_fixo"])

        colunas[ano] = c
        a = c
    return pd.DataFrame(colunas)


def custo_de_capital(p: dict[str, Any]) -> dict[str, float]:
    """CAPM para o capital próprio e WACC para a empresa."""
    ke = p["juro_sem_risco"] + p["beta"] * p["premio_mercado"] + p["premio_adicional"]
    kd_liquido = p["custo_divida"] * (1 - p["aliquota_ir"])
    wd = p["peso_divida"]
    wacc_capm = ke * (1 - wd) + kd_liquido * wd
    # O cenário desloca o custo de capital inteiro: o mesmo tanto no WACC e no Ke.
    ajuste = p["ajuste_wacc"]
    return {
        "ke": ke,
        "kd_liquido": kd_liquido,
        "wacc_capm": wacc_capm,
        "ajuste_wacc": ajuste,
        "wacc": wacc_capm + ajuste,
        "ke_usado": ke + ajuste,
    }


def _valor_presente(
    fluxos: list[float], terminal: float, taxa: float, g: float, fracao: float
) -> tuple[float, float]:
    """Soma dos fluxos descontados e valor presente da perpetuidade.

    O primeiro ano só conta pela fração que falta e cai no meio dela; os demais
    caem no meio de cada ano. A perpetuidade (Gordon) é descontada do fim do
    último ano projetado.
    """
    vp = 0.0
    for i, fluxo in enumerate(fluxos):
        if i == 0:
            vp += fluxo * fracao / (1 + taxa) ** (fracao / 2)
        else:
            vp += fluxo / (1 + taxa) ** (fracao + i - 0.5)
    fim = fracao + len(fluxos) - 1
    vp_terminal = terminal * (1 + g) / (taxa - g) / (1 + taxa) ** fim
    return vp, vp_terminal


def avaliar(
    base: Base,
    proj: pd.DataFrame,
    p: dict[str, Any],
    wacc: float | None = None,
    g: float | None = None,
) -> dict[str, float]:
    """Do fluxo de caixa ao preço por ação. `wacc` e `g` servem à sensibilidade."""
    k = custo_de_capital(p)
    wacc = k["wacc"] if wacc is None else wacc
    g = p["crescimento_perpetuo"] if g is None else g
    ultimo = proj[proj.columns[-1]]
    # Fluxo normalizado: na perpetuidade o capex é um múltiplo da depreciação.
    capex_terminal = p["capex_perpetuidade"] * ultimo["da"]
    fcff_terminal = ultimo["nopat"] + ultimo["da"] - capex_terminal - ultimo["variacao_giro"]
    vp, vp_terminal = _valor_presente(
        list(proj.loc["fcff"]), fcff_terminal, wacc, g, base.fracao_ano1
    )
    ev = vp + vp_terminal
    ponte = base.ponte
    divida_liquida = ponte["divida_bruta"] - ponte["caixa_total"]
    equity = (
        ev - divida_liquida - ponte["minoritarios"] + ponte["investimentos"] - p["outros_ajustes"]
    )

    # Conferência pelo fluxo do acionista, descontado ao custo do capital próprio.
    fcfe_terminal = (
        ultimo["lucro_liquido"]
        - ultimo["equivalencia"]
        + ultimo["da"]
        - capex_terminal
        - ultimo["variacao_giro"]
        + ultimo["captacao_liquida"]
    )
    vp_e, vp_e_terminal = _valor_presente(
        list(proj.loc["fcfe"]), fcfe_terminal, k["ke_usado"], g, base.fracao_ano1
    )
    equity_fcfe = (
        vp_e + vp_e_terminal - ponte["minoritarios"] + ponte["investimentos"] - p["outros_ajustes"]
    )
    preco = equity / base.acoes
    return {
        **k,
        "wacc_usado": wacc,
        "g_usado": g,
        "fcff_terminal": fcff_terminal,
        "vp_fluxos": vp,
        "vp_terminal": vp_terminal,
        "peso_terminal": vp_terminal / ev,
        "ev": ev,
        "divida_liquida": divida_liquida,
        "minoritarios": ponte["minoritarios"],
        "investimentos": ponte["investimentos"],
        "outros_ajustes": p["outros_ajustes"],
        "equity": equity,
        "preco_justo": preco,
        "preco_mercado": base.preco,
        "potencial": preco / base.preco - 1,
        "equity_fcfe": equity_fcfe,
        "preco_fcfe": equity_fcfe / base.acoes,
        "ev_ebitda_implicito": ev / proj[proj.columns[0]]["ebitda"],
    }


def sensibilidade(
    base: Base, proj: pd.DataFrame, p: dict[str, Any], passo_wacc: float = 0.01
) -> pd.DataFrame:
    """Preço por ação para uma grade de WACC (linhas) e crescimento perpétuo (colunas)."""
    centro = custo_de_capital(p)["wacc"]
    waccs = [centro + passo_wacc * d for d in (-2, -1, 0, 1, 2)]
    gs = [p["crescimento_perpetuo"] + 0.005 * d for d in (-2, -1, 0, 1, 2)]
    return pd.DataFrame(
        [[avaliar(base, proj, p, w, g)["preco_justo"] for g in gs] for w in waccs],
        index=waccs,
        columns=gs,
    )


def rodar(
    ticker: str,
    dados: dict[str, Any],
    cenario: str = "moderado",
    manual: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Atalho: carrega a base, projeta e avalia um cenário (com ajuste manual, se houver)."""
    base = carregar_base(ticker, dados)
    p = valores(dados, cenario, manual)
    proj = projetar(base, p, dados["anos"])
    return {"base": base, "premissas": p, "projecao": proj, "valuation": avaliar(base, proj, p)}
