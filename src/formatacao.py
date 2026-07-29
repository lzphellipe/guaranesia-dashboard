"""
Formatação de números no padrão pt-BR, sem depender de `locale` do sistema
(que varia entre máquinas e quebra em containers). Substitui a gambiarra de
`.replace(',', 'X')...` que estava espalhada pelo app.
"""
from __future__ import annotations

from typing import Optional


def _milhar(inteiro: int) -> str:
    """12345678 -> '12.345.678'"""
    s = f"{abs(inteiro):,}".replace(",", ".")
    return f"-{s}" if inteiro < 0 else s


def reais(valor: Optional[float], casas: int = 2) -> str:
    """1234567.8 -> 'R$ 1.234.567,80'. None -> '—'."""
    if valor is None:
        return "—"
    inteiro = int(valor)
    frac = abs(valor) - abs(inteiro)
    corpo = _milhar(inteiro)
    if casas > 0:
        dec = f"{round(frac, casas):.{casas}f}"[2:]  # tira '0.'
        corpo = f"{corpo},{dec}"
    return f"R$ {corpo}"


def reais_compacto(valor: Optional[float]) -> str:
    """Escala automática: 811200000 -> 'R$ 811,2 mi'."""
    if valor is None:
        return "—"
    for limite, sufixo in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
        if abs(valor) >= limite:
            n = valor / limite
            txt = f"{n:.1f}".replace(".", ",")
            return f"R$ {txt} {sufixo}"
    return reais(valor, casas=0)


def inteiro(valor: Optional[int]) -> str:
    return "—" if valor is None else _milhar(int(valor))


def pct(valor: Optional[float], casas: int = 1) -> str:
    if valor is None:
        return "—"
    return f"{valor:.{casas}f}".replace(".", ",") + "%"
