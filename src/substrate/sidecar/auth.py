from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AuthenticatedActor:
    actor_id: str
    actor_kind: str
    allowed_roles: list[str]


class TokenRegistry:
    def __init__(self) -> None:
        self._tokens: dict[str, AuthenticatedActor] = {}

    @classmethod
    def from_file(cls, path: str | Path) -> TokenRegistry:
        reg = cls()
        data = yaml.safe_load(Path(path).read_text())
        for entry in data.get("tokens", []):
            token_sha256 = entry["token_sha256"]
            actor = AuthenticatedActor(
                actor_id=entry["actor_id"],
                actor_kind=entry.get("actor_kind", "agent"),
                allowed_roles=entry.get("allowed_roles", []),
            )
            reg._tokens[token_sha256] = actor
        return reg

    def authenticate(self, raw_token: str) -> AuthenticatedActor:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        actor = self._tokens.get(token_hash)
        if actor is None:
            return None
        return actor
