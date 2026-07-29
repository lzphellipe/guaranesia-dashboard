"""
Persistência leve em SQLite: guarda um retrato (snapshot) da despesa por
função a cada bimestre consultado. Assim o painel acumula série histórica —
que é onde mora o valor de accountability (ver a evolução do gasto no tempo),
já que a API só devolve o estado atual.

Sem ORM, sem dependência extra: só a stdlib `sqlite3`.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterable

import config


@contextmanager
def _con():
    con = sqlite3.connect(config.DB_PATH)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def inicializar() -> None:
    with _con() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS despesa_funcao (
                ano       INTEGER NOT NULL,
                periodo   INTEGER NOT NULL,
                funcao    TEXT    NOT NULL,
                empenhado REAL    NOT NULL,
                capturado_em TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (ano, periodo, funcao)
            )
        """)


def salvar_snapshot(ano: int, periodo: int, linhas: Iterable[dict]) -> int:
    """Grava/atualiza o snapshot. Idempotente por (ano, periodo, função)."""
    inicializar()
    n = 0
    with _con() as con:
        for l in linhas:
            con.execute(
                "INSERT OR REPLACE INTO despesa_funcao (ano,periodo,funcao,empenhado) "
                "VALUES (?,?,?,?)",
                (ano, periodo, l["funcao"], float(l["empenhado"])),
            )
            n += 1
    return n


def serie_funcao(funcao: str) -> list[dict]:
    """Histórico de uma função ao longo dos bimestres já capturados."""
    inicializar()
    with _con() as con:
        cur = con.execute(
            "SELECT ano, periodo, empenhado FROM despesa_funcao "
            "WHERE funcao = ? ORDER BY ano, periodo", (funcao,))
        return [{"ano": a, "periodo": p, "empenhado": v} for a, p, v in cur.fetchall()]


def snapshots_disponiveis() -> list[tuple[int, int]]:
    inicializar()
    with _con() as con:
        cur = con.execute(
            "SELECT DISTINCT ano, periodo FROM despesa_funcao ORDER BY ano, periodo")
        return [(a, p) for a, p in cur.fetchall()]
