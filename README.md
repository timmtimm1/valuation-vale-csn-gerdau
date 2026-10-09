# Valuation: Vale, CSN e Gerdau

Modelo de valuation de **VALE3**, **CSNA3** e **GGBR4**, as mesmas empresas do meu TCC,
montado só com dados públicos. Sai em dois formatos:

- uma **página interativa** (`site/index.html`), em que dá para escolher o cenário, ajustar
  três variáveis dentro de uma faixa e ver o preço por ação mudar na hora;
- uma **planilha por empresa** (`saida/valuation_<TICKER>.xlsx`), com todas as contas em
  fórmulas do Excel. Troque qualquer célula azul e a planilha inteira recalcula.

> Estudo acadêmico e de portfólio. Não é recomendação de compra ou venda.

## O que o modelo faz

A página e a planilha seguem esta ordem:

| # | Etapa | Na planilha |
|---|---|---|
| 1 | Demonstrativos: DRE, balanço e fluxo de caixa de 2018 ao 2T26 | Histórico |
| 2 | Como os três demonstrativos se ligam, com o balanço fechando | Projeção |
| 3 | EBIT, EBITDA, NOPAT, margens, ROIC, ROE e alavancagem | Histórico |
| 4 | Projeção de receita, custos, margens e crescimento | Projeção |
| 5 | Capital de giro | Projeção |
| 6 | Investimentos (capex) e despesas operacionais (opex) | Projeção |
| 7 | Depreciação e amortização | Projeção |
| 8 | Valuation por múltiplos contra comparáveis | Múltiplos |
| 9 | Valuation por fluxo de caixa descontado (DCF) | DCF |
| 10 | Fluxo de caixa da empresa (FCFF) e do acionista (FCFE) | DCF |
| 11 | CAPM e WACC | WACC |
| 12 | Enterprise Value e Equity Value | DCF |
| 13 | Cenários: entradas e saídas de caixa | Cenários |
| 14 | Análise de sensibilidade | DCF |

Sinergias de M&A e valuation pre/post-money ficaram fora: as três empresas são de capital
aberto e não há transação nem rodada de captação real para modelar.

## De onde vêm os dados

- **CVM**, dados abertos: DFP (anual) e ITR (trimestral) consolidados.
- **B3**, arquivo COTAHIST: preços, valor de mercado e beta (contra o BOVA11).
- **Tesouro Direto**: juro sem risco. **Focus**: inflação esperada.
  **Damodaran (NYU)**: prêmio de risco de mercado.

Cada número de mercado fica em `dados/macro.csv` com data e link.

## Como rodar

```bash
uv sync
uv run valuation extrair     # baixa CVM, B3 e macro; monta dados/
uv run valuation propor      # gera premissas/<ticker>.yaml por regra
uv run valuation gerar       # planilhas em saida/
uv run valuation pagina      # site/index.html
uv run valuation verificar   # LibreOffice recalcula e compara com o Python
uv run pytest
```

## Cenários

Três variáveis mudam com o cenário, e só elas. Cada uma pode ser ajustada à mão, mas só
entre o valor pessimista e o otimista.

| Variável | Pessimista | Moderado | Otimista |
|---|---|---|---|
| Crescimento da receita, ao ano | Zero (queda real) | Inflação esperada no Focus | Crescimento médio de 2018 a 2025, limitado a inflação + 4 pontos |
| Margem EBITDA em 2030 | Segundo pior ano de 2021 a 2025 | Mediana de 2021 a 2025 | Segundo melhor ano de 2021 a 2025 |
| WACC | CAPM mais metade da amplitude do juro longo em dois anos | CAPM | CAPM menos a mesma metade |

2026 parte do nível dos últimos doze meses em qualquer cenário, porque o ano já está quase
todo realizado; a margem vai dali até o valor do cenário em linha reta. A margem histórica é
medida sem perdas por recuperabilidade (impairment), que não saem do caixa nem se repetem.

O resto (capex, depreciação, prazos de giro, imposto, beta) vale igual nos três cenários e
pode ser editado na planilha ou em `premissas/<ticker>.yaml`.

`valuation propor` escreve a proposta por essas regras, com a origem de cada número. Ela é
ponto de partida: o analista edita o arquivo e troca `status: proposta` por
`status: aprovada`. Um arquivo aprovado nunca é sobrescrito.

## Três versões do mesmo modelo, conferidas entre si

A conta existe em Python (`src/valuation/modelo.py`), em fórmulas do Excel
(`planilha.py`) e em JavaScript (`site/modelo.js`). Os testes exigem que as três cheguem
ao mesmo resultado: o LibreOffice recalcula a planilha sem tela e o Node roda o
JavaScript, e ambos são comparados com o Python linha a linha.

## Simplificações que vale conhecer

- A margem EBITDA é premissa: o modelo não projeta preço, volume e custo unitário
  separados, porque a CVM não publica dados operacionais. O custo dos produtos é o que
  sobra depois de fixada a margem.
- O cenário desloca o WACC e o Ke no mesmo tanto, sem refazer o CAPM.
- Toda a depreciação é tratada como custo de produção.
- Juros calculados sobre os saldos do início do ano, para não haver referência circular.
- Provisões (barragens, contingências) não entram como dívida, a menos que o analista
  preencha "outros passivos tratados como dívida".
- Beta com preços não ajustados por proventos.
- Fusões e aquisições e valuation pre/post-money ficaram fora do escopo.
