"""Authentication service: signup, login, refresh-token rotation, logout."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    TokenError,
)
from app.models.user import Account, Session
from app.schemas.auth import TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_by_email(self, email: str) -> Account | None:
        result = await self.db.execute(
            select(Account).where(Account.email == email.lower(), Account.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def signup(self, email: str, password: str, display_name: str | None) -> Account:
        if await self._get_by_email(email):
            raise EmailAlreadyExistsError()
        account = Account(
            email=email.lower(),
            password_hash=hash_password(password),
            display_name=display_name,
        )
        self.db.add(account)
        await self.db.flush()
        return account

    async def _issue_tokens(
        self,
        account: Account,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        refresh = generate_refresh_token()
        session = Session(
            account_id=account.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_ttl_days),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(session)
        await self.db.flush()
        access = create_access_token(account.id)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.jwt_access_ttl_minutes * 60,
        )

    async def login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        account = await self._get_by_email(email)
        if account is None or not verify_password(password, account.password_hash):
            raise InvalidCredentialsError()
        return await self._issue_tokens(account, ip_address=ip_address, user_agent=user_agent)

    async def refresh(
        self,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(Session).where(Session.token_hash == token_hash, Session.is_revoked.is_(False))
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise TokenError("Refresh token is invalid or expired")
        # SQLite drops tzinfo on round-trip; treat naive timestamps as UTC.
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise TokenError("Refresh token is invalid or expired")

        # Rotate: revoke the presented token, issue a new pair.
        session.is_revoked = True
        await self.db.flush()
        account = await self.db.get(Account, session.account_id)
        if account is None or account.is_deleted:
            raise TokenError("Account no longer exists")
        return await self._issue_tokens(account, ip_address=ip_address, user_agent=user_agent)

    async def logout(self, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(select(Session).where(Session.token_hash == token_hash))
        session = result.scalar_one_or_none()
        if session is not None:
            session.is_revoked = True
            await self.db.flush()
