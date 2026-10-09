"""Linha de comando: cada etapa do estudo é um comando."""

import typer

from valuation import b3, cvm, historico, macro, multiplos, planilha, premissas
from valuation.empresas import FOCO

app = typer.Typer(help="Valuation de VALE3, CSNA3 e GGBR4.", no_args_is_help=True)


def _tickers(ticker: str | None) -> list[str]:
    return [ticker.upper()] if ticker else [e.ticker for e in FOCO]


@app.command()
def extrair(atualizar: bool = typer.Option(False, help="Baixa de novo cotações e macro.")) -> None:
    """Baixa CVM, B3 e dados macro e monta o histórico padronizado."""
    cvm.extrair()
    historico.construir()
    b3.construir_mercado(b3.extrair_precos(atualizar))
    macro.extrair(atualizar)
    multiplos.construir()
    typer.echo("dados/ atualizado")


@app.command()
def propor(ticker: str = typer.Argument(None)) -> None:
    """Gera a proposta de premissas (não sobrescreve arquivo aprovado)."""
    for t in _tickers(ticker):
        typer.echo(premissas.salvar_proposta(t))


@app.command()
def gerar(ticker: str = typer.Argument(None)) -> None:
    """Gera a planilha de cada empresa em saida/."""
    for t in _tickers(ticker):
        typer.echo(planilha.gerar(t))


@app.command()
def verificar(ticker: str = typer.Argument(None)) -> None:
    """Recalcula cada planilha no LibreOffice e compara com o modelo em Python."""
    from valuation import verificar as v

    falhou = False
    for t in _tickers(ticker):
        problemas = v.conferir(t)
        typer.echo(f"{t}: {'ok' if not problemas else f'{len(problemas)} divergências'}")
        for problema in problemas[:20]:
            typer.echo(f"  {problema}")
        falhou = falhou or bool(problemas)
    if falhou:
        raise typer.Exit(1)


@app.command()
def pagina() -> None:
    """Monta site/index.html com o modelo e os dados embutidos."""
    from valuation import site

    typer.echo(site.construir())
