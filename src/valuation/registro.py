"""Registro do estudo: de onde veio cada dado e como o mercado estava no dia da análise.

Dois arquivos em texto, gerados a partir dos próprios dados (nenhum número digitado):
- `FONTES.md`: cada dado, a fonte pública, o link, o arquivo do repositório e a data
  do dado mais recente;
- `analises/AAAA-MM-DD.md`: a fotografia do dia. Preço de cada ação, juros,
  inflação esperada, minério e o resultado do modelo com as premissas daquele dia.

Rodar `valuation extrair` no futuro atualiza os dados e muda o resultado; a
fotografia fica como registro do que se sabia na data.
"""

from datetime import date
from pathlib import Path

import pandas as pd

from valuation import commodities, modelo, premissas
from valuation import fontes as onde
from valuation.b3 import MERCADO_CSV, PRECOS_CSV
from valuation.cvm import ACOES_CSV, CONTAS_CSV
from valuation.empresas import EMPRESAS, FOCO, POR_TICKER, RAIZ, REPOSITORIO
from valuation.macro import MACRO_CSV

FONTES_MD = RAIZ / "FONTES.md"
ANALISES = RAIZ / "analises"


def _br(iso: str) -> str:
    """Data ISO (AAAA-MM-DD ou AAAA-MM) no formato brasileiro."""
    return "/".join(reversed(str(iso)[:10].split("-")))


def _num(valor: float, casas: int = 2) -> str:
    """Número com ponto de milhar e vírgula decimal."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def _pct(valor: float, casas: int = 1) -> str:
    return _num(valor * 100, casas) + "%"


def _reais(valor: float) -> str:
    """Valor em reais, com o sinal de menos antes do R$."""
    return ("−" if valor < 0 else "") + "R$ " + _num(abs(valor))


def _tabela(cabecalho: list[str], linhas: list[list[str]], direita: int = 1) -> str:
    """Tabela em Markdown; as colunas a partir de `direita` ficam alinhadas à direita."""
    alinhamento = ["---" if i < direita else "---:" for i in range(len(cabecalho))]
    partes = [cabecalho, alinhamento, *linhas]
    return "\n".join("| " + " | ".join(linha) + " |" for linha in partes)


def fontes() -> Path:
    """Escreve FONTES.md."""
    macro = pd.read_csv(MACRO_CSV).set_index("indicador")
    contas = pd.read_csv(CONTAS_CSV, usecols=["doc", "dt_refer"])
    precos = pd.read_csv(PRECOS_CSV)
    serie = pd.read_csv(commodities.SERIES_CSV)
    acoes = pd.read_csv(ACOES_CSV)
    dfp = contas[contas["doc"] == "DFP"]["dt_refer"]
    itr = contas[contas["doc"] == "ITR"]["dt_refer"]

    linhas = [
        [
            "Demonstrações financeiras: DRE, balanço, fluxo de caixa e valor adicionado, "
            "consolidados",
            "CVM, Portal de Dados Abertos: [DFP](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp) "
            "(anual) e [ITR](https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr) (trimestral)",
            "`dados/contas_cvm.csv` (como a empresa entregou) e `dados/historico.csv` (padronizado)",
            f"DFP de {dfp.min()[:4]} a {dfp.max()[:4]}; ITR até {_br(itr.max())}",
        ],
        [
            "Quantidade de ações emitidas e em tesouraria",
            "CVM, quadro de composição do capital, nos mesmos arquivos de DFP e ITR",
            "`dados/acoes.csv`",
            _br(acoes["dt_refer"].max()),
        ],
        [
            "Cotações diárias de fechamento",
            "B3, [Séries Históricas (COTAHIST)](https://www.b3.com.br/pt_br/market-data-e-indices/"
            "servicos-de-dados/market-data/historico/mercado-a-vista/series-historicas/)",
            "`dados/precos.csv`; preço, faixa de 52 semanas, valor de mercado e beta em "
            "`dados/mercado.csv`",
            f"{_br(precos['data'].min())} a {_br(precos['data'].max())}",
        ],
        [
            "Bonificação da Gerdau (uma ação nova para cada cinco), usada para corrigir o preço",
            "B3, eventos corporativos; conferida no COTAHIST (queda de 17% no dia) e no número de "
            "ações da CVM",
            "`src/valuation/empresas.py`",
            "18/04/2024",
        ],
        [
            "Bonificação da Gerdau (uma ação nova para cada vinte), usada para corrigir o preço",
            "Gerdau, [aviso aos acionistas de 28/02/2023](https://www.latibex.com/docs/Documentos/"
            "LED/2023/03/02/BRACN_20230301_125502_B01_GGBR3_001_20230322_001_DOC001.pdf); "
            "conferida no COTAHIST (queda de 4% no dia) e no número de ações da CVM",
            "`src/valuation/empresas.py`",
            "22/03/2023",
        ],
        [
            "Obrigações fora da dívida, mostradas como aviso: provisões de Brumadinho e de "
            "Mariana (Vale) e adiantamentos de clientes (CSN)",
            "CVM, balanço consolidado do ITR, contas do passivo listadas abaixo",
            "`dados/contas_cvm.csv` e a coluna `obrigacoes_extras` de `dados/historico.csv`",
            _br(itr.max()),
        ],
        [
            "Juro prefixado e juro real de dez anos; mínimo e máximo do prefixado em dois anos",
            "[Tesouro Direto, preços e taxas](https://www.tesourotransparente.gov.br/ckan/dataset/"
            "taxas-dos-titulos-ofertados-pelo-tesouro-direto) (Tesouro Transparente)",
            "`dados/macro.csv`",
            _br(macro.loc["juro_prefixado_longo", "data"]),
        ],
        [
            "Inflação esperada (IPCA) de 2026 a 2030",
            "Banco Central, [Boletim Focus](https://www.bcb.gov.br/publicacoes/focus), pela API "
            "de expectativas de mercado",
            "`dados/macro.csv`",
            _br(macro.loc["ipca_2030", "data"]),
        ],
        [
            "Prêmio de risco de mercado",
            "Aswath Damodaran (NYU), [Country Default Spreads and Risk Premiums]"
            "(https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html)",
            "`dados/macro.csv`",
            _br(macro.loc["premio_mercado_maduro", "data"]),
        ],
        [
            "Minério de ferro 62% Fe, CFR China, média mensal",
            "Banco Mundial, [Commodity Price Data (Pink Sheet)]"
            "(https://www.worldbank.org/en/research/commodity-markets)",
            "`dados/commodity_e_acoes.csv`",
            f"{_br(serie['mes'].min())} a {_br(serie['mes'].max())}",
        ],
        [
            "Dólar (PTAX de venda), média mensal",
            "Banco Central, [Sistema Gerenciador de Séries Temporais]"
            "(https://www3.bcb.gov.br/sgspub/), série 3698",
            "`dados/commodity_e_acoes.csv`",
            f"{_br(serie['mes'].min())} a {_br(serie['mes'].max())}",
        ],
    ]
    empresas = ", ".join(f"{e.nome} ({e.ticker})" for e in EMPRESAS)
    por_empresa = "\n\n".join(
        f"**{POR_TICKER[ticker].nome} ({ticker})**\n\n"
        + "\n".join(f"- [{link['rotulo']}]({link['url']})" for link in links)
        for ticker, links in onde.de_todas().items()
    )
    contas_cvm = _tabela(
        ["Número", "Em qual demonstração", "Código da conta na CVM"],
        [list(linha) for linha in onde.CONTAS],
        direita=3,
    )
    texto = f"""# Fontes dos dados

Todos os dados do estudo são públicos e gratuitos. Esta lista é gerada pelo comando
`valuation registrar` a partir dos próprios arquivos, então as datas são as do dado mais
recente que está no repositório.

Empresas: {empresas}.

{_tabela(["Dado", "Fonte", "Onde está no repositório", "Data do dado"], linhas, direita=4)}

## O documento de cada empresa na CVM

Os balanços deste estudo são os que cada empresa entregou à CVM. Os links abaixo abrem o
documento original no site da CVM, com a demonstração do resultado, o balanço e o fluxo de
caixa. Os endereços vêm do índice que a própria CVM publica junto com os dados.

{por_empresa}

## Onde achar cada número dentro do documento

A CVM usa o mesmo plano de contas para todas as empresas. Com o código da conta dá para
achar no documento o mesmo número que está em `dados/contas_cvm.csv`. Use sempre as
demonstrações consolidadas; os valores do documento estão em milhares de reais e os do
estudo em milhões.

{contas_cvm}

## Como conferir

- Cada número de mercado em `dados/macro.csv` tem, na mesma linha, a data e o link de onde
  foi baixado.
- `dados/contas_cvm.csv` traz o código e a descrição de cada conta como a empresa entregou
  à CVM. Dá para abrir a DFP ou o ITR no site da CVM e comparar linha a linha.
- `uv run valuation extrair --atualizar` baixa tudo de novo das fontes. O resultado muda
  conforme os dados andam; a pasta `analises/` guarda como estava em cada data.

## O que é cálculo deste estudo

Margens, prazos, ROIC, beta, correlação, projeções e valor justo não vêm de nenhuma fonte:
são contas feitas aqui, em cima dos dados acima. As regras estão no README e a origem de
cada premissa está em `premissas/<ticker>.yaml`.
"""
    FONTES_MD.write_text(texto, encoding="utf-8")
    return FONTES_MD


def fotografia(dia: date | None = None) -> Path:
    """Escreve analises/AAAA-MM-DD.md com o mercado e o resultado do modelo na data."""
    dia = dia or date.today()
    mercado = pd.read_csv(MERCADO_CSV).set_index("ticker")
    macro = pd.read_csv(MACRO_CSV).set_index("indicador")
    precos = pd.read_csv(PRECOS_CSV)
    serie = pd.read_csv(commodities.SERIES_CSV).set_index("mes")
    correlacao = pd.read_csv(commodities.CORRELACAO_CSV)
    pregao = mercado["data_preco"].max()

    cotacoes = [
        [
            f"{POR_TICKER[t].nome} ({t})",
            "R$ " + _num(m["preco"]),
            "R$ " + _num(m["minimo_52s"]),
            "R$ " + _num(m["maximo_52s"]),
            _num(m["acoes_em_circulacao"], 1),
            _num(m["valor_de_mercado"], 0),
        ]
        for t, m in mercado.iterrows()
    ]
    do_dia = precos[precos["data"] == pregao].set_index("ticker")["fechamento"]
    outros = sorted(set(do_dia.index) - set(mercado.index))
    demais = ", ".join(f"{t} R$ {_num(do_dia[t])}" for t in outros)

    def m(indicador: str) -> float:
        return float(macro.loc[indicador, "valor"])

    ultimo_mes = serie.index[-1]
    do_mercado = [
        [
            "Juro do Tesouro prefixado de dez anos",
            _pct(m("juro_prefixado_longo"), 2),
            _br(macro.loc["juro_prefixado_longo", "data"]),
        ],
        [
            "Juro real do Tesouro IPCA+ de dez anos",
            _pct(m("juro_real_longo"), 2),
            _br(macro.loc["juro_real_longo", "data"]),
        ],
        [
            "Prefixado longo, mínimo e máximo em dois anos",
            f"{_pct(m('juro_prefixado_minimo'), 2)} a {_pct(m('juro_prefixado_maximo'), 2)}",
            _br(macro.loc["juro_prefixado_minimo", "data"]),
        ],
        [
            "Inflação esperada (Focus), 2026 e 2030",
            f"{_pct(m('ipca_2026'), 2)} e {_pct(m('ipca_2030'), 2)}",
            _br(macro.loc["ipca_2030", "data"]),
        ],
        [
            "Prêmio de risco de mercado (Damodaran)",
            _pct(m("premio_mercado_maduro"), 2),
            _br(macro.loc["premio_mercado_maduro", "data"]),
        ],
        [
            "Minério de ferro 62% Fe, média do mês",
            "US$ " + _num(serie.loc[ultimo_mes, "minerio_usd"], 1) + " por tonelada",
            _br(ultimo_mes),
        ],
        [
            "Dólar (PTAX), média do mês",
            "R$ " + _num(serie.loc[ultimo_mes, "dolar"]),
            _br(ultimo_mes),
        ],
    ]

    resultado, cenarios = [], []
    for e in FOCO:
        dados = premissas.carregar(e.ticker)
        rodadas = {c: modelo.rodar(e.ticker, dados, c) for c in premissas.CENARIOS}
        v = rodadas["moderado"]["valuation"]
        resultado.append(
            [
                f"{e.nome} ({e.ticker})",
                "R$ " + _num(v["preco_mercado"]),
                *[_reais(rodadas[c]["valuation"]["preco_justo"]) for c in premissas.CENARIOS],
                _pct(v["wacc"], 2),
                _reais(v["preco_com_obrigacoes"]) if v["obrigacoes_extras"] > 0 else "igual",
            ]
        )
        cen = dados["cenarios"]
        for nome, rotulo in (
            ("crescimento_receita", "Crescimento da receita, ao ano"),
            ("margem_ebitda", f"Margem EBITDA em {dados['anos'][-1]}"),
        ):
            cenarios.append(
                [
                    e.ticker,
                    rotulo,
                    _pct(cen[nome]["partida"]),
                    *[_pct(cen[nome][c]) for c in premissas.CENARIOS],
                ]
            )
        cenarios.append(
            [
                e.ticker,
                "WACC",
                _pct(v["wacc_capm"], 2),
                *[_pct(rodadas[c]["valuation"]["wacc"], 2) for c in premissas.CENARIOS],
            ]
        )
    em_dolar = correlacao[correlacao["minerio"] == "minerio_usd"]
    da_correlacao = [
        [
            f"{POR_TICKER[linha['ticker']].nome} ({linha['ticker']})",
            _num(linha["correlacao"]),
            _num(linha["sensibilidade"]) + "%",
            _pct(linha["r2"], 0),
        ]
        for _, linha in em_dolar.iterrows()
    ]
    nomes = [c.capitalize() for c in premissas.CENARIOS]
    texto = f"""# Análise de {_br(dia.isoformat())}

Registro de como o mercado estava e do que o modelo calculou nesta data. A leitura desses
números está no [README](../README.md#o-que-os-números-dizem).

Isto não é recomendação de investimento. É uma análise feita com os dados que as próprias
empresas divulgam e com simulações que juntam dados reais e dados projetados.

## Preço das ações

Fechamento de {_br(pregao)}, o último pregão disponível quando a análise foi feita. Fonte: B3
(COTAHIST). Valor de mercado em R$ milhões; ações em circulação em milhões, sem tesouraria.

{_tabela(["Empresa", "Preço", "Mínimo em 52 semanas", "Máximo em 52 semanas", "Ações em circulação", "Valor de mercado"], cotacoes)}

Outros papéis usados nas contas, no mesmo fechamento: {demais}.

## Mercado

{_tabela(["Indicador", "Valor", "Data do dado"], do_mercado)}

## Resultado do modelo

Os três cenários saem de regras fixas sobre o histórico de cada empresa e sobre dados de
mercado, descritas no README.

Preço por ação pelo fluxo de caixa descontado (FCFF), em cada cenário. Valor negativo quer
dizer que, naquele cenário, a dívida supera o valor da empresa.

{_tabela(["Empresa", "Mercado", *nomes, "WACC moderado", "Aviso: moderado contando obrigações fora da dívida"], resultado)}

Aviso: a última coluna não é um cenário. Ela mostra quanto o valor moderado cairia se
entrassem como dívida as provisões de Brumadinho e de Mariana da Vale e os adiantamentos que a
CSN recebeu de clientes. O balanço não chama nenhuma das duas de dívida.

## Os três cenários

Partida é o nível de 2026 (últimos doze meses) para crescimento e margem, e o WACC do CAPM.

{_tabela(["Ação", "Variável", "Partida", *nomes], cenarios, direita=2)}

## Ação contra minério de ferro

Variação mensal de {_br(serie.index[0])} a {_br(ultimo_mes)}, contra o minério em dólar.

{_tabela(["Empresa", "Correlação", "Quando o minério anda 1%, a ação anda", "O minério explica"], da_correlacao)}

## Como reproduzir

Este arquivo é gerado por `uv run valuation registrar`. A versão do código e dos dados desta
data está marcada no git com a tag
[`analise-{dia.isoformat()}`]({REPOSITORIO}/tree/analise-{dia.isoformat()}). As fontes de
cada dado estão em [FONTES.md](../FONTES.md).
"""
    ANALISES.mkdir(exist_ok=True)
    destino = ANALISES / f"{dia.isoformat()}.md"
    destino.write_text(texto, encoding="utf-8")
    return destino
