"""Confere a planilha contra o modelo em Python.

A planilha sai do openpyxl só com fórmulas. Aqui uma cópia tem a empresa, o
cenário e os ajustes manuais trocados no Painel; o LibreOffice abre a cópia,
calcula tudo e grava; lemos os valores e comparamos com o que `modelo.py`
calculou por conta própria. Se uma fórmula divergir da conta em Python, ou se a
troca de empresa buscar a linha errada, aparece aqui.
"""

import tempfile
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from valuation import commodities, historico, modelo, planilha, premissas

TOLERANCIA = 1e-6  # relativa
ERROS = ("#DIV/0!", "#REF!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "Err:")

# Os dois cenários extremos, um ajuste manual dentro da faixa e um fora dela, que a
# planilha tem de prender no limite como o Python faz.
SIMULACOES: tuple[tuple[str, dict[str, float]], ...] = (
    ("pessimista", {}),
    ("otimista", {}),
    ("moderado", {"crescimento_receita": 0.02, "ajuste_wacc": 0.005}),
    ("pessimista", {"margem_ebitda": 0.99}),
)


def _linha(ws: Worksheet, rotulo: str) -> int:
    for r in range(1, ws.max_row + 1):
        if ws.cell(r, 2).value == rotulo:
            return r
    raise KeyError(f"{ws.title}: linha '{rotulo}' não encontrada")


def _perto(a: float, b: float, tolerancia: float = TOLERANCIA) -> bool:
    return abs(a - b) <= tolerancia * max(1.0, abs(a), abs(b))


def calculada(
    molde: Workbook, ticker: str, cenario: str = "moderado", manual: dict[str, float] | None = None
) -> Workbook:
    """Escolhe empresa, cenário e ajustes no Painel de uma cópia e devolve os valores calculados."""
    ws = molde["Painel"]
    ws[planilha.CELULA_EMPRESA].value = planilha.NOME_EMPRESA[ticker]
    ws[planilha.CELULA_CENARIO].value = planilha.NOME_CENARIO[cenario]
    dados = premissas.carregar(ticker)
    capm = modelo.custo_de_capital(premissas.valores(dados))["wacc_capm"]
    for nome, linha in planilha.LINHA_VARIAVEL.items():
        chave = "ajuste_wacc" if nome == "wacc" else nome
        valor = (manual or {}).get(chave)
        # No Painel o WACC manual é a taxa inteira, não os pontos sobre o CAPM.
        ws.cell(linha, planilha.COL_MANUAL).value = (
            None if valor is None else valor + (capm if nome == "wacc" else 0.0)
        )
    with tempfile.TemporaryDirectory() as pasta:
        entrada = Path(pasta) / "entrada" / "copia.xlsx"
        entrada.parent.mkdir()
        molde.save(entrada)
        return load_workbook(planilha.recalcular(entrada, Path(pasta)), data_only=True)


def conferir(ticker: str, molde: Workbook | None = None) -> list[str]:
    """Lista de divergências da empresa (vazia quando a planilha e o modelo concordam)."""
    molde = molde or planilha.montar()
    dados = premissas.carregar(ticker)
    r = modelo.rodar(ticker, dados)
    proj, v = r["projecao"], r["valuation"]
    problemas: list[str] = []
    wb = calculada(molde, ticker)

    def comparar(onde: str, obtido: Any, esperado: float, tol: float = TOLERANCIA) -> None:
        numero = isinstance(obtido, int | float)
        if not numero or not _perto(float(obtido), float(esperado), tol):
            problemas.append(f"{ticker} {onde}: planilha {obtido!r}, modelo {esperado:.6f}")

    for ws in wb.worksheets:
        for linha in ws.iter_rows():
            for celula in linha:
                if isinstance(celula.value, str) and celula.value.startswith(ERROS):
                    problemas.append(f"{ticker} {ws.title}!{celula.coordinate}: {celula.value}")

    # Projeção e FCFF: as linhas do modelo, todos os anos
    for aba, rotulos in (
        (
            "Projeção",
            {
                "receita": "Receita líquida",
                "ebitda": "EBITDA",
                "custo_caixa": "(-) Custo dos produtos (sem depreciação)",
                "despesas": "(-) Despesas operacionais (vendas, administrativas e outras)",
                "ebit": "EBIT",
                "lucro_liquido": "Lucro líquido",
                "capex": "Capex",
                "da": "(-) Depreciação e amortização",
                "variacao_giro": "Variação do capital de giro (investimento em giro)",
                "caixa_total": "Caixa e aplicações",
                "patrimonio_liquido": "Patrimônio líquido",
                "checagem_balanco": "Checagem: ativo - passivo (tem de ser zero)",
                "roic": "ROIC (NOPAT / capital investido inicial)",
            },
        ),
        ("FCFF", {"nopat": "(=) NOPAT", "fcff": "(=) FCFF", "fcfe": "(=) FCFE"}),
    ):
        ws = wb[aba]
        for nome, rotulo in rotulos.items():
            linha_xl = _linha(ws, rotulo)
            for i, ano in enumerate(proj.columns):
                comparar(f"{aba} {nome} {ano}", ws.cell(linha_xl, 4 + i).value, proj.loc[nome, ano])
    ws = wb["Projeção"]
    base_checagem = ws.cell(_linha(ws, "Checagem: ativo - passivo (tem de ser zero)"), 3).value
    comparar("Projeção checagem do ano-base", base_checagem, 0.0)

    # Valor justo
    ws = wb["Valor justo"]
    for nome, rotulo in {
        "wacc": "WACC",
        "ev": "Valor da empresa (Enterprise Value)",
        "equity": "Valor do acionista (Equity Value)",
        "preco_justo": "Preço justo por ação",
        "preco_fcfe": "Preço por ação pelo FCFE",
        "peso_terminal": "Peso do valor terminal no valor da empresa",
    }.items():
        comparar(f"Valor justo {nome}", ws.cell(_linha(ws, rotulo), 4).value, v[nome])
    grade = modelo.sensibilidade(r["base"], proj, r["premissas"])
    topo = next(i for i in range(1, ws.max_row + 1) if ws.cell(i, 3).value == "WACC \\ g")
    for i in range(5):
        for j in range(5):
            obtido = ws.cell(topo + 1 + i, 4 + j).value
            comparar(f"Sensibilidade [{i},{j}]", obtido, grade.iat[i, j])

    # Demonstrativos: indicadores em fórmula contra os calculados em pandas
    ws = wb["Demonstrativos"]
    h = historico.carregar()
    h = h[h["ticker"] == ticker].reset_index(drop=True)
    for nome, rotulo in {
        "receita": "Receita líquida",
        "ebitda": "EBITDA (EBIT + depreciação)",
        "nopat": "NOPAT (lucro operacional após imposto de 34%)",
        "margem_ebitda": "Margem EBITDA",
        "margem_ebitda_recorrente": "Margem EBITDA sem perdas por recuperabilidade",
        "prazo_estoque": "Prazo médio de estoque (dias)",
        "divida_liquida_ebitda": "Dívida líquida / EBITDA",
        "roic": "ROIC (NOPAT / capital de giro + ativo fixo)",
    }.items():
        linha_xl = _linha(ws, rotulo)
        for i, periodo in enumerate(h["periodo"]):
            # o CSV guarda seis casas; a planilha calcula com os valores cheios
            obtido = ws.cell(linha_xl, 3 + i).value
            comparar(f"Demonstrativos {nome} {periodo}", obtido, h.at[i, nome], 1e-5)

    # Cenários: a planilha viva bate com o comparativo e o caixa fecha
    ws = wb["Cenários"]
    linha_xl = _linha(ws, "Diferença para o comparativo acima (zero sem ajuste manual)")
    comparar("Cenários: vivo x comparativo", ws.cell(linha_xl, 4).value, 0.0)
    linha_xl = _linha(ws, "Checagem: bate com a variação de caixa da projeção (zero)")
    for i in range(len(proj.columns)):
        comparar(f"Cenários: caixa {proj.columns[i]}", ws.cell(linha_xl, 4 + i).value, 0.0)

    # Múltiplos: preço implícito pelo EV/EBITDA da empresa escolhida
    ws = wb["Múltiplos"]
    from valuation import multiplos

    imp = multiplos.implicitos(multiplos.calcular())
    esperado = imp[(imp["ticker"] == ticker) & (imp["multiplo"] == "ev_ebitda")].iloc[0]
    obtido = ws.cell(_linha(ws, "Pelo EV/EBITDA das comparáveis"), 3).value
    comparar("Múltiplos EV/EBITDA", obtido, esperado["preco_implicito"])

    # Correlação: as fórmulas CORREL, SLOPE e RSQ contra o pandas
    ws = wb["Correlação"]
    stats = commodities.correlacao().set_index(["ticker", "minerio"])
    linha_xl = planilha.LINHA_STATS + planilha.TICKERS.index(ticker)
    for j, minerio in enumerate(("minerio_usd", "minerio_brl")):
        esperada = stats.loc[(ticker, minerio)]
        for d, medida in enumerate(("correlacao", "sensibilidade", "r2")):
            obtido = ws.cell(linha_xl, 3 + 3 * j + d).value
            comparar(f"Correlação {minerio} {medida}", obtido, esperada[medida], 1e-4)

    # Seletor e ajuste manual: mexer no Painel tem de dar o mesmo preço que o Python.
    for cenario, manual in SIMULACOES:
        esperado_preco = modelo.rodar(ticker, dados, cenario, manual)["valuation"]["preco_justo"]
        vj = calculada(molde, ticker, cenario, manual)["Valor justo"]
        obtido = vj.cell(_linha(vj, "Preço justo por ação"), 4).value
        comparar(f"Simulação {cenario} {manual or ''}", obtido, esperado_preco)
    return problemas
