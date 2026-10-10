"""Gera a planilha do estudo: um arquivo só, com as empresas e todas as contas em fórmulas.

Na aba Painel escolhe-se a empresa e o cenário em duas listas; o resto do arquivo
recalcula. O caminho segue o valuation pelo fluxo de caixa da empresa: FCFF, WACC,
valor presente, valor da empresa, valor do acionista e preço por ação. Cada linha
traz ao lado uma frase dizendo o que é e como foi calculada.

Como a escolha da empresa funciona: as abas Dados e Premissas guardam um bloco por
empresa, todos com o mesmo desenho e a mesma altura. As abas do modelo leem sempre
um bloco "em uso", que busca a linha certa com INDEX, somando a altura do bloco
vezes o número da empresa escolhida.

Nada de número calculado em Python colado como valor, com duas exceções: o
histórico da CVM, que é dado, e o comparativo dos cenários na aba Cenários, que o
LibreOffice e o Excel só fariam com tabela de dados.

Todas as abas com anos usam as mesmas colunas: C é o ano-base, D em diante são
os anos projetados.
"""

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference, ScatterChart, Series
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from valuation import commodities, historico, modelo, multiplos, premissas
from valuation.empresas import FOCO, SAIDA
from valuation.explicacoes import GLOSSARIO, LINHAS, PASSOS

ARQUIVO = SAIDA / "valuation_vale_csn_gerdau.xlsx"

COL_BASE = 3  # C
COL_ANO1 = 4  # D

AZUL = Font(color="0000FF")
NEGRITO = Font(bold=True)
TITULO = Font(bold=True, size=14)
GRANDE = Font(bold=True, size=13, color="1F3864")
BRANCO = Font(bold=True, color="FFFFFF")
CINZA = Font(italic=True, color="595959")
FUNDO_CABECALHO = PatternFill("solid", fgColor="1F3864")
FUNDO_SECAO = PatternFill("solid", fgColor="D9E1F2")
FUNDO_ENTRADA = PatternFill("solid", fgColor="FFF2CC")
FUNDO_RESULTADO = PatternFill("solid", fgColor="E2EFDA")
QUEBRA = Alignment(wrap_text=True, vertical="top")

MI = "#,##0;[Red]-#,##0"
PCT = "0.0%;[Red]-0.0%"
PCT2 = "0.00%;[Red]-0.00%"
DIAS = "0"
VEZES = '0.00"x"'
REAIS = '"R$" #,##0.00;[Red]-"R$" #,##0.00'
DEC = "0.00"
DATA = "DD/MM/YYYY"

FORMATO_PREMISSA = {
    "equivalencia": MI,
    "captacao_liquida": MI,
    "outros_ajustes": MI,
    "prazo_recebimento": DIAS,
    "prazo_estoque": DIAS,
    "prazo_pagamento": DIAS,
    "beta": DEC,
    "capex_perpetuidade": VEZES,
    "ajuste_wacc": PCT2,
}
NOME_CENARIO = {"pessimista": "Pessimista", "moderado": "Moderado", "otimista": "Otimista"}
TICKERS = [e.ticker for e in FOCO]
NOME_EMPRESA = {e.ticker: f"{e.nome} ({e.ticker})" for e in FOCO}

# --- Painel: endereços fixos, porque todas as outras abas dependem deles.
EMP = "'Painel'!$Y$5"  # número da empresa escolhida, na ordem de TICKERS
CEN = "'Painel'!$Y$9"  # número do cenário (1 pessimista, 2 moderado, 3 otimista)
CELULA_EMPRESA, CELULA_CENARIO = "D5", "D6"
LINHA_VARIAVEL = {"crescimento_receita": 10, "margem_ebitda": 11, "wacc": 12}
COL_USO, COL_PESS, COL_MOD, COL_OTIM, COL_MANUAL, COL_PARTIDA = 3, 4, 5, 6, 7, 8
USO = {nome: f"'Painel'!$C${linha}" for nome, linha in LINHA_VARIAVEL.items()}

Formula = Callable[[int], Any]


def L(coluna: int) -> str:  # noqa: N802 - nome curto de propósito: aparece em toda fórmula
    return get_column_letter(coluna)


class Aba:
    """Uma aba em que cada linha tem um nome, para as fórmulas se referirem a ele."""

    def __init__(self, ws: Worksheet, colunas: list[int]) -> None:
        self.ws = ws
        self.colunas = colunas
        self.linha: dict[str, int] = {}
        self.proxima = 1

    def ref(self, nome: str, coluna: int, fixa: bool = False) -> str:
        """Endereço da célula, com o nome da aba, pronto para qualquer fórmula."""
        cifrao = "$" if fixa else ""
        return f"'{self.ws.title}'!{cifrao}{L(coluna)}{cifrao}{self.linha[nome]}"

    def titulo(self, texto: str, subtitulo: str = "") -> None:
        self.ws.cell(1, 2, texto).font = TITULO
        if subtitulo:
            self.ws.cell(2, 2, subtitulo).font = CINZA
        self.proxima = 4

    def cabecalho(self, rotulos: dict[int, Any], primeira: str = "R$ milhões") -> None:
        r = self.proxima
        for c in range(2, max(rotulos) + 1):
            celula = self.ws.cell(r, c, rotulos.get(c, primeira if c == 2 else None))
            celula.font = BRANCO
            celula.fill = FUNDO_CABECALHO
            esquerda = c == 2 or c > self.colunas[-1]
            celula.alignment = Alignment(horizontal="left" if esquerda else "center")
        self.proxima += 1

    def secao(self, texto: str) -> None:
        r = self.proxima
        for c in range(2, self.colunas[-1] + 1):
            self.ws.cell(r, c).fill = FUNDO_SECAO
        self.ws.cell(r, 2, texto).font = NEGRITO
        self.proxima += 1

    def pular(self, n: int = 1) -> None:
        self.proxima += n

    def escrever(
        self,
        nome: str,
        rotulo: str,
        conteudo: Formula | dict[int, Any],
        formato: str = MI,
        destaque: bool = False,
        nota: str = "",
    ) -> None:
        r = self.linha.setdefault(nome, self.proxima)
        self.ws.cell(r, 2, rotulo).font = NEGRITO if destaque else Font()
        for c in self.colunas:
            valor = conteudo(c) if callable(conteudo) else conteudo.get(c)
            if valor is None:
                continue
            celula = self.ws.cell(r, c, valor)
            celula.number_format = formato
            if destaque:
                celula.font = NEGRITO
        if nota:
            self.ws.cell(r, self.colunas[-1] + 1, nota).font = CINZA
        self.proxima = max(self.proxima, r + 1)

    def planejar(self, nomes: list[str | None]) -> None:
        """Fixa a linha de cada nome a partir da posição atual (None = linha em branco).

        Permite que uma fórmula aponte para uma linha que ainda vai ser escrita.
        """
        r = self.proxima
        for nome in nomes:
            if nome is not None:
                self.linha[nome] = r
            r += 1

    def larguras(self, rotulo: int = 46, numeros: int = 13, nota: int = 100) -> None:
        self.ws.column_dimensions["A"].width = 2
        self.ws.column_dimensions["B"].width = rotulo
        for c in range(3, self.colunas[-1] + 1):
            self.ws.column_dimensions[L(c)].width = numeros
        self.ws.column_dimensions[L(self.colunas[-1] + 1)].width = nota
        self.ws.sheet_view.showGridLines = False


def _explicacao(aba: Aba, texto: str = "O que é e como se calcula") -> dict[int, str]:
    """Cabeçalho da coluna de explicação, que fica depois da última coluna de números."""
    return {aba.colunas[-1] + 1: texto}


def _titulo_com_empresa(ws: Worksheet, texto: str) -> None:
    """Título da aba seguido do nome da empresa escolhida no Painel."""
    ws.cell(
        1, 2, f"=\"{texto} - \"&'Painel'!${CELULA_EMPRESA[0]}${CELULA_EMPRESA[1:]}"
    ).font = TITULO


# --------------------------------------------------------------------------- Premissas

# Cada empresa ocupa um bloco de ALTURA_PREMISSAS linhas, todos com o mesmo desenho.
# O primeiro bloco é o "em uso": cada célula dele busca a mesma posição no bloco da
# empresa escolhida. `REL` diz em que linha do bloco cada premissa fica.
TOPO_PREMISSAS = 5
MERCADO = ("data_base", "acoes", "preco", "valor_de_mercado", "data_preco")


def _desenho_premissas() -> tuple[dict[str, int], int]:
    rel: dict[str, int] = {"titulo": 0, "cab_cenario": 1}
    r = 2
    for grupo, cabecalho in (
        (premissas.VARIAVEIS, None),
        (premissas.POR_ANO, "cab_ano"),
        (premissas.ESCALARES, "cab_geral"),
        (MERCADO, "cab_mercado"),
    ):
        if cabecalho:
            r += 1  # linha em branco entre as tabelas
            rel[cabecalho] = r
            r += 1
        for nome in grupo:
            rel[nome] = r
            r += 1
    return rel, r + 2


REL, ALTURA_PREMISSAS = _desenho_premissas()
FIM_PREMISSAS = TOPO_PREMISSAS + ALTURA_PREMISSAS * (len(TICKERS) + 1)


def P(nome: str, coluna: int = COL_ANO1) -> str:  # noqa: N802 - aparece em toda fórmula
    """Endereço, no bloco em uso da aba Premissas, da premissa da empresa escolhida."""
    return f"'Premissas'!${L(coluna)}${TOPO_PREMISSAS + REL[nome]}"


def _aba_premissas(
    wb: Workbook, todos: dict[str, dict[str, Any]], anos: list[int], mercado: pd.DataFrame
) -> None:
    ws = wb.create_sheet("Premissas")
    colunas = list(range(COL_ANO1, COL_ANO1 + len(anos)))
    nota_col = colunas[-1] + 1
    ws.cell(1, 2, "Premissas").font = TITULO
    ws.cell(
        2,
        2,
        "O primeiro bloco mostra a empresa escolhida no Painel e é o que o modelo lê. Para "
        "mudar uma premissa, edite as células azuis no bloco da empresa, mais abaixo.",
    ).font = CINZA

    def cabecalho(r: int, primeira: str, rotulos: dict[int, str]) -> None:
        for c in range(2, nota_col + 1):
            celula = ws.cell(r, c, rotulos.get(c, primeira if c == 2 else None))
            celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
            celula.alignment = Alignment(horizontal="left" if c in (2, nota_col) else "center")

    def bloco(topo: int, ticker: str | None) -> None:
        """Escreve um bloco: o de uma empresa (valores) ou o em uso (ticker None, fórmulas)."""
        dados = todos[ticker] if ticker else None

        def por(r: int, coluna: int, valor: Any, formato: str, origem: str = "") -> None:
            if dados is None:
                # Mesma posição, ALTURA linhas abaixo para cada empresa.
                faixa = f"{L(coluna)}$1:{L(coluna)}${FIM_PREMISSAS}"
                celula = ws.cell(r, coluna, f"=INDEX({faixa},ROW()+{ALTURA_PREMISSAS}*{EMP})")
                celula.font = NEGRITO
            else:
                celula = ws.cell(r, coluna, valor)
                celula.font, celula.fill = AZUL, FUNDO_ENTRADA
                if origem:
                    ws.cell(r, nota_col, origem).font = CINZA
            celula.number_format = formato

        if ticker is None:
            ws.cell(topo, 2, f'="EM USO: "&INDEX($L$5:$L${4 + len(TICKERS)},{EMP})').font = GRANDE
        else:
            ws.cell(topo, 2, NOME_EMPRESA[ticker]).font = GRANDE
        origem_col = "De onde veio" if dados else ""

        cabecalho(
            topo + REL["cab_cenario"],
            "Variáveis de cenário",
            {
                3: f"Partida {anos[0]}",
                4: "Pessimista",
                5: "Moderado",
                6: "Otimista",
                nota_col: origem_col,
            },
        )
        for nome, rotulo in premissas.VARIAVEIS.items():
            r = topo + REL[nome]
            ws.cell(r, 2, rotulo)
            cen = dados["cenarios"][nome] if dados else {}
            formato = FORMATO_PREMISSA.get(nome, PCT)
            if nome in premissas.COM_PARTIDA:
                por(r, 3, cen.get("partida"), formato)
            for coluna, chave in ((4, "pessimista"), (5, "moderado"), (6, "otimista")):
                por(
                    r, coluna, cen.get(chave), formato, cen.get("origem", "") if coluna == 4 else ""
                )

        cabecalho(
            topo + REL["cab_ano"],
            "Iguais nos três cenários, por ano",
            {**{c: f"{a}E" for c, a in zip(colunas, anos, strict=True)}, nota_col: origem_col},
        )
        for nome, rotulo in premissas.POR_ANO.items():
            r = topo + REL[nome]
            ws.cell(r, 2, rotulo)
            p = dados["premissas"][nome] if dados else {"valores": [None] * len(anos)}
            for coluna, valor in zip(colunas, p["valores"], strict=True):
                origem = p.get("origem", "") if coluna == colunas[0] else ""
                por(r, coluna, valor, FORMATO_PREMISSA.get(nome, PCT), origem)

        cabecalho(
            topo + REL["cab_geral"],
            "Iguais nos três cenários, gerais",
            {4: "Valor", nota_col: origem_col},
        )
        for nome, rotulo in premissas.ESCALARES.items():
            r = topo + REL[nome]
            ws.cell(r, 2, rotulo)
            p = dados["premissas"][nome] if dados else {}
            por(r, 4, p.get("valor"), FORMATO_PREMISSA.get(nome, PCT), p.get("origem", ""))

        cabecalho(
            topo + REL["cab_mercado"],
            "Dados de mercado e datas",
            {4: "Valor", nota_col: origem_col},
        )
        base = dados["base"] if dados else None
        do_mercado = mercado.loc[ticker] if ticker else None
        linhas_mercado: tuple[tuple[str, str, Any, str, str], ...] = (
            (
                "data_base",
                "Data-base do valuation",
                base.data_base if base else None,
                DATA,
                "Último balanço trimestral (ITR).",
            ),
            (
                "acoes",
                "Ações em circulação (milhões)",
                base.acoes if base else None,
                "#,##0.0",
                "CVM, composição do capital, sem ações em tesouraria.",
            ),
            (
                "preco",
                "Preço da ação (R$)",
                base.preco if base else None,
                REAIS,
                "B3, último fechamento.",
            ),
            (
                "valor_de_mercado",
                "Valor de mercado (R$ milhões)",
                base.valor_de_mercado if base else None,
                MI,
                "Ações em circulação pelo preço de cada classe.",
            ),
            (
                "data_preco",
                "Data do preço",
                do_mercado["data_preco"] if do_mercado is not None else None,
                "@",
                "Pregão do preço acima.",
            ),
        )
        for nome, rotulo, valor, formato, origem in linhas_mercado:
            r = topo + REL[nome]
            ws.cell(r, 2, rotulo)
            por(r, 4, valor, formato, origem)

    bloco(TOPO_PREMISSAS, None)
    for i, ticker in enumerate(TICKERS, start=1):
        bloco(TOPO_PREMISSAS + ALTURA_PREMISSAS * i, ticker)
    # Nomes das empresas, para o título do bloco em uso.
    ws.cell(4, 12, "Empresas").font = NEGRITO
    for i, ticker in enumerate(TICKERS):
        ws.cell(5 + i, 12, NOME_EMPRESA[ticker])

    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 56
    for c in range(3, nota_col):
        ws.column_dimensions[L(c)].width = 13
    ws.column_dimensions[L(nota_col)].width = 110
    ws.column_dimensions["L"].width = 20
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "C4"


# --------------------------------------------------------------------------- Dados e Demonstrativos

# (nome, rótulo) das linhas que entram como dado da CVM; rótulo None abre uma seção.
HIST_DADOS: tuple[tuple[str, str | None], ...] = (
    ("Demonstração do resultado", None),
    ("receita", "Receita líquida"),
    ("custo", "Custo dos produtos vendidos"),
    ("lucro_bruto", "Lucro bruto"),
    ("despesas_vendas", "Despesas com vendas"),
    ("despesas_ga", "Despesas gerais e administrativas"),
    ("perdas_recuperabilidade", "Perdas por recuperabilidade de ativos (impairment)"),
    ("despesas_operacionais", "Total de despesas/receitas operacionais"),
    ("equivalencia", "Equivalência patrimonial"),
    ("ebit", "EBIT (resultado antes do financeiro e dos tributos)"),
    ("resultado_financeiro", "Resultado financeiro"),
    ("lair", "Lucro antes dos tributos"),
    ("ir", "Imposto de renda e CSLL"),
    ("lucro_liquido", "Lucro líquido consolidado"),
    ("lucro_controladores", "Lucro atribuído aos controladores"),
    ("Fluxo de caixa", None),
    ("da", "Depreciação, amortização e exaustão"),
    ("fco", "Caixa das atividades operacionais"),
    ("capex", "Investimento em imobilizado e intangível (capex)"),
    ("dividendos_pagos", "Dividendos e JCP pagos"),
    ("Balanço patrimonial", None),
    ("caixa", "Caixa e equivalentes"),
    ("aplicacoes", "Aplicações financeiras"),
    ("contas_receber", "Contas a receber"),
    ("estoques", "Estoques"),
    ("ativo_circulante", "Ativo circulante"),
    ("investimentos", "Investimentos em coligadas"),
    ("imobilizado", "Imobilizado"),
    ("intangivel", "Intangível"),
    ("ativo_total", "Ativo total"),
    ("fornecedores", "Fornecedores"),
    ("divida_cp", "Empréstimos e financiamentos - curto prazo"),
    ("passivo_circulante", "Passivo circulante"),
    ("divida_lp", "Empréstimos e financiamentos - longo prazo"),
    ("patrimonio_liquido", "Patrimônio líquido consolidado"),
    ("minoritarios", "Participação de não controladores"),
)
LINHAS_DADOS = [nome for nome, rotulo in HIST_DADOS if rotulo is not None]
TOPO_DADOS = 4
ALTURA_DADOS = len(LINHAS_DADOS) + 3


def _aba_dados(wb: Workbook) -> list[str]:
    """Histórico da CVM das empresas do estudo, um bloco embaixo do outro. Devolve os períodos."""
    ws = wb.create_sheet("Dados")
    h = historico.carregar()
    periodos = list(h[h["ticker"] == TICKERS[0]]["periodo"])
    ws.cell(1, 2, "Dados da CVM").font = TITULO
    ws.cell(
        2,
        2,
        "Demonstrações consolidadas entregues à CVM (DFP e ITR), em R$ milhões. A aba "
        "Demonstrativos mostra o bloco da empresa escolhida no Painel.",
    ).font = CINZA
    rotulos = dict(HIST_DADOS)
    for k, ticker in enumerate(TICKERS):
        topo = TOPO_DADOS + ALTURA_DADOS * k
        da_empresa = h[h["ticker"] == ticker].reset_index(drop=True)
        if list(da_empresa["periodo"]) != periodos:
            raise ValueError(f"{ticker}: períodos diferentes dos de {TICKERS[0]}")
        ws.cell(topo, 2, NOME_EMPRESA[ticker]).font = GRANDE
        for j, periodo in enumerate(["R$ milhões", *periodos]):
            celula = ws.cell(topo + 1, 2 + j, periodo)
            celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
        for i, nome in enumerate(LINHAS_DADOS):
            ws.cell(topo + 2 + i, 2, rotulos[nome])
            for j, valor in enumerate(da_empresa[nome].round(3)):
                ws.cell(topo + 2 + i, 3 + j, float(valor)).number_format = MI
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 52
    for c in range(3, 3 + len(periodos)):
        ws.column_dimensions[L(c)].width = 13
    ws.sheet_view.showGridLines = False
    return periodos


def _aba_demonstrativos(wb: Workbook, periodos: list[str]) -> tuple[Aba, int, int]:
    """Histórico da empresa escolhida e os indicadores, em fórmula."""
    colunas = list(range(3, 3 + len(periodos)))
    aba = Aba(wb.create_sheet("Demonstrativos"), colunas)
    aba.titulo(
        "Demonstrativos",
        "DRE, fluxo de caixa e balanço da empresa escolhida no Painel, e os indicadores que saem "
        "deles. LTM = últimos doze meses; o balanço dessa coluna é o do trimestre.",
    )
    _titulo_com_empresa(aba.ws, "Demonstrativos")
    aba.cabecalho({**dict(zip(colunas, periodos, strict=True)), **_explicacao(aba, "O que é")})
    fim = TOPO_DADOS + ALTURA_DADOS * len(TICKERS)

    def do_bloco(indice: int) -> Formula:
        linha_no_bloco = TOPO_DADOS + 2 + indice
        return lambda c: (
            f"=INDEX('Dados'!{L(c)}$1:{L(c)}${fim},{linha_no_bloco}+{ALTURA_DADOS}*({EMP}-1))"
        )

    for nome, rotulo in HIST_DADOS:
        if rotulo is None:
            aba.secao(nome)
            continue
        aba.escrever(nome, rotulo, do_bloco(LINHAS_DADOS.index(nome)), nota=LINHAS.get(nome, ""))

    def x(nome: str, c: int) -> str:
        return f"{L(c)}{aba.linha[nome]}"

    def ant(nome: str, c: int) -> str | None:
        return x(nome, c - 1) if c > colunas[0] else None

    # No histórico vale a alíquota nominal, igual para todas: o passado não pode mudar
    # quando alguém troca a alíquota da projeção na aba Premissas.
    ir = historico.ALIQUOTA_IR
    aba.pular()
    aba.cabecalho(
        {**dict(zip(colunas, periodos, strict=True)), **_explicacao(aba)}, "Indicadores (fórmulas)"
    )
    indicadores: tuple[tuple[str, str, Formula, str], ...] = (
        ("ebitda", "EBITDA (EBIT + depreciação)", lambda c: f"={x('ebit', c)}+{x('da', c)}", MI),
        (
            "ebitda_recorrente",
            "EBITDA sem perdas por recuperabilidade",
            lambda c: f"={x('ebitda', c)}-{x('perdas_recuperabilidade', c)}",
            MI,
        ),
        (
            "custo_caixa",
            "Custo caixa (custo sem depreciação)",
            lambda c: f"={x('custo', c)}+{x('da', c)}",
            MI,
        ),
        (
            "outras_operacionais",
            "Outras receitas/despesas operacionais",
            lambda c: (
                f"={x('despesas_operacionais', c)}-{x('despesas_vendas', c)}"
                f"-{x('despesas_ga', c)}-{x('equivalencia', c)}"
            ),
            MI,
        ),
        (
            "nopat",
            "NOPAT (lucro operacional após imposto de 34%)",
            lambda c: f"=({x('ebit', c)}-{x('equivalencia', c)})*(1-{ir})",
            MI,
        ),
        (
            "crescimento_receita",
            "Crescimento da receita",
            lambda c: f"={x('receita', c)}/{ant('receita', c)}-1" if ant("receita", c) else None,
            PCT,
        ),
        (
            "margem_bruta",
            "Margem bruta",
            lambda c: f"={x('lucro_bruto', c)}/{x('receita', c)}",
            PCT,
        ),
        ("margem_ebitda", "Margem EBITDA", lambda c: f"={x('ebitda', c)}/{x('receita', c)}", PCT),
        (
            "margem_ebitda_recorrente",
            "Margem EBITDA sem perdas por recuperabilidade",
            lambda c: f"={x('ebitda_recorrente', c)}/{x('receita', c)}",
            PCT,
        ),
        ("margem_ebit", "Margem EBIT", lambda c: f"={x('ebit', c)}/{x('receita', c)}", PCT),
        (
            "margem_liquida",
            "Margem líquida",
            lambda c: f"={x('lucro_liquido', c)}/{x('receita', c)}",
            PCT,
        ),
        ("capex_pct", "Capex / receita", lambda c: f"={x('capex', c)}/{x('receita', c)}", PCT),
        (
            "ativo_fixo",
            "Ativo fixo (imobilizado + intangível)",
            lambda c: f"={x('imobilizado', c)}+{x('intangivel', c)}",
            MI,
        ),
        (
            "da_pct_ativo_fixo",
            "Depreciação / ativo fixo do ano anterior",
            lambda c: f"={x('da', c)}/{ant('ativo_fixo', c)}" if ant("ativo_fixo", c) else None,
            PCT,
        ),
        (
            "aliquota_efetiva",
            "Alíquota efetiva de imposto",
            lambda c: f"=-{x('ir', c)}/{x('lair', c)}",
            PCT,
        ),
        (
            "prazo_recebimento",
            "Prazo médio de recebimento (dias)",
            lambda c: f"={x('contas_receber', c)}/{x('receita', c)}*365",
            DIAS,
        ),
        (
            "prazo_estoque",
            "Prazo médio de estoque (dias)",
            lambda c: f"={x('estoques', c)}/-{x('custo_caixa', c)}*365",
            DIAS,
        ),
        (
            "prazo_pagamento",
            "Prazo médio de pagamento (dias)",
            lambda c: f"={x('fornecedores', c)}/-{x('custo_caixa', c)}*365",
            DIAS,
        ),
        (
            "ciclo_caixa",
            "Ciclo de caixa (dias)",
            lambda c: (
                f"={x('prazo_recebimento', c)}+{x('prazo_estoque', c)}-{x('prazo_pagamento', c)}"
            ),
            DIAS,
        ),
        (
            "capital_de_giro",
            "Capital de giro (receber + estoques - fornecedores)",
            lambda c: f"={x('contas_receber', c)}+{x('estoques', c)}-{x('fornecedores', c)}",
            MI,
        ),
        (
            "caixa_total",
            "Caixa e aplicações",
            lambda c: f"={x('caixa', c)}+{x('aplicacoes', c)}",
            MI,
        ),
        (
            "divida_bruta",
            "Dívida bruta",
            lambda c: f"={x('divida_cp', c)}+{x('divida_lp', c)}",
            MI,
        ),
        (
            "divida_liquida",
            "Dívida líquida",
            lambda c: f"={x('divida_bruta', c)}-{x('caixa_total', c)}",
            MI,
        ),
        (
            "divida_liquida_ebitda",
            "Dívida líquida / EBITDA",
            lambda c: f"={x('divida_liquida', c)}/{x('ebitda_recorrente', c)}",
            VEZES,
        ),
        (
            "liquidez_corrente",
            "Liquidez corrente",
            lambda c: f"={x('ativo_circulante', c)}/{x('passivo_circulante', c)}",
            DEC,
        ),
        (
            "roe",
            "ROE (lucro dos controladores / patrimônio dos controladores)",
            lambda c: (
                f"={x('lucro_controladores', c)}"
                f"/({x('patrimonio_liquido', c)}-{x('minoritarios', c)})"
            ),
            PCT,
        ),
        (
            "roic",
            "ROIC (NOPAT / capital de giro + ativo fixo)",
            lambda c: f"={x('nopat', c)}/({x('capital_de_giro', c)}+{x('ativo_fixo', c)})",
            PCT,
        ),
        (
            "fcl_simples",
            "Caixa operacional menos capex",
            lambda c: f"={x('fco', c)}-{x('capex', c)}",
            MI,
        ),
    )
    aba.planejar([nome for nome, *_ in indicadores])
    for nome, rotulo, formula, formato in indicadores:
        aba.escrever(nome, rotulo, formula, formato, nota=LINHAS.get(nome, ""))

    aba.larguras(rotulo=58)
    aba.ws.freeze_panes = "C5"
    return aba, colunas[periodos.index("2025")], colunas[-1]


# --------------------------------------------------------------------------- Projeção e FCFF

LINHAS_FCFF: list[str | None] = [
    "s_fcff", "ebit", "equivalencia", "imposto", "nopat", "da", "capex", "variacao_giro", "fcff",
    None,
    "s_fcfe", "lucro_liquido", "equivalencia_e", "da_e", "capex_e", "variacao_giro_e", "captacao",
    "fcfe",
    None,
    "s_terminal", "capex_terminal", "fcff_terminal", "fcfe_terminal",
]  # fmt: skip


def _aba_projecao(wb: Workbook, anos: list[int], hist: Aba, col_hist: int, fcff: Aba) -> Aba:
    proj_cols = list(range(COL_ANO1, COL_ANO1 + len(anos)))
    aba = Aba(wb.create_sheet("Projeção"), [COL_BASE, *proj_cols])
    aba.titulo(
        "Projeção",
        "DRE, investimento, capital de giro e balanço, ligados entre si. Custos e despesas em "
        "valor positivo. 2025 é o realizado; os outros anos são fórmulas.",
    )
    _titulo_com_empresa(aba.ws, "Projeção")
    anos_cab = {COL_BASE: anos[0] - 1, **{c: f"{a}E" for c, a in zip(proj_cols, anos, strict=True)}}
    aba.cabecalho({**anos_cab, **_explicacao(aba, "Como se calcula")})

    def x(nome: str, c: int) -> str:
        return f"{L(c)}{aba.linha[nome]}"

    def a(nome: str, c: int) -> str:  # ano anterior
        return x(nome, c - 1)

    def h(nome: str) -> str:
        return hist.ref(nome, col_hist)

    def linha(
        nome: str,
        rotulo: str,
        base: str | None,
        formula: Formula,
        formato: str = MI,
        destaque: bool = False,
    ) -> None:
        aba.escrever(
            nome,
            rotulo,
            lambda c: base if c == COL_BASE else formula(c),
            formato,
            destaque=destaque,
            nota=LINHAS.get(f"p_{nome}", ""),
        )

    passos = len(anos) - 1
    estrutura: list[str | None] = [
        "s_cen", "crescimento", "margem", None,
        "s_dre", "receita", "custo_caixa", "despesas", "equivalencia", "ebitda", "da", "ebit",
        "receita_financeira", "despesa_financeira", "resultado_financeiro", "lair", "ir",
        "lucro_liquido", None,
        "s_inv", "capex", "ativo_fixo", "contas_receber", "estoques", "fornecedores",
        "capital_de_giro", "variacao_giro", None,
        "s_cx", "dividendos", "variacao_caixa", None,
        "s_bp", "caixa_total", "investimentos", "outros_ativos", "ativo_total", "divida_bruta",
        "outros_passivos", "patrimonio_liquido", "passivo_e_pl", "checagem_balanco", None,
        "s_ind", "margem_ebit", "divida_liquida", "divida_liquida_ebitda", "roic",
    ]  # fmt: skip
    aba.planejar(estrutura)

    def secao(nome: str, texto: str) -> None:
        aba.proxima = aba.linha[nome]
        aba.secao(texto)

    secao("s_cen", "Do cenário para cada ano (vem do Painel)")
    partida_crescimento, partida_margem = P("crescimento_receita", 3), P("margem_ebitda", 3)
    linha(
        "crescimento",
        "Crescimento da receita",
        None,
        lambda c: "=" + (partida_crescimento if c == proj_cols[0] else USO["crescimento_receita"]),
        PCT,
    )
    linha(
        "margem",
        "Margem EBITDA",
        None,
        lambda c: (
            f"={partida_margem}+({USO['margem_ebitda']}-{partida_margem})"
            f"*{c - proj_cols[0]}/{passos}"
        ),
        PCT,
    )

    secao("s_dre", "Demonstração do resultado")
    linha(
        "receita",
        "Receita líquida",
        f"={h('receita')}",
        lambda c: f"={a('receita', c)}*(1+{x('crescimento', c)})",
        destaque=True,
    )
    linha(
        "custo_caixa",
        "(-) Custo dos produtos (sem depreciação)",
        f"=-{h('custo_caixa')}",
        lambda c: f"={x('receita', c)}-{x('despesas', c)}+{x('equivalencia', c)}-{x('ebitda', c)}",
    )
    linha(
        "despesas",
        "(-) Despesas operacionais (vendas, administrativas e outras)",
        f"=-({h('despesas_vendas')}+{h('despesas_ga')}+{h('outras_operacionais')})",
        lambda c: f"={x('receita', c)}*{P('despesas_pct', c)}",
    )
    linha(
        "equivalencia",
        "(+/-) Equivalência patrimonial",
        f"={h('equivalencia')}",
        lambda c: f"={P('equivalencia', c)}",
    )
    linha(
        "ebitda",
        "EBITDA",
        f"={x('receita', COL_BASE)}-{x('custo_caixa', COL_BASE)}-{x('despesas', COL_BASE)}"
        f"+{x('equivalencia', COL_BASE)}",
        lambda c: f"={x('receita', c)}*{x('margem', c)}",
        destaque=True,
    )
    linha(
        "da",
        "(-) Depreciação e amortização",
        f"={h('da')}",
        lambda c: f"={a('ativo_fixo', c)}*{P('depreciacao_pct', c)}",
    )
    ebit: Formula = lambda c: f"={x('ebitda', c)}-{x('da', c)}"  # noqa: E731
    linha("ebit", "EBIT", ebit(COL_BASE), ebit, destaque=True)
    linha(
        "receita_financeira",
        "(+) Rendimento do caixa",
        None,
        lambda c: f"={a('caixa_total', c)}*{P('rendimento_caixa')}",
    )
    linha(
        "despesa_financeira",
        "(-) Juros da dívida",
        None,
        lambda c: f"={a('divida_bruta', c)}*{P('custo_divida')}",
    )
    linha(
        "resultado_financeiro",
        "(+/-) Resultado financeiro",
        f"={h('resultado_financeiro')}",
        lambda c: f"={x('receita_financeira', c)}-{x('despesa_financeira', c)}",
    )
    lair: Formula = lambda c: f"={x('ebit', c)}+{x('resultado_financeiro', c)}"  # noqa: E731
    linha("lair", "Lucro antes dos tributos", lair(COL_BASE), lair)
    linha(
        "ir",
        "(-) Imposto de renda e CSLL",
        f"=-{h('ir')}",
        lambda c: f"=MAX(0,{x('lair', c)}-{x('equivalencia', c)})*{P('aliquota_ir')}",
    )
    lucro: Formula = lambda c: f"={x('lair', c)}-{x('ir', c)}"  # noqa: E731
    linha("lucro_liquido", "Lucro líquido", lucro(COL_BASE), lucro, destaque=True)

    secao("s_inv", "Investimento, depreciação e capital de giro")
    linha("capex", "Capex", f"={h('capex')}", lambda c: f"={x('receita', c)}*{P('capex_pct', c)}")
    linha(
        "ativo_fixo",
        "Ativo fixo (imobilizado + intangível)",
        f"={h('ativo_fixo')}",
        lambda c: f"={a('ativo_fixo', c)}+{x('capex', c)}-{x('da', c)}",
    )
    linha(
        "contas_receber",
        "Contas a receber",
        f"={h('contas_receber')}",
        lambda c: f"={x('receita', c)}*{P('prazo_recebimento', c)}/365",
    )
    linha(
        "estoques",
        "Estoques",
        f"={h('estoques')}",
        lambda c: f"={x('custo_caixa', c)}*{P('prazo_estoque', c)}/365",
    )
    linha(
        "fornecedores",
        "Fornecedores",
        f"={h('fornecedores')}",
        lambda c: f"={x('custo_caixa', c)}*{P('prazo_pagamento', c)}/365",
    )
    giro: Formula = lambda c: (  # noqa: E731
        f"={x('contas_receber', c)}+{x('estoques', c)}-{x('fornecedores', c)}"
    )
    linha("capital_de_giro", "Capital de giro", giro(COL_BASE), giro, destaque=True)
    linha(
        "variacao_giro",
        "Variação do capital de giro (investimento em giro)",
        None,
        lambda c: f"={x('capital_de_giro', c)}-{a('capital_de_giro', c)}",
    )

    secao("s_cx", "Do lucro ao caixa")
    linha(
        "dividendos",
        "(-) Dividendos",
        None,
        lambda c: f"=MAX(0,{x('lucro_liquido', c)})*{P('payout')}",
    )
    linha(
        "variacao_caixa",
        "Variação do caixa (FCFE da aba FCFF menos dividendos)",
        None,
        lambda c: f"={fcff.ref('fcfe', c)}-{x('dividendos', c)}",
    )

    secao("s_bp", "Balanço patrimonial resumido")
    linha(
        "caixa_total",
        "Caixa e aplicações",
        f"={h('caixa_total')}",
        lambda c: f"={a('caixa_total', c)}+{x('variacao_caixa', c)}",
    )
    linha(
        "investimentos",
        "Investimentos em coligadas",
        f"={h('investimentos')}",
        lambda c: f"={a('investimentos', c)}+{x('equivalencia', c)}",
    )
    linha(
        "outros_ativos",
        "Outros ativos (mantidos)",
        f"={h('ativo_total')}-{x('caixa_total', COL_BASE)}-{x('contas_receber', COL_BASE)}"
        f"-{x('estoques', COL_BASE)}-{x('ativo_fixo', COL_BASE)}-{x('investimentos', COL_BASE)}",
        lambda c: f"={a('outros_ativos', c)}",
    )
    ativo: Formula = lambda c: (  # noqa: E731
        f"={x('caixa_total', c)}+{x('contas_receber', c)}+{x('estoques', c)}"
        f"+{x('ativo_fixo', c)}+{x('investimentos', c)}+{x('outros_ativos', c)}"
    )
    linha("ativo_total", "Ativo total", ativo(COL_BASE), ativo, destaque=True)
    linha(
        "divida_bruta",
        "Dívida bruta",
        f"={h('divida_bruta')}",
        lambda c: f"={a('divida_bruta', c)}+{P('captacao_liquida', c)}",
    )
    linha(
        "outros_passivos",
        "Outros passivos (mantidos)",
        f"={h('ativo_total')}-{x('fornecedores', COL_BASE)}-{x('divida_bruta', COL_BASE)}"
        f"-{x('patrimonio_liquido', COL_BASE)}",
        lambda c: f"={a('outros_passivos', c)}",
    )
    linha(
        "patrimonio_liquido",
        "Patrimônio líquido",
        f"={h('patrimonio_liquido')}",
        lambda c: f"={a('patrimonio_liquido', c)}+{x('lucro_liquido', c)}-{x('dividendos', c)}",
    )
    passivo: Formula = lambda c: (  # noqa: E731
        f"={x('fornecedores', c)}+{x('divida_bruta', c)}+{x('outros_passivos', c)}"
        f"+{x('patrimonio_liquido', c)}"
    )
    linha("passivo_e_pl", "Passivo + patrimônio líquido", passivo(COL_BASE), passivo, destaque=True)
    checagem: Formula = lambda c: f"=ROUND({x('ativo_total', c)}-{x('passivo_e_pl', c)},3)"  # noqa: E731
    linha(
        "checagem_balanco",
        "Checagem: ativo - passivo (tem de ser zero)",
        checagem(COL_BASE),
        checagem,
    )

    secao("s_ind", "Indicadores")
    margem_ebit: Formula = lambda c: f"={x('ebit', c)}/{x('receita', c)}"  # noqa: E731
    linha("margem_ebit", "Margem EBIT", margem_ebit(COL_BASE), margem_ebit, PCT)
    dl: Formula = lambda c: f"={x('divida_bruta', c)}-{x('caixa_total', c)}"  # noqa: E731
    linha("divida_liquida", "Dívida líquida", dl(COL_BASE), dl)
    alav: Formula = lambda c: f"={x('divida_liquida', c)}/{x('ebitda', c)}"  # noqa: E731
    linha("divida_liquida_ebitda", "Dívida líquida / EBITDA", alav(COL_BASE), alav, VEZES)
    linha(
        "roic",
        "ROIC (NOPAT / capital investido inicial)",
        None,
        lambda c: f"={fcff.ref('nopat', c)}/({a('capital_de_giro', c)}+{a('ativo_fixo', c)})",
        PCT,
    )

    aba.larguras(rotulo=56)
    aba.ws.freeze_panes = "C5"
    return aba


def _aba_fcff(aba: Aba, anos: list[int], proj: Aba) -> None:
    """Preenche a aba FCFF, cujas linhas já foram reservadas para a Projeção poder apontar."""
    ultimo = aba.colunas[-1]

    def x(nome: str, c: int) -> str:
        return f"{L(c)}{aba.linha[nome]}"

    def pr(nome: str, c: int) -> str:
        return proj.ref(nome, c)

    def linha(nome: str, rotulo: str, formula: Formula, chave: str, destaque: bool = False) -> None:
        aba.escrever(nome, rotulo, formula, destaque=destaque, nota=LINHAS[chave])

    def unico(nome: str, rotulo: str, formula: str, chave: str, destaque: bool = False) -> None:
        aba.escrever(nome, rotulo, {COL_ANO1: formula}, destaque=destaque, nota=LINHAS[chave])

    def secao(nome: str, texto: str) -> None:
        aba.proxima = aba.linha[nome]
        aba.secao(texto)

    secao("s_fcff", "FCFF: o caixa livre da empresa, para credores e acionistas")
    linha("ebit", "EBIT", lambda c: f"={pr('ebit', c)}", "f_ebit")
    linha(
        "equivalencia",
        "(-) Equivalência patrimonial",
        lambda c: f"={pr('equivalencia', c)}",
        "f_equivalencia",
    )
    linha(
        "imposto",
        "(-) Imposto sobre o lucro da operação",
        lambda c: f"=({x('ebit', c)}-{x('equivalencia', c)})*{P('aliquota_ir')}",
        "f_imposto",
    )
    linha(
        "nopat",
        "(=) NOPAT",
        lambda c: f"={x('ebit', c)}-{x('equivalencia', c)}-{x('imposto', c)}",
        "f_nopat",
        destaque=True,
    )
    linha("da", "(+) Depreciação e amortização", lambda c: f"={pr('da', c)}", "f_da")
    linha("capex", "(-) Capex", lambda c: f"={pr('capex', c)}", "f_capex")
    linha(
        "variacao_giro",
        "(-) Variação do capital de giro",
        lambda c: f"={pr('variacao_giro', c)}",
        "f_variacao_giro",
    )
    linha(
        "fcff",
        "(=) FCFF",
        lambda c: f"={x('nopat', c)}+{x('da', c)}-{x('capex', c)}-{x('variacao_giro', c)}",
        "f_fcff",
        destaque=True,
    )
    for c in aba.colunas:
        aba.ws.cell(aba.linha["fcff"], c).fill = FUNDO_RESULTADO

    secao("s_fcfe", "FCFE: o caixa livre só do acionista")
    linha(
        "lucro_liquido", "Lucro líquido", lambda c: f"={pr('lucro_liquido', c)}", "f_lucro_liquido"
    )
    linha(
        "equivalencia_e",
        "(-) Equivalência patrimonial",
        lambda c: f"={pr('equivalencia', c)}",
        "f_equivalencia",
    )
    linha("da_e", "(+) Depreciação e amortização", lambda c: f"={pr('da', c)}", "f_da")
    linha("capex_e", "(-) Capex", lambda c: f"={pr('capex', c)}", "f_capex")
    linha(
        "variacao_giro_e",
        "(-) Variação do capital de giro",
        lambda c: f"={pr('variacao_giro', c)}",
        "f_variacao_giro",
    )
    linha(
        "captacao",
        "(+) Captação líquida de dívida",
        lambda c: f"={P('captacao_liquida', c)}",
        "f_captacao",
    )
    linha(
        "fcfe",
        "(=) FCFE",
        lambda c: (
            f"={x('lucro_liquido', c)}-{x('equivalencia_e', c)}+{x('da_e', c)}-{x('capex_e', c)}"
            f"-{x('variacao_giro_e', c)}+{x('captacao', c)}"
        ),
        "f_fcfe",
        destaque=True,
    )

    secao("s_terminal", f"Fluxo de {anos[-1]} ajustado para a perpetuidade")
    unico(
        "capex_terminal",
        "Capex de reposição",
        f"={P('capex_perpetuidade')}*{x('da', ultimo)}",
        "f_capex_terminal",
    )
    unico(
        "fcff_terminal",
        f"FCFF normalizado de {anos[-1]}",
        f"={x('nopat', ultimo)}+{x('da', ultimo)}-{x('capex_terminal', COL_ANO1)}"
        f"-{x('variacao_giro', ultimo)}",
        "f_fcff_terminal",
        destaque=True,
    )
    unico(
        "fcfe_terminal",
        f"FCFE normalizado de {anos[-1]}",
        f"={x('lucro_liquido', ultimo)}-{x('equivalencia_e', ultimo)}+{x('da_e', ultimo)}"
        f"-{x('capex_terminal', COL_ANO1)}-{x('variacao_giro_e', ultimo)}+{x('captacao', ultimo)}",
        "f_fcfe_terminal",
    )
    aba.larguras(rotulo=52)
    aba.ws.freeze_panes = "C5"


# --------------------------------------------------------------------------- WACC e valor justo


def _aba_wacc(wb: Workbook, hist: Aba, col_ltm: int) -> Aba:
    aba = Aba(wb.create_sheet("WACC"), [COL_ANO1])
    aba.titulo(
        "Custo de capital",
        "CAPM para o capital próprio; WACC é a média com o custo da dívida depois do imposto.",
    )
    _titulo_com_empresa(aba.ws, "Custo de capital")

    def x(nome: str) -> str:
        return f"{L(COL_ANO1)}{aba.linha[nome]}"

    def linha(
        nome: str, rotulo: str, formula: str, formato: str = PCT2, destaque: bool = False
    ) -> None:
        aba.escrever(
            nome, rotulo, {COL_ANO1: formula}, formato, destaque=destaque, nota=LINHAS[f"w_{nome}"]
        )

    aba.cabecalho({COL_ANO1: "Valor", **_explicacao(aba)}, "Capital próprio (CAPM)")
    linha("rf", "Juro sem risco (Rf)", f"={P('juro_sem_risco')}")
    linha("beta", "Beta", f"={P('beta')}", DEC)
    linha("premio", "Prêmio de risco de mercado", f"={P('premio_mercado')}")
    linha("adicional", "Prêmio adicional", f"={P('premio_adicional')}")
    linha(
        "ke",
        "Custo do capital próprio (Ke)",
        f"={x('rf')}+{x('beta')}*{x('premio')}+{x('adicional')}",
        destaque=True,
    )
    aba.pular()
    aba.cabecalho({COL_ANO1: "Valor", **_explicacao(aba)}, "Dívida")
    linha("kd", "Custo da dívida antes do imposto (Kd)", f"={P('custo_divida')}")
    linha("ir", "Alíquota de IR e CSLL", f"={P('aliquota_ir')}")
    linha(
        "kd_liquido", "Custo da dívida após o imposto", f"={x('kd')}*(1-{x('ir')})", destaque=True
    )
    aba.pular()
    aba.cabecalho({COL_ANO1: "Valor", **_explicacao(aba)}, "Média ponderada")
    linha("wd", "Peso da dívida", f"={P('peso_divida')}")
    linha("we", "Peso do capital próprio", f"=1-{x('wd')}")
    linha(
        "wacc",
        "WACC pelo CAPM",
        f"={x('ke')}*{x('we')}+{x('kd_liquido')}*{x('wd')}",
        destaque=True,
    )
    aba.pular()
    aba.cabecalho({COL_ANO1: "Valor", **_explicacao(aba)}, "Cenário (vem do Painel)")
    linha("wacc_uso", "WACC em uso", f"={USO['wacc']}", destaque=True)
    linha("ajuste", "Diferença para o CAPM", f"={x('wacc_uso')}-{x('wacc')}")
    linha("ke_uso", "Ke em uso", f"={x('ke')}+{x('ajuste')}")
    aba.ws.cell(aba.linha["wacc_uso"], COL_ANO1).fill = FUNDO_RESULTADO
    aba.pular()
    aba.cabecalho(
        {COL_ANO1: "Valor", **_explicacao(aba)}, "Referência: estrutura a valor de mercado"
    )
    linha("mercado", "Valor de mercado (R$ milhões)", f"={P('valor_de_mercado')}", MI)
    linha(
        "divida",
        "Dívida bruta na data-base (R$ milhões)",
        f"={hist.ref('divida_bruta', col_ltm)}",
        MI,
    )
    linha(
        "wd_mercado",
        "Peso da dívida a valor de mercado",
        f"={x('divida')}/({x('divida')}+{x('mercado')})",
    )
    aba.larguras(rotulo=44, numeros=14)
    return aba


def _aba_valor(
    wb: Workbook, anos: list[int], wacc: Aba, fcff: Aba, proj: Aba, hist: Aba, col_ltm: int
) -> Aba:
    cols = list(range(COL_ANO1, COL_ANO1 + len(anos)))
    ultimo = cols[-1]
    aba = Aba(wb.create_sheet("Valor justo"), cols)
    ws = aba.ws
    aba.titulo(
        "Valor justo",
        "Os fluxos de caixa trazidos a valor de hoje, o valor da empresa, o valor do acionista e "
        "o preço por ação.",
    )
    _titulo_com_empresa(ws, "Valor justo")
    aba.cabecalho({**{c: f"{a}E" for c, a in zip(cols, anos, strict=True)}, **_explicacao(aba)})

    def x(nome: str, c: int = COL_ANO1) -> str:
        return f"{L(c)}{aba.linha[nome]}"

    def fx(nome: str, c: int = COL_ANO1) -> str:
        return f"${L(c)}${aba.linha[nome]}"

    def faixa(nome: str) -> str:
        r = aba.linha[nome]
        return f"${L(cols[0])}${r}:${L(ultimo)}${r}"

    def por_ano(
        nome: str, rotulo: str, formula: Formula, formato: str = MI, destaque: bool = False
    ) -> None:
        aba.escrever(nome, rotulo, formula, formato, destaque=destaque, nota=LINHAS[f"v_{nome}"])

    def unico(
        nome: str, rotulo: str, formula: str, formato: str = MI, destaque: bool = False
    ) -> None:
        aba.escrever(
            nome, rotulo, {COL_ANO1: formula}, formato, destaque=destaque, nota=LINHAS[f"v_{nome}"]
        )

    wacc_uso = wacc.ref("wacc_uso", COL_ANO1, fixa=True)
    ke_uso = wacc.ref("ke_uso", COL_ANO1, fixa=True)
    ano1 = anos[0]

    aba.secao("Fluxo da empresa (FCFF), descontado pelo WACC")
    por_ano("fcff", "FCFF", lambda c: f"={fcff.ref('fcff', c)}", destaque=True)
    por_ano(
        "fracao",
        "Parte do ano que entra no valor",
        lambda c: f"=(DATE({ano1},12,31)-{P('data_base')})/365" if c == cols[0] else 1,
        "0.000",
    )
    por_ano(
        "fim",
        "Fim do período (anos desde a data-base)",
        lambda c: f"={x('fracao', c)}" if c == cols[0] else f"={x('fim', c - 1)}+1",
        "0.000",
    )
    por_ano(
        "meio",
        "Meio do período (quando o caixa entra, em média)",
        lambda c: f"={x('fim', c)}-{x('fracao', c)}/2",
        "0.000",
    )
    por_ano("fator", "Fator de desconto", lambda c: f"=1/(1+{wacc_uso})^{x('meio', c)}", "0.0000")
    por_ano(
        "vp",
        "Valor presente do fluxo",
        lambda c: f"={x('fcff', c)}*{x('fracao', c)}*{x('fator', c)}",
        destaque=True,
    )
    aba.pular()

    aba.secao("Perpetuidade (Gordon)")
    unico("wacc", "WACC", f"={wacc_uso}", PCT2)
    unico("g", "Crescimento na perpetuidade (g)", f"={P('crescimento_perpetuo')}", PCT2)
    unico(
        "fcff_terminal",
        f"FCFF normalizado de {anos[-1]}",
        f"={fcff.ref('fcff_terminal', COL_ANO1)}",
    )
    unico(
        "vt",
        "Valor terminal no fim do último ano",
        f"={x('fcff_terminal')}*(1+{x('g')})/({x('wacc')}-{x('g')})",
    )
    unico(
        "vp_vt",
        "Valor presente do valor terminal",
        f"={x('vt')}/(1+{x('wacc')})^{x('fim', ultimo)}",
    )
    aba.pular()

    aba.secao("Do valor da empresa ao preço por ação")
    unico("soma_vp", "Valor presente dos fluxos projetados", f"=SUM({faixa('vp')})")
    unico(
        "ev",
        "Valor da empresa (Enterprise Value)",
        f"={x('soma_vp')}+{x('vp_vt')}",
        destaque=True,
    )
    unico(
        "divida_liquida",
        "(-) Dívida líquida na data-base",
        f"={hist.ref('divida_liquida', col_ltm)}",
    )
    unico(
        "minoritarios",
        "(-) Participação de não controladores",
        f"={hist.ref('minoritarios', col_ltm)}",
    )
    unico(
        "investimentos",
        "(+) Investimentos em coligadas (valor contábil)",
        f"={hist.ref('investimentos', col_ltm)}",
    )
    unico("outros", "(-) Outros passivos tratados como dívida", f"={P('outros_ajustes')}")
    unico(
        "equity",
        "Valor do acionista (Equity Value)",
        f"={x('ev')}-{x('divida_liquida')}-{x('minoritarios')}+{x('investimentos')}-{x('outros')}",
        destaque=True,
    )
    unico("acoes", "Ações em circulação (milhões)", f"={P('acoes')}", "#,##0.0")
    unico(
        "preco_justo", "Preço justo por ação", f"={x('equity')}/{x('acoes')}", REAIS, destaque=True
    )
    ws.cell(aba.linha["preco_justo"], COL_ANO1).fill = FUNDO_RESULTADO
    unico("preco", "Preço de mercado", f"={P('preco')}", REAIS)
    unico(
        "potencial", "Diferença para o preço de mercado", f"={x('preco_justo')}/{x('preco')}-1", PCT
    )
    unico("peso_vt", "Peso do valor terminal no valor da empresa", f"={x('vp_vt')}/{x('ev')}", PCT)
    unico(
        "ev_ebitda",
        f"EV / EBITDA {anos[0]}E implícito",
        f"={x('ev')}/{proj.ref('ebitda', cols[0])}",
        VEZES,
    )
    aba.pular()

    aba.secao("Conferência pelo fluxo do acionista (FCFE), descontado pelo Ke")
    por_ano("fcfe", "FCFE", lambda c: f"={fcff.ref('fcfe', c)}", destaque=True)
    por_ano(
        "fator_ke",
        "Fator de desconto pelo Ke",
        lambda c: f"=1/(1+{ke_uso})^{x('meio', c)}",
        "0.0000",
    )
    por_ano(
        "vp_fcfe",
        "Valor presente do FCFE",
        lambda c: f"={x('fcfe', c)}*{x('fracao', c)}*{x('fator_ke', c)}",
    )
    unico("ke", "Custo do capital próprio (Ke) em uso", f"={ke_uso}", PCT2)
    unico(
        "fcfe_terminal",
        f"FCFE normalizado de {anos[-1]}",
        f"={fcff.ref('fcfe_terminal', COL_ANO1)}",
    )
    unico(
        "vp_vt_fcfe",
        "Valor presente do valor terminal do FCFE",
        f"={x('fcfe_terminal')}*(1+{x('g')})/({x('ke')}-{x('g')})/(1+{x('ke')})^{x('fim', ultimo)}",
    )
    unico(
        "equity_fcfe",
        "Valor do acionista pelo FCFE",
        f"=SUM({faixa('vp_fcfe')})+{x('vp_vt_fcfe')}-{x('minoritarios')}+{x('investimentos')}"
        f"-{x('outros')}",
        destaque=True,
    )
    unico("preco_fcfe", "Preço por ação pelo FCFE", f"={x('equity_fcfe')}/{x('acoes')}", REAIS)
    aba.pular()

    # Sensibilidade: cada célula refaz o desconto inteiro com o seu WACC e o seu g.
    aba.secao("Sensibilidade do preço justo: WACC (linhas) x crescimento perpétuo (colunas)")
    topo = aba.proxima
    canto = ws.cell(topo, COL_BASE, "WACC \\ g")
    canto.font, canto.fill = BRANCO, FUNDO_CABECALHO
    for j, passo in enumerate((-2, -1, 0, 1, 2)):
        celula = ws.cell(topo, COL_ANO1 + j, f"={fx('g')}+{passo}*0.005")
        celula.number_format, celula.font, celula.fill = PCT, BRANCO, FUNDO_CABECALHO
    for i, passo in enumerate((-2, -1, 0, 1, 2)):
        r = topo + 1 + i
        lado = ws.cell(r, COL_BASE, f"={fx('wacc')}+{passo}*0.01")
        lado.number_format, lado.font, lado.fill = PCT, BRANCO, FUNDO_CABECALHO
        for j in range(5):
            w = f"${L(COL_BASE)}{r}"
            gg = f"{L(COL_ANO1 + j)}${topo}"
            celula = ws.cell(
                r,
                COL_ANO1 + j,
                f"=(SUMPRODUCT({faixa('fcff')}*{faixa('fracao')}/(1+{w})^{faixa('meio')})"
                f"+{fx('fcff_terminal')}*(1+{gg})/({w}-{gg})/(1+{w})^{fx('fim', ultimo)}"
                f"-{fx('divida_liquida')}-{fx('minoritarios')}+{fx('investimentos')}-{fx('outros')})"
                f"/{fx('acoes')}",
            )
            celula.number_format = REAIS
            if i == 2 and j == 2:
                celula.fill, celula.font = FUNDO_RESULTADO, NEGRITO
    ws.cell(
        topo,
        cols[-1] + 1,
        "Cada célula refaz a conta inteira com o WACC da linha e o g da coluna. "
        "A do meio é o preço justo.",
    ).font = CINZA
    aba.proxima = topo + 7
    aba.larguras(rotulo=50, numeros=14)
    ws.freeze_panes = "C5"
    return aba


# --------------------------------------------------------------------------- Múltiplos


def _aba_multiplos(wb: Workbook, valor: Aba) -> None:
    t = multiplos.calcular()
    ordem = [*TICKERS, *[k for k in t.index if k not in TICKERS]]  # as do estudo em cima
    ws = wb.create_sheet("Múltiplos")
    ws.cell(1, 2, "Valuation por múltiplos").font = TITULO
    ws.cell(
        2,
        2,
        "Quanto o mercado paga pelas comparáveis, com os números dos últimos doze meses. A "
        "mediana das outras quatro, aplicada à empresa escolhida, dá um preço implícito. "
        "EBITDA e EBIT entram sem as perdas por recuperabilidade; o lucro é o divulgado.",
    ).font = CINZA
    campos = (
        ("Setor", "setor", None),
        ("Preço", "preco", REAIS),
        ("Ações (milhões)", "acoes", "#,##0.0"),
        ("Valor de mercado", "valor_de_mercado", MI),
        ("Dívida líquida", "divida_liquida", MI),
        ("Minoritários", "minoritarios", MI),
        ("EV", None, MI),
        ("EBITDA", "ebitda", MI),
        ("EBIT", "ebit", MI),
        ("Lucro", "lucro", MI),
        ("Patrimônio", "patrimonio", MI),
        ("EV/EBITDA", None, VEZES),
        ("EV/EBIT", None, VEZES),
        ("P/L", None, VEZES),
        ("P/VP", None, VEZES),
    )
    col = {rotulo: 3 + i for i, (rotulo, _, _) in enumerate(campos)}
    cab = 4
    for c, texto in [(2, "Empresa (R$ milhões)"), *[(c, rotulo) for rotulo, c in col.items()]]:
        celula = ws.cell(cab, c, texto)
        celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
        celula.alignment = Alignment(horizontal="left" if c == 2 else "center")
    primeira = cab + 1
    for i, k in enumerate(ordem):
        r = primeira + i
        ws.cell(r, 2, f"{t.loc[k, 'empresa']} ({k})")

        def c(rotulo: str, r: int = r) -> str:
            return f"{L(col[rotulo])}{r}"

        for rotulo, campo, formato in campos:
            if campo is not None:
                bruto = t.loc[k, campo]
                celula = ws.cell(r, col[rotulo], bruto if isinstance(bruto, str) else float(bruto))
            else:
                formula = {
                    "EV": f"={c('Valor de mercado')}+{c('Dívida líquida')}+{c('Minoritários')}",
                    "EV/EBITDA": f"={c('EV')}/{c('EBITDA')}",
                    "EV/EBIT": f"={c('EV')}/{c('EBIT')}",
                    "P/L": f'=IF({c("Lucro")}>0,{c("Valor de mercado")}/{c("Lucro")},"n.a.")',
                    "P/VP": f"={c('Valor de mercado')}/{c('Patrimônio')}",
                }[rotulo]
                celula = ws.cell(r, col[rotulo], formula)
            if formato:
                celula.number_format = formato
            celula.alignment = Alignment(horizontal="right")
    ultima = primeira + len(ordem) - 1
    razoes = ("EV/EBITDA", "EV/EBIT", "P/L", "P/VP")

    # Uma mediana para cada empresa do estudo, sempre sem ela mesma.
    medianas = ultima + 2
    for i, ticker in enumerate(TICKERS):
        r = medianas + i
        ws.cell(r, 2, f"Mediana das comparáveis de {ticker} (sem ela)").font = NEGRITO
        for rotulo in razoes:
            letra = L(col[rotulo])
            pares = ",".join(
                f"{letra}{linha}" for linha in range(primeira, ultima + 1) if linha != primeira + i
            )
            celula = ws.cell(r, col[rotulo], f"=MEDIAN({pares})")
            celula.number_format, celula.fill = VEZES, FUNDO_SECAO

    def propria(rotulo: str) -> str:  # número da empresa escolhida
        letra = L(col[rotulo])
        return f"INDEX({letra}{primeira}:{letra}{primeira + len(TICKERS) - 1},{EMP})"

    def mediana(rotulo: str) -> str:
        letra = L(col[rotulo])
        return f"INDEX({letra}{medianas}:{letra}{medianas + len(TICKERS) - 1},{EMP})"

    acoes = propria("Ações (milhões)")
    r = medianas + len(TICKERS) + 1
    for c_, texto in ((2, ""), (3, "R$ / ação"), (4, "Como se calcula")):
        celula = ws.cell(r, c_, texto)
        celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
    ws.cell(
        r, 2, f"=\"Preço por ação implícito - \"&'Painel'!${CELULA_EMPRESA[0]}${CELULA_EMPRESA[1:]}"
    )
    linhas = (
        (
            "Pelo EV/EBITDA das comparáveis",
            f"=IF({propria('EBITDA')}>0,({mediana('EV/EBITDA')}*{propria('EBITDA')}"
            f'-{propria("Dívida líquida")}-{propria("Minoritários")})/{acoes},"n.a.")',
            "Mediana × EBITDA da empresa, menos dívida líquida e minoritários, ÷ número de ações.",
        ),
        (
            "Pelo EV/EBIT das comparáveis",
            f"=IF({propria('EBIT')}>0,({mediana('EV/EBIT')}*{propria('EBIT')}"
            f'-{propria("Dívida líquida")}-{propria("Minoritários")})/{acoes},"n.a.")',
            "Mediana × EBIT da empresa, menos dívida líquida e minoritários, ÷ número de ações.",
        ),
        (
            "Pelo P/L das comparáveis",
            f'=IF({propria("Lucro")}>0,{mediana("P/L")}*{propria("Lucro")}/{acoes},"n.a.")',
            "Mediana × lucro da empresa ÷ número de ações. Não se aplica com prejuízo.",
        ),
        (
            "Pelo P/VP das comparáveis",
            f"={mediana('P/VP')}*{propria('Patrimônio')}/{acoes}",
            "Mediana × patrimônio dos controladores ÷ número de ações.",
        ),
        (
            "Pelo fluxo de caixa descontado (aba Valor justo)",
            f"={valor.ref('preco_justo', COL_ANO1)}",
            "Para comparar com os múltiplos.",
        ),
        ("Preço de mercado", f"={propria('Preço')}", "Último fechamento na B3."),
    )
    for i, (rotulo, formula, como) in enumerate(linhas, start=1):
        ws.cell(r + i, 2, rotulo)
        celula = ws.cell(r + i, 3, formula)
        celula.number_format = REAIS
        celula.alignment = Alignment(horizontal="right")
        ws.cell(r + i, 4, como).font = CINZA
    nota = r + len(linhas) + 2
    for i, texto in enumerate(
        (
            "EV (valor da empresa) = valor de mercado + dívida líquida + minoritários.",
            "EV/EBITDA: quantos anos de EBITDA o mercado paga pela empresa inteira.",
            "P/L: quantos anos de lucro o mercado paga pela ação. P/VP: quanto paga por real de "
            "patrimônio.",
            "A mediana ignora os extremos: a Usiminas, com EBITDA perto de zero, tem EV/EBITDA "
            "fora da curva.",
        )
    ):
        ws.cell(nota + i, 2, texto).font = CINZA
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 48
    for c_ in col.values():
        ws.column_dimensions[L(c_)].width = 15
    ws.sheet_view.showGridLines = False


# --------------------------------------------------------------------------- Cenários


def _aba_cenarios(
    wb: Workbook, todos: dict[str, dict[str, Any]], anos: list[int], proj: Aba, valor: Aba
) -> None:
    cols = list(range(COL_ANO1, COL_ANO1 + len(anos)))
    aba = Aba(wb.create_sheet("Cenários"), cols)
    ws = aba.ws
    aba.titulo(
        "Cenários e movimento do caixa",
        "De onde vem e para onde vai o caixa em cada ano, no cenário em uso. Abaixo, os três "
        "cenários lado a lado.",
    )
    _titulo_com_empresa(ws, "Cenários")
    aba.cabecalho(
        {**{c: f"{a}E" for c, a in zip(cols, anos, strict=True)}, **_explicacao(aba, "O que é")},
        "Entradas e saídas de caixa",
    )

    def x(nome: str, c: int) -> str:
        return f"{L(c)}{aba.linha[nome]}"

    def pr(nome: str, c: int) -> str:
        return proj.ref(nome, c)

    def linha(nome: str, rotulo: str, formula: Formula, destaque: bool = False) -> None:
        aba.escrever(nome, rotulo, formula, destaque=destaque, nota=LINHAS[f"c_{nome}"])

    aba.secao("Entradas (cash in)")
    linha(
        "operacao",
        "Caixa gerado pela operação (EBITDA sem equivalência)",
        lambda c: f"={pr('ebitda', c)}-{pr('equivalencia', c)}",
    )
    linha("rendimento", "Rendimento do caixa", lambda c: f"={pr('receita_financeira', c)}")
    linha(
        "captacao",
        "Captação líquida de dívida (se positiva)",
        lambda c: f"=MAX(0,{P('captacao_liquida', c)})",
    )
    linha(
        "entradas",
        "Total de entradas",
        lambda c: f"={x('operacao', c)}+{x('rendimento', c)}+{x('captacao', c)}",
        destaque=True,
    )
    aba.secao("Saídas (cash out)")
    linha("impostos", "Imposto de renda e CSLL", lambda c: f"={pr('ir', c)}")
    linha("capex", "Capex", lambda c: f"={pr('capex', c)}")
    linha("giro", "Investimento em capital de giro", lambda c: f"={pr('variacao_giro', c)}")
    linha("juros", "Juros da dívida", lambda c: f"={pr('despesa_financeira', c)}")
    linha(
        "amortizacao",
        "Amortização líquida de dívida (se negativa a captação)",
        lambda c: f"=MAX(0,-{P('captacao_liquida', c)})",
    )
    linha("dividendos", "Dividendos", lambda c: f"={pr('dividendos', c)}")
    linha(
        "saidas",
        "Total de saídas",
        lambda c: f"=SUM({L(c)}{aba.linha['impostos']}:{L(c)}{aba.linha['dividendos']})",
        destaque=True,
    )
    aba.secao("Saldo")
    linha(
        "variacao",
        "Entradas - saídas",
        lambda c: f"={x('entradas', c)}-{x('saidas', c)}",
        destaque=True,
    )
    linha("caixa_final", "Caixa no fim do ano", lambda c: f"={pr('caixa_total', c)}")
    linha(
        "confere",
        "Checagem: bate com a variação de caixa da projeção (zero)",
        lambda c: f"=ROUND({x('variacao', c)}-{pr('variacao_caixa', c)},3)",
    )
    aba.pular(2)

    # Comparativo: valores do modelo em Python, um bloco por empresa com o mesmo desenho.
    ultimo = anos[-1]
    medidas: tuple[tuple[str, Callable[[dict[str, Any]], float], str], ...] = (
        ("Preço justo por ação", lambda r: r["valuation"]["preco_justo"], REAIS),
        ("Valor da empresa (EV)", lambda r: r["valuation"]["ev"], MI),
        ("Valor do acionista", lambda r: r["valuation"]["equity"], MI),
        ("WACC", lambda r: r["valuation"]["wacc"], PCT),
        (
            "Crescimento da receita, ao ano",
            lambda r: r["premissas"]["crescimento_receita"][-1],
            PCT,
        ),
        (f"Margem EBITDA {ultimo}E", lambda r: r["projecao"].loc["margem_ebitda", ultimo], PCT),
        (f"Receita {ultimo}E", lambda r: r["projecao"].loc["receita", ultimo], MI),
        (f"Caixa no fim de {ultimo}E", lambda r: r["projecao"].loc["caixa_total", ultimo], MI),
        (
            f"Dívida líquida / EBITDA {ultimo}E",
            lambda r: r["projecao"].loc["divida_liquida_ebitda", ultimo],
            VEZES,
        ),
    )
    altura = len(medidas) + 3
    topo = aba.proxima
    fim = topo + altura * (len(TICKERS) + 1)

    def cabecalho(r: int, titulo: str) -> None:
        for i, texto in enumerate([titulo, "", *NOME_CENARIO.values()]):
            celula = ws.cell(r, 2 + i, texto)
            celula.font, celula.fill = BRANCO, FUNDO_CABECALHO

    # Bloco em uso: busca a mesma posição no bloco da empresa escolhida.
    cabecalho(topo, "Os três cenários da empresa escolhida (calculados pelo modelo)")
    for i, (rotulo, _, formato) in enumerate(medidas, start=1):
        ws.cell(topo + i, 2, rotulo).font = NEGRITO if i == 1 else Font()
        for j in range(3):
            letra = L(COL_ANO1 + j)
            celula = ws.cell(
                topo + i, COL_ANO1 + j, f"=INDEX({letra}$1:{letra}${fim},ROW()+{altura}*{EMP})"
            )
            celula.number_format = formato
            if i == 1:
                celula.font = NEGRITO
    for k, ticker in enumerate(TICKERS, start=1):
        r0 = topo + altura * k
        dados = todos[ticker]["dados"]
        resultados = {c: modelo.rodar(ticker, dados, c) for c in premissas.CENARIOS}
        cabecalho(r0, NOME_EMPRESA[ticker])
        for i, (rotulo, pegar, formato) in enumerate(medidas, start=1):
            ws.cell(r0 + i, 2, rotulo)
            for j, cenario in enumerate(premissas.CENARIOS):
                celula = ws.cell(r0 + i, COL_ANO1 + j, float(pegar(resultados[cenario])))
                celula.number_format = formato

    r = fim + 1
    ws.cell(r, 2, "Preço justo na planilha viva, no cenário em uso")
    vivo = ws.cell(r, COL_ANO1, f"={valor.ref('preco_justo', COL_ANO1)}")
    vivo.number_format, vivo.font, vivo.fill = REAIS, NEGRITO, FUNDO_RESULTADO
    ws.cell(r + 1, 2, "Diferença para o comparativo acima (zero sem ajuste manual)")
    linhas_manuais = LINHA_VARIAVEL.values()
    manual = (
        f"'Painel'!${L(COL_MANUAL)}${min(linhas_manuais)}:${L(COL_MANUAL)}${max(linhas_manuais)}"
    )
    ws.cell(
        r + 1,
        COL_ANO1,
        f"=IF(COUNT({manual})=0,ROUND({L(COL_ANO1)}{r}"
        f'-INDEX({L(COL_ANO1)}{topo + 1}:{L(COL_ANO1 + 2)}{topo + 1},{CEN}),2),"-")',
    ).number_format = DEC
    ws.cell(
        r + 1,
        cols[-1] + 1,
        "Confere a planilha contra o modelo em Python. Com ajuste manual o cenário já não é "
        "nenhum dos três.",
    ).font = CINZA
    aba.larguras(rotulo=56, numeros=14)


# --------------------------------------------------------------------------- Correlação

# Onde ficam as estatísticas e os dados mensais da aba Correlação.
LINHA_STATS, CAB_MENSAL = 6, 21


def _aba_correlacao(wb: Workbook) -> None:
    """Preço das ações contra o minério de ferro, com as estatísticas em fórmula."""
    t = commodities.series()
    ws = wb.create_sheet("Correlação")
    ws.cell(1, 2, "Ação contra minério de ferro").font = TITULO
    ws.cell(
        2,
        2,
        "A ação anda junto com o minério? A conta usa a variação de um mês para o outro, não o "
        "nível do preço: duas séries que só sobem parecem ligadas mesmo sem ter relação.",
    ).font = CINZA

    # Dados mensais: mês, minério, dólar, minério em reais, as ações, ação escolhida;
    # depois as variações mensais e os índices base 100 que alimentam o gráfico.
    primeira = CAB_MENSAL + 1
    ultima = primeira + len(t) - 1
    titulos = [
        "Mês", "Minério (US$/t)", "Dólar (R$)", "Minério (R$/t)", *TICKERS, "Ação escolhida",
        "Var. minério US$", "Var. minério R$", *[f"Var. {k}" for k in TICKERS],
        "Var. ação escolhida", "Minério, base 100", "Ação escolhida, base 100",
    ]  # fmt: skip
    for j, texto in enumerate(titulos):
        celula = ws.cell(CAB_MENSAL, 2 + j, texto)
        celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
        celula.alignment = Alignment(horizontal="center", wrap_text=True)
    c_mes, c_min, c_dolar, c_min_brl = 2, 3, 4, 5
    c_acao = {k: 6 + i for i, k in enumerate(TICKERS)}
    c_sel = 6 + len(TICKERS)
    c_var_min, c_var_brl = c_sel + 1, c_sel + 2
    c_var = {k: c_sel + 3 + i for i, k in enumerate(TICKERS)}
    c_var_sel = c_sel + 3 + len(TICKERS)
    c_idx_min, c_idx_sel = c_var_sel + 1, c_var_sel + 2
    for i, (mes, linha) in enumerate(t.iterrows()):
        r = primeira + i
        ws.cell(r, c_mes, mes)
        ws.cell(r, c_min, float(linha["minerio_usd"])).number_format = "0.0"
        ws.cell(r, c_dolar, float(linha["dolar"])).number_format = DEC
        ws.cell(r, c_min_brl, f"={L(c_min)}{r}*{L(c_dolar)}{r}").number_format = "0.0"
        for k in TICKERS:
            ws.cell(r, c_acao[k], float(linha[k])).number_format = DEC
        das_acoes = ",".join(f"{L(c_acao[k])}{r}" for k in TICKERS)
        ws.cell(r, c_sel, f"=CHOOSE({EMP},{das_acoes})").number_format = DEC
        if i > 0:
            for origem, destino in (
                (c_min, c_var_min),
                (c_min_brl, c_var_brl),
                *[(c_acao[k], c_var[k]) for k in TICKERS],
                (c_sel, c_var_sel),
            ):
                ws.cell(r, destino, f"={L(origem)}{r}/{L(origem)}{r - 1}-1").number_format = PCT
        ws.cell(r, c_idx_min, f"={L(c_min)}{r}/{L(c_min)}${primeira}*100").number_format = "0.0"
        ws.cell(r, c_idx_sel, f"={L(c_sel)}{r}/{L(c_sel)}${primeira}*100").number_format = "0.0"

    def faixa(coluna: int) -> str:
        return f"{L(coluna)}${primeira + 1}:{L(coluna)}${ultima}"

    # Estatísticas, uma linha por empresa: contra o minério em dólar e em reais.
    ws.cell(LINHA_STATS - 2, 3, "Contra o minério em dólar").font = NEGRITO
    ws.cell(LINHA_STATS - 2, 6, "Contra o minério em reais").font = NEGRITO
    for c, texto in enumerate(
        ["Variação mensal da ação", *["Correlação", "Sensibilidade", "R²"] * 2],
        start=2,
    ):
        celula = ws.cell(LINHA_STATS - 1, c, texto)
        celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
        celula.alignment = Alignment(horizontal="left" if c == 2 else "center")
    for i, k in enumerate(TICKERS):
        r = LINHA_STATS + i
        ws.cell(r, 2, NOME_EMPRESA[k])
        for j, minerio in enumerate((c_var_min, c_var_brl)):
            y, xx = faixa(c_var[k]), faixa(minerio)
            for d, (formula, formato) in enumerate(
                ((f"=CORREL({y},{xx})", DEC), (f"=SLOPE({y},{xx})", DEC), (f"=RSQ({y},{xx})", PCT))
            ):
                ws.cell(r, 3 + 3 * j + d, formula).number_format = formato
    r_sel = LINHA_STATS + len(TICKERS)
    ws.cell(
        r_sel, 2, f"=\"Escolhida: \"&'Painel'!${CELULA_EMPRESA[0]}${CELULA_EMPRESA[1:]}"
    ).font = NEGRITO
    for c in range(3, 9):
        letra = L(c)
        celula = ws.cell(r_sel, c, f"=INDEX({letra}{LINHA_STATS}:{letra}{r_sel - 1},{EMP})")
        celula.number_format = PCT if c in (5, 8) else DEC
        celula.font, celula.fill = NEGRITO, FUNDO_RESULTADO
    for i, texto in enumerate(
        (
            "Correlação: vai de -1 a 1. Perto de 1, a ação sobe quando o minério sobe; perto de 0, "
            "não há relação.",
            "Sensibilidade: quanto a ação costuma variar quando o minério varia 1% (inclinação da "
            "reta).",
            "R²: quanto da oscilação da ação o minério explica sozinho. O resto vem de câmbio, "
            "juros, custos e notícias.",
            f"Período: {t.index[0]} a {t.index[-1]}, {len(t) - 1} variações mensais. Preço médio "
            "do mês; ações sem ajuste de dividendos.",
            "Fontes: Banco Mundial (minério 62% Fe, CFR China), Banco Central (dólar PTAX) e B3 "
            "(COTAHIST).",
        )
    ):
        ws.cell(r_sel + 2 + i, 2, texto).font = CINZA

    # Gráfico 1: minério e ação escolhida, os dois começando em 100.
    linhas = LineChart()
    linhas.title = "Minério de ferro e ação escolhida (primeiro mês = 100)"
    linhas.height, linhas.width = 8.5, 17
    for coluna in (c_idx_min, c_idx_sel):
        linhas.add_data(
            Reference(ws, min_col=coluna, min_row=CAB_MENSAL, max_row=ultima), titles_from_data=True
        )
    linhas.set_categories(Reference(ws, min_col=c_mes, min_row=primeira, max_row=ultima))
    linhas.x_axis.tickLblSkip = 12
    ws.add_chart(linhas, f"J{LINHA_STATS - 3}")

    # Gráfico 2: cada ponto é um mês, variação do minério contra variação da ação.
    pontos = ScatterChart()
    pontos.title = "Cada ponto é um mês: variação do minério (horizontal) e da ação (vertical)"
    pontos.style = 13
    pontos.height, pontos.width = 8.5, 17
    serie = Series(
        Reference(ws, min_col=c_var_sel, min_row=primeira + 1, max_row=ultima),
        Reference(ws, min_col=c_var_min, min_row=primeira + 1, max_row=ultima),
        title="Meses",
    )
    serie.marker.symbol = "circle"
    serie.marker.size = 6
    # Sem cor explícita o LibreOffice desenha os pontos em branco.
    serie.marker.graphicalProperties.solidFill = "2A78D6"
    serie.marker.graphicalProperties.line.solidFill = "2A78D6"
    serie.graphicalProperties.line.noFill = True
    pontos.series.append(serie)
    pontos.legend = None
    ws.add_chart(pontos, f"T{LINHA_STATS - 3}")

    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 44
    for c in range(3, 2 + len(titulos)):
        ws.column_dimensions[L(c)].width = 13
    ws.row_dimensions[CAB_MENSAL].height = 32
    ws.sheet_view.showGridLines = False


# --------------------------------------------------------------------------- Painel, passo a passo e glossário


def _aba_painel(ws: Worksheet, anos: list[int], wacc: Aba, valor: Aba, fcff: Aba) -> None:
    nomes = [e.nome for e in FOCO]
    ws.cell(1, 2, f"Valuation de {', '.join(nomes[:-1])} e {nomes[-1]}").font = TITULO
    ws.cell(
        2, 2, "Escolha a empresa e o cenário nas células amarelas. Todas as abas recalculam."
    ).font = CINZA
    ws.cell(
        3,
        2,
        "Isto não é recomendação de investimento. É uma análise feita com os dados que as próprias "
        "empresas divulgam e com simulações que juntam dados reais e dados projetados.",
    ).font = Font(italic=True, color="C00000")

    # Listas das duas escolhas, fora da área de leitura. As empresas ficam nas linhas 5 a
    # 8 e os cenários começam na 9: cabem quatro empresas.
    if len(TICKERS) > 4:
        raise ValueError("a lista de empresas do Painel só tem lugar para quatro")
    lista_empresas = f"$X$5:$X${4 + len(TICKERS)}"
    ws.cell(4, 24, "Listas (não apagar)").font = NEGRITO
    for i, ticker in enumerate(TICKERS):
        ws.cell(5 + i, 24, NOME_EMPRESA[ticker])
    for i, nome in enumerate(premissas.CENARIOS):
        ws.cell(9 + i, 24, NOME_CENARIO[nome])
    ws.cell(5, 25, f"=MATCH(${CELULA_EMPRESA[0]}${CELULA_EMPRESA[1:]},{lista_empresas},0)")
    ws.cell(9, 25, f"=MATCH(${CELULA_CENARIO[0]}${CELULA_CENARIO[1:]},$X$9:$X$11,0)")

    for endereco, rotulo, inicial, lista in (
        (CELULA_EMPRESA, "Empresa", NOME_EMPRESA[TICKERS[0]], lista_empresas),
        (CELULA_CENARIO, "Cenário", NOME_CENARIO["moderado"], "$X$9:$X$11"),
    ):
        celula = ws[endereco]
        ws.cell(celula.row, 2, rotulo).font = NEGRITO
        celula.value = inicial
        celula.font, celula.fill = Font(bold=True, color="0000FF", size=12), FUNDO_ENTRADA
        for c in (5, 6):
            ws.cell(celula.row, c).fill = FUNDO_ENTRADA
        validacao = DataValidation(type="list", formula1=lista, allow_blank=False)
        ws.add_data_validation(validacao)
        validacao.add(endereco)
        ws.cell(celula.row, 7, "← clique na célula e escolha na lista").font = CINZA

    # As três variáveis do cenário.
    cab = min(LINHA_VARIAVEL.values()) - 1
    for c, texto in (
        (2, "As três variáveis do cenário"),
        (COL_USO, "Em uso"),
        (COL_PESS, "Pessimista"),
        (COL_MOD, "Moderado"),
        (COL_OTIM, "Otimista"),
        (COL_MANUAL, "Ajuste manual"),
        (COL_PARTIDA, "Partida"),
    ):
        celula = ws.cell(cab, c, texto)
        celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
        celula.alignment = Alignment(horizontal="left" if c == 2 else "center")
    capm = wacc.ref("wacc", COL_ANO1, fixa=True)
    variaveis: tuple[tuple[str, str, Formula, str], ...] = (
        (
            "crescimento_receita",
            "Crescimento da receita, ao ano",
            lambda c: f"={P('crescimento_receita', c)}",
            f"={P('crescimento_receita', 3)}",
        ),
        (
            "margem_ebitda",
            f"Margem EBITDA em {anos[-1]}",
            lambda c: f"={P('margem_ebitda', c)}",
            f"={P('margem_ebitda', 3)}",
        ),
        (
            "wacc",
            "WACC (taxa de desconto)",
            lambda c: f"={capm}+{P('ajuste_wacc', c)}",
            f"={capm}",
        ),
    )
    for nome, rotulo, do_cenario, partida in variaveis:
        r = LINHA_VARIAVEL[nome]
        ws.cell(r, 2, rotulo).font = NEGRITO
        for coluna, origem in ((COL_PESS, 4), (COL_MOD, 5), (COL_OTIM, 6)):
            ws.cell(r, coluna, do_cenario(origem)).number_format = PCT
        ws.cell(r, COL_PARTIDA, partida).number_format = PCT
        manual = ws.cell(r, COL_MANUAL)
        manual.number_format, manual.font, manual.fill = PCT, AZUL, FUNDO_ENTRADA
        faixa = f"{L(COL_PESS)}{r}:{L(COL_OTIM)}{r}"
        # O ajuste manual só aceita valor entre o pessimista e o otimista.
        limite = DataValidation(
            type="decimal",
            operator="between",
            formula1=f"=MIN(${L(COL_PESS)}${r}:${L(COL_OTIM)}${r})",
            formula2=f"=MAX(${L(COL_PESS)}${r}:${L(COL_OTIM)}${r})",
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="Fora da faixa",
            error="Use um valor entre o pessimista e o otimista.",
        )
        ws.add_data_validation(limite)
        limite.add(manual.coordinate)
        m = manual.coordinate
        uso = ws.cell(
            r,
            COL_USO,
            f"=IF(ISNUMBER({m}),MIN(MAX({m},MIN({faixa})),MAX({faixa})),"
            f"CHOOSE({CEN},{L(COL_PESS)}{r},{L(COL_MOD)}{r},{L(COL_OTIM)}{r}))",
        )
        uso.number_format, uso.font, uso.fill = PCT, NEGRITO, FUNDO_RESULTADO
    fim_vars = max(LINHA_VARIAVEL.values())
    ws.cell(
        fim_vars + 1,
        2,
        "Ajuste manual: digite um valor entre o pessimista e o otimista (ex.: 5%) para testar um "
        "meio-termo; deixe vazio para usar o cenário. Partida é o nível de hoje.",
    ).font = CINZA

    # Resultado
    r = fim_vars + 3
    for c, texto in ((2, "Resultado"), (3, "Valor"), (4, "O que é")):
        celula = ws.cell(r, c, texto)
        celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
    d = COL_ANO1
    resultados = (
        ("Preço justo por ação", valor.ref("preco_justo", d), REAIS, "Quanto vale cada ação segundo o modelo, no cenário em uso."),
        ("Preço de mercado", valor.ref("preco", d), REAIS, "Último fechamento na B3."),
        ("Diferença para o mercado", valor.ref("potencial", d), PCT, "Preço justo ÷ preço de mercado − 1."),
        ("Valor da empresa (EV)", valor.ref("ev", d), MI, "Valor da operação inteira, em R$ milhões."),
        ("Valor do acionista", valor.ref("equity", d), MI, "EV menos dívida líquida e minoritários, mais investimentos."),
        ("Peso do valor terminal", valor.ref("peso_vt", d), PCT, f"Quanto do valor vem de depois de {anos[-1]}."),
        ("Preço pelo fluxo do acionista (FCFE)", valor.ref("preco_fcfe", d), REAIS, "Conferência por outro caminho: deve ficar perto do preço justo."),
    )  # fmt: skip
    for i, (rotulo, origem, formato, texto) in enumerate(resultados, start=1):
        ws.cell(r + i, 2, rotulo).font = NEGRITO if i == 1 else Font()
        celula = ws.cell(r + i, 3, f"={origem}")
        celula.number_format = formato
        if i == 1:
            celula.font, celula.fill = Font(bold=True, size=14), FUNDO_RESULTADO
        ws.cell(r + i, 4, texto).font = CINZA

    # O caminho da conta, com o número de cada etapa.
    r = r + len(resultados) + 2
    for c, texto in (
        (2, "O caminho do cálculo, começando pelo FCFF"),
        (3, "Valor"),
        (4, "Onde ver"),
    ):
        celula = ws.cell(r, c, texto)
        celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
    caminho = (
        (f"1. FCFF de {anos[1]}E: o caixa livre da empresa", fcff.ref("fcff", d + 1), MI, "Aba FCFF"),
        ("2. WACC: a taxa que traz o futuro a valor de hoje", wacc.ref("wacc_uso", d), PCT2, "Aba WACC"),
        (f"3. Fluxos de {anos[0]} a {anos[-1]}, a valor de hoje", valor.ref("soma_vp", d), MI, "Aba Valor justo"),
        (f"4. Tudo o que vem depois de {anos[-1]}, a valor de hoje", valor.ref("vp_vt", d), MI, "Aba Valor justo"),
        ("5. Valor da empresa (3 + 4)", valor.ref("ev", d), MI, "Aba Valor justo"),
        ("6. Valor do acionista (5 − dívida líquida − minoritários + investimentos)", valor.ref("equity", d), MI, "Aba Valor justo"),
        ("7. Preço justo (6 ÷ número de ações)", valor.ref("preco_justo", d), REAIS, "A aba Passo a passo explica cada etapa"),
    )  # fmt: skip
    for i, (rotulo, origem, formato, onde) in enumerate(caminho, start=1):
        ws.cell(r + i, 2, rotulo)
        ws.cell(r + i, 3, f"={origem}").number_format = formato
        ws.cell(r + i, 4, onde).font = CINZA

    grafico = BarChart()
    grafico.title = "FCFF projetado (R$ milhões)"
    grafico.legend = None
    ultimo = COL_ANO1 + len(anos) - 1
    linha_fcff = fcff.linha["fcff"]
    grafico.add_data(
        Reference(fcff.ws, min_col=COL_ANO1, max_col=ultimo, min_row=linha_fcff), from_rows=True
    )
    grafico.set_categories(Reference(fcff.ws, min_col=COL_ANO1, max_col=ultimo, min_row=4))
    grafico.height, grafico.width = 8.5, 15
    ws.add_chart(grafico, "J5")

    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 62
    for c in range(3, 9):
        ws.column_dimensions[L(c)].width = 15
    ws.column_dimensions["X"].width = 22
    ws.sheet_view.showGridLines = False


def _aba_passos(wb: Workbook, anos: list[int], wacc: Aba, valor: Aba, fcff: Aba) -> None:
    ws = wb.create_sheet("Passo a passo")
    _titulo_com_empresa(ws, "Como o preço justo é calculado")
    ws.cell(
        2,
        2,
        "O valuation pelo fluxo de caixa da empresa, em sete passos. Os números são os da empresa "
        "e do cenário escolhidos no Painel e mudam junto com eles.",
    ).font = CINZA
    ano = anos[1]
    c2 = COL_ANO1 + 1  # coluna do segundo ano projetado, usado de exemplo
    d = COL_ANO1
    contas: tuple[tuple[tuple[str, str, str, str], ...], ...] = (
        (
            (f"NOPAT de {ano}E (lucro da operação depois do imposto)", fcff.ref("nopat", c2), MI, ""),
            ("+ Depreciação", fcff.ref("da", c2), MI, "não saiu do caixa"),
            ("− Capex", fcff.ref("capex", c2), MI, "investimento em ativos"),
            ("− Variação do capital de giro", fcff.ref("variacao_giro", c2), MI, "dinheiro a mais preso na operação"),
            (f"(=) FCFF de {ano}E", fcff.ref("fcff", c2), MI, "a aba FCFF repete a conta para cada ano"),
        ),
        (
            ("Juro sem risco", wacc.ref("rf", d), PCT2, ""),
            ("+ Beta × prêmio de risco de mercado", f"{wacc.ref('beta', d)}*{wacc.ref('premio', d)}", PCT2, ""),
            ("(=) Ke, o retorno que o acionista exige", wacc.ref("ke", d), PCT2, ""),
            ("Custo da dívida depois do imposto", wacc.ref("kd_liquido", d), PCT2, ""),
            ("Peso da dívida", wacc.ref("wd", d), PCT, ""),
            ("WACC pelo CAPM (média de Ke e do custo da dívida)", wacc.ref("wacc", d), PCT2, ""),
            ("(=) WACC em uso (o do cenário ou do ajuste manual)", wacc.ref("wacc_uso", d), PCT2, "é a taxa de desconto"),
        ),
        (
            (f"FCFF de {ano}E", valor.ref("fcff", c2), MI, ""),
            ("× Fator de desconto", valor.ref("fator", c2), "0.0000", "1 ÷ (1 + WACC) elevado aos anos até lá"),
            (f"(=) Valor presente do FCFF de {ano}E", valor.ref("vp", c2), MI, ""),
            (f"(=) Soma dos valores presentes de {anos[0]} a {anos[-1]}", valor.ref("soma_vp", d), MI, ""),
        ),
        (
            (f"FCFF de {anos[-1]} ajustado (só repõe o que desgasta)", valor.ref("fcff_terminal", d), MI, ""),
            ("Crescimento para sempre (g)", valor.ref("g", d), PCT2, "inflação de longo prazo"),
            ("Valor terminal: FCFF × (1 + g) ÷ (WACC − g)", valor.ref("vt", d), MI, ""),
            ("(=) Valor terminal a valor de hoje", valor.ref("vp_vt", d), MI, ""),
        ),
        (
            ("Valor presente dos fluxos projetados", valor.ref("soma_vp", d), MI, ""),
            ("+ Valor presente do valor terminal", valor.ref("vp_vt", d), MI, ""),
            ("(=) Valor da empresa (EV)", valor.ref("ev", d), MI, ""),
        ),
        (
            ("Valor da empresa (EV)", valor.ref("ev", d), MI, ""),
            ("− Dívida líquida", valor.ref("divida_liquida", d), MI, "é dos credores"),
            ("− Minoritários", valor.ref("minoritarios", d), MI, "é dos sócios das controladas"),
            ("+ Investimentos em coligadas", valor.ref("investimentos", d), MI, "o FCFF não contou"),
            ("(=) Valor do acionista (Equity Value)", valor.ref("equity", d), MI, ""),
        ),
        (
            ("Valor do acionista", valor.ref("equity", d), MI, ""),
            ("÷ Ações em circulação (milhões)", valor.ref("acoes", d), "#,##0.0", ""),
            ("(=) Preço justo por ação", valor.ref("preco_justo", d), REAIS, ""),
            ("Preço de mercado", valor.ref("preco", d), REAIS, ""),
            ("Diferença", valor.ref("potencial", d), PCT, "preço justo ÷ preço de mercado − 1"),
        ),
    )  # fmt: skip
    r = 4
    for (titulo, texto), linhas in zip(PASSOS, contas, strict=True):
        for c in (2, 3, 4):
            ws.cell(r, c).fill = FUNDO_CABECALHO
        ws.cell(r, 2, titulo).font = BRANCO
        ws.cell(r + 1, 2, texto).alignment = QUEBRA
        ws.merge_cells(start_row=r + 1, start_column=2, end_row=r + 1, end_column=4)
        ws.row_dimensions[r + 1].height = 48
        r += 2
        for rotulo, origem, formato, nota in linhas:
            resultado = rotulo.startswith("(=)")
            ws.cell(r, 2, rotulo).font = NEGRITO if resultado else Font()
            celula = ws.cell(r, 3, f"={origem}")
            celula.number_format = formato
            if resultado:
                celula.font, celula.fill = NEGRITO, FUNDO_RESULTADO
            if nota:
                ws.cell(r, 4, nota).font = CINZA
            r += 1
        r += 1
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 66
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 60
    ws.sheet_view.showGridLines = False


def _aba_glossario(wb: Workbook) -> None:
    ws = wb.create_sheet("Glossário")
    ws.cell(1, 2, "Glossário").font = TITULO
    ws.cell(2, 2, "O que é cada indicador, como se calcula e em que aba aparece.").font = CINZA
    for c, texto in enumerate(("Termo", "O que é", "Como se calcula", "Onde ver"), start=2):
        celula = ws.cell(4, c, texto)
        celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
    for i, linha in enumerate(GLOSSARIO, start=5):
        for c, texto in enumerate(linha, start=2):
            celula = ws.cell(i, c, texto)
            celula.alignment = QUEBRA
            if c == 2:
                celula.font = NEGRITO
        ws.row_dimensions[i].height = 32
    ws.column_dimensions["A"].width = 2
    for letra, largura in (("B", 30), ("C", 70), ("D", 62), ("E", 18)):
        ws.column_dimensions[letra].width = largura
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "C5"


# --------------------------------------------------------------------------- Montagem

ORDEM = [
    "Painel", "Passo a passo", "Demonstrativos", "Projeção", "FCFF", "WACC", "Valor justo",
    "Múltiplos", "Cenários", "Correlação", "Glossário", "Premissas", "Dados",
]  # fmt: skip


def montar() -> Workbook:
    """Monta a planilha inteira, só com fórmulas (sem valores calculados)."""
    todos: dict[str, dict[str, Any]] = {}
    for ticker in TICKERS:
        dados = premissas.carregar(ticker)
        todos[ticker] = {
            "dados": dados,
            "cenarios": dados["cenarios"],
            "premissas": dados["premissas"],
            "base": modelo.carregar_base(ticker, dados),
        }
    anos: list[int] = todos[TICKERS[0]]["dados"]["anos"]
    mercado = pd.read_csv(modelo.MERCADO_CSV).set_index("ticker")

    wb = Workbook()
    painel = wb.active
    painel.title = "Painel"
    _aba_premissas(wb, todos, anos, mercado)
    periodos = _aba_dados(wb)
    hist, col_base, col_ltm = _aba_demonstrativos(wb, periodos)

    # A Projeção precisa do FCFE e a aba FCFF precisa da Projeção: as linhas da FCFF são
    # reservadas antes, e a aba é preenchida depois.
    cols = list(range(COL_ANO1, COL_ANO1 + len(anos)))
    fcff = Aba(wb.create_sheet("FCFF"), cols)
    fcff.titulo(
        "FCFF e FCFE",
        "O caixa livre de cada ano, que é o ponto de partida do valuation. FCFF é o caixa da "
        "empresa inteira; FCFE é a parte do acionista.",
    )
    _titulo_com_empresa(fcff.ws, "FCFF e FCFE")
    fcff.cabecalho({**{c: f"{a}E" for c, a in zip(cols, anos, strict=True)}, **_explicacao(fcff)})
    fcff.planejar(LINHAS_FCFF)

    proj = _aba_projecao(wb, anos, hist, col_base, fcff)
    _aba_fcff(fcff, anos, proj)
    wacc = _aba_wacc(wb, hist, col_ltm)
    valor = _aba_valor(wb, anos, wacc, fcff, proj, hist, col_ltm)
    _aba_multiplos(wb, valor)
    _aba_cenarios(wb, todos, anos, proj, valor)
    _aba_correlacao(wb)
    _aba_painel(painel, anos, wacc, valor, fcff)
    _aba_passos(wb, anos, wacc, valor, fcff)
    _aba_glossario(wb)

    wb._sheets = [wb[nome] for nome in ORDEM]
    wb.active = 0
    return wb


def recalcular(planilha: Path, destino: Path) -> Path:
    """Abre no LibreOffice sem tela e salva com os valores calculados."""
    soffice = shutil.which("soffice")
    if soffice is None:
        raise RuntimeError("LibreOffice (soffice) não encontrado")
    subprocess.run(
        [soffice, "--headless", "--calc", "--convert-to", "xlsx", "--outdir", destino, planilha],
        check=True,
        capture_output=True,
        timeout=180,
    )
    return destino / planilha.name


def gerar(pronta: bool = True) -> Path:
    """Grava a planilha em saida/.

    Com `pronta`, o LibreOffice abre o arquivo, calcula tudo e grava de novo: assim a
    planilha já chega com os números em qualquer programa, inclusive em visualizadores
    que não calculam fórmulas. Sem LibreOffice instalado, fica só com as fórmulas.
    """
    SAIDA.mkdir(exist_ok=True)
    wb = montar()
    if pronta and shutil.which("soffice"):
        with tempfile.TemporaryDirectory() as pasta:
            bruta = Path(pasta) / "entrada" / ARQUIVO.name
            bruta.parent.mkdir()
            wb.save(bruta)
            shutil.copy(recalcular(bruta, Path(pasta)), ARQUIVO)
    else:
        wb.save(ARQUIVO)
    return ARQUIVO
