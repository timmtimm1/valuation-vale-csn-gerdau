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
from valuation.empresas import FOCO, SITE
from valuation.macro import MACRO_CSV

CORPO = '<div class="wrap">'

# Linhas do histórico que a página mostra.
HISTORICO = (
    "receita",
    "ebitda",
    "ebit",
    "lucro_liquido",
    "capex",
    "da",
    "fco",
    "divida_liquida",
    "margem_ebitda",
    "divida_liquida_ebitda",
    "roic",
    "roe",
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
        "origens": {nome: p[nome]["origem"] for nome in p},
        "cenarios": {c: dados["cenarios"][c] for c in ("pessimista", "otimista")},
        "historico": {
            "periodos": list(h["periodo"]),
            **{linha: [round(float(v), 4) for v in h[linha]] for linha in HISTORICO},
        },
    }


def dados_da_pagina() -> dict[str, Any]:
    t = multiplos.calcular()
    imp = multiplos.implicitos(t)
    macro = pd.read_csv(MACRO_CSV)
    return {
        "empresas": {e.ticker: _empresa(e.ticker) for e in FOCO},
        "rotulos": {**premissas.POR_ANO, **premissas.ESCALARES},
        "multiplos": json.loads(t.reset_index().to_json(orient="records")),
        "implicitos": json.loads(imp.to_json(orient="records")),
        "macro": json.loads(
            macro[["indicador", "valor", "data", "detalhe"]].to_json(orient="records")
        ),
    }


def construir() -> Path:
    """Grava a página completa (index.html) e o fragmento para publicar como artefato."""
    molde = (SITE / "pagina.html").read_text(encoding="utf-8")
    motor = (SITE / "modelo.js").read_text(encoding="utf-8")
    dados = json.dumps(dados_da_pagina(), ensure_ascii=False, separators=(",", ":"))
    fragmento = molde.replace("/*__MODELO__*/", motor).replace("/*__DADOS__*/", dados)
    (SITE / "artefato.html").write_text(fragmento, encoding="utf-8")

    # O molde começa por <title>, <link> e <style>: isso vai no <head> da página completa.
    cabeca, corpo = fragmento.split(CORPO, 1)
    destino = SITE / "index.html"
    destino.write_text(
        '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'{cabeca}</head>\n<body style="margin:0">\n{CORPO}{corpo}</body>\n</html>\n',
        encoding="utf-8",
    )
    return destino
