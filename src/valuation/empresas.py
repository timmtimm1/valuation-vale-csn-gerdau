"""Cadastro das empresas do estudo.

As três do TCC são o foco (`foco=True`): ganham projeção, DCF e planilha. As
demais entram só como comparáveis no valuation por múltiplos.
"""

from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "dados"
CACHE = DADOS / "cache"
PREMISSAS = RAIZ / "premissas"
SAIDA = RAIZ / "saida"
SITE = RAIZ / "site"


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


EMPRESAS: tuple[Empresa, ...] = (
    Empresa("VALE3", "Vale", "33.592.510/0001-54", "Mineração", True, escala_acoes=1000),
    Empresa("CSNA3", "CSN", "33.042.730/0001-04", "Siderurgia", True),
    Empresa("GGBR4", "Gerdau", "33.611.500/0001-19", "Siderurgia", True, outros_tickers=("GGBR3",)),
    Empresa(
        "USIM5", "Usiminas", "60.894.730/0001-05", "Siderurgia", False, outros_tickers=("USIM3",)
    ),
    Empresa("CMIN3", "CSN Mineração", "08.902.291/0001-15", "Mineração", False),
)

# Eventos que mudam o preço sem mudar o valor da empresa. Sem o ajuste, a bonificação
# aparece como uma queda de 17% num dia. (ticker, primeiro pregão sem o direito, fator)
EVENTOS: tuple[tuple[str, str, float], ...] = (
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
