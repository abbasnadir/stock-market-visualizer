"""Supabase client and authentication service."""

from __future__ import annotations

import logging
from typing import Any

from supabase import Client, ClientOptions, create_client

from src.config.settings import AppSettings
from src.core.result import OperationResult


LOGGER = logging.getLogger(__name__)


class SupabaseService:
    """Encapsulates Supabase initialization and auth operations.

    The server keeps no signed-in session of its own. Sign-in returns the user's
    tokens, the browser keeps them in its session store, and every database call
    uses a client built from that user's access token, so row-level security
    applies to the right user.
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.client: Client | None = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if not self.settings.has_supabase_credentials:
            return

        try:
            self.client = self._new_client()
        except Exception:
            self.client = None

    def _new_client(self, access_token: str | None = None) -> Client:
        # No background token refresh or stored session: each client is short-lived.
        options = ClientOptions(auto_refresh_token=False, persist_session=False)
        if access_token:
            options.headers["Authorization"] = f"Bearer {access_token}"
        return create_client(
            self.settings.supabase_url,
            self.settings.supabase_anon_key,
            options=options,
        )

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def client_for(self, access_token: str | None) -> Client | None:
        """Client whose table calls run as the user that owns the access token."""
        if not self.client or not access_token:
            return None
        return self._new_client(access_token)

    @staticmethod
    def _session_data(user: Any, session: Any) -> dict[str, Any]:
        return {
            "user_id": str(user.id),
            "email": user.email,
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
        }

    @staticmethod
    def _exception_metadata(exc: Exception) -> str:
        """Extract non-sensitive diagnostic metadata from provider exceptions."""
        metadata: list[str] = []
        for key in ("code", "status_code", "details", "hint"):
            value = getattr(exc, key, None)
            if value:
                metadata.append(f"{key}={value}")
        return " | ".join(metadata)

    def _auth_error_result(self, action: str, exc: Exception) -> OperationResult:
        raw_message = str(exc)
        normalized = raw_message.lower()
        diagnostic = self._exception_metadata(exc)

        if "email rate limit exceeded" in normalized or ("rate limit" in normalized and "email" in normalized):
            return OperationResult(
                success=False,
                message=(
                    "Supabase email verification rate limit is active for this project. "
                    "Use Login if the account already exists. If this persists, check Supabase Auth rate limits "
                    "and SMTP settings in the project dashboard."
                ),
                data={"code": "email_rate_limit", "raw_error": raw_message, "action": action},
            )

        if "database error saving new user" in normalized:
            return OperationResult(
                success=False,
                message=(
                    "Sign-up could not complete because Supabase failed to save the new auth user. "
                    "Most common cause is a failing auth trigger/RLS rule (often on profile creation). "
                    "Open Supabase Logs -> Auth and Database to inspect the exact SQL error."
                ),
                data={
                    "code": "database_error_saving_new_user",
                    "raw_error": raw_message,
                    "action": action,
                    "diagnostic": diagnostic,
                },
            )

        if "user already registered" in normalized or "already been registered" in normalized:
            return OperationResult(
                success=False,
                message="Account already exists. Try logging in instead of creating a new account.",
                data={"code": "user_exists", "raw_error": raw_message, "action": action},
            )

        if "email not confirmed" in normalized:
            return OperationResult(
                success=False,
                message="Account exists but email is not verified yet. Check your inbox and verify before logging in.",
                data={"code": "email_not_confirmed", "raw_error": raw_message, "action": action},
            )

        if "invalid login credentials" in normalized:
            return OperationResult(
                success=False,
                message="Invalid email or password.",
                data={"code": "invalid_credentials", "raw_error": raw_message, "action": action},
            )

        return OperationResult(
            success=False,
            message=f"{action.capitalize()} failed: {raw_message}",
            data={
                "code": "unknown_auth_error",
                "raw_error": raw_message,
                "action": action,
                "diagnostic": diagnostic,
            },
        )

    def sign_up(self, email: str, password: str) -> OperationResult:
        if not self.client:
            return OperationResult(
                success=False,
                message="Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to .env.",
            )

        try:
            auth_response = self._new_client().auth.sign_up({"email": email, "password": password})
            user = getattr(auth_response, "user", None)
            session = getattr(auth_response, "session", None)
            if user:
                # session is None when the project requires email confirmation first
                data = self._session_data(user, session) if session else {"user_id": str(user.id), "email": user.email}
                return OperationResult(
                    success=True,
                    message="Sign-up successful. Check your mailbox if email confirmation is enabled.",
                    data=data,
                )
            return OperationResult(success=False, message="Sign-up returned no user object.")
        except Exception as exc:
            LOGGER.exception("Supabase sign-up failed: %s | %s", exc, self._exception_metadata(exc))
            return self._auth_error_result("sign-up", exc)

    def sign_in(self, email: str, password: str) -> OperationResult:
        if not self.client:
            return OperationResult(
                success=False,
                message="Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to .env.",
            )

        try:
            auth_response = self._new_client().auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            user = getattr(auth_response, "user", None)
            session = getattr(auth_response, "session", None)

            if user and session:
                return OperationResult(
                    success=True,
                    message="Login successful.",
                    data=self._session_data(user, session),
                )

            return OperationResult(success=False, message="Invalid login response from Supabase.")
        except Exception as exc:
            LOGGER.exception("Supabase login failed: %s | %s", exc, self._exception_metadata(exc))
            return self._auth_error_result("login", exc)

    def sign_out(self, access_token: str | None) -> OperationResult:
        if not self.client:
            return OperationResult(
                success=False,
                message="Supabase is not configured.",
            )

        if not access_token:
            return OperationResult(success=True, message="Logged out.")

        try:
            # Revokes this browser's refresh token only; other sessions of the user stay signed in.
            self._new_client().auth.admin.sign_out(access_token, scope="local")
            return OperationResult(success=True, message="Logged out.")
        except Exception as exc:
            return OperationResult(success=False, message=f"Logout failed: {exc}")

    def refresh_session(self, refresh_token: str | None) -> OperationResult:
        if not self.client or not refresh_token:
            return OperationResult(success=False, message="No session to refresh.")

        try:
            auth_response = self._new_client().auth.refresh_session(refresh_token)
            user = getattr(auth_response, "user", None)
            session = getattr(auth_response, "session", None)
            if user and session:
                return OperationResult(success=True, message="Session refreshed.", data=self._session_data(user, session))
            return OperationResult(success=False, message="Invalid refresh response from Supabase.")
        except Exception as exc:
            LOGGER.warning("Supabase session refresh failed: %s | %s", exc, self._exception_metadata(exc))
            return OperationResult(success=False, message=f"Session refresh failed: {exc}")
