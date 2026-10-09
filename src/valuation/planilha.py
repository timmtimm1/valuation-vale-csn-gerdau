"""Gera a planilha de cada empresa com as contas em fórmulas do Excel.

Nada de número calculado em Python colado como valor: o histórico entra como dado
e todo o resto (indicadores, projeção, WACC, DCF, sensibilidade, múltiplos) é
fórmula. Quem abre pode trocar qualquer célula azul e ver o preço mudar.

A única exceção é a tabela comparativa dos três cenários, que o Excel só faria
com Tabela de Dados: ali os valores vêm do modelo em Python, e uma célula ao lado
confere o cenário selecionado contra a planilha viva.

Todas as abas com anos usam as mesmas colunas: C é o ano-base, D em diante são
os anos projetados. Assim uma fórmula sempre olha para a mesma letra em outra aba.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from valuation import historico, modelo, multiplos, premissas
from valuation.empresas import SAIDA, empresa

COL_BASE = 3  # C
COL_ANO1 = 4  # D

AZUL = Font(color="0000FF")
NEGRITO = Font(bold=True)
TITULO = Font(bold=True, size=14)
BRANCO = Font(bold=True, color="FFFFFF")
FUNDO_CABECALHO = PatternFill("solid", fgColor="1F3864")
FUNDO_SECAO = PatternFill("solid", fgColor="D9E1F2")
FUNDO_ENTRADA = PatternFill("solid", fgColor="FFF2CC")
FUNDO_RESULTADO = PatternFill("solid", fgColor="E2EFDA")

MI = "#,##0;[Red]-#,##0"
PCT = "0.0%;[Red]-0.0%"
DIAS = "0"
VEZES = '0.00"x"'
REAIS = '"R$" #,##0.00;[Red]-"R$" #,##0.00'
DEC = "0.00"

FORMATO_PREMISSA = {
    "equivalencia": MI,
    "captacao_liquida": MI,
    "outros_ajustes": MI,
    "prazo_recebimento": DIAS,
    "prazo_estoque": DIAS,
    "prazo_pagamento": DIAS,
    "beta": DEC,
    "capex_perpetuidade": VEZES,
}
NOME_CENARIO = {"pessimista": "Pessimista", "moderado": "Moderado", "otimista": "Otimista"}

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

    def intervalo(self, nome: str) -> str:
        r = self.linha[nome]
        return f"'{self.ws.title}'!${L(self.colunas[0])}${r}:${L(self.colunas[-1])}${r}"

    def titulo(self, texto: str, subtitulo: str = "") -> None:
        self.ws.cell(1, 2, texto).font = TITULO
        if subtitulo:
            self.ws.cell(2, 2, subtitulo).font = Font(italic=True, color="595959")
        self.proxima = 4

    def cabecalho(self, rotulos: dict[int, Any], primeira: str = "R$ milhões") -> None:
        r = self.proxima
        for c in range(2, max(rotulos) + 1):
            celula = self.ws.cell(r, c, rotulos.get(c, primeira if c == 2 else None))
            celula.font = BRANCO
            celula.fill = FUNDO_CABECALHO
            celula.alignment = Alignment(horizontal="left" if c == 2 else "center")
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
        entrada: bool = False,
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
            if entrada:
                celula.font = AZUL
                celula.fill = FUNDO_ENTRADA
            elif destaque:
                celula.font = NEGRITO
        if nota:
            self.ws.cell(r, self.colunas[-1] + 1, nota).font = Font(italic=True, color="595959")
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

    def larguras(self, rotulo: int = 46, numeros: int = 13, nota: int = 70) -> None:
        self.ws.column_dimensions["A"].width = 2
        self.ws.column_dimensions["B"].width = rotulo
        for c in range(3, self.colunas[-1] + 1):
            self.ws.column_dimensions[L(c)].width = numeros
        self.ws.column_dimensions[L(self.colunas[-1] + 1)].width = nota
        self.ws.sheet_view.showGridLines = False


def _celula(ws: Worksheet, linha: int, coluna: int = 4) -> str:
    return f"'{ws.title}'!${L(coluna)}${linha}"


# --------------------------------------------------------------------------- Premissas


def _aba_premissas(
    wb: Workbook, dados: dict[str, Any], base: modelo.Base, mercado: pd.Series
) -> tuple[Aba, dict[str, str]]:
    """Entradas do modelo. Devolve a aba e o endereço de cada premissa escalar."""
    anos: list[int] = dados["anos"]
    colunas = list(range(COL_ANO1, COL_ANO1 + len(anos)))
    aba = Aba(wb.create_sheet("Premissas"), colunas)
    ws = aba.ws
    status = "PROPOSTA AUTOMÁTICA, AINDA NÃO APROVADA" if dados["status"] != "aprovada" else ""
    aba.titulo(
        f"Premissas - {dados['empresa']} ({dados['ticker']})",
        "Células azuis em fundo amarelo são entradas: troque e a planilha inteira recalcula. "
        + status,
    )
    p = dados["premissas"]
    cen = dados["cenarios"]
    esc: dict[str, str] = {}
    nota_col = colunas[-1] + 1

    # Seletor de cenário
    ws.cell(4, 2, "Cenário em uso").font = NEGRITO
    seletor = ws.cell(4, 4, NOME_CENARIO["moderado"])
    seletor.font, seletor.fill = AZUL, FUNDO_ENTRADA
    for i, nome in enumerate(premissas.CENARIOS):
        ws.cell(4 + i, 12, NOME_CENARIO[nome])
    ws.cell(3, 12, "Cenários").font = NEGRITO
    validacao = DataValidation(type="list", formula1="$L$4:$L$6", allow_blank=False)
    ws.add_data_validation(validacao)
    validacao.add("D4")
    ws.cell(5, 2, "Número do cenário (1 pessimista, 2 moderado, 3 otimista)")
    ws.cell(5, 4, "=MATCH(D4,L4:L6,0)")
    esc["cenario"] = _celula(ws, 5)
    aba.proxima = 7

    # As três variáveis de cenário: valor de cada cenário, ajuste manual e o que está em uso.
    c_uso, c_partida, c_pess, c_mod, c_otim, c_manual = 3, 4, 5, 6, 7, 8
    aba.cabecalho(
        {
            c_uso: "Em uso",
            c_partida: f"Partida {anos[0]}",
            c_pess: "Pessimista",
            c_mod: "Moderado",
            c_otim: "Otimista",
            c_manual: "Ajuste manual",
            nota_col: "De onde veio",
        },
        "Variáveis de cenário",
    )
    for nome, rotulo in premissas.VARIAVEIS.items():
        r = aba.proxima
        ws.cell(r, 2, rotulo).font = NEGRITO
        formato = "0.00%;[Red]-0.00%" if nome == "ajuste_wacc" else PCT
        entradas = [(c_pess, "pessimista"), (c_mod, "moderado"), (c_otim, "otimista")]
        if nome in premissas.COM_PARTIDA:
            entradas.insert(0, (c_partida, "partida"))
        for coluna, chave in entradas:
            celula = ws.cell(r, coluna, cen[nome][chave])
            celula.number_format, celula.font, celula.fill = formato, AZUL, FUNDO_ENTRADA
        manual = ws.cell(r, c_manual)
        manual.number_format, manual.font, manual.fill = formato, AZUL, FUNDO_ENTRADA
        faixa = f"{L(c_pess)}{r}:{L(c_otim)}{r}"
        # O ajuste manual só aceita valor entre o pessimista e o otimista.
        limite = DataValidation(
            type="decimal",
            operator="between",
            formula1=f"=MIN(${L(c_pess)}${r}:${L(c_otim)}${r})",
            formula2=f"=MAX(${L(c_pess)}${r}:${L(c_otim)}${r})",
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
            c_uso,
            f"=IF(ISNUMBER({m}),MIN(MAX({m},MIN({faixa})),MAX({faixa})),"
            f"CHOOSE({esc['cenario'].split('!')[1]},{L(c_pess)}{r},{L(c_mod)}{r},{L(c_otim)}{r}))",
        )
        uso.number_format, uso.font, uso.fill = formato, NEGRITO, FUNDO_RESULTADO
        ws.cell(r, nota_col, cen[nome]["origem"]).font = Font(italic=True, color="595959")
        aba.linha[f"var_{nome}"] = r
        esc[f"var_{nome}"] = _celula(ws, r, c_uso)
        esc[f"partida_{nome}"] = _celula(ws, r, c_partida)
        aba.proxima += 1
    esc["ajuste_wacc"] = esc["var_ajuste_wacc"]
    ws.cell(aba.proxima, 2, "Ajuste manual vazio = vale o cenário escolhido acima.").font = Font(
        italic=True, color="595959"
    )
    aba.pular(2)

    rotulos_anos = {c: f"{a}E" for c, a in zip(colunas, anos, strict=True)}
    passos = len(anos) - 1

    aba.cabecalho(rotulos_anos, "Do cenário para cada ano (o que a projeção lê)")
    aba.escrever(
        "crescimento_receita",
        "Crescimento da receita",
        lambda c: (
            "="
            + (
                esc["partida_crescimento_receita"]
                if c == colunas[0]
                else esc["var_crescimento_receita"]
            ).split("!")[1]
        ),
        PCT,
    )
    aba.escrever(
        "margem_ebitda",
        "Margem EBITDA",
        lambda c: (
            f"={esc['partida_margem_ebitda'].split('!')[1]}"
            f"+({esc['var_margem_ebitda'].split('!')[1]}-{esc['partida_margem_ebitda'].split('!')[1]})"
            f"*{c - colunas[0]}/{passos}"
        ),
        PCT,
    )
    aba.pular()

    aba.cabecalho(
        {**rotulos_anos, nota_col: "De onde veio"}, "Premissas iguais nos três cenários (editáveis)"
    )
    for nome, rotulo in premissas.POR_ANO.items():
        aba.escrever(
            nome,
            rotulo,
            dict(zip(colunas, p[nome]["valores"], strict=True)),
            FORMATO_PREMISSA.get(nome, PCT),
            entrada=True,
            nota=p[nome]["origem"],
        )
    aba.pular()

    aba.cabecalho({COL_ANO1: "Valor", nota_col: "De onde veio"}, "Premissas gerais")
    for nome, rotulo in premissas.ESCALARES.items():
        aba.escrever(
            nome,
            rotulo,
            {COL_ANO1: p[nome]["valor"]},
            FORMATO_PREMISSA.get(nome, PCT),
            entrada=True,
            nota=p[nome]["origem"],
        )
        esc[nome] = _celula(ws, aba.linha[nome])
    aba.pular()

    aba.cabecalho({COL_ANO1: "Valor", nota_col: "Fonte"}, "Dados de mercado e datas")
    ano1 = anos[0]
    for nome, rotulo, valor, formato, nota in (
        ("data_base", "Data-base do valuation", base.data_base, "DD/MM/YYYY", "Último ITR."),
        (
            "fracao_ano1",
            f"Fração de {ano1} que ainda falta",
            f"=(DATE({ano1},12,31)-{L(COL_ANO1)}{aba.proxima})/365",
            "0.000",
            f"Só essa parte do fluxo de {ano1} entra no valor.",
        ),
        (
            "acoes",
            "Ações em circulação (milhões)",
            base.acoes,
            "#,##0.0",
            f"CVM, composição do capital em {mercado['data_acoes']}, sem tesouraria.",
        ),
        (
            "preco",
            "Preço da ação (R$)",
            base.preco,
            REAIS,
            f"B3, fechamento de {mercado['data_preco']}.",
        ),
        (
            "valor_de_mercado",
            "Valor de mercado (R$ milhões)",
            base.valor_de_mercado,
            MI,
            "Ações em circulação pelo preço de cada classe.",
        ),
    ):
        aba.escrever(nome, rotulo, {COL_ANO1: valor}, formato, entrada=True, nota=nota)
        esc[nome] = _celula(ws, aba.linha[nome])

    aba.larguras(rotulo=56, nota=90)
    ws.freeze_panes = "C4"
    return aba, esc


# --------------------------------------------------------------------------- Histórico

# (nome, rótulo, formato) das linhas que entram como dado da CVM.
HIST_DADOS = (
    ("Demonstração do resultado", None, None),
    ("receita", "Receita líquida", MI),
    ("custo", "Custo dos produtos vendidos", MI),
    ("lucro_bruto", "Lucro bruto", MI),
    ("despesas_vendas", "Despesas com vendas", MI),
    ("despesas_ga", "Despesas gerais e administrativas", MI),
    ("perdas_recuperabilidade", "Perdas por recuperabilidade de ativos (impairment)", MI),
    ("despesas_operacionais", "Total de despesas/receitas operacionais", MI),
    ("equivalencia", "Equivalência patrimonial", MI),
    ("ebit", "EBIT (resultado antes do financeiro e dos tributos)", MI),
    ("resultado_financeiro", "Resultado financeiro", MI),
    ("lair", "Lucro antes dos tributos", MI),
    ("ir", "Imposto de renda e CSLL", MI),
    ("lucro_liquido", "Lucro líquido consolidado", MI),
    ("lucro_controladores", "Lucro atribuído aos controladores", MI),
    ("Fluxo de caixa", None, None),
    ("da", "Depreciação, amortização e exaustão", MI),
    ("fco", "Caixa das atividades operacionais", MI),
    ("capex", "Investimento em imobilizado e intangível (capex)", MI),
    ("dividendos_pagos", "Dividendos e JCP pagos", MI),
    ("Balanço patrimonial", None, None),
    ("caixa", "Caixa e equivalentes", MI),
    ("aplicacoes", "Aplicações financeiras", MI),
    ("contas_receber", "Contas a receber", MI),
    ("estoques", "Estoques", MI),
    ("ativo_circulante", "Ativo circulante", MI),
    ("investimentos", "Investimentos em coligadas", MI),
    ("imobilizado", "Imobilizado", MI),
    ("intangivel", "Intangível", MI),
    ("ativo_total", "Ativo total", MI),
    ("fornecedores", "Fornecedores", MI),
    ("divida_cp", "Empréstimos e financiamentos - curto prazo", MI),
    ("passivo_circulante", "Passivo circulante", MI),
    ("divida_lp", "Empréstimos e financiamentos - longo prazo", MI),
    ("patrimonio_liquido", "Patrimônio líquido consolidado", MI),
    ("minoritarios", "Participação de não controladores", MI),
)


def _aba_historico(wb: Workbook, ticker: str, esc: dict[str, str]) -> tuple[Aba, int, int]:
    """Dados da CVM e indicadores em fórmula. Devolve a aba e as colunas do ano-base e do LTM."""
    h = historico.carregar()
    h = h[h["ticker"] == ticker].reset_index(drop=True)
    colunas = list(range(3, 3 + len(h)))
    aba = Aba(wb.create_sheet("Histórico"), colunas)
    aba.titulo(
        f"Histórico - {empresa(ticker).nome}",
        "Fonte: demonstrações consolidadas entregues à CVM (DFP e ITR). "
        "LTM = últimos doze meses; o balanço é o do trimestre.",
    )
    aba.cabecalho(dict(zip(colunas, h["periodo"], strict=True)))
    for nome, rotulo, formato in HIST_DADOS:
        if rotulo is None:
            aba.secao(nome)
            continue
        aba.escrever(nome, rotulo, dict(zip(colunas, h[nome].round(3), strict=True)), formato)

    def x(nome: str, c: int) -> str:
        return f"{L(c)}{aba.linha[nome]}"

    def ant(nome: str, c: int) -> str | None:
        return x(nome, c - 1) if c > colunas[0] else None

    # No histórico vale a alíquota nominal, igual para todas: o passado não pode mudar
    # quando alguém troca a alíquota da projeção na aba Premissas.
    ir = historico.ALIQUOTA_IR
    aba.secao("Indicadores (fórmulas)")
    indicadores: tuple[tuple[str, str, Formula, str], ...] = (
        ("ebitda", "EBITDA (EBIT + depreciação)", lambda c: f"={x('ebit', c)}+{x('da', c)}", MI),
        (
            "ebitda_recorrente",
            "EBITDA sem perdas por recuperabilidade",
            lambda c: f"={x('ebitda', c)}-{x('perdas_recuperabilidade', c)}",
            MI,
        ),
        (
            "margem_ebitda_recorrente",
            "Margem EBITDA sem perdas por recuperabilidade",
            lambda c: f"={x('ebitda_recorrente', c)}/{x('receita', c)}",
            PCT,
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
        ("margem_ebit", "Margem EBIT", lambda c: f"={x('ebit', c)}/{x('receita', c)}", PCT),
        (
            "margem_liquida",
            "Margem líquida",
            lambda c: f"={x('lucro_liquido', c)}/{x('receita', c)}",
            PCT,
        ),
        (
            "outras_pct",
            "Outras operacionais / receita",
            lambda c: f"={x('outras_operacionais', c)}/{x('receita', c)}",
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
            lambda c: f"={x('divida_liquida', c)}/{x('ebitda', c)}",
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
        aba.escrever(nome, rotulo, formula, formato)

    aba.larguras(rotulo=58, nota=4)
    aba.ws.freeze_panes = "C5"
    ano_base = colunas[list(h["periodo"]).index("2025")]
    ltm = colunas[-1]
    return aba, ano_base, ltm


# --------------------------------------------------------------------------- Projeção


def _aba_projecao(
    wb: Workbook, dados: dict[str, Any], prem: Aba, esc: dict[str, str], hist: Aba, col_hist: int
) -> Aba:
    anos: list[int] = dados["anos"]
    proj_cols = list(range(COL_ANO1, COL_ANO1 + len(anos)))
    aba = Aba(wb.create_sheet("Projeção"), [COL_BASE, *proj_cols])
    aba.titulo(
        f"Projeção - {dados['empresa']}",
        "DRE, balanço e fluxo de caixa ligados. Custos e despesas em valor positivo. "
        f"{dados['ano_base']} é o realizado; os demais anos são fórmulas sobre as premissas.",
    )
    aba.cabecalho(
        {COL_BASE: dados["ano_base"], **{c: f"{a}E" for c, a in zip(proj_cols, anos, strict=True)}}
    )

    def x(nome: str, c: int) -> str:
        return f"{L(c)}{aba.linha[nome]}"

    def a(nome: str, c: int) -> str:  # ano anterior
        return x(nome, c - 1)

    def p(nome: str, c: int) -> str:
        return prem.ref(nome, c)

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
        )

    ir = esc["aliquota_ir"]
    estrutura: list[str | None] = [
        "s_dre", "receita", "custo_caixa", "despesas", "equivalencia", "ebitda", "da", "ebit",
        "receita_financeira", "despesa_financeira", "resultado_financeiro", "lair", "ir",
        "lucro_liquido", "nopat", None,
        "s_inv", "capex", "ativo_fixo", "contas_receber", "estoques", "fornecedores",
        "capital_de_giro", "variacao_giro", None,
        "s_fc", "fcff", "captacao_liquida", "fcfe", "dividendos", "variacao_caixa", None,
        "s_bp", "caixa_total", "investimentos", "outros_ativos", "ativo_total", "divida_bruta",
        "outros_passivos", "patrimonio_liquido", "passivo_e_pl", "checagem_balanco", None,
        "s_ind", "crescimento_receita", "margem_ebitda", "margem_ebit", "divida_liquida",
        "divida_liquida_ebitda", "roic",
    ]  # fmt: skip
    aba.planejar(estrutura)

    def secao(nome: str, texto: str) -> None:
        aba.proxima = aba.linha[nome]
        aba.secao(texto)

    secao("s_dre", "Demonstração do resultado")
    linha(
        "receita",
        "Receita líquida",
        f"={h('receita')}",
        lambda c: f"={a('receita', c)}*(1+{p('crescimento_receita', c)})",
        destaque=True,
    )
    # O custo é o que sobra: a margem EBITDA vem do cenário e as despesas seguem a receita.
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
        lambda c: f"={x('receita', c)}*{p('despesas_pct', c)}",
    )
    linha(
        "equivalencia",
        "(+/-) Equivalência patrimonial",
        f"={h('equivalencia')}",
        lambda c: f"={p('equivalencia', c)}",
    )
    linha(
        "ebitda",
        "EBITDA",
        f"={x('receita', COL_BASE)}-{x('custo_caixa', COL_BASE)}-{x('despesas', COL_BASE)}"
        f"+{x('equivalencia', COL_BASE)}",
        lambda c: f"={x('receita', c)}*{p('margem_ebitda', c)}",
        destaque=True,
    )
    linha(
        "da",
        "(-) Depreciação e amortização",
        f"={h('da')}",
        lambda c: f"={a('ativo_fixo', c)}*{p('depreciacao_pct', c)}",
    )
    ebit: Formula = lambda c: f"={x('ebitda', c)}-{x('da', c)}"  # noqa: E731
    linha("ebit", "EBIT", ebit(COL_BASE), ebit, destaque=True)
    linha(
        "receita_financeira",
        "(+) Rendimento do caixa",
        None,
        lambda c: f"={a('caixa_total', c)}*{esc['rendimento_caixa']}",
    )
    linha(
        "despesa_financeira",
        "(-) Juros da dívida",
        None,
        lambda c: f"={a('divida_bruta', c)}*{esc['custo_divida']}",
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
        lambda c: f"=MAX(0,{x('lair', c)}-{x('equivalencia', c)})*{ir}",
    )
    lucro: Formula = lambda c: f"={x('lair', c)}-{x('ir', c)}"  # noqa: E731
    linha("lucro_liquido", "Lucro líquido", lucro(COL_BASE), lucro, destaque=True)
    nopat: Formula = lambda c: f"=({x('ebit', c)}-{x('equivalencia', c)})*(1-{ir})"  # noqa: E731
    linha("nopat", "NOPAT (EBIT sem equivalência, após imposto)", nopat(COL_BASE), nopat)

    secao("s_inv", "Investimento, depreciação e capital de giro")
    linha("capex", "Capex", f"={h('capex')}", lambda c: f"={x('receita', c)}*{p('capex_pct', c)}")
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
        lambda c: f"={x('receita', c)}*{p('prazo_recebimento', c)}/365",
    )
    linha(
        "estoques",
        "Estoques",
        f"={h('estoques')}",
        lambda c: f"={x('custo_caixa', c)}*{p('prazo_estoque', c)}/365",
    )
    linha(
        "fornecedores",
        "Fornecedores",
        f"={h('fornecedores')}",
        lambda c: f"={x('custo_caixa', c)}*{p('prazo_pagamento', c)}/365",
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

    secao("s_fc", "Fluxos de caixa livres")
    linha(
        "fcff",
        "FCFF - fluxo de caixa livre da empresa",
        None,
        lambda c: f"={x('nopat', c)}+{x('da', c)}-{x('capex', c)}-{x('variacao_giro', c)}",
        destaque=True,
    )
    linha(
        "captacao_liquida",
        "(+) Captação líquida de dívida",
        None,
        lambda c: f"={p('captacao_liquida', c)}",
    )
    linha(
        "fcfe",
        "FCFE - fluxo de caixa livre do acionista",
        None,
        lambda c: (
            f"={x('lucro_liquido', c)}-{x('equivalencia', c)}+{x('da', c)}-{x('capex', c)}"
            f"-{x('variacao_giro', c)}+{x('captacao_liquida', c)}"
        ),
        destaque=True,
    )
    linha(
        "dividendos",
        "(-) Dividendos",
        None,
        lambda c: f"=MAX(0,{x('lucro_liquido', c)})*{esc['payout']}",
    )
    linha(
        "variacao_caixa",
        "Variação do caixa",
        None,
        lambda c: f"={x('fcfe', c)}-{x('dividendos', c)}",
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
        lambda c: f"={a('divida_bruta', c)}+{x('captacao_liquida', c)}",
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
    linha(
        "crescimento_receita",
        "Crescimento da receita",
        None,
        lambda c: f"={x('receita', c)}/{a('receita', c)}-1",
        PCT,
    )
    margem: Formula = lambda c: f"={x('ebitda', c)}/{x('receita', c)}"  # noqa: E731
    linha("margem_ebitda", "Margem EBITDA", margem(COL_BASE), margem, PCT)
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
        lambda c: f"={x('nopat', c)}/({a('capital_de_giro', c)}+{a('ativo_fixo', c)})",
        PCT,
    )

    aba.larguras(rotulo=52, nota=4)
    aba.ws.freeze_panes = "C5"
    return aba


# --------------------------------------------------------------------------- WACC e DCF


def _aba_wacc(wb: Workbook, esc: dict[str, str], hist: Aba, col_ltm: int) -> dict[str, str]:
    aba = Aba(wb.create_sheet("WACC"), [COL_ANO1])
    ws = aba.ws
    aba.titulo(
        "Custo de capital",
        "CAPM para o capital próprio; WACC é a média com o custo da dívida depois do imposto.",
    )
    nota = COL_ANO1 + 1

    def x(nome: str) -> str:
        return f"{L(COL_ANO1)}{aba.linha[nome]}"

    def linha(nome: str, rotulo: str, formula: str, formato: str = PCT, **kw: Any) -> None:
        aba.escrever(nome, rotulo, {COL_ANO1: formula}, formato, **kw)

    aba.cabecalho({COL_ANO1: "Valor", nota: "Conta"}, "Capital próprio (CAPM)")
    linha("rf", "Juro sem risco (Rf)", f"={esc['juro_sem_risco']}")
    linha("beta", "Beta", f"={esc['beta']}", DEC)
    linha("premio", "Prêmio de risco de mercado", f"={esc['premio_mercado']}")
    linha("adicional", "Prêmio adicional", f"={esc['premio_adicional']}")
    linha(
        "ke",
        "Custo do capital próprio (Ke)",
        f"={x('rf')}+{x('beta')}*{x('premio')}+{x('adicional')}",
        destaque=True,
        nota="Ke = Rf + beta x prêmio de mercado + prêmio adicional",
    )
    aba.pular()
    aba.cabecalho({COL_ANO1: "Valor", nota: "Conta"}, "Dívida")
    linha("kd", "Custo da dívida antes do imposto (Kd)", f"={esc['custo_divida']}")
    linha("ir", "Alíquota de IR e CSLL", f"={esc['aliquota_ir']}")
    linha(
        "kd_liquido",
        "Custo da dívida após o imposto",
        f"={x('kd')}*(1-{x('ir')})",
        destaque=True,
        nota="Juro é dedutível: Kd x (1 - alíquota)",
    )
    aba.pular()
    aba.cabecalho({COL_ANO1: "Valor", nota: "Conta"}, "Média ponderada")
    linha("wd", "Peso da dívida", f"={esc['peso_divida']}")
    linha("we", "Peso do capital próprio", f"=1-{x('wd')}")
    linha(
        "wacc",
        "WACC pelo CAPM",
        f"={x('ke')}*{x('we')}+{x('kd_liquido')}*{x('wd')}",
        destaque=True,
        nota="WACC = Ke x peso do capital próprio + Kd após imposto x peso da dívida",
    )
    aba.pular()
    aba.cabecalho({COL_ANO1: "Valor", nota: "Conta"}, "Cenário")
    linha(
        "ajuste",
        "Ajuste do cenário (pontos sobre o CAPM)",
        f"={esc['ajuste_wacc']}",
        "0.00%;[Red]-0.00%",
        nota="Da aba Premissas: zero no moderado, positivo no pessimista, negativo no otimista.",
    )
    linha(
        "wacc_uso",
        "WACC em uso",
        f"={x('wacc')}+{x('ajuste')}",
        destaque=True,
        nota="É a taxa que desconta o fluxo da empresa (FCFF) na aba DCF.",
    )
    linha(
        "ke_uso",
        "Ke em uso",
        f"={x('ke')}+{x('ajuste')}",
        nota="O mesmo ajuste no custo do capital próprio, que desconta o FCFE.",
    )
    ws.cell(aba.linha["wacc_uso"], COL_ANO1).fill = FUNDO_RESULTADO
    aba.pular()
    aba.cabecalho({COL_ANO1: "Valor", nota: "Conta"}, "Referência: estrutura a valor de mercado")
    linha("mercado", "Valor de mercado (R$ milhões)", f"={esc['valor_de_mercado']}", MI)
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
        nota="Compare com o peso usado acima.",
    )
    aba.larguras(rotulo=44, numeros=14, nota=70)
    return {"ke": _celula(ws, aba.linha["ke_uso"]), "wacc": _celula(ws, aba.linha["wacc_uso"])}


def _aba_dcf(
    wb: Workbook,
    dados: dict[str, Any],
    esc: dict[str, str],
    taxas: dict[str, str],
    proj: Aba,
    hist: Aba,
    col_ltm: int,
) -> tuple[Aba, dict[str, str]]:
    anos: list[int] = dados["anos"]
    cols = list(range(COL_ANO1, COL_ANO1 + len(anos)))
    ultimo = cols[-1]
    aba = Aba(wb.create_sheet("DCF"), cols)
    ws = aba.ws
    aba.titulo(
        f"Fluxo de caixa descontado - {dados['empresa']}",
        "O valor da empresa é a soma dos fluxos de caixa futuros trazidos a valor de hoje.",
    )
    aba.cabecalho({c: f"{a}E" for c, a in zip(cols, anos, strict=True)})

    def x(nome: str, c: int = COL_ANO1) -> str:
        return f"{L(c)}{aba.linha[nome]}"

    def fx(nome: str, c: int = COL_ANO1) -> str:
        return f"${L(c)}${aba.linha[nome]}"

    def faixa(nome: str) -> str:
        r = aba.linha[nome]
        return f"${L(cols[0])}${r}:${L(ultimo)}${r}"

    wacc, ke, g = taxas["wacc"], taxas["ke"], esc["crescimento_perpetuo"]

    aba.secao("Fluxo da empresa (FCFF), descontado pelo WACC")
    aba.escrever("fcff", "FCFF", lambda c: f"={proj.ref('fcff', c)}", destaque=True)
    aba.escrever(
        "fracao",
        "Parte do ano que entra no valor",
        lambda c: f"={esc['fracao_ano1']}" if c == cols[0] else 1,
        "0.000",
    )
    aba.escrever(
        "fim",
        "Fim do período (anos desde a data-base)",
        lambda c: f"={x('fracao', c)}" if c == cols[0] else f"={x('fim', c - 1)}+1",
        "0.000",
    )
    aba.escrever(
        "meio",
        "Meio do período (quando o caixa entra, em média)",
        lambda c: f"={x('fim', c)}-{x('fracao', c)}/2",
        "0.000",
    )
    aba.escrever("fator", "Fator de desconto", lambda c: f"=1/(1+{wacc})^{x('meio', c)}", "0.0000")
    aba.escrever(
        "vp",
        "Valor presente do fluxo",
        lambda c: f"={x('fcff', c)}*{x('fracao', c)}*{x('fator', c)}",
        destaque=True,
    )
    aba.pular()

    def unico(nome: str, rotulo: str, formula: str, formato: str = MI, **kw: Any) -> None:
        aba.escrever(nome, rotulo, {COL_ANO1: formula}, formato, **kw)

    aba.secao("Perpetuidade (Gordon)")
    unico("wacc", "WACC", f"={wacc}", PCT)
    unico("g", "Crescimento na perpetuidade (g)", f"={g}", PCT)
    unico(
        "fcff_terminal",
        f"FCFF normalizado de {anos[-1]}",
        f"={proj.ref('nopat', ultimo)}+{proj.ref('da', ultimo)}"
        f"-{esc['capex_perpetuidade']}*{proj.ref('da', ultimo)}"
        f"-{proj.ref('variacao_giro', ultimo)}",
        nota="NOPAT + depreciação - capex de reposição - investimento em giro",
    )
    unico(
        "vt",
        "Valor terminal no fim do último ano",
        f"={x('fcff_terminal')}*(1+{x('g')})/({x('wacc')}-{x('g')})",
        nota="FCFF x (1 + g) / (WACC - g)",
    )
    unico(
        "vp_vt",
        "Valor presente do valor terminal",
        f"={x('vt')}/(1+{x('wacc')})^{x('fim', ultimo)}",
    )
    aba.pular()

    aba.secao("Do valor da empresa ao preço por ação")
    unico("soma_vp", "Valor presente dos fluxos projetados", f"=SUM({faixa('vp')})")
    unico("vp_vt2", "(+) Valor presente do valor terminal", f"={x('vp_vt')}")
    unico(
        "ev", "Valor da empresa (Enterprise Value)", f"={x('soma_vp')}+{x('vp_vt2')}", destaque=True
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
        nota="O FCFF não inclui a equivalência; as coligadas entram pelo valor do balanço.",
    )
    unico("outros", "(-) Outros passivos tratados como dívida", f"={esc['outros_ajustes']}")
    unico(
        "equity",
        "Valor do acionista (Equity Value)",
        f"={x('ev')}-{x('divida_liquida')}-{x('minoritarios')}+{x('investimentos')}-{x('outros')}",
        destaque=True,
    )
    unico("acoes", "Ações em circulação (milhões)", f"={esc['acoes']}", "#,##0.0")
    unico(
        "preco_justo", "Preço justo por ação", f"={x('equity')}/{x('acoes')}", REAIS, destaque=True
    )
    ws.cell(aba.linha["preco_justo"], COL_ANO1).fill = FUNDO_RESULTADO
    unico("preco", "Preço de mercado", f"={esc['preco']}", REAIS)
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
    aba.escrever("fcfe", "FCFE", lambda c: f"={proj.ref('fcfe', c)}", destaque=True)
    aba.escrever("fator_ke", "Fator de desconto", lambda c: f"=1/(1+{ke})^{x('meio', c)}", "0.0000")
    aba.escrever(
        "vp_fcfe",
        "Valor presente do fluxo",
        lambda c: f"={x('fcfe', c)}*{x('fracao', c)}*{x('fator_ke', c)}",
    )
    unico("ke", "Custo do capital próprio (Ke)", f"={ke}", PCT)
    unico(
        "fcfe_terminal",
        f"FCFE normalizado de {anos[-1]}",
        f"={proj.ref('lucro_liquido', ultimo)}-{proj.ref('equivalencia', ultimo)}"
        f"+{proj.ref('da', ultimo)}-{esc['capex_perpetuidade']}*{proj.ref('da', ultimo)}"
        f"-{proj.ref('variacao_giro', ultimo)}+{proj.ref('captacao_liquida', ultimo)}",
    )
    unico(
        "vp_vt_fcfe",
        "Valor presente do valor terminal",
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
    aba.linha["sens_topo"] = topo
    aba.proxima = topo + 7

    aba.larguras(rotulo=50, numeros=14, nota=70)
    ws.freeze_panes = "C5"
    saidas = {k: _celula(ws, aba.linha[k]) for k in ("preco_justo", "ev", "equity", "potencial")}
    return aba, saidas


# --------------------------------------------------------------------------- Múltiplos e cenários


def _aba_multiplos(wb: Workbook, ticker: str, dcf: dict[str, str]) -> None:
    t = multiplos.calcular()
    ordem = [ticker, *[k for k in t.index if k != ticker]]  # a empresa em cima, as pares abaixo
    ws = wb.create_sheet("Múltiplos")
    aba = Aba(ws, list(range(3, 16)))
    aba.titulo(
        "Valuation por múltiplos",
        "Últimos doze meses. A mediana das comparáveis é aplicada aos números da empresa.",
    )
    campos = (
        ("Setor", "setor", None),
        ("Preço", "preco", REAIS),
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
    aba.colunas = list(col.values())
    aba.cabecalho({c: rotulo for rotulo, c in col.items()}, "Empresa (R$ milhões)")
    primeira = aba.proxima
    for i, k in enumerate(ordem):
        r = primeira + i
        ws.cell(r, 2, f"{t.loc[k, 'empresa']} ({k})").font = NEGRITO if i == 0 else Font()

        def c(rotulo: str, r: int = r) -> str:
            return f"{L(col[rotulo])}{r}"

        for rotulo, campo, formato in campos:
            if campo is not None:
                valor = t.loc[k, campo]
                celula = ws.cell(r, col[rotulo], valor if isinstance(valor, str) else float(valor))
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
    mediana = ultima + 1
    ws.cell(mediana, 2, "Mediana das comparáveis (sem a empresa)").font = NEGRITO
    for rotulo in ("EV/EBITDA", "EV/EBIT", "P/L", "P/VP"):
        letra = L(col[rotulo])
        celula = ws.cell(mediana, col[rotulo], f"=MEDIAN({letra}{primeira + 1}:{letra}{ultima})")
        celula.number_format, celula.font, celula.fill = VEZES, NEGRITO, FUNDO_SECAO

    def e(rotulo: str) -> str:  # número da própria empresa
        return f"{L(col[rotulo])}{primeira}"

    def m(rotulo: str) -> str:
        return f"{L(col[rotulo])}{mediana}"

    acoes = f"({e('Valor de mercado')}/{e('Preço')})"
    r = mediana + 2
    ws.cell(r, 2, "Preço por ação implícito").font = BRANCO
    ws.cell(r, 3, "R$ / ação").font = BRANCO
    ws.cell(r, 4, "Como").font = BRANCO
    for c_ in (2, 3, 4):
        ws.cell(r, c_).fill = FUNDO_CABECALHO
    linhas = (
        (
            "Pelo EV/EBITDA das comparáveis",
            f"=IF({e('EBITDA')}>0,({m('EV/EBITDA')}*{e('EBITDA')}-{e('Dívida líquida')}"
            f'-{e("Minoritários")})/{acoes},"n.a.")',
            "Mediana x EBITDA, menos dívida líquida e minoritários",
        ),
        (
            "Pelo EV/EBIT das comparáveis",
            f"=IF({e('EBIT')}>0,({m('EV/EBIT')}*{e('EBIT')}-{e('Dívida líquida')}"
            f'-{e("Minoritários")})/{acoes},"n.a.")',
            "Mediana x EBIT, menos dívida líquida e minoritários",
        ),
        (
            "Pelo P/L das comparáveis",
            f'=IF({e("Lucro")}>0,{m("P/L")}*{e("Lucro")}/{acoes},"n.a.")',
            "Mediana x lucro (não se aplica com prejuízo)",
        ),
        (
            "Pelo P/VP das comparáveis",
            f"={m('P/VP')}*{e('Patrimônio')}/{acoes}",
            "Mediana x patrimônio dos controladores",
        ),
        ("Pelo fluxo de caixa descontado (aba DCF)", f"={dcf['preco_justo']}", "Para comparar"),
        ("Preço de mercado", f"={e('Preço')}", ""),
    )
    for i, (rotulo, formula, como) in enumerate(linhas, start=1):
        ws.cell(r + i, 2, rotulo)
        celula = ws.cell(r + i, 3, formula)
        celula.number_format = REAIS
        celula.alignment = Alignment(horizontal="right")
        ws.cell(r + i, 4, como).font = Font(italic=True, color="595959")
    aba.larguras(rotulo=44, numeros=15, nota=4)


def _aba_cenarios(
    wb: Workbook,
    ticker: str,
    dados: dict[str, Any],
    prem: Aba,
    esc: dict[str, str],
    proj: Aba,
    dcf: dict[str, str],
) -> None:
    anos: list[int] = dados["anos"]
    cols = list(range(COL_ANO1, COL_ANO1 + len(anos)))
    aba = Aba(wb.create_sheet("Cenários"), cols)
    ws = aba.ws
    aba.titulo(
        "Cenários e movimento do caixa",
        "Troque o cenário na aba Premissas (célula D4) ou ajuste uma variável à mão: tudo abaixo "
        "e o resto da planilha seguem.",
    )
    ws.cell(aba.proxima, 2, "Cenário em uso").font = NEGRITO
    ws.cell(aba.proxima, COL_ANO1, "='Premissas'!D4").font = NEGRITO
    aba.pular(2)

    aba.cabecalho(
        {c: f"{a}E" for c, a in zip(cols, anos, strict=True)}, "Entradas e saídas de caixa"
    )

    def x(nome: str, c: int) -> str:
        return f"{L(c)}{aba.linha[nome]}"

    def pr(nome: str, c: int) -> str:
        return proj.ref(nome, c)

    aba.secao("Entradas (cash in)")
    aba.escrever(
        "operacao",
        "Caixa gerado pela operação (EBITDA sem equivalência)",
        lambda c: f"={pr('ebitda', c)}-{pr('equivalencia', c)}",
    )
    aba.escrever(
        "rendimento",
        "Rendimento do caixa",
        lambda c: f"={pr('caixa_total', c - 1)}*{esc['rendimento_caixa']}",
    )
    aba.escrever(
        "captacao",
        "Captação líquida de dívida (se positiva)",
        lambda c: f"=MAX(0,{pr('captacao_liquida', c)})",
    )
    aba.escrever(
        "entradas",
        "Total de entradas",
        lambda c: f"={x('operacao', c)}+{x('rendimento', c)}+{x('captacao', c)}",
        destaque=True,
    )
    aba.secao("Saídas (cash out)")
    aba.escrever("impostos", "Imposto de renda e CSLL", lambda c: f"={pr('ir', c)}")
    aba.escrever("capex", "Capex", lambda c: f"={pr('capex', c)}")
    aba.escrever("giro", "Investimento em capital de giro", lambda c: f"={pr('variacao_giro', c)}")
    aba.escrever(
        "juros", "Juros da dívida", lambda c: f"={pr('divida_bruta', c - 1)}*{esc['custo_divida']}"
    )
    aba.escrever(
        "amortizacao",
        "Amortização líquida de dívida (se negativa a captação)",
        lambda c: f"=MAX(0,-{pr('captacao_liquida', c)})",
    )
    aba.escrever("dividendos", "Dividendos", lambda c: f"={pr('dividendos', c)}")
    aba.escrever(
        "saidas",
        "Total de saídas",
        lambda c: f"=SUM({L(c)}{aba.linha['impostos']}:{L(c)}{aba.linha['dividendos']})",
        destaque=True,
    )
    aba.secao("Saldo")
    aba.escrever(
        "variacao",
        "Entradas - saídas",
        lambda c: f"={x('entradas', c)}-{x('saidas', c)}",
        destaque=True,
    )
    aba.escrever("caixa_final", "Caixa no fim do ano", lambda c: f"={pr('caixa_total', c)}")
    aba.escrever(
        "confere",
        "Checagem: bate com a variação de caixa da projeção (zero)",
        lambda c: f"=ROUND({x('variacao', c)}-{pr('variacao_caixa', c)},3)",
    )
    aba.pular(2)

    # Comparativo: valores do modelo em Python para os três cenários.
    topo = aba.proxima
    titulos = ["Comparativo dos cenários (calculado pelo modelo)", "", *NOME_CENARIO.values()]
    for i, texto in enumerate(titulos):
        celula = ws.cell(topo, 2 + i, texto)
        celula.font, celula.fill = BRANCO, FUNDO_CABECALHO
    resultados = {c: modelo.rodar(ticker, dados, c) for c in premissas.CENARIOS}
    ultimo = anos[-1]
    linhas: tuple[tuple[str, Callable[[dict[str, Any]], float], str], ...] = (
        ("Preço justo por ação", lambda r: r["valuation"]["preco_justo"], REAIS),
        ("Valor da empresa (EV)", lambda r: r["valuation"]["ev"], MI),
        ("Valor do acionista", lambda r: r["valuation"]["equity"], MI),
        ("WACC", lambda r: r["valuation"]["wacc"], PCT),
        (f"Receita {ultimo}E", lambda r: r["projecao"].loc["receita", ultimo], MI),
        (f"Margem EBITDA {ultimo}E", lambda r: r["projecao"].loc["margem_ebitda", ultimo], PCT),
        (f"Caixa no fim de {ultimo}E", lambda r: r["projecao"].loc["caixa_total", ultimo], MI),
        (
            f"Dívida líquida / EBITDA {ultimo}E",
            lambda r: r["projecao"].loc["divida_liquida_ebitda", ultimo],
            VEZES,
        ),
    )
    for i, (rotulo, pegar, formato) in enumerate(linhas, start=1):
        ws.cell(topo + i, 2, rotulo)
        for j, cenario in enumerate(premissas.CENARIOS):
            celula = ws.cell(topo + i, COL_ANO1 + j, float(pegar(resultados[cenario])))
            celula.number_format = formato
    r = topo + len(linhas) + 2
    ws.cell(r, 2, "Preço justo na planilha viva, no cenário em uso")
    vivo = ws.cell(r, COL_ANO1, f"={dcf['preco_justo']}")
    vivo.number_format, vivo.font, vivo.fill = REAIS, NEGRITO, FUNDO_RESULTADO
    ws.cell(r + 1, 2, "Diferença para o comparativo acima (zero sem ajuste manual)")
    preco_linha = topo + 1
    # Com ajuste manual o cenário em uso já não é nenhum dos três do comparativo.
    manuais = [prem.linha[f"var_{nome}"] for nome in premissas.VARIAVEIS]
    faixa_manual = f"'Premissas'!$H${min(manuais)}:$H${max(manuais)}"
    ws.cell(
        r + 1,
        COL_ANO1,
        f"=IF(COUNT({faixa_manual})=0,ROUND({L(COL_ANO1)}{r}"
        f"-INDEX({L(COL_ANO1)}{preco_linha}:{L(COL_ANO1 + 2)}{preco_linha},{esc['cenario']}),2),"
        '"-")',
    ).number_format = DEC
    aba.linha["comparativo"] = topo
    aba.larguras(rotulo=56, numeros=14, nota=4)


def _aba_resumo(
    wb: Workbook, dados: dict[str, Any], dcf_aba: Aba, dcf: dict[str, str], proj: Aba
) -> None:
    ws = wb.create_sheet("Resumo", 0)
    aba = Aba(ws, [COL_ANO1])
    anos: list[int] = dados["anos"]
    aba.titulo(
        f"Valuation - {dados['empresa']} ({dados['ticker']})",
        f"Data-base {dados['data_base']}. Dados públicos da CVM e da B3. "
        "R$ milhões, salvo indicação.",
    )
    aviso = (
        "Estudo acadêmico e de portfólio. Não é recomendação de compra ou venda. "
        "O resultado depende das premissas da aba Premissas"
        + (
            ", que nesta versão são uma proposta automática ainda não revisada."
            if dados["status"] != "aprovada"
            else "."
        )
    )
    ws.cell(3, 2, aviso).font = Font(italic=True, color="C00000")
    aba.proxima = 5
    aba.cabecalho({COL_ANO1: "Valor"}, "Resultado no cenário em uso")

    def unico(rotulo: str, formula: str, formato: str, destaque: bool = False) -> None:
        aba.escrever(rotulo, rotulo, {COL_ANO1: formula}, formato, destaque=destaque)

    d = dcf_aba
    unico("Cenário", "='Premissas'!D4", "@")
    unico("Preço justo por ação (DCF)", f"={dcf['preco_justo']}", REAIS, True)
    unico("Preço de mercado", f"={d.ref('preco', COL_ANO1)}", REAIS)
    unico("Diferença para o mercado", f"={dcf['potencial']}", PCT)
    unico("Valor da empresa (EV)", f"={dcf['ev']}", MI)
    unico("Valor do acionista", f"={dcf['equity']}", MI)
    unico("WACC", f"={d.ref('wacc', COL_ANO1)}", PCT)
    unico("Custo do capital próprio (Ke)", f"={d.ref('ke', COL_ANO1)}", PCT)
    unico("Crescimento na perpetuidade", f"={d.ref('g', COL_ANO1)}", PCT)
    unico("Peso do valor terminal", f"={d.ref('peso_vt', COL_ANO1)}", PCT)
    unico("Preço pelo fluxo do acionista (FCFE)", f"={d.ref('preco_fcfe', COL_ANO1)}", REAIS)
    ws.cell(aba.linha["Preço justo por ação (DCF)"], COL_ANO1).fill = FUNDO_RESULTADO
    aba.pular()
    aba.cabecalho({COL_ANO1: "Aba"}, "Como ler a planilha")
    for nome, texto in (
        ("Premissas", "Os três cenários, o ajuste manual e as demais entradas. Comece por aqui."),
        ("Histórico", "DRE, balanço e fluxo de caixa da CVM, com indicadores."),
        ("Projeção", "Receita, custos, capex, depreciação, giro e as três demonstrações ligadas."),
        ("Múltiplos", "EV/EBITDA, P/L e P/VP contra as comparáveis."),
        ("DCF", "FCFF e FCFE descontados, valor da empresa, valor do acionista, sensibilidade."),
        ("WACC", "CAPM, custo médio ponderado de capital e o ajuste do cenário."),
        ("Cenários", "Entradas e saídas de caixa e comparativo pessimista, moderado e otimista."),
    ):
        ws.cell(aba.proxima, 2, texto)
        ws.cell(aba.proxima, COL_ANO1, nome).font = NEGRITO
        aba.pular()
    aba.larguras(rotulo=78, numeros=16, nota=4)
    ws.column_dimensions["C"].width = 2

    grafico = BarChart()
    grafico.title = "FCFF projetado (R$ milhões)"
    grafico.legend = None
    r = proj.linha["fcff"]
    cab = 4  # linha do cabeçalho de anos na aba Projeção
    ultimo = COL_ANO1 + len(anos) - 1
    grafico.add_data(
        Reference(proj.ws, min_col=COL_ANO1, max_col=ultimo, min_row=r), from_rows=True
    )
    grafico.set_categories(Reference(proj.ws, min_col=COL_ANO1, max_col=ultimo, min_row=cab))
    grafico.height, grafico.width = 7.5, 14
    ws.add_chart(grafico, "F5")


# --------------------------------------------------------------------------- Montagem


def gerar(ticker: str) -> Path:
    """Monta e grava `saida/valuation_<TICKER>.xlsx`."""
    dados = premissas.carregar(ticker)
    base = modelo.carregar_base(ticker, dados)
    mercado = pd.read_csv(modelo.MERCADO_CSV).set_index("ticker").loc[ticker]

    wb = Workbook()
    wb.remove(wb.active)
    prem, esc = _aba_premissas(wb, dados, base, mercado)
    hist, col_base, col_ltm = _aba_historico(wb, ticker, esc)
    proj = _aba_projecao(wb, dados, prem, esc, hist, col_base)
    taxas = _aba_wacc(wb, esc, hist, col_ltm)
    dcf_aba, dcf = _aba_dcf(wb, dados, esc, taxas, proj, hist, col_ltm)
    _aba_multiplos(wb, ticker, dcf)
    _aba_cenarios(wb, ticker, dados, prem, esc, proj, dcf)
    _aba_resumo(wb, dados, dcf_aba, dcf, proj)

    # As abas ficam na ordem em que o estudo é lido: demonstrativos, projeção, múltiplos,
    # DCF, custo de capital e cenários.
    ordem = ["Resumo", "Premissas", "Histórico", "Projeção", "Múltiplos", "DCF", "WACC", "Cenários"]
    wb._sheets = [wb[nome] for nome in ordem]

    SAIDA.mkdir(exist_ok=True)
    destino = SAIDA / f"valuation_{ticker}.xlsx"
    wb.save(destino)
    return destino
