"""O registro das fontes e da fotografia do dia tem de bater com os dados."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from valuation import registro
from valuation.b3 import MERCADO_CSV
from valuation.empresas import EMPRESAS


@pytest.fixture
def pasta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(registro, "ANALISES", tmp_path)
    monkeypatch.setattr(registro, "FONTES_MD", tmp_path / "FONTES.md")
    return tmp_path


def test_fotografia_traz_o_preco_de_cada_acao_no_ultimo_pregao(pasta: Path) -> None:
    texto = registro.fotografia(date(2026, 10, 9)).read_text(encoding="utf-8")
    mercado = pd.read_csv(MERCADO_CSV).set_index("ticker")
    for e in EMPRESAS:
        preco = f"{mercado.loc[e.ticker, 'preco']:.2f}".replace(".", ",")
        assert f"({e.ticker}) | R$ {preco} |" in texto
    pregao = "/".join(reversed(mercado["data_preco"].max().split("-")))
    assert f"Fechamento de {pregao}" in texto
    assert "# Análise de 09/10/2026" in texto


def test_fontes_cita_todos_os_arquivos_de_dados(pasta: Path) -> None:
    texto = registro.fontes().read_text(encoding="utf-8")
    for arquivo in ("contas_cvm", "historico", "acoes", "precos", "mercado", "macro"):
        assert f"dados/{arquivo}.csv" in texto
    assert "dados/commodity_e_acoes.csv" in texto
    assert texto.count("https://") >= 8
