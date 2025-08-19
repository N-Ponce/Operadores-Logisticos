# ──────────────────────────────────────────────────────────────────────────────
# APP DE OPERADORES LOGÍSTICOS — v2 (sin descarga CSV, con comparativa Santiago)
# ──────────────────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Recomendación de Operadores (v2)", layout="wide")
st.title("Operadores Logísticos — Recomendador (v2)")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Configuración")

    # Fuente de datos
    fuente = st.radio("Fuente de datos", ["Subir Excel", "Ruta local"], horizontal=True)
    up = None
    ruta = None
    if fuente == "Subir Excel":
        up = st.file_uploader("Carga tu Excel", type=["xlsx"])
    else:
        ruta = st.text_input("Ruta local (ej: operadores.xlsx)", "operadores.xlsx")

    # Presets de pesos
    perfil = st.selectbox(
        "Prioridad de decisión",
        ["Balanceado", "Costo primero", "SLA primero", "Cobertura primero"],
    )
    presets = {
        "Balanceado":    {'sla':0.35,'costo':0.25,'capacidad':0.20,'cobertura':0.20},
        "Costo primero": {'sla':0.25,'costo':0.45,'capacidad':0.15,'cobertura':0.15},
        "SLA primero":   {'sla':0.50,'costo':0.20,'capacidad':0.15,'cobertura':0.15},
        "Cobertura primero": {'sla':0.25,'costo':0.20,'capacidad':0.15,'cobertura':0.40},
    }
    usar_preset = st.checkbox("Usar preset", value=True)

    if usar_preset:
        pesos = presets[perfil].copy()
    else:
        colw1, colw2 = st.columns(2)
        with colw1:
            wsla   = st.slider("Peso SLA", 0.0, 1.0, 0.35, 0.05)
            wcap   = st.slider("Peso Capacidad", 0.0, 1.0, 0.20, 0.05)
        with colw2:
            wcosto = st.slider("Peso Costo", 0.0, 1.0, 0.25, 0.05)
            wcob   = st.slider("Peso Cobertura", 0.0, 1.0, 0.20, 0.05)
        s = wsla + wcosto + wcap + wcob
        if s == 0:
            pesos = presets["Balanceado"].copy()
            st.info("Ajusté los pesos a ‘Balanceado’ porque la suma era 0.")
        else:
            pesos = {'sla':wsla/s, 'costo':wcosto/s, 'capacidad':wcap/s, 'cobertura':wcob/s}

    top_n = st.slider("¿Cuántas opciones mostrar?", 1, 10, 4)

    st.divider()
    st.caption("Comparativas")
    ver_comp_scl = st.checkbox("Mostrar comparativa de despacho en Santiago", value=True)

# ── Utilidades ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def cargar_excel(uploaded_file=None, path=None) -> pd.DataFrame:
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return pd.read_excel(path)

def to_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def normalizar(col):
    c = col.astype(float)
    rng = c.max() - c.min()
    if rng == 0:
        return pd.Series(1.0, index=c.index)
    return (c - c.min()) / rng

def calcular_scores(df, pesos):
    tmp = df.copy()

    # 👉 Ajusta estos nombres a tus columnas reales si difieren:
    req = ['SLA_on_time','Costo_x_envio','Capacidad_diaria','Cobertura_regiones']
    faltan = [c for c in req if c not in tmp.columns]
    if faltan:
        st.error(f"Faltan columnas requeridas: {faltan}")
        st.stop()

    # Tipos numéricos e imputación conservadora
    tmp = to_numeric(tmp, req)
    for c in req:
        if tmp[c].isna().all():
            st.error(f"La columna {c} está completamente vacía.")
            st.stop()
        tmp[c] = tmp[c].fillna(tmp[c].median())

    # Normalizaciones
    tmp['n_sla']       = normalizar(tmp['SLA_on_time'])        # mayor mejor
    tmp['n_capacidad'] = normalizar(tmp['Capacidad_diaria'])   # mayor mejor
    tmp['n_cobertura'] = normalizar(tmp['Cobertura_regiones']) # mayor mejor
    n_costo = normalizar(tmp['Costo_x_envio'])                 # menor mejor
    tmp['n_costo'] = 1 - n_costo

    # Score
    tmp['score'] = (
        pesos['sla']       * tmp['n_sla'] +
        pesos['costo']     * tmp['n_costo'] +
        pesos['capacidad'] * tmp['n_capacidad'] +
        pesos['cobertura'] * tmp['n_cobertura']
    )

    # Explicación simple (top2 fortalezas + trade-off)
    def explicar(r):
        vect = {
            "SLA alto": r['n_sla'],
            "Costo competitivo": r['n_costo'],
            "Alta capacidad": r['n_capacidad'],
            "Buena cobertura": r['n_cobertura'],
        }
        orden = sorted(vect.items(), key=lambda x: x[1], reverse=True)
        fort = [orden[0][0], orden[1][0]]
        deb  = min(vect, key=vect.get)
        return f"Fortalezas: {', '.join(fort)}. Trade-off: {deb}."

    tmp['explicacion'] = tmp.apply(explicar, axis=1)

    # Orden + desempates
    tmp = tmp.sort_values(
        by=['score','n_sla','n_cobertura','n_costo','n_capacidad'],
        ascending=[False, False, False, False, False]
    ).reset_index(drop=True)

    return tmp

# ── Comparativa Santiago (valores confirmados) ────────────────────────────────
CROSSDOCK_SCL = {
    "SP":   {"ripley": 3990,  "externo": 3990},
    "XXS":  {"ripley": 4990,  "externo": 7990},
    "XS":   {"ripley": 9990,  "externo": 14990},
    "S":    {"ripley": 9990,  "externo": 19990},
    "M1":   {"ripley": 10990, "externo": 39990},
    "M2":   {"ripley": 13990, "externo": 79990},
    "L/XL": {"ripley": 16990, "externo": 199990},
}

# ── Carga, filtros y UI ───────────────────────────────────────────────────────
try:
    df = None
    if fuente == "Subir Excel" and up is not None:
        df = cargar_excel(uploaded_file=up)
    elif fuente == "Ruta local":
        df = cargar_excel(path=ruta)

    if df is not None:
        st.success("Datos cargados correctamente.")

        # Filtros opcionales si existen
        with st.expander("Filtros (opcional)"):
            df_filtrado = df.copy()
            if 'Categoria' in df.columns:
                cat_sel = st.multiselect("Categoría", sorted(df['Categoria'].dropna().unique()))
                if cat_sel: df_filtrado = df_filtrado[df_filtrado['Categoria'].isin(cat_sel)]
            if 'Region' in df.columns:
                reg_sel = st.multiselect("Región", sorted(df['Region'].dropna().unique()))
                if reg_sel: df_filtrado = df_filtrado[df_filtrado['Region'].isin(reg_sel)]
            if 'Tamano' in df.columns:
                tam_sel = st.multiselect("Tamaño", sorted(df['Tamano'].dropna().unique()))
                if tam_sel: df_filtrado = df_filtrado[df_filtrado['Tamano'].isin(tam_sel)]

        st.markdown("Presiona **Ver opciones** para calcular y mostrar todas las alternativas ordenadas.")
        if st.button("Ver opciones"):
            ranking = calcular_scores(df_filtrado, pesos)

            # Top N con ordinales
            ordinal = {1:"Primero",2:"Segundo",3:"Tercero",4:"Cuarto",5:"Quinto",6:"Sexto",7:"Séptimo",8:"Octavo",9:"Noveno",10:"Décimo"}
            top = ranking.head(top_n).copy()
            top['Pos'] = np.arange(1, len(top)+1)

            for _, row in top.iterrows():
                pos = int(row['Pos'])
                nombre = row['Operador'] if 'Operador' in row else 'Operador'
                st.subheader(f"**{ordinal.get(pos, f'#{pos}')}** — {nombre}")
                st.write(f"**Score:** {row['score']:.3f}")
                kpi = st.columns(4)
                with kpi[0]:
                    st.metric("SLA on-time", f"{row['SLA_on_time']:.1f}%")
                with kpi[1]:
                    st.metric("Costo x envío", f"${row['Costo_x_envio']:.0f}")
                with kpi[2]:
                    st.metric("Capacidad diaria", f"{int(row['Capacidad_diaria'])}")
                with kpi[3]:
                    st.metric("Cobertura (regiones)", f"{int(row['Cobertura_regiones'])}")
                st.caption(f"**¿Por qué quedó aquí?** {row['explicacion']}")
                st.divider()

            # Tabla completa
            with st.expander("Ver tabla completa (todas las opciones en orden)"):
                cols_show = ['Operador','score','SLA_on_time','Costo_x_envio','Capacidad_diaria','Cobertura_regiones']
                cols_show = [c for c in cols_show if c in ranking.columns]
                st.dataframe(ranking[cols_show], use_container_width=True)

            # Comparativa Santiago (sin gráficos)
            if ver_comp_scl:
                st.markdown("### Comparativa de despacho en **Santiago** (Crossdock)")
                comp = pd.DataFrame([
                    {"Tamaño": k, "Ripley (Crossdock)": v["ripley"], "Operadores externos": v["externo"]}
                    for k, v in CROSSDOCK_SCL.items()
                ])
                comp['Diferencia'] = comp['Operadores externos'] - comp['Ripley (Crossdock)']
                comp['Nota'] = comp['Tamaño'].apply(
                    lambda t: "Diferencia baja en pequeños" if t in ["SP","XXS","XS"]
                              else "Diferencia significativa en medianos/grandes"
                )
                st.dataframe(comp, use_container_width=True)
                st.info("**Claves**: En productos pequeños la diferencia es baja; en medianos/grandes, Ripley resulta mucho más conveniente (puede ser hasta 12× más barato).")
    else:
        st.warning("Carga un Excel o indica una ruta para comenzar.")

except Exception as ex:
    st.error(f"Ocurrió un error: {ex}")
