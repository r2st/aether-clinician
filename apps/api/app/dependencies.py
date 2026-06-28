"""FastAPI dependency-injection wiring."""

from __future__ import annotations

import uuid

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.exceptions import TokenError
from app.models.user import Account


async def get_current_account(request: Request, db: AsyncSession = Depends(get_db)) -> Account:
    """Resolve the authenticated account from the Bearer access token."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise TokenError("Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise TokenError("Wrong token type")
    try:
        account_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise TokenError("Malformed token subject") from exc

    account = await db.get(Account, account_id)
    if account is None or account.is_deleted:
        raise TokenError("Account not found")
    return account


# Convenience alias used across routers.
CurrentAccount = Depends(get_current_account)
DBSession = Depends(get_db)
