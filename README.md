# Dashboard Estratégico de Testigos Bogotá

Dashboard territorial en Streamlit para visualizar concentración de testigos por puesto de votación, localidad y templo/sector.

## Qué Incluye

- Mapa de concentración por puesto de votación.
- Límites de localidades de Bogotá.
- Filtros por zona, localidad y templo/sector.
- Indicadores de testigos, líderes activos, beneficiarios de mesas de trabajo y referidos activos.
- Rankings por localidad, templo/sector y puestos de mayor concentración.

## Datos Usados

La app usa datos agregados y geográficos ubicados en:

- `outputs/dataset_mapa_testigos_por_puesto_templo.csv`
- `outputs/tabla_maestra_puestos_votacion_bogota.csv`
- `localidades_bogota_ideca.geojson`

No se requiere subir la base nominal con nombres, cédulas o teléfonos para ejecutar esta versión.

## Ejecutar Localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Despliegue En Streamlit Cloud

1. Subir este proyecto a un repositorio privado de GitHub.
2. En Streamlit Cloud, crear una nueva app desde ese repositorio.
3. Seleccionar `app.py` como archivo principal.
4. Mantener el repositorio y la app con acceso restringido.

