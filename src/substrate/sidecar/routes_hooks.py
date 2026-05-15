from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .auth import AuthenticatedActor, TokenRegistry
from .models import ClaimHooksRequest, CompleteHookRequest, FailHookRequest, _serialize


def _get_actor(request: Request) -> AuthenticatedActor:
    actor = getattr(request.state, "actor", None)
    if actor is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return actor


def register_hook_routes(app, substrate, tokens: TokenRegistry):
    router = APIRouter(prefix="/v1/hooks")

    @router.post("/claim")
    async def claim_hooks(body: ClaimHooksRequest, request: Request):
        _get_actor(request)
        result = substrate.claim_hooks(
            max_batch=body.max_batch,
            lease_seconds=body.lease_seconds,
        )
        return _serialize(result)

    @router.post("/{hook_id}/complete")
    async def complete_hook(hook_id: int, body: CompleteHookRequest, request: Request):
        _get_actor(request)
        substrate.complete_hook(hook_id)
        return {"status": "ok"}

    @router.post("/{hook_id}/fail")
    async def fail_hook(hook_id: int, body: FailHookRequest, request: Request):
        _get_actor(request)
        substrate.fail_hook(hook_id, body.error)
        return {"status": "ok"}

    app.include_router(router)
