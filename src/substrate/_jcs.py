from __future__ import annotations

from typing import Any

import rfc8785


def canonicalize(obj: Any) -> bytes:
    return rfc8785.dumps(obj)
