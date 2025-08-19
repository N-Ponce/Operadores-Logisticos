# ──────────────────────────────────────────────────────────────────────────────
# APP DE OPERADORES LOGÍSTICOS — v3 (Formulario + Tablas comparativas 3 columnas)
# Sin Excel, sin preguntas de "entrega rápida" ni "cobertura nacional"
# ──────────────────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Recomendación de Operadores (v3)", layout="wide")
st.title("Operadores Logísticos — Recomendador (Formulario · Comparativas)")

# ── Datos confirmados para explicaciones ──────────────────────────────────────
# Comparativa de despacho Santiago (Crossdock vs operadores externos)
CROSSDOCK_SCL = {
    "SP":   {"ripley": 3990,  "externo": 3990},
    "XXS":  {"ripley": 4990,  "externo": 7990},
    "XS":   {"ripley": 9990,  "externo": 14990},
    "S":    {"ripley": 9990,  "externo": 19990},
    "M1":   {"ripley": 10990, "externo": 39990},
    "M2":   {"ripley": 13990, "externo": 79990},
    "L/XL": {"ripley": 16990, "externo": 199990},
}

# Fulfillment: almacenamiento + cofinanciamiento (tabla oficial)
FULF_STORAGE = [
    "XXXS: $0,3/día + $1.000 / $2.600 por venta",
    "S: $7/día + $4.500 por venta",
    "M1: $20/día + $6.800 por venta",
    "XXL: $260/día + $8.500 por venta",
    "XXXL: $400/día + $11.000 por venta",
]

# Flota propia (Ripley – Envíame) RM
FLOTA_ENV = {  # tamaños disponibles
    "SP": 3200, "P1": 3200, "P2": 4990, "P3": 5990, "M": 5990, "G": 6990, "SG": 18740
}

# ── Formulario (sin archivos) ────────────────────────────────────────────────
with st.form("selector"):
    st.subheader("Tu escenario")

    colA, colB, colC = st.columns(3)
    with colA:
        tamano = st.selectbox("Tamaño del producto", ["SP","XXS","XS","S","M1","M2","L/XL"])
        region = st.selectbox("Región de operación principal", ["RM","Otra"])
        volumen = st.number_input("Órdenes diarias (promedio)", min_value=0, step=1, value=10)

    with colB:
        tiene_bodega = st.radio("¿Tienes bodega propia?", ["Sí","No"], index=0)
        alta_rotacion = st.checkbox("Alta rotación (ventas frecuentes)", value=True)

    with colC:
        retiro_tienda = st.checkbox("Ofrecer retiro en tienda", value=True)
        foco_control_marca = st.checkbox("Quiero máximo control/branding de entrega", value=False)

    enviado = st.form_submit_button("Ver recomendaciones")

# ── Motor de decisión ────────────────────────────────────────────────────────
def puntuar_modalidades(tamano, region, volumen, tiene_bodega,
                        alta_rotacion, retiro_tienda, foco_control_marca):
    en_RM = (region == "RM")
    sin_bodega = (tiene_bodega == "No")
    es_peq = tamano in ["SP","XXS","XS"]
    es_med = tamano in ["S","M1"]
    es_grd = tamano in ["M2","L/XL"]

    # Pesos globales (consistentes con decisiones previas)
    W = {"costo":0.42, "velocidad":0.28, "control":0.20, "cobertura":0.10}

    perfiles = {
        "Operador Logístico": {"costo":0.60, "velocidad":0.50, "control":0.80, "cobertura":0.65},
        "Crossdock":          {"costo":0.80, "velocidad":0.70, "control":0.60, "cobertura":0.70},
        "Fulfillment":        {"costo":0.50, "velocidad":0.90, "control":0.40, "cobertura":0.80},
        "Flota Propia":       {"costo":0.60, "velocidad":0.70, "control":1.00, "cobertura":0.45},
    }

    # Ajustes contextuales
    if en_RM and (es_med or es_grd):
        perfiles["Crossdock"]["costo"] += 0.15
        perfiles["Crossdock"]["velocidad"] += 0.05
    if es_peq:
        perfiles["Crossdock"]["costo"] -= 0.05  # en pequeños la diferencia con externos es baja

    if alta_rotacion or sin_bodega:
        perfiles["Fulfillment"]["velocidad"] += 0.05
        perfiles["Fulfillment"]["cobertura"] += 0.05
        perfiles["Fulfillment"]["costo"] -= 0.05  # eficiencia compensa parte del costo

    if foco_control_marca and en_RM and volumen >= 20:
        perfiles["Flota Propia"]["control"] += 0.05
        perfiles["Flota Propia"]["velocidad"] += 0.05
        perfiles["Flota Propia"]["costo"] += 0.05  # volumen ayuda al costo unitario

    if (tiene_bodega == "Sí") and (es_peq or es_med):
        perfiles["Operador Logístico"]["control"] += 0.05
        perfiles["Operador Logístico"]["costo"] += 0.05

    filas = []
    for mod, p in perfiles.items():
        score = (W["costo"]*p["costo"] + W["velocidad"]*p["velocidad"] +
                 W["control"]*p["control"] + W["cobertura"]*p["cobertura"])
        filas.append({"Modalidad": mod, "score": score, "perfil": p})
    df = pd.DataFrame(filas).sort_values("score", ascending=False).reset_index(drop=True)
    return df

# ── Ventajas / Desventajas / Notas-Costos ────────────────────────────────────
def ventajas_y_desventajas(mod, tamano, region, volumen,
                           tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca):
    en_RM = (region == "RM")
    es_peq = tamano in ["SP","XXS","XS"]
    es_med = tamano in ["S","M1"]
    es_grd = tamano in ["M2","L/XL"]
    sin_bodega = (tiene_bodega == "No")

    ventajas, desventajas, notas = [], [], []

    if mod == "Operador Logístico":
        ventajas += [
            "Control total del inventario si ya tienes bodega propia.",
            "Modelo simple: primera milla definida y despacho estándar.",
            "Encaja bien con productos pequeños/medianos cuando gestionas tu stock."
        ]
        desventajas += [
            "Tiempos algo mayores en algunos casos frente a Crossdock/Fulfillment.",
            "Menor visibilidad punta a punta comparado con Fulfillment.",
            "Necesitas gestionar tu bodega (si no tienes, no es ideal)."
        ]
        notas.append("Costos confirmados de primera milla: SP $1.000, P2 $6.690, G $12.990.")

    elif mod == "Crossdock":
        ventajas += [
            "Plazos más cortos y opción de retiro en tienda.",
            "Operación eficiente en RM; especialmente útil para medianos/grandes."
        ]
        if retiro_tienda:
            ventajas.append("Permite $0 para el cliente si retira en tienda (cuando aplica).")
        desventajas += [
            "Requiere coordinación con Ripley (ventanas de retiro/entrega).",
            "Depende de bodega en RM para operar de forma óptima."
        ]
        if en_RM and tamano in CROSSDOCK_SCL:
            r = CROSSDOCK_SCL[tamano]
            if es_peq:
                notas.append(f"Santiago: Ripley ${r['ripley']:,} ≈ externos ${r['externo']:,} (diferencia baja en pequeños).")
            else:
                notas.append(f"Santiago: Ripley ${r['ripley']:,} vs externos ${r['externo']:,} (brecha muy alta en medianos/grandes).")

    elif mod == "Fulfillment":
        ventajas += [
            "Mayor conversión por SLA y experiencia de entrega superiores.",
            "Ideal si no tienes bodega propia o si la rotación es alta.",
            "Mejor visibilidad operacional (inventario, preparación, despacho)."
        ]
        if alta_rotacion or sin_bodega:
            ventajas.append("Reduce fricciones operativas y sostiene picos de demanda.")
        desventajas += [
            "Costos de arriendo y operación del CD de Ripley.",
            "Menor control directo del inventario (lo gestiona el CD).",
            "Exige planificación de inbound/outbound al CD."
        ]
        notas.append("Almacenamiento + cofinanciamiento por venta (oficial):")
        for linea in FULF_STORAGE:
            notas.append(f"· {linea}")

    elif mod == "Flota Propia":
        ventajas += [
            "Máximo control de la experiencia y branding propio.",
            "Puede ser muy competitivo en RM si hay volumen y rutas optimizadas."
        ]
        if en_RM and volumen >= 20:
            ventajas.append("Con alto volumen en RM, el costo unitario mejora por optimización de rutas.")
        desventajas += [
            "Limitado principalmente a RM (cobertura nacional acotada).",
            "Requiere inversión y gestión logística (personal, vehículos, mantención).",
        ]
        if tamano in FLOTA_ENV:
            notas.append(f"Tarifa última milla RM para {tamano}: ${FLOTA_ENV[tamano]:,}.")
        else:
            notas.append("Tarifario confirmado disponible (SP, P1, P2, P3, M, G, SG).")

    return ventajas, desventajas, notas

# ── Render ───────────────────────────────────────────────────────────────────
if enviado:
    ranking = puntuar_modalidades(
        tamano, region, volumen, tiene_bodega,
        alta_rotacion, retiro_tienda, foco_control_marca
    )

    st.success("Recomendaciones generadas según tu escenario.")
    ordinal = {1:"Primero",2:"Segundo",3:"Tercero",4:"Cuarto"}

    for i, row in ranking.iterrows():
        pos = i + 1
        mod = row["Modalidad"]
        st.subheader(f"**{ordinal.get(pos, f'#{pos}')}** — {mod}")
        st.write(f"**Score:** {row['score']:.3f}")

        ventajas, desventajas, notas = ventajas_y_desventajas(
            mod, tamano, region, volumen,
            tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca
        )

        # Normalizamos longitudes y construimos la tabla comparativa 3 columnas
        max_len = max(len(ventajas), len(desventajas), len(notas))
        ventajas += [""] * (max_len - len(ventajas))
        desventajas += [""] * (max_len - len(desventajas))
        notas += [""] * (max_len - len(notas))

        df_comp = pd.DataFrame({
            "Ventajas": ventajas,
            "Desventajas": desventajas,
            "Notas/Costos": notas
        })
        st.table(df_comp)
        st.divider()

    # Mensaje clave para Santiago
    if region == "RM":
        st.info("**Clave Santiago**: En productos pequeños la diferencia de precio con externos es baja; en medianos/grandes la ventaja de Crossdock (Ripley) es muy significativa.")

else:
    st.info("Completa el formulario y presiona **Ver recomendaciones** para ver el orden sugerido con tablas comparativas por operador (3 columnas).")
