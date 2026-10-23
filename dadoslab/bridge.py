from __future__ import annotations
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
MAX_ROLLS = 100_000


def validate(values):
    data = list(values)
    if len(data) > MAX_ROLLS or any(type(v) is not int or not 1 <= v <= 6 for v in data):
        raise ValueError("Use no máximo 100.000 valores inteiros entre 1 e 6.")
    return data


class NativeDice:
    def __init__(self, path=None):
        filename = "dice.dll" if sys.platform == "win32" else "libdice.so"
        self.path = Path(path) if path else ROOT / "bin" / filename
        if not self.path.is_file():
            raise RuntimeError("Motor C++ ausente. Execute python scripts/build.py antes de iniciar.")
        self.lib = ctypes.CDLL(str(self.path))
        self.lib.dice_version.restype = ctypes.c_int
        if self.lib.dice_version() != 1:
            raise RuntimeError("Versão incompatível do motor C++.")
        self.lib.dice_roll.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t]
        self.lib.dice_roll.restype = ctypes.c_int
        self.lib.dice_counts.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint64)]
        self.lib.dice_counts.restype = ctypes.c_int

    def roll(self, count=1):
        if type(count) is not int or not 1 <= count <= MAX_ROLLS:
            raise ValueError("Quantidade deve estar entre 1 e 100.000.")
        buffer = (ctypes.c_uint32 * count)()
        if self.lib.dice_roll(buffer, count):
            raise RuntimeError("O gerador C++ recusou o lançamento.")
        return list(buffer)

    def counts(self, values):
        values = validate(values)
        buffer = (ctypes.c_uint32 * len(values))(*values)
        result = (ctypes.c_uint64 * 6)()
        if self.lib.dice_counts(buffer, len(values), result):
            raise RuntimeError("Falha na contagem C++.")
        return list(result)


def audit(values, java=None):
    values = validate(values)
    bundled = ROOT / "runtime-java" / "bin" / ("java.exe" if sys.platform == "win32" else "java")
    executable = java or (str(bundled) if bundled.is_file() else shutil.which("java"))
    if not executable:
        raise RuntimeError("Java 17+ não encontrado. Instale um JDK 17+ ou use o pacote portátil completo.")
    classpath = ROOT / "bin" / "java"
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    result = subprocess.run([str(executable), "-cp", str(classpath), "SequenceAudit"],
        input=" ".join(map(str, values)) + "\n", text=True, encoding="utf-8",
        capture_output=True, timeout=30, **flags)
    if result.returncode:
        raise RuntimeError("Análise Java falhou: " + result.stderr.strip()[:300])
    answer = json.loads(result.stdout)
    if answer["n"] != len(values):
        raise RuntimeError("A auditoria Java retornou tamanho inconsistente.")
    return answer
