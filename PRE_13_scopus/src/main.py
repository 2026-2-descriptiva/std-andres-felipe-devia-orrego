"""Análisis bibliométrico de registros de Scopus sobre PropTech.

Genera, en `submission/`, las tablas de frecuencia, las matrices de
co-ocurrencia, los clústeres de países y palabras clave, y los gráficos
interactivos (HTML) del corpus.
"""

import itertools
import os
import shutil
from collections import Counter
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

FOLDER = Path(__file__).resolve().parents[1]
INPUT_FILE = FOLDER / "data" / "scopus.csv.gz"
OUTPUT_DIR = FOLDER / "submission"

TOP_COUNTRIES = 25
TOP_KEYWORDS = 30
PLOTLY_JS = "cdn"

#: Países esperados en el campo `Affiliations` de Scopus.
COUNTRIES = {
    "Algeria", "Australia", "Austria", "Bahrain", "Belarus", "Belgium",
    "Brazil", "Bulgaria", "Canada", "Chile", "China", "Colombia", "Costa Rica",
    "Croatia", "Cyprus", "Czech Republic", "Denmark", "Ecuador", "Egypt",
    "Estonia", "Ethiopia", "Finland", "France", "Germany", "Ghana", "Greece",
    "Hong Kong", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq",
    "Ireland", "Israel", "Italy", "Japan", "Jordan", "Kazakhstan", "Kenya",
    "Kuwait", "Latvia", "Lebanon", "Lithuania", "Luxembourg", "Macao",
    "Malaysia", "Malta", "Mexico", "Morocco", "Nepal", "Netherlands",
    "New Zealand", "Nigeria", "North Macedonia", "Norway", "Oman", "Pakistan",
    "Palestine", "Peru", "Philippines", "Poland", "Portugal", "Qatar",
    "Romania", "Russian Federation", "Saudi Arabia", "Serbia", "Singapore",
    "Slovakia", "Slovenia", "South Africa", "South Korea", "Spain",
    "Sri Lanka", "Sweden", "Switzerland", "Taiwan", "Tanzania", "Thailand",
    "Tunisia", "Turkey", "Uganda", "Ukraine", "United Arab Emirates",
    "United Kingdom", "United States", "Uruguay", "Viet Nam", "Zimbabwe",
}

#: Variantes encontradas en los datos y su nombre canónico.
COUNTRY_ALIASES = {
    "USA": "United States",
    "U.S.A.": "United States",
    "United States of America": "United States",
    "UK": "United Kingdom",
    "England": "United Kingdom",
    "Scotland": "United Kingdom",
    "Wales": "United Kingdom",
    "Korea": "South Korea",
    "Republic of Korea": "South Korea",
    "Vietnam": "Viet Nam",
    "Russia": "Russian Federation",
    "Macau": "Macao",
    "UAE": "United Arab Emirates",
    "Czechia": "Czech Republic",
}

#: Nombres que entiende el `locationmode="country names"` de Plotly.
PLOTLY_COUNTRY_NAMES = {
    "Russian Federation": "Russia",
    "Viet Nam": "Vietnam",
    "South Korea": "South Korea",
    "United States": "United States",
    "United Kingdom": "United Kingdom",
}


# ---------------------------------------------------------------------------
# Carga y normalización
# ---------------------------------------------------------------------------


def split_field(value, separator=";"):
    """Divide un campo multivaluado de Scopus en una lista limpia."""
    if pd.isna(value):
        return []
    items = [item.strip() for item in str(value).split(separator)]
    return [item for item in items if item and item.lower() != "nan"]


def extract_countries(affiliations):
    """País de cada afiliación: último componente de cada dirección."""
    countries = []
    for affiliation in split_field(affiliations):
        token = affiliation.split(",")[-1].strip().rstrip(".")
        token = COUNTRY_ALIASES.get(token, token)
        if token in COUNTRIES:
            countries.append(token)
    return sorted(set(countries))


def normalize_keyword(keyword):
    return keyword.strip().lower()


def load_data():
    df = pd.read_csv(INPUT_FILE)
    df["authors_list"] = df["Authors"].map(
        lambda value: [
            author
            for author in split_field(value)
            if author.lower() not in ("[no author name available]",)
        ]
    )
    df["countries_list"] = df["Affiliations"].map(extract_countries)
    df["keywords_list"] = [
        sorted(
            {
                normalize_keyword(keyword)
                for keyword in split_field(author_kw) + split_field(index_kw)
            }
        )
        for author_kw, index_kw in zip(df["Author Keywords"], df["Index Keywords"])
    ]
    return df


# ---------------------------------------------------------------------------
# Tablas de frecuencia
# ---------------------------------------------------------------------------


def frequency_table(df, column, label, cited_column="Cited by"):
    """Frecuencia de un campo multivaluado, con citaciones asociadas."""
    counts = Counter()
    citations = Counter()
    for items, cited in zip(df[column], df[cited_column].fillna(0)):
        for item in items:
            counts[item] += 1
            citations[item] += cited
    table = pd.DataFrame(
        {
            label: list(counts.keys()),
            "documents": list(counts.values()),
            "citations": [citations[item] for item in counts],
        }
    )
    table["share"] = (table["documents"] / len(df)).round(4)
    table["avg_citations"] = (table["citations"] / table["documents"]).round(2)
    table = table.sort_values(
        ["documents", "citations"], ascending=False
    ).reset_index(drop=True)
    table["rank"] = table.index + 1
    return table


def source_frequency(df):
    table = (
        df.groupby("Source title")
        .agg(
            documents=("Title", "count"),
            citations=("Cited by", "sum"),
            first_year=("Year", "min"),
            last_year=("Year", "max"),
        )
        .reset_index()
        .rename(columns={"Source title": "source"})
    )
    table["share"] = (table["documents"] / len(df)).round(4)
    table["avg_citations"] = (table["citations"] / table["documents"]).round(2)
    table = table.sort_values(
        ["documents", "citations"], ascending=False
    ).reset_index(drop=True)
    table["rank"] = table.index + 1
    return table


def documents_by_year(df):
    table = (
        df.groupby("Year")
        .agg(documents=("Title", "count"), citations=("Cited by", "sum"))
        .reset_index()
        .sort_values("Year")
    )
    table["cumulative_documents"] = table["documents"].cumsum()
    return table


# ---------------------------------------------------------------------------
# Co-ocurrencia y clústeres
# ---------------------------------------------------------------------------


def cooccurrence_matrix(df, column, top_items):
    """Matriz simétrica de co-ocurrencia; la diagonal es la frecuencia."""
    index = list(top_items)
    matrix = pd.DataFrame(0, index=index, columns=index, dtype=int)
    position = set(index)
    for items in df[column]:
        present = [item for item in items if item in position]
        for item in present:
            matrix.loc[item, item] += 1
        for left, right in itertools.combinations(sorted(present), 2):
            matrix.loc[left, right] += 1
            matrix.loc[right, left] += 1
    matrix.index.name = column.replace("_list", "")
    return matrix


def build_network(matrix, min_weight=1):
    """Grafo no dirigido ponderado a partir de la matriz de co-ocurrencia."""
    graph = nx.Graph()
    for item in matrix.index:
        graph.add_node(item, frequency=int(matrix.loc[item, item]))
    for left, right in itertools.combinations(matrix.index, 2):
        weight = int(matrix.loc[left, right])
        if weight >= min_weight:
            graph.add_edge(left, right, weight=weight)
    return graph


def detect_clusters(graph):
    """Comunidades por modularidad, ordenadas por tamaño."""
    if graph.number_of_edges() == 0:
        return [sorted(graph.nodes())]
    communities = nx.community.greedy_modularity_communities(
        graph, weight="weight"
    )
    clusters = [
        sorted(community, key=lambda node: -graph.nodes[node]["frequency"])
        for community in communities
    ]
    return sorted(clusters, key=len, reverse=True)


def write_clusters(clusters, graph, path, title):
    lines = [title, "=" * len(title), ""]
    if graph.number_of_edges():
        modularity = nx.community.modularity(
            graph, [set(cluster) for cluster in clusters], weight="weight"
        )
        lines.append(f"Nodos: {graph.number_of_nodes()}")
        lines.append(f"Enlaces: {graph.number_of_edges()}")
        lines.append(f"Clusters: {len(clusters)}")
        lines.append(f"Modularidad: {modularity:.4f}")
        lines.append("")
    for number, cluster in enumerate(clusters, start=1):
        lines.append(f"Cluster {number} ({len(cluster)} elementos)")
        for item in cluster:
            lines.append(f"  - {item} ({graph.nodes[item]['frequency']})")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------


def save_figure(figure, name):
    figure.write_html(
        OUTPUT_DIR / name, include_plotlyjs=PLOTLY_JS, full_html=True
    )


def plot_documents_by_year(by_year):
    figure = go.Figure()
    figure.add_bar(
        x=by_year["Year"], y=by_year["documents"], name="Documentos por año"
    )
    figure.add_scatter(
        x=by_year["Year"],
        y=by_year["cumulative_documents"],
        name="Acumulado",
        mode="lines+markers",
        yaxis="y2",
    )
    figure.update_layout(
        title="Producción científica por año",
        xaxis_title="Año",
        yaxis_title="Documentos",
        yaxis2=dict(title="Acumulado", overlaying="y", side="right"),
        template="plotly_white",
    )
    save_figure(figure, "documents_by_year.html")


def plot_country_frequency(countries, top_n=TOP_COUNTRIES):
    top = countries.head(top_n).sort_values("documents")
    figure = px.bar(
        top,
        x="documents",
        y="country",
        orientation="h",
        color="avg_citations",
        color_continuous_scale="Blues",
        title=f"Top {top_n} países por número de documentos",
        labels={
            "documents": "Documentos",
            "country": "País",
            "avg_citations": "Citaciones promedio",
        },
    )
    figure.update_layout(template="plotly_white", height=750)
    save_figure(figure, "country_frequency_plot.html")


def plot_world_map(countries):
    data = countries.copy()
    data["map_country"] = data["country"].replace(PLOTLY_COUNTRY_NAMES)
    figure = px.choropleth(
        data,
        locations="map_country",
        locationmode="country names",
        color="documents",
        hover_name="country",
        hover_data={"documents": True, "citations": True, "avg_citations": True},
        color_continuous_scale="Viridis",
        title="Distribución geográfica de la producción científica",
    )
    figure.update_layout(template="plotly_white")
    save_figure(figure, "world_map.html")


def plot_heatmap(matrix, name, title):
    data = matrix.copy()
    for item in data.index:
        data.loc[item, item] = 0
    figure = px.imshow(
        data,
        color_continuous_scale="Blues",
        aspect="auto",
        title=title,
        labels=dict(color="Co-ocurrencias"),
    )
    figure.update_layout(template="plotly_white", height=850)
    save_figure(figure, name)


def plot_network(graph, clusters, name, title, min_weight=1):
    """Dibuja el grafo con layout de resorte, coloreando por clúster."""
    edges = [
        (left, right, data)
        for left, right, data in graph.edges(data=True)
        if data["weight"] >= min_weight
    ]
    drawn = nx.Graph()
    drawn.add_nodes_from(graph.nodes(data=True))
    drawn.add_edges_from(edges)

    positions = nx.spring_layout(drawn, weight="weight", seed=42, k=0.8)
    cluster_of = {
        node: number
        for number, cluster in enumerate(clusters, start=1)
        for node in cluster
    }

    edge_x, edge_y = [], []
    for left, right, _ in edges:
        edge_x += [positions[left][0], positions[right][0], None]
        edge_y += [positions[left][1], positions[right][1], None]

    figure = go.Figure()
    figure.add_scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=0.6, color="#b0b0b0"),
        hoverinfo="skip",
        showlegend=False,
    )
    frequencies = [drawn.nodes[node]["frequency"] for node in drawn.nodes]
    max_frequency = max(frequencies) if frequencies else 1
    figure.add_scatter(
        x=[positions[node][0] for node in drawn.nodes],
        y=[positions[node][1] for node in drawn.nodes],
        mode="markers+text",
        text=list(drawn.nodes),
        textposition="top center",
        marker=dict(
            size=[
                10 + 35 * drawn.nodes[node]["frequency"] / max_frequency
                for node in drawn.nodes
            ],
            color=[cluster_of.get(node, 0) for node in drawn.nodes],
            colorscale="Turbo",
            line=dict(width=1, color="white"),
        ),
        hovertext=[
            f"{node}<br>Frecuencia: {drawn.nodes[node]['frequency']}"
            f"<br>Cluster: {cluster_of.get(node, 0)}"
            for node in drawn.nodes
        ],
        hoverinfo="text",
        showlegend=False,
    )
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=850,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    save_figure(figure, name)


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    shutil.copyfile(INPUT_FILE, OUTPUT_DIR / "scopus.csv.gz")

    df = load_data()

    authors = frequency_table(df, "authors_list", "author")
    countries = frequency_table(df, "countries_list", "country")
    keywords = frequency_table(df, "keywords_list", "keyword")
    sources = source_frequency(df)
    by_year = documents_by_year(df)

    authors.to_csv(OUTPUT_DIR / "authors_frequency.csv", index=False)
    countries.to_csv(OUTPUT_DIR / "country_frequency.csv", index=False)
    keywords.to_csv(OUTPUT_DIR / "keywords_frequency.csv", index=False)
    sources.to_csv(OUTPUT_DIR / "source_frequency.csv", index=False)

    country_matrix = cooccurrence_matrix(
        df, "countries_list", countries.head(TOP_COUNTRIES)["country"]
    )
    keyword_matrix = cooccurrence_matrix(
        df, "keywords_list", keywords.head(TOP_KEYWORDS)["keyword"]
    )
    country_matrix.to_csv(OUTPUT_DIR / "country_cooc_matrix.csv")
    keyword_matrix.to_csv(OUTPUT_DIR / "keywords_cooc_matrix.csv")

    country_graph = build_network(country_matrix)
    keyword_graph = build_network(keyword_matrix)
    country_clusters = detect_clusters(country_graph)
    keyword_clusters = detect_clusters(keyword_graph)

    write_clusters(
        country_clusters,
        country_graph,
        OUTPUT_DIR / "country_clusters.txt",
        "Clusters de colaboracion entre paises",
    )
    write_clusters(
        keyword_clusters,
        keyword_graph,
        OUTPUT_DIR / "keywords_clusters.txt",
        "Clusters tematicos de palabras clave",
    )

    plot_documents_by_year(by_year)
    plot_country_frequency(countries)
    plot_world_map(countries)
    plot_heatmap(
        country_matrix,
        "country_cooc_heatmap.html",
        f"Co-ocurrencia de paises (top {TOP_COUNTRIES})",
    )
    plot_network(
        country_graph,
        country_clusters,
        "country_collab_network.html",
        "Red de colaboracion internacional",
    )
    plot_network(
        keyword_graph,
        keyword_clusters,
        "keywords_cooc_network.html",
        f"Red de co-ocurrencia de palabras clave (top {TOP_KEYWORDS})",
        min_weight=2,
    )


if __name__ == "__main__":
    main()
