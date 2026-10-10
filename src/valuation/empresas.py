"""Cadastro das empresas do estudo.

As três do TCC e a Usiminas são o foco (`foco=True`): ganham projeção, DCF e
planilha. A CSN Mineração entra só como comparável no valuation por múltiplos.
"""

from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "dados"
CACHE = DADOS / "cache"
PREMISSAS = RAIZ / "premissas"
SAIDA = RAIZ / "saida"
SITE = RAIZ / "site"

# Onde o projeto está publicado.
REPOSITORIO = "https://github.com/timmtimm1/valuation-vale-csn-gerdau"
PAGINA = "https://timmtimm1.github.io/valuation-vale-csn-gerdau/"


@dataclass(frozen=True)
class Empresa:
    ticker: str
    nome: str
    cnpj: str
    setor: str
    foco: bool
    # A CVM recebe a quantidade de ações na unidade que a empresa informa; a Vale
    # informa em milhares, as outras em unidades.
    escala_acoes: int = 1
    # Demais classes de ação da mesma empresa, para o valor de mercado somar todas.
    outros_tickers: tuple[str, ...] = ()
    # Obrigações grandes que o balanço não chama de dívida. Não entram no preço justo:
    # aparecem ao lado, como aviso de quanto ele cairia se entrassem. O padrão é
    # procurado na descrição das contas do passivo, sem acento e em minúsculas.
    obrigacoes: str = ""
    obrigacoes_nome: str = ""
    # Página de relações com investidores, para quem quiser conferir na própria empresa.
    ri: str = ""


EMPRESAS: tuple[Empresa, ...] = (
    Empresa(
        "VALE3",
        "Vale",
        "33.592.510/0001-54",
        "Mineração",
        True,
        escala_acoes=1000,
        # A segunda conta é onde a Vale registra a reparação de Mariana (Samarco).
        obrigacoes=r"brumadinho|participacao em coligadas e joint ventures",
        obrigacoes_nome="provisões de Brumadinho e de Mariana (Samarco)",
        ri="https://www.vale.com/pt/investidores",
    ),
    Empresa(
        "CSNA3",
        "CSN",
        "33.042.730/0001-04",
        "Siderurgia",
        True,
        # Até 2024 a conta se chamava "Adiantamento de clientes".
        obrigacoes=r"passivos de contratos|adiantamento de clientes",
        obrigacoes_nome="adiantamentos recebidos de clientes por produtos a entregar",
        ri="https://ri.csn.com.br",
    ),
    Empresa(
        "GGBR4",
        "Gerdau",
        "33.611.500/0001-19",
        "Siderurgia",
        True,
        outros_tickers=("GGBR3",),
        ri="https://ri.gerdau.com",
    ),
    Empresa(
        "USIM5",
        "Usiminas",
        "60.894.730/0001-05",
        "Siderurgia",
        True,
        outros_tickers=("USIM3",),
        ri="https://ri.usiminas.com",
    ),
    Empresa(
        "CMIN3",
        "CSN Mineração",
        "08.902.291/0001-15",
        "Mineração",
        False,
        ri="https://ri.csnmineracao.com.br",
    ),
)

# Eventos que mudam o preço sem mudar o valor da empresa. Sem o ajuste, a bonificação
# aparece como uma queda de 17% num dia. (ticker, primeiro pregão sem o direito, fator)
EVENTOS: tuple[tuple[str, str, float], ...] = (
    # Bonificação de uma ação nova para cada vinte, para quem tinha o papel em 21/03/2023
    # (aviso aos acionistas de 28/02/2023). Sem ela o dia 22 parecia uma queda de 4%.
    ("GGBR4", "2023-03-22", 1.05),
    ("GGBR3", "2023-03-22", 1.05),
    ("GGBR4", "2024-04-18", 1.2),  # bonificação de uma ação nova para cada cinco
    ("GGBR3", "2024-04-18", 1.2),
)

POR_TICKER = {e.ticker: e for e in EMPRESAS}
POR_CNPJ = {e.cnpj: e for e in EMPRESAS}
FOCO = tuple(e for e in EMPRESAS if e.foco)


def empresa(ticker: str) -> Empresa:
    try:
        return POR_TICKER[ticker.upper()]
    except KeyError:
        raise ValueError(f"ticker fora do estudo: {ticker}") from None
