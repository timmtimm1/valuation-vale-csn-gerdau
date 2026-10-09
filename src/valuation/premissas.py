"""Premissas do modelo: os três cenários e o arquivo que o analista aprova.

Três variáveis mudam com o cenário, e só elas: o crescimento da receita, a margem
EBITDA e o WACC. Cada uma tem um valor pessimista, um moderado e um otimista, e
pode ser ajustada à mão dentro dessa faixa. O resto (capex, depreciação, capital
de giro, imposto) vale igual nos três cenários.

`propor` monta a proposta por regra, a partir do histórico da própria empresa e
dos dados de mercado, e grava em `premissas/<ticker>.yaml` com a origem de cada
número. O analista edita o arquivo e troca `status: proposta` por
`status: aprovada`; a partir daí a proposta não sobrescreve o arquivo.
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
CENARIOS = ("pessimista", "moderado", "otimista")

# As variáveis de cenário. `partida` é o nível de 2026, igual nos três cenários.
VARIAVEIS = {
    "crescimento_receita": "Crescimento da receita, ao ano (2027 a 2030)",
    "margem_ebitda": "Margem EBITDA em 2030",
    "ajuste_wacc": "WACC: pontos acima ou abaixo do CAPM",
}
COM_PARTIDA = ("crescimento_receita", "margem_ebitda")

# Premissas iguais nos três cenários. Uma lista com um valor por ano projetado.
POR_ANO = {
    "despesas_pct": "Despesas operacionais (% da receita)",
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
    "juros_divida": "Juros pagos sobre a dívida (% do saldo inicial)",
    "custo_divida": "Custo da dívida no WACC, em reais, antes do imposto (Kd)",
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
# O crescimento otimista vem do histórico, mas parte dele foi aquisição: fica limitado
# a este tanto acima da inflação.
TETO_CRESCIMENTO_REAL = 0.04
DIVIDA_YAML = PREMISSAS / "divida_divulgada.yaml"
INFLACAO_EUA = 0.02  # meta do Federal Reserve


def _pct(valor: float, casas: int = 1) -> str:
    """Percentual escrito como se lê em português: vírgula decimal."""
    return f"{valor * 100:.{casas}f}%".replace(".", ",")


def caminho(ticker: str) -> Path:
    return PREMISSAS / f"{ticker.lower()}.yaml"


def _convergir(inicio: float, fim: float) -> list[float]:
    """Do valor de hoje até o nível de longo prazo, em linha reta."""
    n = len(ANOS) - 1
    return [inicio + (fim - inicio) * i / n for i in range(len(ANOS))]


def _cenario(pessimista: float, moderado: float, otimista: float, origem: str) -> dict[str, Any]:
    return {
        "pessimista": round(float(pessimista), 4),
        "moderado": round(float(moderado), 4),
        "otimista": round(float(otimista), 4),
        "origem": origem,
    }


def custo_da_divida(
    ticker: str, h: pd.DataFrame, m: dict[str, float]
) -> tuple[float, float, str, str]:
    """Juros pagos e custo da dívida em reais, a partir do que a empresa divulga.

    Devolve (juros pagos, custo no WACC, origem dos juros, origem do custo). `h` é o
    histórico da empresa, indexado pelo período.
    """
    divulgado = yaml.safe_load(DIVIDA_YAML.read_text(encoding="utf-8"))[ticker]
    fonte = " ".join(divulgado["fonte"].split())
    parcelas = divulgado["parcelas"]
    if not parcelas:
        # Sem custo divulgado: o que ela pagou de juros sobre a dívida média do ano.
        ano = divulgado["juros_pagos"]["ano"]
        media = (h.loc[str(ano), "divida_bruta"] + h.loc[str(ano - 1), "divida_bruta"]) / 2
        pagos = divulgado["juros_pagos"]["valor"] / media
        return (
            pagos,
            m["juro_prefixado_longo"],
            fonte,
            "A empresa não divulga custo médio: mantido o piso, a taxa do Tesouro prefixado de"
            " dez anos, sem spread de crédito.",
        )

    inflacao = m[f"ipca_{ANOS[-1]}"]
    total = sum(p["peso"] for p in parcelas)
    pagos = custo = 0.0
    for p in parcelas:
        peso = p["peso"] / total
        if p["indexador"] == "dolar":
            pagos += peso * p["taxa"]
            # Em reais a dívida em dólar custa a taxa mais o que o real perde para o dólar.
            custo += peso * ((1 + p["taxa"]) * (1 + inflacao) / (1 + INFLACAO_EUA) - 1)
        else:
            pagos += peso * (m["cdi"] + p["taxa"])
            custo += peso * (m["cdi"] + p["taxa"])
    tem_dolar = any(p["indexador"] == "dolar" for p in parcelas)
    conversao = (
        f" A parte em dólar foi trazida para reais pela diferença de inflação"
        f" ({_pct(inflacao, 1)} no Brasil, {_pct(INFLACAO_EUA, 1)} nos EUA)."
        if tem_dolar
        else ""
    )
    cdi = f" CDI de {_pct(m['cdi'], 2)}." if any(p["indexador"] == "cdi" for p in parcelas) else ""
    return pagos, custo, fonte + cdi, fonte + cdi + conversao


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
    n = len(ANOS)
    partida = f"{ANOS[0]}: nível dos últimos 12 meses ({ltm_rotulo}). "

    def por_ano(valores: list[float], origem: str) -> dict[str, Any]:
        return {"valores": [round(float(v), 4) for v in valores], "origem": origem}

    def escalar(valor: float, origem: str) -> dict[str, Any]:
        return {"valor": round(float(valor), 4), "origem": origem}

    # --- as três variáveis de cenário
    inflacao = sum(m[f"ipca_{a}"] for a in ANOS[1:]) / (n - 1)
    primeiro = h.index[0]
    anos_de_historia = int(ANO_BASE) - int(primeiro)
    crescimento_historico = (base["receita"] / h.loc[primeiro, "receita"]) ** (
        1 / anos_de_historia
    ) - 1
    teto = inflacao + TETO_CRESCIMENTO_REAL
    sobre_o_teto = (
        f", limitado a {_pct(TETO_CRESCIMENTO_REAL, 0)} acima da inflação porque parte veio de"
        " aquisições."
        if crescimento_historico > teto
        else "."
    )
    margens = sorted(cinco["margem_ebitda_recorrente"])
    amplitude = (m["juro_prefixado_maximo"] - m["juro_prefixado_minimo"]) / 2

    cenarios = {
        "crescimento_receita": {
            "partida": round(float(ltm["receita"] / base["receita"] - 1), 4),
            **_cenario(
                0.0,
                inflacao,
                min(crescimento_historico, teto),
                partida + "Pessimista: receita parada, ou seja, queda real. Moderado: inflação"
                f" esperada no Focus para {ANOS[1]}-{ANOS[-1]}, crescimento real zero. Otimista:"
                f" crescimento médio da receita de {primeiro} a {ANO_BASE}"
                f" ({_pct(crescimento_historico, 1)} ao ano){sobre_o_teto}",
            ),
        },
        "margem_ebitda": {
            "partida": round(float(ltm["margem_ebitda_recorrente"]), 4),
            **_cenario(
                margens[1],
                margens[2],
                margens[3],
                partida + f"Daí até {ANOS[-1]} em linha reta. Faixa: margem EBITDA de 2021 a"
                " 2025, sem perdas por recuperabilidade. Pessimista é o segundo pior ano,"
                " moderado a mediana e otimista o segundo melhor.",
            ),
        },
        "ajuste_wacc": _cenario(
            amplitude,
            0.0,
            -amplitude,
            "Moderado: o WACC que sai do CAPM. O juro prefixado longo andou de"
            f" {_pct(m['juro_prefixado_minimo'])} a {_pct(m['juro_prefixado_maximo'])} nos"
            " últimos dois anos; pessimista e otimista deslocam o WACC em metade dessa amplitude.",
        ),
    }

    # --- o que vale igual nos três cenários
    p: dict[str, Any] = {
        "despesas_pct": por_ano(
            _convergir(ltm["despesas_pct"], cinco["despesas_pct"].median()),
            "Vendas, administrativas e outras, sem perdas por recuperabilidade. Do nível dos"
            " últimos 12 meses até a mediana de 2021-2025.",
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
    beta_2a = f"{mercado['beta_2a']:.2f}".replace(".", ",")
    juros_pagos, custo_wacc, origem_juros, origem_custo = custo_da_divida(ticker, h, m)
    p |= {
        "aliquota_ir": escalar(historico.ALIQUOTA_IR, "Alíquota nominal: IRPJ 25% + CSLL 9%."),
        "juros_divida": escalar(juros_pagos, origem_juros),
        "custo_divida": escalar(custo_wacc, origem_custo),
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
            f" proventos. Beta de 2 anos: {beta_2a}.",
        ),
        "premio_mercado": escalar(
            m["premio_mercado_maduro"],
            "Damodaran, mercado maduro. O risco-país já está no juro em reais.",
        ),
        "premio_adicional": escalar(0.0, "Sem prêmio adicional."),
        "peso_divida": escalar(
            divida / (divida + mercado["valor_de_mercado"]),
            f"Dívida bruta do {ltm_rotulo.removeprefix('LTM ')} sobre dívida mais valor de"
            " mercado.",
        ),
        "crescimento_perpetuo": escalar(
            m[f"ipca_{ANOS[-1]}"], f"IPCA esperado para {ANOS[-1]}: crescimento real zero."
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
        "cenarios": cenarios,
        "premissas": {nome: p[nome] for nome in (*POR_ANO, *ESCALARES)},
    }


def salvar_proposta(ticker: str) -> Path:
    destino = caminho(ticker)
    # Lê só o status, sem validar: o arquivo pode ser de um formato anterior.
    atual = yaml.safe_load(destino.read_text(encoding="utf-8")) if destino.exists() else {}
    if atual.get("status") == "aprovada":
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
    for nome in VARIAVEIS:
        exigidos = {*CENARIOS, *(("partida",) if nome in COM_PARTIDA else ())}
        faltando = exigidos - set(dados["cenarios"][nome])
        if faltando:
            raise ValueError(f"{ticker}: cenário de {nome} sem {sorted(faltando)}")
    return dados


def faixa(dados: dict[str, Any], nome: str) -> tuple[float, float]:
    """Menor e maior valor que a variável pode assumir: os extremos dos cenários."""
    valores_cenario = [dados["cenarios"][nome][c] for c in CENARIOS]
    return min(valores_cenario), max(valores_cenario)


def escolha(
    dados: dict[str, Any], cenario: str = "moderado", manual: dict[str, float] | None = None
) -> dict[str, float]:
    """Valor de cada variável: o do cenário, ou o ajuste manual preso à faixa."""
    saida = {nome: float(dados["cenarios"][nome][cenario]) for nome in VARIAVEIS}
    for nome, valor in (manual or {}).items():
        minimo, maximo = faixa(dados, nome)
        saida[nome] = min(max(float(valor), minimo), maximo)
    return saida


def valores(
    dados: dict[str, Any], cenario: str = "moderado", manual: dict[str, float] | None = None
) -> dict[str, Any]:
    """Premissas prontas para o modelo: listas por ano e escalares, já no cenário."""
    p = dados["premissas"]
    saida: dict[str, Any] = {nome: list(p[nome]["valores"]) for nome in POR_ANO}
    saida |= {nome: p[nome]["valor"] for nome in ESCALARES}
    e = escolha(dados, cenario, manual)
    n = len(dados["anos"])
    cen = dados["cenarios"]
    # 2026 já está quase todo realizado: parte do nível atual em qualquer cenário.
    saida["crescimento_receita"] = [
        cen["crescimento_receita"]["partida"],
        *[e["crescimento_receita"]] * (n - 1),
    ]
    inicio = cen["margem_ebitda"]["partida"]
    saida["margem_ebitda"] = [
        inicio + (e["margem_ebitda"] - inicio) * i / (n - 1) for i in range(n)
    ]
    saida["ajuste_wacc"] = e["ajuste_wacc"]
    return saida
