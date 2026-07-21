"""Secretariat service exceptions."""

from __future__ import annotations


class SecretariatError(Exception):
    """A user-facing business rule violation."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
