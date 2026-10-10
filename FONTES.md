# Fontes dos dados

Todos os dados do estudo são públicos e gratuitos. Esta lista é gerada pelo comando
`valuation registrar` a partir dos próprios arquivos, então as datas são as do dado mais
recente que está no repositório.

Empresas: Vale (VALE3), CSN (CSNA3), Gerdau (GGBR4), Usiminas (USIM5), CSN Mineração (CMIN3).

| Dado | Fonte | Onde está no repositório | Data do dado |
| --- | --- | --- | --- |
| Demonstrações financeiras: DRE, balanço, fluxo de caixa e valor adicionado, consolidados | CVM, Portal de Dados Abertos: [DFP](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp) (anual) e [ITR](https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr) (trimestral) | `dados/contas_cvm.csv` (como a empresa entregou) e `dados/historico.csv` (padronizado) | DFP de 2018 a 2025; ITR até 30/06/2026 |
| Quantidade de ações emitidas e em tesouraria | CVM, quadro de composição do capital, nos mesmos arquivos de DFP e ITR | `dados/acoes.csv` | 30/06/2026 |
| Cotações diárias de fechamento | B3, [Séries Históricas (COTAHIST)](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/series-historicas/) | `dados/precos.csv`; preço, faixa de 52 semanas, valor de mercado e beta em `dados/mercado.csv` | 04/01/2021 a 08/10/2026 |
| Bonificação da Gerdau (uma ação nova para cada cinco), usada para corrigir o preço | B3, eventos corporativos; conferida no COTAHIST (queda de 17% no dia) e no número de ações da CVM | `src/valuation/empresas.py` | 18/04/2024 |
| Bonificação da Gerdau (uma ação nova para cada vinte), usada para corrigir o preço | Gerdau, [aviso aos acionistas de 28/02/2023](https://www.latibex.com/docs/Documentos/LED/2023/03/02/BRACN_20230301_125502_B01_GGBR3_001_20230322_001_DOC001.pdf); conferida no COTAHIST (queda de 4% no dia) e no número de ações da CVM | `src/valuation/empresas.py` | 22/03/2023 |
| Obrigações fora da dívida, mostradas como aviso: provisões de Brumadinho e de Mariana (Vale) e adiantamentos de clientes (CSN) | CVM, balanço consolidado do ITR, contas do passivo listadas abaixo | `dados/contas_cvm.csv` e a coluna `obrigacoes_extras` de `dados/historico.csv` | 30/06/2026 |
| Juro prefixado e juro real de dez anos; mínimo e máximo do prefixado em dois anos | [Tesouro Direto, preços e taxas](https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto) (Tesouro Transparente) | `dados/macro.csv` | 08/10/2026 |
| Inflação esperada (IPCA) de 2026 a 2030 | Banco Central, [Boletim Focus](https://www.bcb.gov.br/publicacoes/focus), pela API de expectativas de mercado | `dados/macro.csv` | 02/10/2026 |
| Prêmio de risco de mercado | Aswath Damodaran (NYU), [Country Default Spreads and Risk Premiums](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html) | `dados/macro.csv` | 16/02/2026 |
| Minério de ferro 62% Fe, CFR China, média mensal | Banco Mundial, [Commodity Price Data (Pink Sheet)](https://www.worldbank.org/en/research/commodity-markets) | `dados/commodity_e_acoes.csv` | 01/2021 a 09/2026 |
| Dólar (PTAX de venda), média mensal | Banco Central, [Sistema Gerenciador de Séries Temporais](https://www3.bcb.gov.br/sgspub/), série 3698 | `dados/commodity_e_acoes.csv` | 01/2021 a 09/2026 |

## O documento de cada empresa na CVM

Os balanços deste estudo são os que cada empresa entregou à CVM. Os links abaixo abrem o
documento original no site da CVM, com a demonstração do resultado, o balanço e o fluxo de
caixa. Os endereços vêm do índice que a própria CVM publica junto com os dados.

**Vale (VALE3)**

- [Balanço trimestral (ITR) de 30/06/2026, como a Vale entregou à CVM em 31/07/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=159978&CodigoTipoInstituicao=1)
- [Balanço anual (DFP) de 31/12/2025, como a Vale entregou à CVM em 12/03/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=155313&CodigoTipoInstituicao=1)
- [Todos os documentos da Vale na CVM](https://www.rad.cvm.gov.br/ENET/frmConsultaExternaCVM.aspx?codigoCVM=4170)
- [Relações com investidores da Vale](https://www.vale.com/pt/investidores)

**CSN (CSNA3)**

- [Balanço trimestral (ITR) de 30/06/2026, como a CSN entregou à CVM em 12/08/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=160568&CodigoTipoInstituicao=1)
- [Balanço anual (DFP) de 31/12/2025, como a CSN entregou à CVM em 11/03/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=155288&CodigoTipoInstituicao=1)
- [Todos os documentos da CSN na CVM](https://www.rad.cvm.gov.br/ENET/frmConsultaExternaCVM.aspx?codigoCVM=4030)
- [Relações com investidores da CSN](https://ri.csn.com.br)

**Gerdau (GGBR4)**

- [Balanço trimestral (ITR) de 30/06/2026, como a Gerdau entregou à CVM em 04/08/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=160130&CodigoTipoInstituicao=1)
- [Balanço anual (DFP) de 31/12/2025, como a Gerdau entregou à CVM em 23/02/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=154830&CodigoTipoInstituicao=1)
- [Todos os documentos da Gerdau na CVM](https://www.rad.cvm.gov.br/ENET/frmConsultaExternaCVM.aspx?codigoCVM=3980)
- [Relações com investidores da Gerdau](https://ri.gerdau.com)

**Usiminas (USIM5)**

- [Balanço trimestral (ITR) de 30/06/2026, como a Usiminas entregou à CVM em 30/07/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=159792&CodigoTipoInstituicao=1)
- [Balanço anual (DFP) de 31/12/2025, como a Usiminas entregou à CVM em 13/02/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=154757&CodigoTipoInstituicao=1)
- [Todos os documentos da Usiminas na CVM](https://www.rad.cvm.gov.br/ENET/frmConsultaExternaCVM.aspx?codigoCVM=14320)
- [Relações com investidores da Usiminas](https://ri.usiminas.com)

**CSN Mineração (CMIN3)**

- [Balanço trimestral (ITR) de 30/06/2026, como a CSN Mineração entregou à CVM em 12/08/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=160566&CodigoTipoInstituicao=1)
- [Balanço anual (DFP) de 31/12/2025, como a CSN Mineração entregou à CVM em 12/03/2026](https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx?NumeroSequencialDocumento=155318&CodigoTipoInstituicao=1)
- [Todos os documentos da CSN Mineração na CVM](https://www.rad.cvm.gov.br/ENET/frmConsultaExternaCVM.aspx?codigoCVM=25585)
- [Relações com investidores da CSN Mineração](https://ri.csnmineracao.com.br)

## Onde achar cada número dentro do documento

A CVM usa o mesmo plano de contas para todas as empresas. Com o código da conta dá para
achar no documento o mesmo número que está em `dados/contas_cvm.csv`. Use sempre as
demonstrações consolidadas; os valores do documento estão em milhares de reais e os do
estudo em milhões.

| Número | Em qual demonstração | Código da conta na CVM |
| --- | --- | --- |
| Receita líquida | Demonstração do Resultado | 3.01 |
| Lucro bruto | Demonstração do Resultado | 3.03 |
| Perdas por recuperabilidade (impairment) | Demonstração do Resultado | 3.04.03 |
| EBIT (resultado antes do financeiro e dos tributos) | Demonstração do Resultado | 3.05 |
| Lucro líquido consolidado | Demonstração do Resultado | 3.11 |
| Depreciação, amortização e exaustão | Demonstração do Valor Adicionado | 7.04.01 |
| Caixa e aplicações financeiras | Balanço, Ativo | 1.01.01 e 1.01.02 |
| Dívida (empréstimos e financiamentos) | Balanço, Passivo | 2.01.04 e 2.02.01 |
| Patrimônio líquido | Balanço, Passivo | 2.03 |
| Caixa das operações | Demonstração do Fluxo de Caixa | 6.01 |
| Investimento (capex) | Demonstração do Fluxo de Caixa | linhas de 6.02 |
| Dividendos pagos | Demonstração do Fluxo de Caixa | linhas de 6.03 |
| Vale: provisões de Brumadinho e de Mariana (aviso) | Balanço, Passivo | 2.01.06.02 e 2.02.04.02 |
| CSN: adiantamentos de clientes, 'passivos de contratos' (aviso) | Balanço, Passivo | 2.01.05.02 e 2.02.02.02 |
| Usiminas: perda por recuperabilidade de 2025 | Demonstração do Fluxo de Caixa | ajustes do lucro, em 6.01.01 |

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
