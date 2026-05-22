import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)


def clean_code(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(2) if text.isdigit() else text.upper()


def yes(series):
    return series.fillna("").astype(str).str.upper().str.strip().eq("SI")


def lower(series):
    return series.fillna("").astype(str).str.lower().str.strip()


def pct(numerator, denominator):
    if denominator == 0:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, 1)


base = pd.read_excel(
    ROOT / "Caracterizacion_Testigos_Bogota_2026.xlsx",
    sheet_name="Datos base Anonimizados",
    header=1,
    dtype=str,
)

for col in ["Ref. activos", "Ref. inactivos", "Ref. totales", "# mesas trabajo"]:
    base[col] = pd.to_numeric(base[col], errors="coerce").fillna(0)

base["zona_codigo"] = base["Cod zona votación"].map(clean_code)
base["puesto_codigo"] = base["Cod puesto votación"].map(clean_code)
base["codigo_puesto_unico"] = "16001" + base["zona_codigo"].fillna("") + base["puesto_codigo"].fillna("")
base["es_lider_activo"] = lower(base["Tipo líder"]).eq("lider") & lower(base["Estado líder"]).eq("activo")
base["es_beneficiario_mesas"] = yes(base["Benef. mesas trabajo"])

leaders = base["es_lider_activo"]
base["lider_ref_0"] = leaders & base["Ref. activos"].eq(0)
base["lider_ref_1_5"] = leaders & base["Ref. activos"].between(1, 5)
base["lider_ref_6_9"] = leaders & base["Ref. activos"].between(6, 9)
base["lider_ref_10_mas"] = leaders & base["Ref. activos"].ge(10)

features = json.loads((ROOT / "puestos_votacion_ideca.geojson").read_text())["features"]
ideca_rows = []
for feature in features:
    props = feature["properties"]
    lon, lat = feature["geometry"]["coordinates"]
    ideca_rows.append(
        {
            "codigo_puesto_unico": props.get("PVOCODIGO"),
            "localidad_codigo": props.get("LOCCODIGO"),
            "localidad": props.get("LOCNOMBRE"),
            "direccion": props.get("PVODIRECCI"),
            "nombre_sitio": props.get("PVONSITIO"),
            "nombre_puesto_ideca": props.get("PVONOMBRE"),
            "numero_puesto_ideca": props.get("PVONPUESTO"),
            "latitud": lat,
            "longitud": lon,
            "fuente_geografica": "IDECA/Catastro Bogotá - Puestos de Votación 2023",
        }
    )
ideca = pd.DataFrame(ideca_rows)

valid = base.dropna(subset=["zona_codigo", "puesto_codigo", "Nom puesto votación"]).copy()

def summarize(source, group_cols):
    grouped = (
        source.groupby(group_cols, dropna=False)
        .agg(
            total_testigos=("ID", "count"),
            lideres_activos=("es_lider_activo", "sum"),
            beneficiarios_mesas_trabajo=("es_beneficiario_mesas", "sum"),
            referidos_activos_lideres=("Ref. activos", lambda s: int(s[source.loc[s.index, "es_lider_activo"]].sum())),
            lideres_ref_0=("lider_ref_0", "sum"),
            lideres_ref_1_5=("lider_ref_1_5", "sum"),
            lideres_ref_6_9=("lider_ref_6_9", "sum"),
            lideres_ref_10_mas=("lider_ref_10_mas", "sum"),
        )
        .reset_index()
    )
    grouped["pct_lideres_activos"] = grouped.apply(
        lambda r: pct(r["lideres_activos"], r["total_testigos"]), axis=1
    )
    grouped["pct_beneficiarios_mesas_trabajo"] = grouped.apply(
        lambda r: pct(r["beneficiarios_mesas_trabajo"], r["total_testigos"]), axis=1
    )
    return grouped


puesto_name = (
    valid.groupby("codigo_puesto_unico")["Nom puesto votación"]
    .agg(lambda s: s.value_counts().index[0])
    .rename("nombre_puesto_base")
    .reset_index()
)
puesto_variants = (
    valid.groupby("codigo_puesto_unico")["Nom puesto votación"]
    .agg(lambda s: " | ".join(sorted(set(s.dropna().astype(str)))))
    .rename("nombres_puesto_base_variantes")
    .reset_index()
)
templo_principal = (
    valid.groupby("codigo_puesto_unico")["Templo / sector"]
    .agg(lambda s: s.value_counts().index[0])
    .rename("templo_principal")
    .reset_index()
)

master = summarize(valid, ["codigo_puesto_unico", "zona_codigo", "puesto_codigo"]).merge(
    puesto_name, on="codigo_puesto_unico", how="left"
)
master = master.merge(puesto_variants, on="codigo_puesto_unico", how="left")
master = master.merge(templo_principal, on="codigo_puesto_unico", how="left")
master = master.merge(ideca, on="codigo_puesto_unico", how="left")
master["estado_geocodificacion"] = master["latitud"].notna().map({True: "geocodificado", False: "pendiente_validacion"})
master["nombre_puesto_dashboard"] = master["nombre_puesto_ideca"].fillna(master["nombre_puesto_base"])

front_cols = [
    "codigo_puesto_unico",
    "zona_codigo",
    "puesto_codigo",
    "nombre_puesto_dashboard",
    "nombre_puesto_base",
    "nombres_puesto_base_variantes",
    "nombre_puesto_ideca",
    "nombre_sitio",
    "localidad_codigo",
    "localidad",
    "direccion",
    "latitud",
    "longitud",
    "estado_geocodificacion",
    "fuente_geografica",
    "templo_principal",
]
metric_cols = [c for c in master.columns if c not in front_cols]
master = master[front_cols + metric_cols]

fact_source = base.copy()
missing_puesto = fact_source[["zona_codigo", "puesto_codigo", "Nom puesto votación"]].isna().any(axis=1)
fact_source.loc[missing_puesto, "codigo_puesto_unico"] = "SIN_CODIGO_PUESTO"
fact_source.loc[missing_puesto, "zona_codigo"] = "SIN_ZONA"
fact_source.loc[missing_puesto, "puesto_codigo"] = "SIN_PUESTO"
fact_source.loc[missing_puesto, "Nom puesto votación"] = "Sin puesto de votación"

fact = summarize(
    fact_source,
    [
        "codigo_puesto_unico",
        "zona_codigo",
        "puesto_codigo",
        "Zona",
        "Templo / sector",
    ]
)
fact = fact.merge(puesto_name, on="codigo_puesto_unico", how="left").merge(
    puesto_variants, on="codigo_puesto_unico", how="left"
).merge(
    ideca, on="codigo_puesto_unico", how="left"
)
fact["estado_geocodificacion"] = fact["latitud"].notna().map({True: "geocodificado", False: "pendiente_validacion"})
fact["nombre_puesto_dashboard"] = fact["nombre_puesto_ideca"].fillna(fact["nombre_puesto_base"])
fact = fact.rename(columns={"Zona": "zona_operativa", "Templo / sector": "templo_sector"})

fact_front_cols = [
    "codigo_puesto_unico",
    "zona_codigo",
    "puesto_codigo",
    "zona_operativa",
    "templo_sector",
    "nombre_puesto_dashboard",
    "nombre_puesto_base",
    "nombres_puesto_base_variantes",
    "nombre_puesto_ideca",
    "nombre_sitio",
    "localidad_codigo",
    "localidad",
    "direccion",
    "latitud",
    "longitud",
    "estado_geocodificacion",
    "fuente_geografica",
]
fact_metric_cols = [c for c in fact.columns if c not in fact_front_cols]
fact = fact[fact_front_cols + fact_metric_cols]

master.to_csv(OUT / "tabla_maestra_puestos_votacion_bogota.csv", index=False, encoding="utf-8-sig")
fact.to_csv(OUT / "dataset_mapa_testigos_por_puesto_templo.csv", index=False, encoding="utf-8-sig")

coverage = {
    "puestos_unicos_base_por_codigo": int(len(master)),
    "combinaciones_puesto_nombre_base": int(
        base.dropna(subset=["Cod zona votación", "Cod puesto votación", "Nom puesto votación"])[
            ["Cod zona votación", "Cod puesto votación", "Nom puesto votación"]
        ]
        .drop_duplicates()
        .shape[0]
    ),
    "puestos_geocodificados": int(master["latitud"].notna().sum()),
    "puestos_pendientes_validacion": int(master["latitud"].isna().sum()),
    "pct_puestos_geocodificados": pct(master["latitud"].notna().sum(), len(master)),
    "testigos_en_puestos_geocodificados": int(master.loc[master["latitud"].notna(), "total_testigos"].sum()),
    "testigos_en_puestos_pendientes": int(master.loc[master["latitud"].isna(), "total_testigos"].sum()),
    "testigos_sin_codigo_puesto_votacion": int(
        base[["Cod zona votación", "Cod puesto votación", "Nom puesto votación"]].isna().any(axis=1).sum()
    ),
    "total_testigos_base": int(len(base)),
    "pct_testigos_geocodificados": pct(
        master.loc[master["latitud"].notna(), "total_testigos"].sum(),
        master["total_testigos"].sum(),
    ),
}
(OUT / "resumen_cobertura_geografica.json").write_text(
    json.dumps(coverage, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(json.dumps(coverage, ensure_ascii=False, indent=2))
