"""User authentication feature with Supabase auth."""

from __future__ import annotations

import time

from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from src.features.base_feature import BaseFeature

# Access tokens last an hour; renew them when less than this is left.
TOKEN_REFRESH_MARGIN_SECONDS = 600


class AuthFeature(BaseFeature):
    """Handles login, signup, logout, and user state persistence."""

    def get_layout(self):
        return html.Section(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Secure Sign In", className="panel-title"),
                                html.P(
                                    "Use Supabase account to unlock trading, portfolio, watchlist, alerts.",
                                    className="panel-subtitle",
                                ),
                            ],
                            className="panel-copy",
                        ),
                        html.Div(
                            [
                                dcc.Input(
                                    id="auth-email-input",
                                    type="email",
                                    placeholder="Email address",
                                    className="app-input",
                                ),
                                dcc.Input(
                                    id="auth-password-input",
                                    type="password",
                                    placeholder="Password",
                                    className="app-input",
                                ),
                            ],
                            className="form-grid",
                        ),
                        html.Div(
                            [
                                html.Button("Login", id="auth-login-btn", n_clicks=0, className="primary-btn"),
                                html.Button("Create Account", id="auth-signup-btn", n_clicks=0, className="secondary-btn"),
                                html.Button("Logout", id="auth-logout-btn", n_clicks=0, className="ghost-danger-btn"),
                            ],
                            className="button-row wrap",
                        ),
                        html.Div(
                            [
                                html.P("Session status", className="status-label"),
                                html.P("Not signed in.", id="auth-message", className="status-message"),
                            ],
                            className="status-panel",
                        ),
                        dcc.Interval(id="auth-refresh-interval", interval=300000, n_intervals=0),
                    ],
                    className="auth-panel",
                )
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("auth-login-btn", "style"),
            Output("auth-signup-btn", "style"),
            Output("auth-logout-btn", "style"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def toggle_auth_buttons(user_store):
            user_store = user_store or {}
            is_logged_in = bool(user_store.get("user_id"))
            if is_logged_in:
                return {"display": "none"}, {"display": "none"}, {"display": "inline-flex"}
            return {"display": "inline-flex"}, {"display": "inline-flex"}, {"display": "none"}

        @app.callback(
            Output("auth-message", "children"),
            Output("global-user-store", "data"),
            Output("auth-user-display", "children"),
            Input("auth-login-btn", "n_clicks"),
            Input("auth-signup-btn", "n_clicks"),
            Input("auth-logout-btn", "n_clicks"),
            Input("profile-switch-btn", "n_clicks"),
            Input("profile-logout-btn", "n_clicks"),
            Input("app-location", "pathname"),
            Input("auth-refresh-interval", "n_intervals"),
            State("auth-email-input", "value"),
            State("auth-password-input", "value"),
            State("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def handle_auth(
            login_clicks,
            signup_clicks,
            logout_clicks,
            switch_clicks,
            prof_logout_clicks,
            pathname,
            refresh_ticks,
            email,
            password,
            user_store,
        ):
            del login_clicks, signup_clicks, logout_clicks, switch_clicks, prof_logout_clicks, pathname, refresh_ticks
            try:
                action = ctx.triggered_id
                user_store = user_store or {}

                if action in {"app-location", "auth-refresh-interval"}:
                    # The session lives only in this browser's store; renew its token before it expires.
                    if not user_store.get("user_id"):
                        return no_update, no_update, "Current user: not signed in"

                    email = user_store.get("email", "Signed in")
                    expires_at = float(user_store.get("expires_at") or 0)
                    if expires_at - time.time() > TOKEN_REFRESH_MARGIN_SECONDS:
                        return no_update, no_update, f"Current user: {email}"

                    refreshed = self.services.supabase_service.refresh_session(user_store.get("refresh_token"))
                    if refreshed.success:
                        return no_update, refreshed.data, f"Current user: {email}"
                    return (
                        "Session expired. Log in again.",
                        {},
                        "Current user: not signed in",
                    )

                if action in {"auth-logout-btn", "profile-logout-btn", "profile-switch-btn"}:
                    result = self.services.supabase_service.sign_out(user_store.get("access_token"))
                    if result.success:
                        return (
                            "Logged out successfully.",
                            {},
                            "Current user: not signed in",
                        )
                    return (
                        f"Logout notice: {result.message}",
                        {},
                        "Current user: not signed in",
                    )

                if not email or not password:
                    return (
                        "Email and password are required.",
                        no_update,
                        no_update,
                    )

                if action == "auth-signup-btn":
                    result = self.services.supabase_service.sign_up(email=email, password=password)
                    if result.success:
                        data = result.data or {}
                        user_id = data.get("user_id")
                        if user_id and data.get("access_token"):
                            profile_message = ""
                            profile_result = self.services.portfolio_repository.for_session(data).ensure_user_profile(
                                user_id, email=email
                            )
                            if not profile_result.success:
                                profile_message = f" Profile setup issue: {profile_result.message}"
                            return (
                                f"{result.message}{profile_message}",
                                data,
                                f"Current user: {data.get('email', email)}",
                            )
                        return (
                            f"{result.message} Sign in after verification if required.",
                            {},
                            "Current user: not signed in",
                        )

                    result_data = result.data or {}
                    error_code = result_data.get("code")
                    if error_code == "database_error_saving_new_user":
                        diagnostic = result_data.get("diagnostic")
                        diagnostic_text = f" Diagnostic: {diagnostic}" if diagnostic else ""
                        return (
                            (
                                f"{result.message}"
                                " Quick check: if you created a trigger on auth.users to insert into profiles, "
                                "ensure it runs with SECURITY DEFINER and RLS policies allow the insert."
                                f"{diagnostic_text}"
                            ),
                            no_update,
                            no_update,
                        )

                    if error_code in {"email_rate_limit", "user_exists"}:
                        login_result = self.services.supabase_service.sign_in(email=email, password=password)
                        if login_result.success:
                            login_data = login_result.data or {}
                            user_id = login_data.get("user_id")
                            resolved_email = login_data.get("email", email)
                            profile_message = ""
                            if user_id:
                                profile_result = self.services.portfolio_repository.for_session(login_data).ensure_user_profile(
                                    user_id, email=resolved_email
                                )
                                if not profile_result.success:
                                    profile_message = f" Profile setup issue: {profile_result.message}"
                            return (
                                f"{result.message} Logged in with existing account.{profile_message}",
                                login_data,
                                f"Current user: {resolved_email}",
                            )
                        return (
                            f"{result.message} Auto-login attempt also failed: {login_result.message}",
                            no_update,
                            no_update,
                        )

                    return (result.message, no_update, no_update)

                if action == "auth-login-btn":
                    result = self.services.supabase_service.sign_in(email=email, password=password)
                    if result.success:
                        data = result.data or {}
                        user_id = data.get("user_id")
                        resolved_email = data.get("email", email)
                        profile_message = ""
                        if user_id:
                            profile_result = self.services.portfolio_repository.for_session(data).ensure_user_profile(
                                user_id, email=resolved_email
                            )
                            if not profile_result.success:
                                profile_message = f" Profile setup issue: {profile_result.message}"
                        return (
                            f"{result.message}{profile_message}",
                            data,
                            f"Current user: {resolved_email}",
                        )
                    return (result.message, no_update, no_update)

                return no_update, no_update, no_update
            except Exception as exc:
                return f"Authentication error: {exc}", no_update, no_update
