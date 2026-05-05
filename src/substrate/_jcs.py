import math
import re
from typing import Any


def _serialize_string(s: str) -> str:
    parts = ['"']
    for ch in s:
        code = ord(ch)
        if ch == '"':
            parts.append('\\"')
        elif ch == '\\':
            parts.append('\\\\')
        elif ch == '\b':
            parts.append('\\b')
        elif ch == '\f':
            parts.append('\\f')
        elif ch == '\n':
            parts.append('\\n')
        elif ch == '\r':
            parts.append('\\r')
        elif ch == '\t':
            parts.append('\\t')
        elif code < 0x20:
            parts.append(f'\\u{code:04x}')
        else:
            parts.append(ch)
    parts.append('"')
    return ''.join(parts)


def _serialize_number(n: float | int) -> str:
    if isinstance(n, bool):
        raise ValueError("booleans are not numbers")
    if isinstance(n, float):
        if math.isnan(n) or math.isinf(n):
            raise ValueError("NaN and Infinity are not valid JSON numbers")
        if n == int(n) and not math.isinf(n):
            abs_n = abs(n)
            if abs_n < 1e21:
                return str(int(n))
        r = repr(n)
        if 'e' in r or 'E' in r:
            r = r.lower()
            r = r.replace('e+', 'e')
            r = re.sub(r'e(-?)0+(?=\d)', r'e\1', r)
        return r
    return str(n)


def _serialize_array(arr: list) -> str:
    parts = []
    for item in arr:
        parts.append(_serialize_value(item))
    return '[' + ','.join(parts) + ']'


def _serialize_object(obj: dict) -> str:
    parts = []
    for key in sorted(obj.keys()):
        parts.append(_serialize_string(key) + ':' + _serialize_value(obj[key]))
    return '{' + ','.join(parts) + '}'


def _serialize_value(v: Any) -> str:
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return _serialize_number(v)
    if isinstance(v, float):
        return _serialize_number(v)
    if isinstance(v, str):
        return _serialize_string(v)
    if isinstance(v, dict):
        return _serialize_object(v)
    if isinstance(v, list):
        return _serialize_array(v)
    raise ValueError(f"unsupported type: {type(v)}")


def canonicalize(obj: Any) -> bytes:
    return _serialize_value(obj).encode('utf-8')
