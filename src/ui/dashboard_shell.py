"""Dashboard shell builder and page metadata."""

from __future__ import annotations

from dash import dcc, html
from dash.development.base_component import Component


PAGE_CONFIG = (
    {"key": "overview", "path": "/", "short": "MK", "label": "Market"},
    {"key": "trading", "path": "/trading", "short": "TR", "label": "Trading"},
    {"key": "portfolio", "path": "/portfolio", "short": "PF", "label": "Portfolio"},
    {"key": "watchlist", "path": "/watchlist", "short": "WL", "label": "Watchlist"},
    {"key": "alerts", "path": "/alerts", "short": "AL", "label": "Alerts"},
)


def section_shell(title: str, subtitle: str, body: Component, extra_class: str = "") -> Component:
    """Wrap feature content in consistent section chrome."""
    return html.Div(
        [
            html.Div(
                [
                    html.P("APP SECTION", className="section-eyebrow"),
                    html.H2(title, className="section-title"),
                    html.P(subtitle, className="section-subtitle"),
                ],
                className="section-headline",
            ),
            body,
        ],
        className=f"section-shell {extra_class}".strip(),
    )


def _nav_link(page: dict[str, str], active_path: str) -> Component:
    is_active = active_path == page["path"]
    class_name = "nav-link active" if is_active else "nav-link"
    return dcc.Link(
        [
            html.Span(page["short"], className="nav-link-token"),
            html.Span(page["label"], className="nav-link-label"),
        ],
        href=page["path"],
        refresh=False,
        id=f"nav-{page['key']}",
        className=class_name,
    )


def build_dashboard_layout(
    *,
    market_layout: Component,
    trading_layout: Component,
    portfolio_layout: Component,
    watchlist_layout: Component,
    alerts_layout: Component,
    auth_layout: Component,
    profile_layout: Component,
    supabase_status: str,
    default_symbol: str,
) -> Component:
    """Build main app layout from composed feature sections."""
    overview_section = section_shell(
        "Market Overview",
        "Live quote, chart, metadata, quick signals",
        html.Div(market_layout, className="feature-card market-feature-wrapper"),
    )
    trading_section = section_shell(
        "Trade Execution",
        "Place buy and sell orders with live prices and account cash",
        html.Div(trading_layout, className="feature-card secondary-card"),
    )
    portfolio_section = section_shell(
        "Portfolio Analytics",
        "Allocation, performance, holdings, and recent activity",
        html.Div(portfolio_layout, className="feature-card secondary-card"),
    )
    watchlist_section = section_shell(
        "Watchlist",
        "Track symbols, price moves, and jump back into research",
        html.Div(watchlist_layout, className="feature-card secondary-card"),
    )
    alerts_section = section_shell(
        "Price Alerts",
        "Create rules, monitor thresholds, and review triggers",
        html.Div(alerts_layout, className="feature-card secondary-card"),
    )

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("SM", className="logo-box"),
                            html.Div(
                                [
                                    html.P("Signal Market", className="sidebar-brand-title"),
                                    html.P("Trader workstation", className="sidebar-brand-subtitle"),
                                ],
                                className="sidebar-brand-copy",
                            ),
                        ],
                        className="sidebar-brand",
                    ),
                    html.Div([_nav_link(page, "/") for page in PAGE_CONFIG], className="sidebar-nav"),
                ],
                className="left-sidebar",
            ),
            html.Div(
                [
                    dcc.Location(id="app-location", refresh=False),
                    dcc.Store(id="global-user-store", storage_type="session", data={}),
                    dcc.Store(
                        id="selected-symbol-store",
                        storage_type="memory",
                        data={"symbol": default_symbol},
                    ),
                    dcc.Interval(id="workspace-status-interval", interval=45000, n_intervals=0),
                    html.Div(id="auth-user-display", style={"display": "none"}),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.P("Trading Workspace", className="topbar-label"),
                                    html.Div(
                                        [
                                            html.Span("Overview / ", className="breadcrumbs-muted"),
                                            html.Strong("Market", id="top-breadcrumb"),
                                        ],
                                        className="breadcrumbs",
                                    ),
                                ],
                                className="top-bar-copy",
                            ),
                            profile_layout,
                        ],
                        className="top-bar",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [html.Strong("SPY"), html.Span("US broad market", className="ticker-price")],
                                className="ticker-item",
                            ),
                            html.Div(
                                [html.Strong("QQQ"), html.Span("Large-cap tech", className="ticker-price")],
                                className="ticker-item",
                            ),
                            html.Div(
                                [html.Strong("VIX"), html.Span("Risk gauge", className="ticker-price")],
                                className="ticker-item",
                            ),
                            html.Div(
                                [html.Strong("DB"), html.Span(supabase_status, className="ticker-price")],
                                className="ticker-item",
                            ),
                            html.Div(
                                [html.Strong("FOCUS"), html.Span(default_symbol, className="ticker-price")],
                                className="ticker-item",
                            ),
                        ],
                        className="ticker-tape",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(overview_section, id="page-overview", className="page-pane"),
                                    html.Div(
                                        trading_section,
                                        id="page-trading",
                                        className="page-pane",
                                        style={"display": "none"},
                                    ),
                                    html.Div(
                                        portfolio_section,
                                        id="page-portfolio",
                                        className="page-pane",
                                        style={"display": "none"},
                                    ),
                                    html.Div(
                                        watchlist_section,
                                        id="page-watchlist",
                                        className="page-pane",
                                        style={"display": "none"},
                                    ),
                                    html.Div(
                                        alerts_section,
                                        id="page-alerts",
                                        className="page-pane",
                                        style={"display": "none"},
                                    ),
                                ],
                                className="market-main",
                            ),
                            html.Div(
                                [
                                    section_shell(
                                        "Account",
                                        "Supabase authentication and active session",
                                        html.Div(auth_layout, className="auth-card"),
                                        "right-shell",
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.P("APP SECTION", className="section-eyebrow"),
                                                    html.H3("Feature Status", className="section-title"),
                                                    html.P(
                                                        "What is live now, what needs login, and what needs attention",
                                                        className="section-subtitle",
                                                    ),
                                                ],
                                                className="section-headline",
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Span("Market Data", className="status-feature"),
                                                            html.Span("Checking", id="status-market", className="status-badge pending"),
                                                        ],
                                                        className="status-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Authentication", className="status-feature"),
                                                            html.Span("Checking", id="status-auth", className="status-badge pending"),
                                                        ],
                                                        className="status-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Trading", className="status-feature"),
                                                            html.Span("Checking", id="status-trading", className="status-badge pending"),
                                                        ],
                                                        className="status-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Portfolio", className="status-feature"),
                                                            html.Span("Checking", id="status-portfolio", className="status-badge pending"),
                                                        ],
                                                        className="status-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Watchlist", className="status-feature"),
                                                            html.Span("Checking", id="status-watchlist", className="status-badge pending"),
                                                        ],
                                                        className="status-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Alerts", className="status-feature"),
                                                            html.Span("Checking", id="status-alerts", className="status-badge pending"),
                                                        ],
                                                        className="status-row",
                                                    ),
                                                ],
                                                className="status-grid",
                                            ),
                                            html.P(
                                                "Status updates every 45 seconds.",
                                                id="status-note",
                                                className="status-note",
                                            ),
                                        ],
                                        className="details-card status-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.P("APP SECTION", className="section-eyebrow"),
                                                    html.H3("Live Instrument Details", className="section-title"),
                                                    html.P(
                                                        "Context panel for currently tracked symbol",
                                                        className="section-subtitle",
                                                    ),
                                                ],
                                                className="section-headline",
                                            ),
                                            html.Div(
                                                [
                                                    html.P("Company profile", id="rs-company-name"),
                                                    html.Div(
                                                        [
                                                            html.Span("Company", className="label"),
                                                            html.Span("-", id="rs-company", className="val"),
                                                        ],
                                                        className="detail-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Current Price", className="label"),
                                                            html.Span("-", id="rs-price", className="val"),
                                                        ],
                                                        className="detail-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Ticker", className="label"),
                                                            html.Span("-", id="rs-ticker", className="val"),
                                                        ],
                                                        className="detail-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Change", className="label"),
                                                            html.Span("-", id="rs-change", className="val"),
                                                        ],
                                                        className="detail-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Market Cap", className="label"),
                                                            html.Span("-", id="rs-mcap", className="val"),
                                                        ],
                                                        className="detail-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("Volume", className="label"),
                                                            html.Span("-", id="rs-volume", className="val"),
                                                        ],
                                                        className="detail-row",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span("PE Ratio", className="label"),
                                                            html.Span("-", id="rs-pe", className="val"),
                                                        ],
                                                        className="detail-row",
                                                    ),
                                                ]
                                            ),
                                        ],
                                        className="details-card",
                                    ),
                                ],
                                className="right-sidebar",
                            ),
                        ],
                        className="content-scroll-area",
                    ),
                ],
                className="main-wrapper",
            ),
        ],
        className="dashboard-layout",
    )
