---
number: "117"
title: InMemory remove_link fallback logic broken
severity: high
status: implemented
kind: bug
author: adversarial-review
---

## Problem

When no active link object is found in `self._links`, the fallback scans the event stream. It computes:

```python
has_removed = any(
    e.transition == "link_removed"
    and ...
    for e in events
)
```

This is `True` if **any** historical `link_removed` event exists, regardless of whether a later `link_created` re-established the link. A link that was removed and then recreated cannot be removed a second time through the fallback path.

## Impact

A valid second `remove_link` call raises `LINK_NOT_FOUND` incorrectly, even though a live link exists. This violates the expected lifecycle of links and could break workflows that remove and recreate links.

## Fix

Check the **most recent** event for the `(from, to, type)` tuple, not whether any removal ever happened. If the most recent event is `link_created`, the link is live and removal should succeed.

## Related

- `_in_memory.py` `remove_link`
- `_links.py` `remove_link` (Postgres)
