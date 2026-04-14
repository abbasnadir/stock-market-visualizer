"""User authentication feature with Supabase auth."""

from __future__ import annotations

from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from src.features.base_feature import BaseFeature


class AuthFeature(BaseFeature):
    """Handles login, signup, logout, and user state persistence."""

    def get_layout(self):
        return html.Section(
            [
                html.H2("User Authentication"),
                html.Div(
                    [
                        dcc.Input(
                            id="auth-email-input",
                            type="email",
                            placeholder="Email",
                            style={"marginRight": "8px"},
                        ),
                        dcc.Input(
                            id="auth-password-input",
                            type="password",
                            placeholder="Password",
                            style={"marginRight": "8px"},
                        ),
                        html.Button("Login", id="auth-login-btn", n_clicks=0),
                        html.Button(
                            "Sign Up",
                            id="auth-signup-btn",
                            n_clicks=0,
                            style={"marginLeft": "8px"},
                        ),
                        html.Button(
                            "Logout",
                            id="auth-logout-btn",
                            n_clicks=0,
                            style={"marginLeft": "8px"},
                        ),
                    ],
                    style={"display": "flex", "flexWrap": "wrap", "gap": "8px"},
                ),
                html.P(id="auth-message", style={"marginTop": "10px"}),
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("auth-message", "children"),
            Output("global-user-store", "data"),
            Output("auth-user-display", "children"),
            Input("auth-login-btn", "n_clicks"),
            Input("auth-signup-btn", "n_clicks"),
            Input("auth-logout-btn", "n_clicks"),
            Input("profile-switch-btn", "n_clicks"),
            Input("profile-logout-btn", "n_clicks"),
            State("auth-email-input", "value"),
            State("auth-password-input", "value"),
            State("global-user-store", "data"),
            prevent_initial_call=True,
        )
        def handle_auth(login_clicks, signup_clicks, logout_clicks, switch_clicks, prof_logout_clicks, email, password, user_store):
            del login_clicks, signup_clicks, logout_clicks, switch_clicks, prof_logout_clicks

            action = ctx.triggered_id
            user_store = user_store or {}

            if action in {"auth-logout-btn", "profile-logout-btn", "profile-switch-btn"}:
                result = self.services.supabase_service.sign_out()
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
                    if user_id:
                        self.services.portfolio_repository.ensure_user_profile(user_id, email=email)
                    return (
                        result.message,
                        {"user_id": user_id, "email": email},
                        f"Current user: {email}",
                    )
                return (result.message, no_update, no_update)

            if action == "auth-login-btn":
                result = self.services.supabase_service.sign_in(email=email, password=password)
                if result.success:
                    data = result.data or {}
                    user_id = data.get("user_id")
                    resolved_email = data.get("email", email)
                    if user_id:
                        self.services.portfolio_repository.ensure_user_profile(user_id, email=resolved_email)
                    return (
                        result.message,
                        {"user_id": user_id, "email": resolved_email},
                        f"Current user: {resolved_email}",
                    )
                return (result.message, no_update, no_update)

            return no_update, no_update, no_update
