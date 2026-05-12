---
number: "119"
title: validate_json_safe_value raises raw TypeError on non-string dict keys
severity: high
status: implemented
kind: bug
author: adversarial-review
---

## Problem

`_check_string_safe` expects a `str` but is called with whatever the dict key is. If a caller passes `actor_metadata={1: "bad"}` or any non-string key, the `"\u0000" in value` line raises an unhandled `TypeError` instead of the expected `SubstrateError(INVALID_ARGUMENT)`.

## Impact

Unhandled exception leaks out of the library boundary. Callers cannot catch it with `SubstrateError`, breaking the API contract. Any external system that wraps substrate in its own error handling will see an unexpected exception type.

## Fix

Add an `isinstance(value, str)` guard at the top of `_check_string_safe` and raise `SubstrateError(INVALID_ARGUMENT)` if false.

## Related

- `_contract.py` `_check_string_safe`
- `_contract.py` `validate_json_safe_value`
