"""A planilha em fórmulas tem de dar o mesmo resultado que o modelo em Python."""

import shutil

import pytest

from valuation import planilha, verificar
from valuation.empresas import FOCO


@pytest.mark.skipif(shutil.which("soffice") is None, reason="precisa do LibreOffice")
@pytest.mark.parametrize("ticker", [e.ticker for e in FOCO])
def test_planilha_recalculada_bate_com_o_modelo(ticker: str) -> None:
    planilha.gerar(ticker)
    assert verificar.conferir(ticker) == []
