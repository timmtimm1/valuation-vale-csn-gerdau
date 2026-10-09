# Valuation: Vale, CSN e Gerdau

Modelo de valuation de **VALE3**, **CSNA3** e **GGBR4**, as mesmas empresas do meu TCC,
montado só com dados públicos. Sai em dois formatos:

- uma **página interativa** (`site/index.html`), em que dá para escolher o cenário, ajustar
  três variáveis dentro de uma faixa e ver o preço por ação mudar na hora;
- uma **planilha** (`saida/valuation_vale_csn_gerdau.xlsx`) com as três empresas e todas as
  contas em fórmulas. Na primeira aba escolhe-se a empresa e o cenário em duas listas e o
  arquivo inteiro recalcula. Abre no Excel e no LibreOffice.

**[Abrir a página interativa](https://timmtimm1.github.io/valuation-vale-csn-gerdau/)** ·
**[Baixar a planilha](https://github.com/timmtimm1/valuation-vale-csn-gerdau/raw/main/saida/valuation_vale_csn_gerdau.xlsx)** ·
[fonte de cada dado](FONTES.md) · [preços no dia da análise](analises/2026-10-09.md)

> Estudo acadêmico e de portfólio. Não é recomendação de compra ou venda.

## O que o modelo faz

A página e a planilha seguem esta ordem:

| # | Etapa | Na planilha |
|---|---|---|
| 1 | Demonstrativos: DRE, balanço e fluxo de caixa de 2018 ao 2T26 | Demonstrativos |
| 2 | Como os três demonstrativos se ligam, com o balanço fechando | Projeção |
| 3 | EBIT, EBITDA, NOPAT, margens, ROIC, ROE e alavancagem | Demonstrativos |
| 4 | Projeção de receita, custos, margens e crescimento | Projeção |
| 5 | Capital de giro | Projeção |
| 6 | Investimentos (capex) e despesas operacionais (opex) | Projeção |
| 7 | Depreciação e amortização | Projeção |
| 8 | Valuation por múltiplos contra comparáveis | Múltiplos |
| 9 | Valuation por fluxo de caixa descontado (DCF) | Valor justo |
| 10 | Fluxo de caixa da empresa (FCFF) e do acionista (FCFE) | FCFF |
| 11 | CAPM e WACC | WACC |
| 12 | Enterprise Value e Equity Value | Valor justo |
| 13 | Cenários: entradas e saídas de caixa | Cenários |
| 14 | Análise de sensibilidade | Valor justo |

Sinergias de M&A e valuation pre/post-money ficaram fora: as três empresas são de capital
aberto e não há transação nem rodada de captação real para modelar.

## A planilha

Segue o valuation pelo fluxo de caixa da empresa, começando pelo FCFF. Cada linha de conta
tem ao lado uma frase dizendo o que é e como foi calculada.

| Aba | O que tem |
|---|---|
| Painel | Escolha da empresa e do cenário, ajuste manual das três variáveis e o resultado |
| Passo a passo | O preço justo em sete passos, com os números da empresa escolhida |
| Demonstrativos | DRE, fluxo de caixa, balanço e indicadores de 2018 ao 2T26 |
| Projeção | Receita, custos, margens, capex, depreciação, giro e balanço até 2030 |
| FCFF | Caixa livre da empresa e do acionista, ano a ano |
| WACC | CAPM, custo da dívida e a taxa em uso |
| Valor justo | Desconto dos fluxos, perpetuidade, EV, valor do acionista, preço e sensibilidade |
| Múltiplos | EV/EBITDA, P/L e P/VP contra as comparáveis |
| Cenários | Entradas e saídas de caixa e os três cenários lado a lado |
| Correlação | Variação mensal de cada ação contra a do minério de ferro |
| Glossário | O que é cada indicador e como se calcula |
| Premissas | Um bloco editável por empresa (células azuis) |
| Dados | O histórico da CVM das três empresas |

A correlação usa a variação de um mês para o outro, de 2021 a 2026: o minério explica 48%
da oscilação da Vale, 30% da CSN e 14% da Gerdau.

## De onde vêm os dados

- **CVM**, dados abertos: DFP (anual) e ITR (trimestral) consolidados.
- **B3**, arquivo COTAHIST: preços, valor de mercado e beta (contra o BOVA11).
- **Banco Mundial**: preço mensal do minério de ferro. **Banco Central**: dólar mensal.
- **Tesouro Direto**: juro sem risco. **Focus**: inflação esperada.
  **Damodaran (NYU)**: prêmio de risco de mercado.

Cada número de mercado fica em `dados/macro.csv` com data e link. A lista completa, com o
link de cada fonte e a data do dado mais recente, está em [FONTES.md](FONTES.md).

## Quando a análise foi feita

A pasta [`analises/`](analises/) guarda uma fotografia de cada data: o preço das ações no
último pregão, os juros, a inflação esperada, o minério e o resultado do modelo com as
premissas daquele dia. A primeira é a de [09/10/2026](analises/2026-10-09.md), com o
fechamento de 08/10/2026. Cada fotografia tem uma tag no git (`analise-2026-10-09`), para
quem quiser ver o código e os dados exatamente como estavam.

## Como rodar

```bash
git clone https://github.com/timmtimm1/valuation-vale-csn-gerdau.git
cd valuation-vale-csn-gerdau
uv sync
uv run valuation extrair     # baixa CVM, B3 e macro; monta dados/
uv run valuation propor      # gera premissas/<ticker>.yaml por regra
uv run valuation gerar       # a planilha em saida/, já calculada pelo LibreOffice
uv run valuation pagina      # site/index.html
uv run valuation verificar   # LibreOffice recalcula e compara com o Python
uv run valuation registrar   # FONTES.md e a fotografia do dia em analises/
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

A conta existe em Python (`src/valuation/modelo.py`), em fórmulas de planilha
(`planilha.py`) e em JavaScript (`site/modelo.js`). Os testes exigem que as três cheguem
ao mesmo resultado: o LibreOffice recalcula a planilha sem tela, trocando a empresa, o
cenário e os ajustes manuais, e o Node roda o JavaScript; ambos são comparados com o
Python linha a linha.

## Simplificações que vale conhecer

- A margem EBITDA é premissa: o modelo não projeta preço, volume e custo unitário
  separados, porque a CVM não publica dados operacionais. O custo dos produtos é o que
  sobra depois de fixada a margem.
- O cenário desloca o WACC e o Ke no mesmo tanto, sem refazer o CAPM.
- Toda a depreciação é tratada como custo de produção.
- Juros calculados sobre os saldos do início do ano, para não haver referência circular.
- Provisões (barragens, contingências) não entram como dívida, a menos que o analista
  preencha "outros passivos tratados como dívida".
- Preços ajustados pela bonificação da Gerdau de 2024, mas não por dividendos (beta e
  correlação).
- Fusões e aquisições e valuation pre/post-money ficaram fora do escopo.
