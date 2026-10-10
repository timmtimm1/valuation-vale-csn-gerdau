"""Onde conferir cada dado na fonte.

Uma lista só, usada pelo FONTES.md, pela página e pela aba Fontes da planilha: os links
gerais (CVM, B3, Tesouro, Banco Central, Damodaran, Banco Mundial), o documento que cada
empresa entregou à CVM e o código das contas de onde saem os números principais.

Os links dos documentos vêm do índice que a própria CVM publica dentro de cada zip
(`dfp_cia_aberta_AAAA.csv` e `itr_cia_aberta_AAAA.csv`), não são montados à mão.
"""

import pandas as pd

from valuation.empresas import DADOS, EMPRESAS, POR_TICKER

DOCUMENTOS_CSV = DADOS / "documentos_cvm.csv"

# Abre o documento no navegador, com DRE, balanço e fluxo de caixa navegáveis.
URL_DOCUMENTO = (
    "https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx"
    "?NumeroSequencialDocumento={id_doc}&CodigoTipoInstituicao=1"
)
# Todos os documentos que a empresa já entregou.
URL_EMPRESA_NA_CVM = "https://www.rad.cvm.gov.br/ENET/frmConsultaExternaCVM.aspx?codigoCVM={cd_cvm}"

GERAIS: tuple[tuple[str, str, str], ...] = (
    (
        "Balanços de todas as companhias abertas, anuais (DFP)",
        "CVM, Portal de Dados Abertos",
        "https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp",
    ),
    (
        "Balanços de todas as companhias abertas, trimestrais (ITR)",
        "CVM, Portal de Dados Abertos",
        "https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr",
    ),
    (
        "Cotações diárias de fechamento (arquivo COTAHIST)",
        "B3, Séries Históricas",
        "https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/"
        "historico/mercado-a-vista/series-historicas/",
    ),
    (
        "Juro do Tesouro prefixado e do Tesouro IPCA+",
        "Tesouro Direto, preços e taxas (Tesouro Transparente)",
        "https://www.tesourotransparente.gov.br/ckan/dataset/"
        "taxas-dos-titulos-ofertados-pelo-tesouro-direto",
    ),
    (
        "Inflação esperada (IPCA)",
        "Banco Central, Boletim Focus",
        "https://www.bcb.gov.br/publicacoes/focus",
    ),
    (
        "Prêmio de risco de mercado",
        "Aswath Damodaran (NYU), Country Default Spreads and Risk Premiums",
        "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html",
    ),
    (
        "Minério de ferro 62% Fe, média mensal",
        "Banco Mundial, Commodity Price Data (Pink Sheet)",
        "https://www.worldbank.org/en/research/commodity-markets",
    ),
    (
        "Dólar (PTAX de venda), média mensal, série 3698",
        "Banco Central, Sistema Gerenciador de Séries Temporais",
        "https://www3.bcb.gov.br/sgspub/",
    ),
    (
        "Bonificação da Gerdau de 5% em ações, de março de 2023",
        "Gerdau, aviso aos acionistas de 28/02/2023",
        "https://www.latibex.com/docs/Documentos/LED/2023/03/02/"
        "BRACN_20230301_125502_B01_GGBR3_001_20230322_001_DOC001.pdf",
    ),
)

# Onde achar, dentro do documento da CVM, os números que mais aparecem no estudo.
CONTAS: tuple[tuple[str, str, str], ...] = (
    ("Receita líquida", "Demonstração do Resultado", "3.01"),
    ("Lucro bruto", "Demonstração do Resultado", "3.03"),
    ("Perdas por recuperabilidade (impairment)", "Demonstração do Resultado", "3.04.03"),
    ("EBIT (resultado antes do financeiro e dos tributos)", "Demonstração do Resultado", "3.05"),
    ("Lucro líquido consolidado", "Demonstração do Resultado", "3.11"),
    ("Depreciação, amortização e exaustão", "Demonstração do Valor Adicionado", "7.04.01"),
    ("Caixa e aplicações financeiras", "Balanço, Ativo", "1.01.01 e 1.01.02"),
    ("Dívida (empréstimos e financiamentos)", "Balanço, Passivo", "2.01.04 e 2.02.01"),
    ("Patrimônio líquido", "Balanço, Passivo", "2.03"),
    ("Caixa das operações", "Demonstração do Fluxo de Caixa", "6.01"),
    ("Investimento (capex)", "Demonstração do Fluxo de Caixa", "linhas de 6.02"),
    ("Dividendos pagos", "Demonstração do Fluxo de Caixa", "linhas de 6.03"),
    (
        "Vale: provisões de Brumadinho e de Mariana (aviso)",
        "Balanço, Passivo",
        "2.01.06.02 e 2.02.04.02",
    ),
    (
        "CSN: adiantamentos de clientes, 'passivos de contratos' (aviso)",
        "Balanço, Passivo",
        "2.01.05.02 e 2.02.02.02",
    ),
    (
        "Usiminas: perda por recuperabilidade de 2025",
        "Demonstração do Fluxo de Caixa",
        "ajustes do lucro, em 6.01.01",
    ),
)


def _data_br(iso: str) -> str:
    return "/".join(reversed(iso[:10].split("-")))


def documentos() -> pd.DataFrame:
    return pd.read_csv(DOCUMENTOS_CSV, dtype=str)


def da_empresa(ticker: str) -> list[dict[str, str]]:
    """Links para conferir uma empresa: os dois documentos mais recentes e as páginas dela."""
    e = POR_TICKER[ticker]
    docs = documentos()
    docs = docs[docs["ticker"] == ticker]
    saida = []
    for tipo, nome in (("ITR", "Balanço trimestral (ITR)"), ("DFP", "Balanço anual (DFP)")):
        ultimo = docs[docs["doc"] == tipo].sort_values("dt_refer").iloc[-1]
        saida.append(
            {
                "rotulo": f"{nome} de {_data_br(ultimo['dt_refer'])}, como a {e.nome} entregou"
                f" à CVM em {_data_br(ultimo['dt_receb'])}",
                "url": URL_DOCUMENTO.format(id_doc=ultimo["id_doc"]),
            }
        )
    saida.append(
        {
            "rotulo": f"Todos os documentos da {e.nome} na CVM",
            "url": URL_EMPRESA_NA_CVM.format(cd_cvm=int(docs["cd_cvm"].iloc[0])),
        }
    )
    saida.append({"rotulo": f"Relações com investidores da {e.nome}", "url": e.ri})
    return saida


def de_todas() -> dict[str, list[dict[str, str]]]:
    return {e.ticker: da_empresa(e.ticker) for e in EMPRESAS}
