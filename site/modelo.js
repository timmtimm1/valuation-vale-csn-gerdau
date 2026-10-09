// O mesmo modelo de src/valuation/modelo.py, para a página recalcular no navegador.
// Qualquer mudança aqui tem de ser feita lá também: tests/test_site.py roda este
// arquivo no Node e exige o mesmo resultado do Python.
// Convenções: R$ milhões; custos e despesas positivos; uma posição de array por ano.

const Modelo = (() => {
  function projetar(base, p, anos) {
    const linhas = {};
    const guardar = (nome, i, valor) => {
      (linhas[nome] ||= new Array(anos.length))[i] = valor;
    };
    let a = { ...base.ano };
    const tIr = p.aliquota_ir;
    anos.forEach((_, i) => {
      const volume = 1 + p.crescimento_volume[i];
      const custos = 1 + p.inflacao_custos[i];
      const c = {};

      // DRE
      c.receita = a.receita * volume * (1 + p.variacao_preco[i]);
      // Custo acompanha volume e inflação de custos, não o preço de venda.
      c.custo_caixa = a.custo_caixa * volume * custos;
      c.despesas_vendas = a.despesas_vendas * volume * custos;
      c.despesas_ga = a.despesas_ga * custos;
      c.outras_operacionais = c.receita * p.outras_pct[i];
      c.equivalencia = p.equivalencia[i];
      c.ebitda =
        c.receita - c.custo_caixa - c.despesas_vendas - c.despesas_ga +
        c.outras_operacionais + c.equivalencia;
      c.da = a.ativo_fixo * p.depreciacao_pct[i];
      c.ebit = c.ebitda - c.da;
      c.resultado_financeiro = a.caixa_total * p.rendimento_caixa - a.divida_bruta * p.custo_divida;
      c.lair = c.ebit + c.resultado_financeiro;
      c.ir = Math.max(0, c.lair - c.equivalencia) * tIr;
      c.lucro_liquido = c.lair - c.ir;
      c.nopat = (c.ebit - c.equivalencia) * (1 - tIr);

      // Investimento e capital de giro
      c.capex = c.receita * p.capex_pct[i];
      c.ativo_fixo = a.ativo_fixo + c.capex - c.da;
      c.contas_receber = (c.receita * p.prazo_recebimento[i]) / 365;
      c.estoques = (c.custo_caixa * p.prazo_estoque[i]) / 365;
      c.fornecedores = (c.custo_caixa * p.prazo_pagamento[i]) / 365;
      c.capital_de_giro = c.contas_receber + c.estoques - c.fornecedores;
      const giroAnterior = a.contas_receber + a.estoques - a.fornecedores;
      c.variacao_giro = c.capital_de_giro - giroAnterior;

      // Fluxos de caixa livres
      c.fcff = c.nopat + c.da - c.capex - c.variacao_giro;
      c.captacao_liquida = p.captacao_liquida[i];
      c.fcfe =
        c.lucro_liquido - c.equivalencia + c.da - c.capex - c.variacao_giro + c.captacao_liquida;
      c.dividendos = Math.max(0, c.lucro_liquido) * p.payout;

      // Balanço: o caixa fecha a conta
      c.variacao_caixa = c.fcfe - c.dividendos;
      c.caixa_total = a.caixa_total + c.variacao_caixa;
      c.investimentos = a.investimentos + c.equivalencia;
      c.outros_ativos = a.outros_ativos;
      c.divida_bruta = a.divida_bruta + c.captacao_liquida;
      c.outros_passivos = a.outros_passivos;
      c.patrimonio_liquido = a.patrimonio_liquido + c.lucro_liquido - c.dividendos;
      c.ativo_total =
        c.caixa_total + c.contas_receber + c.estoques + c.ativo_fixo + c.investimentos +
        c.outros_ativos;
      c.passivo_e_pl = c.fornecedores + c.divida_bruta + c.outros_passivos + c.patrimonio_liquido;
      c.checagem_balanco = c.ativo_total - c.passivo_e_pl;

      // Indicadores
      c.margem_ebitda = c.ebitda / c.receita;
      c.divida_liquida = c.divida_bruta - c.caixa_total;
      c.divida_liquida_ebitda = c.divida_liquida / c.ebitda;
      c.roic = c.nopat / (giroAnterior + a.ativo_fixo);

      for (const nome in c) guardar(nome, i, c[nome]);
      a = c;
    });
    return linhas;
  }

  function custoDeCapital(p) {
    const ke = p.juro_sem_risco + p.beta * p.premio_mercado + p.premio_adicional;
    const kdLiquido = p.custo_divida * (1 - p.aliquota_ir);
    const wd = p.peso_divida;
    return { ke, kd_liquido: kdLiquido, wacc: ke * (1 - wd) + kdLiquido * wd };
  }

  // O primeiro ano só conta pela fração que falta; os fluxos caem no meio do período.
  function valorPresente(fluxos, terminal, taxa, g, fracao) {
    let vp = 0;
    fluxos.forEach((fluxo, i) => {
      vp += i === 0
        ? (fluxo * fracao) / (1 + taxa) ** (fracao / 2)
        : fluxo / (1 + taxa) ** (fracao + i - 0.5);
    });
    const fim = fracao + fluxos.length - 1;
    return [vp, (terminal * (1 + g)) / (taxa - g) / (1 + taxa) ** fim];
  }

  function avaliar(base, proj, p, wacc, g) {
    const k = custoDeCapital(p);
    wacc = wacc ?? k.wacc;
    g = g ?? p.crescimento_perpetuo;
    const u = proj.fcff.length - 1;
    const capexTerminal = p.capex_perpetuidade * proj.da[u];
    const fcffTerminal = proj.nopat[u] + proj.da[u] - capexTerminal - proj.variacao_giro[u];
    const [vp, vpTerminal] = valorPresente(proj.fcff, fcffTerminal, wacc, g, base.fracao_ano1);
    const ev = vp + vpTerminal;
    const ponte = base.ponte;
    const dividaLiquida = ponte.divida_bruta - ponte.caixa_total;
    const equity = ev - dividaLiquida - ponte.minoritarios + ponte.investimentos - p.outros_ajustes;

    const fcfeTerminal =
      proj.lucro_liquido[u] - proj.equivalencia[u] + proj.da[u] - capexTerminal -
      proj.variacao_giro[u] + proj.captacao_liquida[u];
    const [vpE, vpETerminal] = valorPresente(proj.fcfe, fcfeTerminal, k.ke, g, base.fracao_ano1);
    const equityFcfe = vpE + vpETerminal - ponte.minoritarios + ponte.investimentos - p.outros_ajustes;
    const preco = equity / base.acoes;
    return {
      ...k,
      wacc_usado: wacc,
      g_usado: g,
      fcff_terminal: fcffTerminal,
      vp_fluxos: vp,
      vp_terminal: vpTerminal,
      peso_terminal: vpTerminal / ev,
      ev,
      divida_liquida: dividaLiquida,
      minoritarios: ponte.minoritarios,
      investimentos: ponte.investimentos,
      outros_ajustes: p.outros_ajustes,
      equity,
      preco_justo: preco,
      preco_mercado: base.preco,
      potencial: preco / base.preco - 1,
      equity_fcfe: equityFcfe,
      preco_fcfe: equityFcfe / base.acoes,
      ev_ebitda_implicito: ev / proj.ebitda[0],
    };
  }

  const PASSOS = [-2, -1, 0, 1, 2];

  function sensibilidade(base, proj, p) {
    const centro = custoDeCapital(p).wacc;
    const waccs = PASSOS.map((d) => centro + 0.01 * d);
    const gs = PASSOS.map((d) => p.crescimento_perpetuo + 0.005 * d);
    return {
      waccs,
      gs,
      precos: waccs.map((w) => gs.map((g) => avaliar(base, proj, p, w, g).preco_justo)),
    };
  }

  return { projetar, custoDeCapital, avaliar, sensibilidade };
})();

if (typeof module !== "undefined") module.exports = Modelo;
