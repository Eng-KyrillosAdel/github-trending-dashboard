import os
import threading
import time

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dash_table, dcc, html

import scraper

REFRESH_MINUTES = int(os.environ.get("REFRESH_MINUTES", 30))
CSV_PATH = scraper.CSV_PATH


def load_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        scraper.run()
    return pd.read_csv(CSV_PATH)


def background_scraper():
    while True:
        time.sleep(REFRESH_MINUTES * 60)
        try:
            scraper.run()
        except Exception as exc:
            print("Scrape failed:", exc)


def kpi_card(card_id: str, title: str) -> html.Div:
    return html.Div(className="kpi", children=[
        html.Div(title, className="kpi-title"),
        html.Div("-", id=card_id, className="kpi-value"),
    ])


app = Dash(__name__, title="GitHub Trending Dashboard")
server = app.server

app.index_string = app.index_string.replace("</head>", """
<style>
 body{font-family:Segoe UI,Arial,sans-serif;background:#0d1117;color:#e6edf3;margin:0}
 .wrap{max-width:1200px;margin:auto;padding:20px}
 h1{margin:0 0 4px} .sub{color:#8b949e;margin-bottom:16px}
 .filters{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px}
 .filters>div{flex:1;min-width:260px;color:#111}
 .filters label{color:#e6edf3;display:block;margin-bottom:4px;font-weight:600}
 .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:16px}
 .kpi{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px}
 .kpi-title{color:#8b949e;font-size:13px} .kpi-value{font-size:24px;font-weight:700;margin-top:6px;word-break:break-word}
 .charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:12px;margin-bottom:16px}
 .card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:8px}
 @media(max-width:560px){.charts{grid-template-columns:1fr}}
</style></head>""")


df0 = load_data()

app.layout = html.Div(className="wrap", children=[
    html.H1("GitHub Trending Repositories"),
    html.Div(id="updated", className="sub"),

    html.Div(className="filters", children=[
        html.Div([html.Label("Trending period"),
                  dcc.Dropdown(id="period",
                               options=[{"label": p.title(), "value": p} for p in scraper.PERIODS],
                               value="daily", clearable=False)]),
        html.Div([html.Label("Programming language"),
                  dcc.Dropdown(id="language", multi=True, placeholder="All languages")]),
    ]),

    html.Div(className="kpis", children=[
        kpi_card("kpi-repos", "Trending repositories"),
        kpi_card("kpi-stars", "Total stars"),
        kpi_card("kpi-avg", "Average stars / repo"),
        kpi_card("kpi-lang", "Most popular language"),
        kpi_card("kpi-top", "Top repository"),
    ]),

    html.Div(className="charts", children=[
        html.Div(dcc.Graph(id="top10"), className="card"),
        html.Div(dcc.Graph(id="lang-dist"), className="card"),
        html.Div(dcc.Graph(id="scatter"), className="card"),
        html.Div(dcc.Graph(id="lang-stars"), className="card"),
    ]),

    html.Div(className="card", children=[
        dash_table.DataTable(
            id="table", page_size=10, sort_action="native",
            columns=[{"name": c.replace("_", " ").title(), "id": c} for c in
                     ["rank", "repository", "language", "stars", "forks", "stars_gained", "description"]],
            style_header={"backgroundColor": "#21262d", "color": "#e6edf3", "fontWeight": "bold"},
            style_cell={"backgroundColor": "#161b22", "color": "#e6edf3", "textAlign": "left",
                        "maxWidth": 380, "overflow": "hidden", "textOverflow": "ellipsis"},
        )]),

    dcc.Interval(id="tick", interval=60 * 1000, n_intervals=0),
])

@app.callback(Output("language", "options"), Input("period", "value"), Input("tick", "n_intervals"))

def language_options(period, _):
    d = load_data()
    langs = sorted(d.loc[d["period"] == period, "language"].unique())
    return [{"label": l, "value": l} for l in langs]

@app.callback(
    Output("kpi-repos", "children"), Output("kpi-stars", "children"), Output("kpi-avg", "children"),
    Output("kpi-lang", "children"), Output("kpi-top", "children"),
    Output("top10", "figure"), Output("lang-dist", "figure"),
    Output("scatter", "figure"), Output("lang-stars", "figure"),
    Output("table", "data"), Output("updated", "children"),
    Input("period", "value"), Input("language", "value"), Input("tick", "n_intervals"),
)

def update(period, languages, _):
    d = load_data()
    updated = f"Last scraped: {d['scraped_at'].max()}  |  Source: github.com/trending"
    d = d[d["period"] == period]
    if languages:
        d = d[d["language"].isin(languages)]

    template = "plotly_dark"
    if d.empty:
        empty = px.scatter(title="No data for this selection", template=template)
        return "0", "0", "0", "-", "-", empty, empty, empty, empty, [], updated

    top10 = d.nlargest(10, "stars").sort_values("stars")
    fig_top = px.bar(top10, x="stars", y="repository", orientation="h", color="language",
                     title="Top 10 trending repositories by stars", template=template)

    lang_counts = d["language"].value_counts().reset_index()
    lang_counts.columns = ["language", "repositories"]
    fig_lang = px.pie(lang_counts, names="language", values="repositories", hole=0.45,
                      title="Programming language distribution", template=template)

    fig_scatter = px.scatter(d, x="stars", y="stars_gained", size="forks", color="language",
                             hover_name="repository", log_x=True,
                             title=f"Stars vs stars gained ({period})", template=template)

    lang_stars = d.groupby("language", as_index=False)["stars"].sum().sort_values("stars", ascending=False)
    fig_ls = px.bar(lang_stars, x="language", y="stars", title="Total stars by language", template=template)

    top_repo = d.loc[d["stars"].idxmax(), "repository"]
    top_lang = lang_counts.iloc[0]["language"]
    return (f"{len(d):,}", f"{d['stars'].sum():,}", f"{int(d['stars'].mean()):,}",
            top_lang, top_repo, fig_top, fig_lang, fig_scatter, fig_ls,
            d.sort_values("rank").to_dict("records"), updated)


if __name__ == "__main__":

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Thread(target=background_scraper, daemon=True).start()
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
