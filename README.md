# Valuation: Vale, CSN e Gerdau

Quanto valem a Vale, a CSN e a Gerdau? Montei este modelo para responder a essa pergunta com
as três empresas que estudei no meu TCC, usando só dados públicos: os balanços que elas
entregam à CVM, as cotações da B3 e os juros do Tesouro.

O resultado está em dois formatos:

- Na **[página interativa](https://timmtimm1.github.io/valuation-vale-csn-gerdau/)** dá para
  trocar de cenário, mexer em três variáveis e ver o preço por ação mudar.
- Na **[planilha](https://github.com/timmtimm1/valuation-vale-csn-gerdau/raw/main/saida/valuation_vale_csn_gerdau.xlsx)**
  estão as mesmas contas em fórmulas, com uma frase ao lado de cada linha explicando o que ela
  é e como foi calculada. Na primeira aba escolhem-se a empresa e o cenário, e o arquivo
  inteiro recalcula. Abre no Excel e no LibreOffice.

Para conferir os números, veja [a fonte de cada dado](FONTES.md) e
[os preços no dia da análise](analises/2026-10-09.md).

> Isto não é recomendação de investimento. É uma análise feita com os dados que as próprias
> empresas divulgam e com simulações que juntam dados reais e dados projetados.

## O que os números dizem

<!-- resumo:inicio -->
Análise de 9 de outubro de 2026. Os preços são do fechamento do dia 8 e os balanços vão até
junho de 2026. Os valores dos cenários são por ação.

| | Vale (VALE3) | CSN (CSNA3) | Gerdau (GGBR4) |
| --- | ---: | ---: | ---: |
| Preço na bolsa | R$ 67,64 | R$ 6,36 | R$ 24,77 |
| Valor no cenário pessimista | R$ 51,05 | −R$ 8,04 | R$ 11,49 |
| Valor no cenário moderado | R$ 84,07 | R$ 4,42 | R$ 21,38 |
| Valor no cenário otimista | R$ 138,61 | R$ 41,79 | R$ 40,84 |
| Moderado contra o preço | +24% | −31% | −14% |
| Margem EBITDA em 12 meses, sem baixas contábeis | 34,6% | 17,1% | 15,4% |
| Dívida líquida ÷ EBITDA | 1,3 | 5,1 | 0,9 |
| Lucro líquido em 12 meses | R$ 8,7 bi | −R$ 2,0 bi | R$ 2,3 bi |
| Caixa que sobra depois de investir, em 12 meses | R$ 18,8 bi | −R$ 6,2 bi | R$ 3,7 bi |

Das três, a Vale é a que se destaca. É a única em que o valor do cenário moderado fica acima
do preço da bolsa, tem cerca do dobro da margem das outras duas e é a que menos perde no
cenário pessimista. A Gerdau tem a menor dívida, mas a ação já custa mais do que o modelo
calcula no cenário moderado. Na CSN, a dívida líquida é quase do tamanho do valor da operação
inteira, e por isso o valor da ação vai de negativo a R$ 41,79 conforme o cenário.
<!-- resumo:fim -->

<!-- analise:inicio -->
### Como cheguei a esses valores

O valor por ação vem de um fluxo de caixa descontado. Projetei o caixa livre de cada empresa
(FCFF) de 2026 a 2030, trouxe esses fluxos a valor de hoje pelo custo de capital (WACC), somei
o valor dos anos seguintes e tirei a dívida. O que sobra é dividido pelo número de ações.

Só três variáveis mudam de um cenário para outro: o crescimento da receita, a margem EBITDA de
2030 e o WACC. Cada uma sai de uma regra fixa, igual para as três empresas. No moderado, por
exemplo, a receita cresce pela inflação esperada e a margem de 2030 é a mediana de 2021 a 2025.
Usei a mesma taxa de juros para as três, a do Tesouro prefixado de dez anos (12,91% ao ano),
para comparar todas na mesma base.

### Vale

Nos doze meses até junho de 2026 a Vale vendeu R$ 218 bilhões e ficou com 34,6% disso como
EBITDA, sem contar as baixas contábeis. É cerca do dobro da margem da CSN e da Gerdau, mas bem
abaixo dos 54,5% que a própria Vale teve em 2021.

O lucro caiu mais do que a margem. Em 2025 a empresa registrou R$ 25,1 bilhões em perdas por
recuperabilidade (impairment), uma baixa que reduz o lucro sem tirar dinheiro do caixa. O lucro
do ano foi de R$ 11,8 bilhões, contra R$ 30,4 bilhões em 2024.

A operação gerou R$ 50,6 bilhões de caixa em doze meses e os investimentos levaram R$ 31,8
bilhões. Sobraram R$ 18,8 bilhões, menos do que os R$ 23,1 bilhões pagos em dividendos no
período. A dívida líquida, que era de R$ 10,5 bilhões no fim de 2021, chegou a R$ 68,2 bilhões
em junho de 2026. Isso equivale a 1,3 vez o EBITDA de um ano.

No cenário moderado a receita cresce 3,8% ao ano, a margem volta a 39,4% até 2030 e o WACC é
de 14,12%. O resultado é R$ 84,07 por ação, 24% acima do preço. Pelo fluxo de caixa do
acionista (FCFE) a conta dá R$ 71,97, também acima. A tabela de sensibilidade refaz o cálculo
para 25 combinações de WACC e de crescimento na perpetuidade, e o valor fica acima do preço em
22 delas. Fica abaixo só quando o WACC sobe dois pontos e o crescimento na perpetuidade não
passa de 3,5%.

Pelos múltiplos o resultado é o oposto. Quando aplico à Vale a mediana do que o mercado paga
pelas outras quatro empresas do grupo de comparação (CSN, Gerdau, Usiminas e CSN Mineração), o
preço implícito fica entre R$ 37,52 e R$ 63,54, sempre abaixo da bolsa. Uma parte disso vem da
baixa contábil: com ela a Vale negocia a 6,7 vezes o EBITDA, e sem ela a 4,6 vezes. O grupo
também é pequeno, e duas das quatro empresas estão no prejuízo.

### CSN

Na CSN a dívida decide o resultado. A dívida líquida é de R$ 39,1 bilhões: 5,1 vezes o EBITDA
de um ano e 4,6 vezes o valor de mercado da empresa, que é de R$ 8,4 bilhões.

A margem EBITDA caiu de 47,5% em 2021 para 17,1%. A empresa dá prejuízo desde 2024: R$ 1,5
bilhão em 2024, R$ 1,5 bilhão em 2025 e R$ 2,0 bilhões nos últimos doze meses. Nesses doze
meses a operação consumiu R$ 0,2 bilhão de caixa em vez de gerar, e os investimentos foram de
R$ 6,0 bilhões.

No cenário moderado a operação inteira vale R$ 39,2 bilhões, quase o mesmo que a dívida
líquida. O que sobra para o acionista vem das participações em outras empresas, e o valor por
ação fica em R$ 4,42, 31% abaixo do preço. No pessimista a dívida supera o valor da operação e
a conta dá −R$ 8,04. No otimista dá R$ 41,79.

Com tanta dívida, uma mudança pequena no valor da empresa vira uma mudança grande no valor da
ação. Com um ponto a mais no WACC, o valor do cenário moderado cai para R$ 0,07.

Pelo fluxo de caixa do acionista o resultado é pior. Os juros projetados, de R$ 6,8 bilhões por
ano, são maiores do que o lucro operacional em todos os anos até 2030, e o valor por ação fica
negativo (−R$ 7,68).

O método ainda favorece a CSN em um ponto. Ela tem o menor WACC das três (9,98%) porque 86% do
capital é dívida, e a dívida entra na conta a 8,5% ao ano depois do imposto, a mesma taxa das
outras duas. É um efeito da fórmula. O risco da ação medido pelo beta é o maior das três: 1,48,
contra 0,76 da Vale e 0,79 da Gerdau.

### Gerdau

A Gerdau tem o balanço mais leve. A dívida líquida é de R$ 8,1 bilhões, 0,9 vez o EBITDA, e
sobra caixa depois dos investimentos todos os anos desde 2020.

O problema está na margem. O EBITDA sem baixas contábeis caiu de 30% da receita em 2021 para
13,4% em 2025, e está em 15,4% nos últimos doze meses. O lucro de 2025 foi de R$ 1,4 bilhão,
depois de uma baixa de R$ 2,0 bilhões.

O cenário moderado supõe que a margem volte a 19,7% até 2030 e chega a R$ 21,38 por ação, 14%
abaixo dos R$ 24,77 da bolsa. A ação está perto da máxima de 52 semanas (R$ 26,31). O preço de
hoje só aparece no modelo com premissas entre o cenário moderado e o otimista.

Os múltiplos ficam mais perto da bolsa: os preços implícitos vão de R$ 16,70 a R$ 28,56, e o
preço de mercado está dentro dessa faixa.

A Gerdau é também a menos ligada ao minério de ferro. Ele explica 14% da variação mensal da
ação, contra 30% na CSN e 48% na Vale.

### Por que a Vale se destaca

Destacar-se, aqui, quer dizer sair melhor nas contas deste modelo, com estas premissas. A Vale
sai melhor por três motivos:

- É a única em que o cenário moderado fica acima do preço, tanto pelo fluxo de caixa da empresa
  (R$ 84,07) quanto pelo do acionista (R$ 71,97).
- É a que menos perde quando as premissas pioram. No cenário pessimista o valor fica 25% abaixo
  do preço. Na Gerdau fica 54% abaixo e na CSN fica negativo.
- Tem a maior margem das três e continua com lucro e com sobra de caixa depois de investir
  R$ 31,8 bilhões em um ano.

### O que pode mudar essa conclusão

- Os múltiplos não confirmam o fluxo de caixa. Por eles a Vale não está barata.
- O resultado depende de a margem voltar de 34,6% para 39,4%. Se a margem ficar onde está, a
  receita parar de crescer e o WACC subir 1,56 ponto, o valor cai para R$ 51,05.
- A Vale é a mais exposta ao minério de ferro, que explica 48% da variação mensal da ação. O
  modelo não projeta o preço do minério. Ele entra só pela margem.
- Provisões, como as de barragens, não entram como dívida nas contas.
- Nas três empresas, mais de 70% do valor calculado vem do período depois de 2030, que é o mais
  incerto.

Isto não é recomendação de investimento. É uma análise feita com os dados que as próprias
empresas divulgam e com simulações que juntam dados reais e dados projetados. O resultado muda
quando as premissas mudam, e a página e a planilha estão abertas para quem quiser testar as
suas.
<!-- analise:fim -->

## Como o modelo foi montado

A página e a planilha seguem a mesma ordem, em 14 etapas:

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

Deixei de fora sinergias de fusões e aquisições e valuation pre e post-money. As três empresas
são de capital aberto e não há transação nem rodada de captação para modelar.

## A planilha

O valuation começa pelo caixa livre da empresa (FCFF). Cada linha de conta tem ao lado uma
frase dizendo o que é e como foi calculada.

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

## As regras dos cenários

Só três variáveis mudam de um cenário para outro. Cada uma pode ser ajustada à mão, desde que
fique entre o valor pessimista e o otimista.

| Variável | Pessimista | Moderado | Otimista |
|---|---|---|---|
| Crescimento da receita, ao ano | Zero (queda real) | Inflação esperada no Focus | Crescimento médio de 2018 a 2025, limitado a inflação + 4 pontos |
| Margem EBITDA em 2030 | Segundo pior ano de 2021 a 2025 | Mediana de 2021 a 2025 | Segundo melhor ano de 2021 a 2025 |
| WACC | CAPM mais metade da amplitude do juro longo em dois anos | CAPM | CAPM menos a mesma metade |

Em qualquer cenário, 2026 parte do nível dos últimos doze meses, porque o ano já está quase
todo realizado. Dali a margem vai em linha reta até o valor do cenário em 2030. A margem
histórica é medida sem perdas por recuperabilidade (impairment), que não saem do caixa nem se
repetem.

O resto (capex, depreciação, prazos de giro, imposto, beta) é igual nos três cenários e pode
ser editado na planilha ou em `premissas/<ticker>.yaml`.

O comando `valuation propor` escreve as premissas por essas regras, com a origem de cada
número. Quem revisa o arquivo troca `status: proposta` por `status: aprovada`, e um arquivo
aprovado não é mais sobrescrito.

## De onde vêm os dados

- **CVM**, dados abertos: DFP (anual) e ITR (trimestral) consolidados.
- **B3**, arquivo COTAHIST: preços, valor de mercado e beta (contra o BOVA11).
- **Banco Mundial**: preço mensal do minério de ferro. **Banco Central**: dólar mensal.
- **Tesouro Direto**: juro sem risco. **Focus**: inflação esperada.
  **Damodaran (NYU)**: prêmio de risco de mercado.

Cada número de mercado fica em `dados/macro.csv` com data e link. A lista completa, com o link
de cada fonte e a data do dado mais recente, está em [FONTES.md](FONTES.md).

## Quando a análise foi feita

A pasta [`analises/`](analises/) guarda uma fotografia de cada data: o preço das ações no
último pregão, os juros, a inflação esperada, o minério e o resultado do modelo com as
premissas daquele dia. A primeira é a de [09/10/2026](analises/2026-10-09.md), com o
fechamento de 08/10/2026. Cada fotografia tem uma tag no git (`analise-2026-10-09`), para
quem quiser ver o código e os dados como estavam.

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

A análise escrita acima é de uma data. Se os dados forem baixados de novo, os números da
página e da planilha mudam e o texto precisa ser revisto.

## A mesma conta feita três vezes

O modelo existe em Python (`src/valuation/modelo.py`), em fórmulas de planilha (`planilha.py`)
e em JavaScript (`site/modelo.js`). Os testes exigem que os três cheguem ao mesmo resultado. O
LibreOffice recalcula a planilha sem tela, trocando a empresa, o cenário e os ajustes manuais,
e o Node roda o JavaScript. Os dois são comparados com o Python linha a linha.

## Limites do modelo

- A margem EBITDA é premissa. O modelo não projeta preço, volume e custo unitário separados,
  porque a CVM não publica dados operacionais. O custo dos produtos é o que sobra depois de
  fixada a margem.
- O cenário desloca o WACC e o Ke no mesmo tanto, sem refazer o CAPM.
- Toda a depreciação é tratada como custo de produção.
- Os juros são calculados sobre os saldos do início do ano, para não haver referência circular.
- Provisões (barragens, contingências) não entram como dívida, a menos que se preencha
  "outros passivos tratados como dívida".
- Os preços são ajustados pela bonificação da Gerdau de 2024, mas não por dividendos. Isso
  afeta o beta e a correlação.
- Fusões e aquisições e valuation pre e post-money ficaram fora do escopo.
