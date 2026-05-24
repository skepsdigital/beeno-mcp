#!/usr/bin/env python3
"""Utilitarios da skill beeno-crm-readonly-notes: load .env, env vars, exceptions."""

import os
from pathlib import Path
from typing import Optional


class BeenoSkillError(Exception):
    """Erro base da skill."""


class AuthenticationError(BeenoSkillError):
    """Credenciais ausentes ou invalidas."""


class ScopeError(BeenoSkillError):
    """Tentativa de operacao fora do escopo permitido pela skill."""


class ApiError(BeenoSkillError):
    """Erro retornado pela API Beeno."""

    def __init__(self, status_code: int, message: str, endpoint: str):
        super().__init__(f"API Error ({status_code}) on {endpoint}: {message}")
        self.status_code = status_code
        self.endpoint = endpoint


def load_env_file(path: str = ".env") -> dict:
    """Carrega um arquivo .env no os.environ. Procura no CWD e em diretorios pai ate a raiz.

    Retorna dict com as variaveis carregadas (uteis para debug)."""
    loaded = {}
    env_path = _find_env_file(path)
    if not env_path:
        return loaded

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
        loaded[key] = value
    return loaded


def _find_env_file(filename: str) -> Optional[Path]:
    """Procura arquivo .env subindo a hierarquia de diretorios."""
    if os.path.isabs(filename):
        p = Path(filename)
        return p if p.is_file() else None

    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / filename
        if candidate.is_file():
            return candidate
    return None


def get_env_var(name: str, default: Optional[str] = None) -> Optional[str]:
    """Le variavel de ambiente, opcionalmente com default."""
    return os.environ.get(name, default)


def require_env_var(name: str) -> str:
    """Le variavel de ambiente, lanca AuthenticationError se ausente."""
    value = os.environ.get(name)
    if not value:
        raise AuthenticationError(
            f"Variavel de ambiente '{name}' nao encontrada. "
            f"Configure no .env do projeto ou exporte na sessao."
        )
    return value
