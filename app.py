from pathlib import Path
import html
import json
import unicodedata

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "outputs" / "dataset_mapa_testigos_por_puesto_templo.csv"
MASTER_PATH = ROOT / "outputs" / "tabla_maestra_puestos_votacion_bogota.csv"
LOCALIDADES_PATH = ROOT / "localidades_bogota_ideca.geojson"


st.set_page_config(
    page_title="Dashboard Testigos Bogotá",
    page_icon="📍",
    layout="wide",
)


@st.cache_data
def load_data():
    fact = pd.read_csv(DATA_PATH)
    master = pd.read_csv(MASTER_PATH)
    for df in (fact, master):
        df["localidad"] = df["localidad"].fillna("Pendiente validación")
        for col in [
            "total_testigos",
            "lideres_activos",
            "beneficiarios_mesas_trabajo",
            "referidos_activos_lideres",
            "lideres_ref_0",
            "lideres_ref_1_5",
            "lideres_ref_6_9",
            "lideres_ref_10_mas",
        ]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    fact["zona_operativa"] = fact["zona_operativa"].fillna("Sin zona")
    fact["templo_sector"] = fact["templo_sector"].fillna("Sin templo")
    return fact, master


@st.cache_data
def load_localidades():
    data = json.loads(LOCALIDADES_PATH.read_text(encoding="utf-8"))
    for feature in data["features"]:
        feature["properties"]["localidad_norm"] = feature["properties"]["LOCNOMBRE"].title()
        feature["properties"]["localidad_match"] = norm_name(feature["properties"]["LOCNOMBRE"])
    return data


def format_int(value):
    return f"{int(value):,}".replace(",", ".")


def pct(part, whole):
    if whole == 0:
        return "0,0%"
    return f"{part / whole * 100:.1f}%".replace(".", ",")


def norm_name(value):
    text = str(value or "").upper().strip()
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    if text.startswith("LOS "):
        text = text[4:]
    return text


def metric_card(label, value, detail=None):
    detail = detail or ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_chart(chart):
    return (
        chart.configure(background="#ffffff")
        .configure_view(strokeWidth=0, fill="#ffffff")
        .configure_axis(
            labelColor="#243247",
            titleColor="#243247",
            gridColor="#edf1f6",
            domainColor="#cbd3df",
            tickColor="#cbd3df",
            labelFontSize=12,
            titleFontSize=12,
        )
        .configure_legend(
            labelColor="#243247",
            titleColor="#243247",
            orient="top",
            labelFontSize=12,
            titleFontSize=12,
        )
    )


def rank_overlay_chart(data, label_col, height=360):
    chart_data = data.reset_index().rename(columns={label_col: "Categoría"}).copy()
    chart_data = chart_data.sort_values("Testigos", ascending=False)
    chart_data["Etiqueta"] = chart_data.apply(
        lambda row: f"{format_int(row['Testigos'])} | {format_int(row['Lideres'])}",
        axis=1,
    )
    order = chart_data["Categoría"].tolist()
    x_max = max(int(chart_data["Testigos"].max() * 1.42), 1) if not chart_data.empty else 1

    base = alt.Chart(chart_data).encode(
        y=alt.Y(
            "Categoría:N",
            sort=order,
            title=None,
            axis=alt.Axis(labelLimit=240, labelPadding=8),
        )
    )
    total_bar = base.mark_bar(cornerRadiusEnd=3, color="#d88445", opacity=0.9).encode(
        x=alt.X("Testigos:Q", title=None, scale=alt.Scale(domain=[0, x_max])),
        tooltip=[
            "Categoría:N",
            alt.Tooltip("Testigos:Q", format=","),
            alt.Tooltip("Lideres:Q", title="Líderes", format=","),
            alt.Tooltip("Referidos:Q", format=","),
        ],
    )
    leader_bar = base.mark_bar(cornerRadiusEnd=3, color="#39789e", opacity=0.95, size=11).encode(
        x=alt.X("Lideres:Q", title=None, scale=alt.Scale(domain=[0, x_max]))
    )
    labels = base.mark_text(
        align="left",
        dx=5,
        color="#243247",
        fontSize=10,
        fontWeight="bold",
    ).encode(
        x=alt.X("Testigos:Q", title=None, scale=alt.Scale(domain=[0, x_max])),
        text="Etiqueta:N",
    )
    chart = (total_bar + leader_bar + labels).properties(height=height, background="#ffffff")
    return clean_chart(chart)


st.markdown(
    """
    <style>
    .stApp {
        background: #f6f7f9;
        color: #18212b;
    }
    [data-testid="stHeader"] {
        background: rgba(246, 247, 249, 0.92);
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        letter-spacing: 0;
    }
    .headline {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        border-bottom: 1px solid #d8dee8;
        padding-bottom: 0.9rem;
        margin-bottom: 0.95rem;
    }
    .headline h1 {
        font-size: 1.55rem;
        margin: 0;
        color: #18212b;
    }
    .headline p {
        margin: 0.2rem 0 0;
        color: #344255;
        font-size: 0.92rem;
    }
    .source-pill {
        border: 1px solid #cbd3df;
        border-radius: 999px;
        padding: 0.35rem 0.7rem;
        color: #243247;
        font-size: 0.8rem;
        white-space: nowrap;
        background: #ffffff;
    }
    .metric-card {
        border: 1px solid #d8dee8;
        border-radius: 8px;
        padding: 0.95rem 1rem;
        background: #ffffff;
        min-height: 112px;
        box-shadow: 0 6px 20px rgba(35, 50, 70, 0.06);
    }
    .metric-label {
        color: #40506a;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        min-height: 34px;
    }
    .metric-value {
        color: #111923;
        font-size: 1.65rem;
        font-weight: 700;
        line-height: 1.1;
        margin-top: 0.2rem;
    }
    .metric-detail {
        color: #53647b;
        font-size: 0.82rem;
        margin-top: 0.35rem;
        font-weight: 600;
    }
    .section-title {
        color: #18212b;
        font-size: 1rem;
        font-weight: 700;
        margin: 0.25rem 0 0.65rem;
    }
    .stDataFrame {
        border: 1px solid #d8dee8;
        border-radius: 8px;
    }
    div[data-testid="stMultiSelect"] label,
    div[data-testid="stSelectbox"] label {
        color: #1e2b3f;
        font-weight: 700;
    }
    div[data-baseweb="select"] > div {
        border-color: #cbd3df;
        background-color: #ffffff;
    }
    div[data-baseweb="select"] * {
        color: #243247 !important;
    }
    .rank-table {
        width: 100%;
        border-collapse: collapse;
        background: #ffffff;
        border: 1px solid #d8dee8;
        border-radius: 8px;
        overflow: hidden;
        font-size: 0.86rem;
    }
    .rank-table th {
        background: #eef2f7;
        color: #243247;
        text-align: left;
        padding: 0.55rem 0.65rem;
        border-bottom: 1px solid #d8dee8;
        font-weight: 700;
    }
    .rank-table td {
        color: #243247;
        padding: 0.5rem 0.65rem;
        border-bottom: 1px solid #edf1f6;
        vertical-align: top;
    }
    .rank-table tr:last-child td {
        border-bottom: none;
    }
    .rank-table td.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
    }
    .insight-box {
        border: 1px solid #cbd3df;
        border-left: 4px solid #2b7197;
        background: #ffffff;
        border-radius: 8px;
        padding: 0.75rem 0.9rem;
        margin: 0.65rem 0 0.2rem;
        color: #243247;
        font-size: 0.9rem;
        line-height: 1.45;
    }
    .insight-box strong {
        color: #111923;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


fact, master = load_data()
localidades_geojson = load_localidades()

st.markdown(
    """
    <div class="headline">
        <div>
            <h1>Dashboard Estratégico de Testigos Bogotá</h1>
            <p>Distribución espacial, concentración por puesto y fuerza de liderazgo.</p>
        </div>
        <div class="source-pill">Corte 30/04/2026</div>
    </div>
    """,
    unsafe_allow_html=True,
)

filter_col1, filter_col2, filter_col3 = st.columns([0.8, 1.35, 1.8])
zonas = sorted(fact["zona_operativa"].dropna().unique())
with filter_col1:
    zona_choice = st.selectbox("Zona", ["Todas"] + zonas)
zona_filter = zonas if zona_choice == "Todas" else [zona_choice]

after_zona = fact[fact["zona_operativa"].isin(zona_filter)]
localidades = sorted(after_zona["localidad"].dropna().unique())
with filter_col2:
    localidad_selected = st.multiselect(
        "Localidad",
        localidades,
        default=[],
        placeholder="Todas las localidades",
    )
localidad_filter = localidades if not localidad_selected else localidad_selected

after_localidad = after_zona[after_zona["localidad"].isin(localidad_filter)]
templos = sorted(after_localidad["templo_sector"].dropna().unique())
with filter_col3:
    templo_selected = st.multiselect(
        "Templo / sector (estructura)",
        templos,
        default=[],
        placeholder="Todos los templos / sectores",
    )
templo_filter = templos if not templo_selected else templo_selected

st.caption("Los puestos sin coordenadas quedan fuera del mapa, pero sí cuentan en los indicadores.")

if templo_selected and not localidad_selected:
    st.markdown(
        """
        <div class="insight-box">
            <strong>Lectura del filtro:</strong> “Templo / sector” corresponde a la estructura organizativa
            de origen, no a la localidad geográfica del puesto de votación. Por eso un sector como
            <strong>KENNEDY</strong> puede tener testigos votando en puestos de Kennedy y también en otras
            localidades. Para ver solo puestos dentro de una localidad, usa el filtro <strong>Localidad</strong>.
        </div>
        """,
        unsafe_allow_html=True,
    )


filtered = fact[
    fact["zona_operativa"].isin(zona_filter)
    & fact["localidad"].isin(localidad_filter)
    & fact["templo_sector"].isin(templo_filter)
].copy()

total_testigos = int(filtered["total_testigos"].sum())
lideres_activos = int(filtered["lideres_activos"].sum())
beneficiarios = int(filtered["beneficiarios_mesas_trabajo"].sum())
referidos_activos = int(filtered["referidos_activos_lideres"].sum())
geocoded_testigos = int(filtered.loc[filtered["latitud"].notna() & filtered["longitud"].notna(), "total_testigos"].sum())

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Total testigos", format_int(total_testigos), f"{pct(geocoded_testigos, total_testigos)} geocodificados")
with col2:
    metric_card("Líderes activos", format_int(lideres_activos), f"{pct(lideres_activos, total_testigos)} del total filtrado")
with col3:
    metric_card("Beneficiarios mesas de trabajo", format_int(beneficiarios), f"{pct(beneficiarios, total_testigos)} del total filtrado")
with col4:
    avg_refs = referidos_activos / lideres_activos if lideres_activos else 0
    metric_card("Referidos activos de líderes", format_int(referidos_activos), f"{avg_refs:.1f} promedio por líder".replace(".", ","))

st.markdown("")

map_data = (
    filtered.dropna(subset=["latitud", "longitud"])
    .groupby(
        [
            "codigo_puesto_unico",
            "nombre_puesto_dashboard",
            "localidad",
            "direccion",
            "latitud",
            "longitud",
        ],
        dropna=False,
    )
    .agg(
        total_testigos=("total_testigos", "sum"),
        lideres_activos=("lideres_activos", "sum"),
        beneficiarios_mesas_trabajo=("beneficiarios_mesas_trabajo", "sum"),
        referidos_activos_lideres=("referidos_activos_lideres", "sum"),
    )
    .reset_index()
)

if not map_data.empty:
    max_testigos = max(int(map_data["total_testigos"].max()), 1)
    map_data["radio"] = 55 + (map_data["total_testigos"] / max_testigos) * 420
    map_data["color"] = map_data["total_testigos"].apply(
        lambda value: [168, 56, 74, 180]
        if value >= 40
        else ([219, 124, 54, 170] if value >= 20 else [43, 113, 151, 165])
    )

    center_lat = float(map_data["latitud"].mean())
    center_lon = float(map_data["longitud"].mean())
    selected_localidades = (
        {norm_name(localidad) for localidad in localidad_filter}
        if len(localidad_filter) < len(localidades)
        else set()
    )
    locality_features = [
        feature
        for feature in localidades_geojson["features"]
        if feature["properties"]["localidad_match"] in selected_localidades
    ]
    layers = [
        pdk.Layer(
            "GeoJsonLayer",
            data=localidades_geojson,
            stroked=True,
            filled=False,
            get_line_color=[36, 56, 82, 110],
            get_line_width=55,
            line_width_min_pixels=1,
            pickable=False,
        )
    ]
    if locality_features:
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data={"type": "FeatureCollection", "features": locality_features},
                stroked=True,
                filled=True,
                get_fill_color=[36, 148, 142, 42],
                get_line_color=[24, 107, 134, 235],
                get_line_width=120,
                line_width_min_pixels=3,
                pickable=False,
            )
        )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position="[longitud, latitud]",
        get_radius="radio",
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
    )
    layers.append(layer)
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=10.6,
            pitch=0,
        ),
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip={
            "html": """
                <b>{nombre_puesto_dashboard}</b><br/>
                Localidad: {localidad}<br/>
                Dirección: {direccion}<br/>
                Testigos: {total_testigos}<br/>
                Líderes activos: {lideres_activos}<br/>
                Benef. mesas trabajo: {beneficiarios_mesas_trabajo}<br/>
                Referidos activos: {referidos_activos_lideres}
            """,
            "style": {"backgroundColor": "#18212b", "color": "white"},
        },
    )
    st.markdown('<div class="section-title">Mapa de concentración por puesto de votación</div>', unsafe_allow_html=True)
    st.pydeck_chart(deck, use_container_width=True, height=560)
else:
    st.warning("No hay puestos geocodificados para los filtros seleccionados.")

coverage_note = pct(geocoded_testigos, total_testigos)
st.caption(f"El mapa representa {format_int(geocoded_testigos)} testigos geocodificados ({coverage_note} del filtro actual).")

if templo_selected:
    locality_mix = (
        filtered.groupby("localidad", dropna=False)
        .agg(Testigos=("total_testigos", "sum"), Puestos=("codigo_puesto_unico", "nunique"))
        .sort_values("Testigos", ascending=False)
        .reset_index()
    )
    locality_mix["%"] = locality_mix["Testigos"].apply(lambda value: pct(value, total_testigos))
    mix_rows = []
    for _, row in locality_mix.head(8).iterrows():
        mix_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['localidad']))}</td>"
            f"<td class='num'>{format_int(row['Testigos'])}</td>"
            f"<td class='num'>{row['%']}</td>"
            f"<td class='num'>{format_int(row['Puestos'])}</td>"
            "</tr>"
        )
    st.markdown(
        f"""
        <div class="section-title">Distribución geográfica del templo / sector seleccionado</div>
        <table class="rank-table">
            <thead>
                <tr>
                    <th>Localidad de votación</th>
                    <th>Testigos</th>
                    <th>%</th>
                    <th>Puestos</th>
                </tr>
            </thead>
            <tbody>
                {''.join(mix_rows)}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

left, right = st.columns([1.05, 0.95])

with left:
    st.markdown('<div class="section-title">Líderes por referidos activos</div>', unsafe_allow_html=True)
    ref_summary = pd.DataFrame(
        [
            {"Categoría": "0", "Líderes": int(filtered["lideres_ref_0"].sum())},
            {"Categoría": "1 a 5", "Líderes": int(filtered["lideres_ref_1_5"].sum())},
            {"Categoría": "6 a 9", "Líderes": int(filtered["lideres_ref_6_9"].sum())},
            {"Categoría": "10 o más", "Líderes": int(filtered["lideres_ref_10_mas"].sum())},
        ]
    )
    ref_summary["% líderes activos"] = ref_summary["Líderes"].apply(
        lambda value: value / lideres_activos * 100 if lideres_activos else 0
    )
    ref_summary["Etiqueta"] = ref_summary.apply(
        lambda row: f"{format_int(row['Líderes'])} ({row['% líderes activos']:.1f}%)".replace(".", ","),
        axis=1,
    )
    ref_order = ["0", "1 a 5", "6 a 9", "10 o más"]
    ref_x_max = max(int(ref_summary["Líderes"].max() * 1.22), 1)
    ref_chart = (
        alt.Chart(ref_summary)
        .mark_bar(cornerRadiusEnd=3, color="#2b7197")
        .encode(
            y=alt.Y(
                "Categoría:N",
                sort=ref_order,
                title=None,
                axis=alt.Axis(labelLimit=120, labelPadding=8),
            ),
            x=alt.X("Líderes:Q", title=None, scale=alt.Scale(domain=[0, ref_x_max])),
            tooltip=[
                "Categoría:N",
                alt.Tooltip("Líderes:Q", format=","),
                alt.Tooltip("% líderes activos:Q", format=".1f"),
            ],
        )
        .properties(height=280)
    )
    ref_labels = (
        alt.Chart(ref_summary)
        .mark_text(align="left", dx=6, color="#243247", fontSize=12, fontWeight="bold")
        .encode(
            y=alt.Y("Categoría:N", sort=ref_order, title=None),
            x=alt.X("Líderes:Q", title=None, scale=alt.Scale(domain=[0, ref_x_max])),
            text="Etiqueta:N",
        )
    )
    st.altair_chart(clean_chart(ref_chart + ref_labels), use_container_width=True, theme=None)

with right:
    st.markdown('<div class="section-title">Top puestos por concentración</div>', unsafe_allow_html=True)
    top_puestos = (
        map_data.sort_values("total_testigos", ascending=False)
        .head(8)[
            [
                "nombre_puesto_dashboard",
                "localidad",
                "total_testigos",
                "lideres_activos",
                "referidos_activos_lideres",
            ]
        ]
        .rename(
            columns={
                "nombre_puesto_dashboard": "Puesto",
                "localidad": "Localidad",
                "total_testigos": "Testigos",
                "lideres_activos": "Líderes activos",
                "referidos_activos_lideres": "Referidos activos",
            }
        )
    )
    top_puestos_display = top_puestos.copy()
    for col in ["Testigos", "Líderes activos", "Referidos activos"]:
        top_puestos_display[col] = top_puestos_display[col].map(format_int)
    table_rows = []
    for _, row in top_puestos_display.iterrows():
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['Puesto']))}</td>"
            f"<td>{html.escape(str(row['Localidad']))}</td>"
            f"<td class='num'>{row['Testigos']}</td>"
            f"<td class='num'>{row['Líderes activos']}</td>"
            f"<td class='num'>{row['Referidos activos']}</td>"
            "</tr>"
        )
    st.markdown(
        """
        <table class="rank-table">
            <thead>
                <tr>
                    <th>Puesto</th>
                    <th>Localidad</th>
                    <th>Testigos</th>
                    <th>Líderes</th>
                    <th>Referidos</th>
                </tr>
            </thead>
            <tbody>
        """
        + "".join(table_rows)
        + """
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-title">Distribución por localidad</div>', unsafe_allow_html=True)
localidad_summary = (
    filtered.groupby("localidad")
    .agg(
        Testigos=("total_testigos", "sum"),
        Lideres=("lideres_activos", "sum"),
        Referidos=("referidos_activos_lideres", "sum"),
    )
    .sort_values("Testigos", ascending=False)
    .head(12)
)
st.altair_chart(
    rank_overlay_chart(
        localidad_summary,
        "localidad",
        height=330,
    ),
    use_container_width=True,
    theme=None,
)

st.markdown('<div class="section-title">Distribución por templo / sector</div>', unsafe_allow_html=True)
templo_summary = (
    filtered.groupby("templo_sector")
    .agg(
        Testigos=("total_testigos", "sum"),
        Lideres=("lideres_activos", "sum"),
        Beneficiarios=("beneficiarios_mesas_trabajo", "sum"),
        Referidos=("referidos_activos_lideres", "sum"),
    )
    .sort_values("Testigos", ascending=False)
    .head(12)
)
st.altair_chart(
    rank_overlay_chart(
        templo_summary,
        "templo_sector",
        height=330,
    ),
    use_container_width=True,
    theme=None,
)

with st.expander("Ver datos filtrados para auditoría"):
    audit_cols = [
        "codigo_puesto_unico",
        "zona_operativa",
        "localidad",
        "templo_sector",
        "nombre_puesto_dashboard",
        "direccion",
        "total_testigos",
        "lideres_activos",
        "beneficiarios_mesas_trabajo",
        "referidos_activos_lideres",
        "lideres_ref_0",
        "lideres_ref_1_5",
        "lideres_ref_6_9",
        "lideres_ref_10_mas",
    ]
    st.dataframe(filtered[audit_cols], use_container_width=True, hide_index=True)
