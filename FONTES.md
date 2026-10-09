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
| Juro prefixado e juro real de dez anos; mínimo e máximo do prefixado em dois anos | [Tesouro Direto, preços e taxas](https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto) (Tesouro Transparente) | `dados/macro.csv` | 08/10/2026 |
| Inflação esperada (IPCA) de 2026 a 2030 | Banco Central, [Boletim Focus](https://www.bcb.gov.br/publicacoes/focus), pela API de expectativas de mercado | `dados/macro.csv` | 02/10/2026 |
| Prêmio de risco de mercado | Aswath Damodaran (NYU), [Country Default Spreads and Risk Premiums](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html) | `dados/macro.csv` | 16/02/2026 |
| Minério de ferro 62% Fe, CFR China, média mensal | Banco Mundial, [Commodity Price Data (Pink Sheet)](https://www.worldbank.org/en/research/commodity-markets) | `dados/commodity_e_acoes.csv` | 01/2021 a 09/2026 |
| Dólar (PTAX de venda), média mensal | Banco Central, [Sistema Gerenciador de Séries Temporais](https://www3.bcb.gov.br/sgspub/), série 3698 | `dados/commodity_e_acoes.csv` | 01/2021 a 09/2026 |

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
