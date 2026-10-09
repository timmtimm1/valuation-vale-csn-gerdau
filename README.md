# Valuation: Vale, CSN e Gerdau

Modelo de valuation de **VALE3**, **CSNA3** e **GGBR4**, as mesmas empresas do meu TCC,
montado só com dados públicos. Sai em dois formatos:

- uma **página interativa** (`site/index.html`), em que dá para mexer nas premissas e ver o
  preço por ação mudar na hora;
- uma **planilha por empresa** (`saida/valuation_<TICKER>.xlsx`), com todas as contas em
  fórmulas do Excel. Troque qualquer célula azul e a planilha inteira recalcula.

> Estudo acadêmico e de portfólio. Não é recomendação de compra ou venda.

## O que o modelo faz

| Etapa | Onde está |
|---|---|
| DRE, balanço e fluxo de caixa de 2018 ao 2T26 | `historico.py`, aba Histórico |
| EBIT, EBITDA, NOPAT, margens, giro, alavancagem, ROIC, ROE | `historico.py`, aba Histórico |
| Projeção de receita, custos, margens, capex, depreciação e capital de giro | `modelo.py`, aba Projeção |
| As três demonstrações ligadas, com o balanço fechando | `modelo.py`, aba Projeção |
| CAPM e WACC | `modelo.py`, aba WACC |
| DCF por FCFF e por FCFE, valor da empresa e valor do acionista | `modelo.py`, aba DCF |
| Sensibilidade do preço a WACC e crescimento perpétuo | aba DCF |
| Valuation por múltiplos contra comparáveis | `multiplos.py`, aba Múltiplos |
| Cenários e entradas e saídas de caixa | aba Cenários |

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

## Premissas

`valuation propor` escreve uma proposta neutra em `premissas/<ticker>.yaml`: 2026 parte dos
últimos doze meses e, dali em diante, preço e custo andam com a inflação do Focus. Cada
número traz a regra que o gerou. A proposta é ponto de partida: o analista edita o arquivo
e troca `status: proposta` por `status: aprovada`. Um arquivo aprovado nunca é sobrescrito.

## Três versões do mesmo modelo, conferidas entre si

A conta existe em Python (`src/valuation/modelo.py`), em fórmulas do Excel
(`planilha.py`) e em JavaScript (`site/modelo.js`). Os testes exigem que as três cheguem
ao mesmo resultado: o LibreOffice recalcula a planilha sem tela e o Node roda o
JavaScript, e ambos são comparados com o Python linha a linha.

## Simplificações que vale conhecer

- Sem toneladas nem preço por tonelada: a CVM não publica dados operacionais. Volume e
  preço entram como variações percentuais.
- Toda a depreciação é tratada como custo de produção.
- Juros calculados sobre os saldos do início do ano, para não haver referência circular.
- Provisões (barragens, contingências) não entram como dívida, a menos que o analista
  preencha "outros passivos tratados como dívida".
- Beta com preços não ajustados por proventos.
- Fusões e aquisições e valuation pre/post-money ficaram fora do escopo.
