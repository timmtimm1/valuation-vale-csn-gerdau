"""Premissas do modelo: a proposta automática e o arquivo que o analista aprova.

`propor` monta uma proposta neutra por regra, a partir do histórico e dos dados de
mercado, e grava em `premissas/<ticker>.yaml` com a origem de cada número. O
analista edita o arquivo e troca `status: proposta` por `status: aprovada`. A
proposta nunca sobrescreve um arquivo aprovado.
"""

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from valuation import historico, macro
from valuation.b3 import MERCADO_CSV
from valuation.empresas import PREMISSAS, empresa

ANOS = [2026, 2027, 2028, 2029, 2030]
ANO_BASE = "2025"

# Uma lista com um valor por ano projetado.
POR_ANO = {
    "crescimento_volume": "Crescimento do volume vendido",
    "variacao_preco": "Variação do preço médio de venda",
    "inflacao_custos": "Inflação dos custos e despesas",
    "outras_pct": "Outras receitas/despesas operacionais (% da receita)",
    "equivalencia": "Equivalência patrimonial (R$ milhões)",
    "capex_pct": "Investimento - capex (% da receita)",
    "depreciacao_pct": "Depreciação (% do ativo fixo inicial)",
    "prazo_recebimento": "Prazo médio de recebimento (dias)",
    "prazo_estoque": "Prazo médio de estoque (dias)",
    "prazo_pagamento": "Prazo médio de pagamento (dias)",
    "captacao_liquida": "Captação líquida de dívida (R$ milhões)",
}
ESCALARES = {
    "aliquota_ir": "Alíquota de IR e CSLL",
    "custo_divida": "Custo da dívida antes do imposto (Kd)",
    "rendimento_caixa": "Rendimento do caixa",
    "payout": "Dividendos (% do lucro)",
    "juro_sem_risco": "Juro sem risco (Rf)",
    "beta": "Beta",
    "premio_mercado": "Prêmio de risco de mercado",
    "premio_adicional": "Prêmio adicional (tamanho, risco específico)",
    "peso_divida": "Peso da dívida na estrutura de capital",
    "crescimento_perpetuo": "Crescimento na perpetuidade (g)",
    "capex_perpetuidade": "Capex na perpetuidade (múltiplo da depreciação)",
    "outros_ajustes": "Outros passivos tratados como dívida (R$ milhões)",
}
# Premissas que os cenários deslocam, somando ao valor do cenário base.
CENARIZAVEIS = ("crescimento_volume", "variacao_preco", "inflacao_custos")
CENARIOS = ("pessimista", "base", "otimista")


def caminho(ticker: str) -> Path:
    return PREMISSAS / f"{ticker.lower()}.yaml"


def _convergir(inicio: float, fim: float) -> list[float]:
    """Do valor de hoje até o nível de longo prazo, em linha reta."""
    n = len(ANOS) - 1
    return [inicio + (fim - inicio) * i / n for i in range(len(ANOS))]


def propor(ticker: str) -> dict[str, Any]:
    h = historico.carregar()
    h = h[h["ticker"] == ticker].set_index("periodo")
    base = h.loc[ANO_BASE]
    ltm_rotulo = next(p for p in h.index if p.startswith("LTM"))
    ltm = h.loc[ltm_rotulo]
    cinco = h.loc[[str(a) for a in range(2021, 2026)]]
    tres = h.loc[[str(a) for a in range(2023, 2026)]]
    m = macro.carregar()
    mercado = pd.read_csv(MERCADO_CSV).set_index("ticker").loc[ticker]
    ipca = [m[f"ipca_{a}"] for a in ANOS]
    n = len(ANOS)

    def por_ano(valores: list[float], origem: str) -> dict[str, Any]:
        return {"valores": [round(float(v), 4) for v in valores], "origem": origem}

    def escalar(valor: float, origem: str) -> dict[str, Any]:
        return {"valor": round(float(valor), 4), "origem": origem}

    inflacao = f"{ANOS[1]} em diante: IPCA esperado no Focus"
    p: dict[str, Any] = {
        "crescimento_volume": por_ano(
            [0.0] * n,
            "Volume constante. A CVM não publica toneladas: usar o guidance da empresa.",
        ),
        "variacao_preco": por_ano(
            [ltm["receita"] / base["receita"] - 1, *ipca[1:]],
            f"{ANOS[0]}: receita dos últimos 12 meses ({ltm_rotulo}) sobre {ANO_BASE}. {inflacao}"
            " (preço constante em termos reais).",
        ),
        "inflacao_custos": por_ano(
            [ltm["custo_caixa"] / base["custo_caixa"] - 1, *ipca[1:]],
            f"{ANOS[0]}: custo caixa dos últimos 12 meses sobre {ANO_BASE}. {inflacao}.",
        ),
        "outras_pct": por_ano(
            _convergir(ltm["outras_pct"], cinco["outras_pct"].median()),
            "Do nível dos últimos 12 meses até a mediana de 2021-2025.",
        ),
        "equivalencia": por_ano(
            [cinco["equivalencia"].median()] * n, "Mediana de 2021-2025, mantida."
        ),
        "capex_pct": por_ano(
            _convergir(ltm["capex_pct"], cinco["capex_pct"].median()),
            "Do nível dos últimos 12 meses até a mediana de 2021-2025.",
        ),
        "depreciacao_pct": por_ano(
            [cinco["da_pct_ativo_fixo"].median()] * n, "Mediana de 2021-2025, mantida."
        ),
        "captacao_liquida": por_ano([0.0] * n, "Dívida bruta mantida no nível de 2025."),
    }
    for prazo in ("prazo_recebimento", "prazo_estoque", "prazo_pagamento"):
        p[prazo] = por_ano([base[prazo]] * n, f"Prazo de {ANO_BASE}, mantido.")

    divida = ltm["divida_bruta"]
    p |= {
        "aliquota_ir": escalar(historico.ALIQUOTA_IR, "Alíquota nominal: IRPJ 25% + CSLL 9%."),
        "custo_divida": escalar(
            m["juro_prefixado_longo"],
            "Piso: a taxa do Tesouro prefixado de dez anos, sem spread de crédito."
            f" Custo implícito mediano 2023-2025: {tres['custo_implicito_divida'].median():.1%}.",
        ),
        "rendimento_caixa": escalar(
            tres["rendimento_implicito_caixa"].median(),
            "Mediana 2023-2025 da receita financeira sobre o caixa médio.",
        ),
        "payout": escalar(
            min(max(cinco["payout"].median(), 0.0), 1.0),
            "Mediana 2021-2025 de dividendos pagos sobre lucro, limitada a 0-100%.",
        ),
        "juro_sem_risco": escalar(
            m["juro_prefixado_longo"], "Tesouro prefixado de dez anos (em reais, nominal)."
        ),
        "beta": escalar(
            mercado["beta_5a"],
            "Regressão de 5 anos, retornos semanais contra o BOVA11, preços sem ajuste de"
            f" proventos. Beta de 2 anos: {mercado['beta_2a']:.2f}.",
        ),
        "premio_mercado": escalar(
            m["premio_mercado_maduro"],
            "Damodaran, mercado maduro. O risco-país já está no juro em reais.",
        ),
        "premio_adicional": escalar(0.0, "Sem prêmio adicional."),
        "peso_divida": escalar(
            divida / (divida + mercado["valor_de_mercado"]),
            f"Dívida bruta do {ltm_rotulo.removeprefix('LTM ')} sobre dívida mais valor de mercado.",
        ),
        "crescimento_perpetuo": escalar(
            ipca[-1], f"IPCA esperado para {ANOS[-1]}: crescimento real zero."
        ),
        "capex_perpetuidade": escalar(1.0, "Na perpetuidade a empresa reinveste o que deprecia."),
        "outros_ajustes": escalar(
            0.0, "Nenhum. Provisões (barragens, contingências) não entram como dívida."
        ),
    }
    return {
        "ticker": ticker,
        "empresa": empresa(ticker).nome,
        "status": "proposta",
        "data_base": ltm["data_balanco"],
        "ano_base": int(ANO_BASE),
        "anos": ANOS,
        "premissas": p,
        "cenarios": {
            "origem": "Choque de 5% no preço em 2027, mantido depois. Ilustrativo.",
            "pessimista": {"variacao_preco": [0.0, -0.05, 0.0, 0.0, 0.0]},
            "otimista": {"variacao_preco": [0.0, 0.05, 0.0, 0.0, 0.0]},
        },
    }


def salvar_proposta(ticker: str) -> Path:
    destino = caminho(ticker)
    if destino.exists() and carregar(ticker)["status"] == "aprovada":
        raise RuntimeError(f"{destino.name} já foi aprovado; a proposta não o sobrescreve")
    PREMISSAS.mkdir(exist_ok=True)
    # default_flow_style=None deixa cada lista de anos numa linha só, mais fácil de editar.
    texto = yaml.safe_dump(
        propor(ticker), allow_unicode=True, sort_keys=False, width=100, default_flow_style=None
    )
    destino.write_text(texto, encoding="utf-8")
    return destino


def carregar(ticker: str) -> dict[str, Any]:
    dados: dict[str, Any] = yaml.safe_load(caminho(ticker).read_text(encoding="utf-8"))
    n = len(dados["anos"])
    for nome in POR_ANO:
        if len(dados["premissas"][nome]["valores"]) != n:
            raise ValueError(f"{ticker}: {nome} precisa de {n} valores, um por ano")
    for nome in ESCALARES:
        if "valor" not in dados["premissas"][nome]:
            raise ValueError(f"{ticker}: falta o valor de {nome}")
    return dados


def valores(dados: dict[str, Any], cenario: str = "base") -> dict[str, Any]:
    """Premissas prontas para o modelo: listas por ano e escalares, já no cenário."""
    p = dados["premissas"]
    saida: dict[str, Any] = {nome: list(p[nome]["valores"]) for nome in POR_ANO}
    saida |= {nome: p[nome]["valor"] for nome in ESCALARES}
    if cenario != "base":
        for nome, deltas in dados["cenarios"][cenario].items():
            saida[nome] = [v + d for v, d in zip(saida[nome], deltas, strict=True)]
    return saida
