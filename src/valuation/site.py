"""Monta a página interativa: um HTML só, com o modelo e os dados embutidos.

`site/pagina.html` é o molde (estrutura, estilo e interface), `site/modelo.js`
são as contas. Aqui os dois são juntados com os dados das três empresas em
`site/index.html`, que abre direto no navegador e pode ser hospedado em qualquer
servidor de arquivos estáticos.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from valuation import historico, modelo, multiplos, premissas
from valuation.empresas import FOCO, PAGINA, REPOSITORIO, SITE
from valuation.macro import MACRO_CSV
from valuation.planilha import ARQUIVO

CORPO = '<div class="wrap">'
LIGACOES = "<!--__LIGACOES__-->"
DESCRICAO = (
    "Valuation de VALE3, CSNA3 e GGBR4 por fluxo de caixa descontado e por múltiplos, "
    "com três cenários ajustáveis e só dados públicos."
)

# Linhas do histórico que a página mostra.
HISTORICO = (
    # demonstração do resultado
    "receita",
    "custo",
    "lucro_bruto",
    "despesas_operacionais",
    "ebit",
    "resultado_financeiro",
    "lucro_liquido",
    # balanço
    "ativo_total",
    "caixa_total",
    "capital_de_giro",
    "ativo_fixo",
    "divida_bruta",
    "patrimonio_liquido",
    # fluxo de caixa
    "fco",
    "capex",
    "dividendos_pagos",
    "fcl_simples",
    # indicadores
    "da",
    "ebitda",
    "ebitda_recorrente",
    "nopat",
    "crescimento_receita",
    "margem_bruta",
    "margem_ebitda",
    "margem_ebitda_recorrente",
    "margem_liquida",
    "divida_liquida",
    "divida_liquida_ebitda",
    "roic",
    "roe",
    "prazo_recebimento",
    "prazo_estoque",
    "prazo_pagamento",
    "ciclo_caixa",
    "capex_pct",
    "despesas_pct",
)


def _empresa(ticker: str) -> dict[str, Any]:
    dados = premissas.carregar(ticker)
    base = modelo.carregar_base(ticker, dados)
    h = historico.carregar()
    h = h[h["ticker"] == ticker]
    mercado = pd.read_csv(modelo.MERCADO_CSV).set_index("ticker").loc[ticker]
    p = dados["premissas"]
    return {
        "ticker": ticker,
        "nome": dados["empresa"],
        "status": dados["status"],
        "data_base": dados["data_base"],
        "ano_base": dados["ano_base"],
        "anos": dados["anos"],
        "base": {
            "ano": base.ano,
            "ponte": base.ponte,
            "acoes": base.acoes,
            "preco": base.preco,
            "fracao_ano1": base.fracao_ano1,
        },
        "mercado": {
            "data_preco": mercado["data_preco"],
            "minimo_52s": float(mercado["minimo_52s"]),
            "maximo_52s": float(mercado["maximo_52s"]),
            "valor_de_mercado": base.valor_de_mercado,
        },
        "premissas": premissas.valores(dados),
        "origens": {nome: p[nome]["origem"] for nome in p}
        | {nome: c["origem"] for nome, c in dados["cenarios"].items()},
        "cenarios": dados["cenarios"],
        "historico": {
            "periodos": list(h["periodo"]),
            # Sem valor (primeiro ano de uma variação, por exemplo) vira null: NaN não é JSON.
            **{
                linha: [None if pd.isna(v) else round(float(v), 4) for v in h[linha]]
                for linha in HISTORICO
            },
        },
    }


def dados_da_pagina() -> dict[str, Any]:
    t = multiplos.calcular()
    imp = multiplos.implicitos(t)
    macro = pd.read_csv(MACRO_CSV)
    return {
        "empresas": {e.ticker: _empresa(e.ticker) for e in FOCO},
        "rotulos": {**premissas.VARIAVEIS, **premissas.POR_ANO, **premissas.ESCALARES},
        "nomes_cenarios": {
            "pessimista": "Pessimista",
            "moderado": "Moderado",
            "otimista": "Otimista",
        },
        "multiplos": json.loads(t.reset_index().to_json(orient="records")),
        "implicitos": json.loads(imp.to_json(orient="records")),
        "macro": json.loads(
            macro[["indicador", "valor", "data", "detalhe"]].to_json(orient="records")
        ),
    }


def _ligacoes() -> str:
    """Links da página publicada: a planilha, o código e o registro das fontes."""
    return (
        f'<p><a href="{REPOSITORIO}/raw/main/saida/{ARQUIVO.name}">Baixar a planilha (.xlsx)</a>'
        f' · <a href="{REPOSITORIO}">código e dados no GitHub</a>'
        f' · <a href="{REPOSITORIO}/blob/main/FONTES.md">fonte de cada dado</a>'
        f' · <a href="{REPOSITORIO}/tree/main/analises">preços no dia da análise</a></p>'
    )


def construir() -> Path:
    """Grava a página completa (index.html) e o fragmento para publicar como artefato."""
    molde = (SITE / "pagina.html").read_text(encoding="utf-8")
    motor = (SITE / "modelo.js").read_text(encoding="utf-8")
    dados = json.dumps(dados_da_pagina(), ensure_ascii=False, separators=(",", ":"))
    fragmento = molde.replace("/*__MODELO__*/", motor).replace("/*__DADOS__*/", dados)
    # O artefato não deixa baixar arquivo: os links ficam só na página completa.
    (SITE / "artefato.html").write_text(fragmento.replace(LIGACOES, ""), encoding="utf-8")

    # O molde começa por <title>, <link> e <style>: isso vai no <head> da página completa.
    cabeca, corpo = fragmento.replace(LIGACOES, _ligacoes()).split(CORPO, 1)
    destino = SITE / "index.html"
    destino.write_text(
        '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="description" content="{DESCRICAO}">\n'
        '<meta property="og:type" content="website">\n'
        '<meta property="og:title" content="Valuation: Vale, CSN e Gerdau">\n'
        f'<meta property="og:description" content="{DESCRICAO}">\n'
        f'<meta property="og:url" content="{PAGINA}">\n'
        f'{cabeca}</head>\n<body style="margin:0">\n{CORPO}{corpo}</body>\n</html>\n',
        encoding="utf-8",
    )
    return destino
