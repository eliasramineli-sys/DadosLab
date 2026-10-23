from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import uuid
from .bridge import validate


def data_directory():
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    folder = base / "DadosLab"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_directory() / "sessions.sqlite3"
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, mode TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS rolls(session TEXT NOT NULL REFERENCES sessions(id),
          position INTEGER NOT NULL, face INTEGER NOT NULL CHECK(face BETWEEN 1 AND 6),
          PRIMARY KEY(session, position));
        """)

    def load(self, mode):
        if mode not in ("virtual", "fisico"):
            raise ValueError("Origem inválida")
        row = self.connection.execute("SELECT id FROM sessions WHERE mode=? ORDER BY rowid DESC LIMIT 1", (mode,)).fetchone()
        session = row[0] if row else self.new(mode)
        values = [r[0] for r in self.connection.execute("SELECT face FROM rolls WHERE session=? ORDER BY position", (session,))]
        return session, validate(values)

    def new(self, mode):
        if mode not in ("virtual", "fisico"):
            raise ValueError("Origem inválida")
        session = str(uuid.uuid4())
        with self.connection:
            self.connection.execute("INSERT INTO sessions VALUES(?,?,?)", (session, mode, datetime.now(timezone.utc).isoformat()))
        return session

    def append(self, session, values):
        values = validate(values)
        with self.connection:
            start = self.connection.execute("SELECT COUNT(*) FROM rolls WHERE session=?", (session,)).fetchone()[0]
            if start + len(values) > 100000:
                raise ValueError("Limite de 100.000 lançamentos por sessão.")
            self.connection.executemany("INSERT INTO rolls VALUES(?,?,?)", ((session, start+i, v) for i,v in enumerate(values)))

    def close(self):
        self.connection.close()
