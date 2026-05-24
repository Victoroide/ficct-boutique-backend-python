"""RS256 JWT authentication for DRF — verifies tokens minted by the Go core."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Optional, Tuple

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions


class AuthenticatedUser:
    """Lightweight user wrapper that carries JWT claims into views.

    We intentionally don't materialize a Django user row — this service is
    stateless w.r.t. identity, the Go core is the source of truth.
    """

    is_authenticated = True
    is_active = True
    is_anonymous = False

    def __init__(self, user_id: str, email: str, role: str, claims: dict) -> None:
        self.id = user_id
        self.pk = user_id
        self.email = email
        self.role = role
        self.claims = claims

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"


@functools.lru_cache(maxsize=1)
def _load_public_key() -> bytes:
    path = Path(settings.FICCT_AI["JWT_PUBLIC_KEY_PATH"])
    return path.read_bytes()


class RS256JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request) -> Optional[Tuple[AuthenticatedUser, str]]:
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            return None
        token = parts[1]

        try:
            decoded = jwt.decode(
                token,
                _load_public_key(),
                algorithms=["RS256"],
                issuer=settings.FICCT_AI["JWT_ISSUER"],
                audience=settings.FICCT_AI["JWT_AUDIENCE"],
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed(f"invalid token: {exc}") from exc

        sub = decoded.get("sub")
        role = decoded.get("role")
        if not sub or not role:
            raise exceptions.AuthenticationFailed("claims missing sub/role")

        user = AuthenticatedUser(
            user_id=str(sub),
            email=str(decoded.get("email", "")),
            role=str(role),
            claims=decoded,
        )
        return (user, token)

    def authenticate_header(self, request) -> str:
        return f"{self.keyword} realm=ficct-ai"
