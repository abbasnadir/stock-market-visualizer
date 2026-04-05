"""Supabase client and authentication service."""

from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from src.config.settings import AppSettings
from src.core.result import OperationResult


class SupabaseService:
    """Encapsulates Supabase initialization and auth operations."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.client: Client | None = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if not self.settings.has_supabase_credentials:
            return

        try:
            self.client = create_client(
                self.settings.supabase_url,
                self.settings.supabase_anon_key,
            )
        except Exception:
            self.client = None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def sign_up(self, email: str, password: str) -> OperationResult:
        if not self.client:
            return OperationResult(
                success=False,
                message="Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to .env.",
            )

        try:
            auth_response = self.client.auth.sign_up({"email": email, "password": password})
            user = getattr(auth_response, "user", None)
            if user:
                return OperationResult(
                    success=True,
                    message="Sign-up successful. Check your mailbox if email confirmation is enabled.",
                    data={"user_id": str(user.id), "email": user.email},
                )
            return OperationResult(success=False, message="Sign-up returned no user object.")
        except Exception as exc:
            return OperationResult(success=False, message=f"Sign-up failed: {exc}")

    def sign_in(self, email: str, password: str) -> OperationResult:
        if not self.client:
            return OperationResult(
                success=False,
                message="Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to .env.",
            )

        try:
            auth_response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            user = getattr(auth_response, "user", None)
            session = getattr(auth_response, "session", None)

            if user and session:
                return OperationResult(
                    success=True,
                    message="Login successful.",
                    data={
                        "user_id": str(user.id),
                        "email": user.email,
                        "access_token": session.access_token,
                    },
                )

            return OperationResult(success=False, message="Invalid login response from Supabase.")
        except Exception as exc:
            return OperationResult(success=False, message=f"Login failed: {exc}")

    def sign_out(self) -> OperationResult:
        if not self.client:
            return OperationResult(
                success=False,
                message="Supabase is not configured.",
            )

        try:
            self.client.auth.sign_out()
            return OperationResult(success=True, message="Logged out.")
        except Exception as exc:
            return OperationResult(success=False, message=f"Logout failed: {exc}")

    def get_current_user(self) -> dict[str, Any] | None:
        if not self.client:
            return None

        try:
            user_response = self.client.auth.get_user()
            user = getattr(user_response, "user", None)
            if not user:
                return None
            return {"user_id": str(user.id), "email": user.email}
        except Exception:
            return None
