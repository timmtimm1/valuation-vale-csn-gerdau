# Valuation: Vale, CSN, Gerdau e Usiminas

Quanto valem a Vale, a CSN, a Gerdau e a Usiminas? Montei este modelo para responder a essa
pergunta com as três empresas que estudei no meu TCC e com a Usiminas, que entrou depois para
completar as siderúrgicas. Usei só dados públicos: os balanços que elas entregam à CVM, as
cotações da B3 e os juros do Tesouro.

O resultado está em dois formatos:

- Na **[página interativa](https://timmtimm1.github.io/valuation-vale-csn-gerdau/)** dá para
  trocar de cenário, mexer em três variáveis e ver o preço por ação mudar.
- Na **[planilha](https://github.com/timmtimm1/valuation-vale-csn-gerdau/raw/main/saida/valuation_vale_csn_gerdau.xlsx)**
  estão as mesmas contas em fórmulas, com uma frase ao lado de cada linha explicando o que ela
  é e como foi calculada. Na primeira aba escolhem-se a empresa e o cenário, e o arquivo
  inteiro recalcula. Abre no Excel e no LibreOffice.

Para conferir os números, veja [a fonte de cada dado](FONTES.md) e
[os preços no dia da análise](analises/2026-10-10.md).

> Isto não é recomendação de investimento. É uma análise feita com os dados que as próprias
> empresas divulgam e com simulações que juntam dados reais e dados projetados.

## O que os números dizem

<!-- resumo:inicio -->
Análise de 9 de outubro de 2026, revista no dia 10 com a inclusão da Usiminas. Os preços são
do fechamento do dia 8 e os balanços vão até junho de 2026. Os valores dos cenários são por
ação.

| | Vale (VALE3) | CSN (CSNA3) | Gerdau (GGBR4) | Usiminas (USIM5) |
| --- | ---: | ---: | ---: | ---: |
| Preço na bolsa | R$ 67,64 | R$ 6,36 | R$ 24,77 | R$ 7,21 |
| Valor no cenário pessimista | R$ 51,05 | −R$ 8,04 | R$ 11,23 | R$ 1,33 |
| Valor no cenário moderado | R$ 84,07 | R$ 4,42 | R$ 21,12 | R$ 2,19 |
| Valor no cenário otimista | R$ 138,61 | R$ 41,79 | R$ 40,63 | R$ 13,87 |
| Moderado contra o preço | +24% | −31% | −15% | −70% |
| Aviso: moderado contando obrigações fora da dívida | R$ 79,15 | −R$ 5,46 | igual | igual |
| Margem EBITDA em 12 meses, sem baixas contábeis | 34,6% | 17,1% | 15,4% | 9,6% |
| Dívida líquida ÷ EBITDA, sem baixas contábeis | 0,9 | 5,1 | 0,8 | caixa líquido |
| Lucro líquido em 12 meses | R$ 8,7 bi | −R$ 2,0 bi | R$ 2,3 bi | −R$ 2,1 bi |
| Caixa que sobra depois de investir, em 12 meses | R$ 18,8 bi | −R$ 6,2 bi | R$ 3,5 bi | R$ 1,5 bi |

Das quatro, a Vale é a que se destaca. É a única em que o valor do cenário moderado fica acima
do preço da bolsa, tem mais que o dobro da margem das outras e é a que menos perde no cenário
pessimista. A Gerdau e a Usiminas têm os balanços mais leves, mas as duas custam na bolsa mais
do que o modelo calcula no cenário moderado, e na Usiminas a distância é grande. Na CSN, a
dívida líquida é quase do tamanho do valor da operação inteira, e por isso o valor da ação vai
de negativo a R$ 41,79 conforme o cenário.

Aviso: a Vale e a CSN têm obrigações grandes que o balanço não chama de dívida e que, por
isso, não entram nos valores dos cenários. Na Vale são R$ 20,0 bilhões em provisões de
Brumadinho e de Mariana. Na CSN são R$ 13,1 bilhões que ela já recebeu de clientes por
produtos que ainda vai entregar. A linha de aviso da tabela mostra o valor moderado se as duas
entrassem como dívida: a Vale continua 17% acima do preço e a CSN fica negativa.
<!-- resumo:fim -->

<!-- analise:inicio -->
### Como cheguei a esses valores

O valor por ação vem de um fluxo de caixa descontado. Projetei o caixa livre de cada empresa
(FCFF) de 2026 a 2030, trouxe esses fluxos a valor de hoje pelo custo de capital (WACC), somei
o valor dos anos seguintes e tirei a dívida. O que sobra é dividido pelo número de ações.

Só três variáveis mudam de um cenário para outro: o crescimento da receita, a margem EBITDA de
2030 e o WACC. Cada uma sai de uma regra fixa, igual para as quatro empresas. No moderado, por
exemplo, a receita cresce pela inflação esperada e a margem de 2030 é a mediana de 2021 a 2025.
Usei a mesma taxa de juros para as quatro, a do Tesouro prefixado de dez anos (12,91% ao ano),
para comparar todas na mesma base.

### Vale

Nos doze meses até junho de 2026 a Vale vendeu R$ 218 bilhões e ficou com 34,6% disso como
EBITDA, sem contar as baixas contábeis. É mais que o dobro da margem das outras três, mas bem
abaixo dos 54,5% que a própria Vale teve em 2021.

O lucro caiu mais do que a margem. Em 2025 a empresa registrou R$ 25,1 bilhões em perdas por
recuperabilidade (impairment), uma baixa que reduz o lucro sem tirar dinheiro do caixa. O lucro
do ano foi de R$ 11,8 bilhões, contra R$ 30,4 bilhões em 2024.

A operação gerou R$ 50,6 bilhões de caixa em doze meses e os investimentos levaram R$ 31,8
bilhões. Sobraram R$ 18,8 bilhões, menos do que os R$ 23,1 bilhões pagos em dividendos no
período. Essa sobra ainda não conta os R$ 10,5 bilhões pagos no mesmo período pela reparação
de Mariana (Samarco), que a empresa registra entre os investimentos. A dívida líquida, que era de
R$ 10,5 bilhões no fim de 2021, chegou a R$ 68,2 bilhões em junho de 2026. Isso equivale a
0,9 vez o EBITDA de um ano, sem as baixas.

No cenário moderado a receita cresce 3,8% ao ano, a margem volta a 39,4% até 2030 e o WACC é
de 14,12%. O resultado é R$ 84,07 por ação, 24% acima do preço. Pelo fluxo de caixa do
acionista (FCFE) a conta dá R$ 71,97, também acima. A tabela de sensibilidade refaz o cálculo
para 25 combinações de WACC e de crescimento na perpetuidade, e o valor fica acima do preço em
22 delas. Fica abaixo só quando o WACC sobe dois pontos e o crescimento na perpetuidade não
passa de 3,5%.

Os múltiplos se dividem. Apliquei à Vale a mediana do que o mercado paga pelas outras quatro
empresas do grupo de comparação (CSN, Gerdau, Usiminas e CSN Mineração). Pelo resultado da
operação, sem as baixas, a Vale parece barata: negocia a 4,6 vezes o EBITDA, contra 4,9 das
outras, e o preço implícito fica em R$ 72,91 pelo EBITDA e em R$ 99,72 pelo EBIT. Pelo lucro e
pelo patrimônio, que a baixa de 2025 reduziu, parece cara: R$ 41,15 e R$ 37,52. O grupo é
pequeno, e duas das quatro empresas estão no prejuízo.

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
negativo (−R$ 7,68). Pelos múltiplos de EBITDA e de EBIT das comparáveis também fica negativo.

O método ainda favorece a CSN em dois pontos. Ela tem o menor WACC das quatro (9,98%) porque
86% do capital é dívida, e a dívida entra na conta a 8,5% ao ano depois do imposto, a mesma
taxa das outras. É um efeito da fórmula. O risco da ação medido pelo beta é o maior das quatro:
1,48, contra 1,02 da Usiminas, 0,78 da Gerdau e 0,76 da Vale. O segundo ponto é o que ficou
fora da dívida: a CSN já recebeu R$ 13,1 bilhões de clientes por produtos que ainda vai
entregar. Se esse valor entrasse como dívida, o cenário moderado daria −R$ 5,46 por ação.

### Gerdau

A Gerdau tem um balanço leve. A dívida líquida é de R$ 8,1 bilhões, 0,8 vez o EBITDA sem as
baixas, e sobra caixa depois dos investimentos todos os anos desde 2020.

O problema está na margem. O EBITDA sem baixas contábeis caiu de 30% da receita em 2021 para
13,4% em 2025, e está em 15,4% nos últimos doze meses. O lucro de 2025 foi de R$ 1,4 bilhão,
depois de uma baixa de R$ 2,0 bilhões.

O cenário moderado supõe que a margem volte a 19,7% até 2030 e chega a R$ 21,12 por ação, 15%
abaixo dos R$ 24,77 da bolsa. A ação está perto da máxima de 52 semanas (R$ 26,31). O preço de
hoje aparece no modelo quando a margem de 2030 chega a 21,6%, entre o cenário moderado e o
otimista.

Os múltiplos ficam mais perto da bolsa: os preços implícitos vão de R$ 21,22 a R$ 28,56, e o
preço de mercado está dentro dessa faixa.

A Gerdau é também a menos ligada ao minério de ferro. Ele explica 13% da variação mensal da
ação, contra 15% na Usiminas, 30% na CSN e 48% na Vale.

### Usiminas

A Usiminas é a única das quatro com mais caixa do que dívida: R$ 6,8 bilhões em caixa contra
R$ 6,2 bilhões de dívida. Nos últimos doze meses a operação gerou R$ 2,7 bilhões, os
investimentos levaram R$ 1,2 bilhão e sobrou R$ 1,5 bilhão.

O que pesa é a margem, a menor do grupo. O EBITDA sem baixas foi de 38,1% da receita em 2021,
caiu para 6,7% em 2023 e 2024 e está em 9,6% nos últimos doze meses. Em 2025 a empresa deu
prejuízo de R$ 2,9 bilhões, depois de uma baixa de R$ 2,2 bilhões em ativos e de uma despesa
de R$ 1,3 bilhão com imposto diferido. No primeiro semestre de 2026 voltou ao lucro (R$ 1,3 bilhão).

Pela regra do cenário moderado, a margem de 2030 é a mediana de 2021 a 2025, que na Usiminas
é de 8,1%, abaixo da margem de hoje. Com essa margem a operação inteira vale R$ 3,2 bilhões,
1,4 vez o EBITDA de um ano, e o valor por ação fica em R$ 2,19, 70% abaixo dos R$ 7,21 da
bolsa. Nenhuma das 25 combinações da tabela de sensibilidade chega perto do preço.

A bolsa está pagando por uma recuperação que a mediana dos últimos cinco anos não mostra. O
preço de hoje aparece no modelo quando a margem de 2030 chega a 12,2%, e o cenário otimista,
com margem de 15,3%, dá R$ 13,87. Os múltiplos contam a mesma história do mercado: a 4,6 vezes
o EBITDA sem baixas a Usiminas negocia como as comparáveis, e o preço implícito por esse
múltiplo é de R$ 7,62.

Dois detalhes pesam nessa conta. Uma parte da operação pertence a sócios de fora (a mineração
é dividida com a Sumitomo), e tirei R$ 2,9 bilhões do valor por isso, pelo valor contábil.
E a ação custa 0,42 vez o patrimônio, o menor número do grupo.

### Por que a Vale se destaca

Destacar-se, aqui, quer dizer sair melhor nas contas deste modelo, com estas premissas. A Vale
sai melhor por três motivos:

- É a única em que o cenário moderado fica acima do preço, tanto pelo fluxo de caixa da empresa
  (R$ 84,07) quanto pelo do acionista (R$ 71,97).
- É a que menos perde quando as premissas pioram. No cenário pessimista o valor fica 25% abaixo
  do preço. Na Gerdau fica 55% abaixo, na Usiminas 82% e na CSN fica negativo.
- Tem a maior margem das quatro e continua com lucro e com sobra de caixa depois de investir
  R$ 31,8 bilhões em um ano.

### O que pode mudar essa conclusão

- Os múltiplos não dão uma resposta só. Pelo EBITDA e pelo EBIT a Vale parece barata, pelo
  lucro e pelo patrimônio parece cara.
- O resultado depende de a margem voltar de 34,6% para 39,4%. Se a margem ficar onde está, a
  receita parar de crescer e o WACC subir 1,56 ponto, o valor cai para R$ 51,05.
- A Vale é a mais exposta ao minério de ferro, que explica 48% da variação mensal da ação. O
  modelo não projeta o preço do minério. Ele entra só pela margem.
- Provisões não entram como dívida nas contas. Na Vale, as de Brumadinho e de Mariana somam
  R$ 20,0 bilhões no balanço de junho de 2026. Tirando esse valor, o cenário moderado cai de
  R$ 84,07 para R$ 79,15, ainda 17% acima do preço.
- A regra da margem olha para trás. Ela é dura com a Usiminas, que vem dos piores anos da
  série, e não sabe se esses anos foram exceção ou o novo normal.
- Em três das quatro empresas, mais de 70% do valor calculado vem do período depois de 2030,
  que é o mais incerto. Na Usiminas é 66%.

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

Deixei de fora sinergias de fusões e aquisições e valuation pre e post-money. As quatro empresas
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
| Dados | O histórico da CVM das quatro empresas |

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
fechamento de 08/10/2026 e três empresas. A de [10/10/2026](analises/2026-10-10.md) usa os
mesmos preços e traz a Usiminas e as correções listadas abaixo. Cada fotografia tem uma tag
no git (`analise-2026-10-09`, `analise-2026-10-10`), para quem quiser ver o código e os dados
como estavam.

### O que mudou na revisão de 10/10/2026

- A Usiminas passou de comparável a empresa do estudo, com projeção, DCF e cenários.
- O investimento da Gerdau e da Usiminas estava menor do que é: a regra não achava as compras
  de ativos intangíveis. Na Gerdau o cenário moderado caiu de R$ 21,38 para R$ 21,04 só por isso.
- A dívida líquida ÷ EBITDA passou a usar o EBITDA sem baixas contábeis, como a margem. Na
  Vale o número foi de 1,3 para 0,9.
- Os múltiplos de EBITDA e de EBIT das comparáveis também passaram a ser sem baixas. Com a
  baixa de 2025, a Usiminas aparecia a 66 vezes o EBITDA.
- Os dividendos pagos pela CSN em doze meses eram R$ 695 milhões, não R$ 906 milhões.
- Faltava ajustar os preços da Gerdau pela bonificação de 5% de março de 2023 (uma ação nova
  para cada vinte, para quem tinha o papel em 21/03/2023). Sem o ajuste o dia 22 contava como
  uma queda de 4%. O beta foi de 0,79 para 0,78, e com as duas correções o cenário moderado
  da Gerdau fecha em R$ 21,12.
- As obrigações da Vale e da CSN que ficam fora da dívida passaram a aparecer como aviso, com
  o valor que o cenário moderado teria se entrassem. Elas não mudam os valores dos cenários.

Os valores da Vale e da CSN pelo fluxo de caixa não mudaram.

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
  "outros passivos tratados como dívida". O mesmo vale para o que a CSN recebeu adiantado de
  clientes.
- Arrendamentos entram na dívida só quando a empresa os registra junto dos empréstimos, como
  a Vale. Na Gerdau, na CSN e na Usiminas ficam de fora.
- A parte dos sócios minoritários sai pelo valor contábil, não pelo de mercado.
- Os preços são ajustados pelas bonificações da Gerdau de 2023 e de 2024, mas não por dividendos. Isso
  afeta o beta e a correlação.
- Fusões e aquisições e valuation pre e post-money ficaram fora do escopo.
