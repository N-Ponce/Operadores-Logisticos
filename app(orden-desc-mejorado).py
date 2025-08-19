# ──────────────────────────────────────────────────────────────────────────────
# APP DE OPERADORES LOGÍSTICOS — v5 (formato ficha + Desventajas)
# Sin Excel. Fichas por operador: Título (ordinal fucsia), descripción,
# "Costos estimados" (tabla sin índice), "Beneficios clave" y "Desventajas".
# ──────────────────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Recomendación de Operadores (v5)", layout="wide")
st.title("Operadores Logísticos — Recomendador")

# ── Estilos globales (títulos y tablas) ───────────────────────────────────────
st.markdown(
    """
    <style>
    .rank-title { font-size: 40px; font-weight: 800; margin: 8px 0 0 0; }
    .rank-badge { color: #E91E63; }       /* fucsia Ripley */
    .rank-name  { color: #222; font-weight: 800; }
    .subdesc { font-size: 18px; color: #444; margin: 6px 0 16px 0; }
    .section-h3 { font-size: 22px; font-weight: 800; color: #333; margin: 12px 0 8px 0; }

    table { width: 100%; border-collapse: separate !important; border-spacing: 0; }
    thead th {
        background: #F6F7F9 !important;
        font-size: 16px !important;
        color: #444 !important;
        text-align: left !important;
        border-bottom: 1px solid #E5E7EB !important;
        padding: 10px !important;
    }
    tbody td {
        font-size: 15px !important;
        color: #222 !important;
        padding: 10px !important;
        border-top: 1px solid #F0F2F5 !important;
    }
    table, tbody tr:last-child td { border-bottom: 1px solid #E5E7EB !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ── Datos confirmados para costos/notas ───────────────────────────────────────
CROSSDOCK_SCL = {
    "SP":   {"ripley": 3990,  "externo": 3990},
    "XXS":  {"ripley": 4990,  "externo": 7990},
    "XS":   {"ripley": 9990,  "externo": 14990},
    "S":    {"ripley": 9990,  "externo": 19990},
    "M1":   {"ripley": 10990, "externo": 39990},
    "M2":   {"ripley": 13990, "externo": 79990},
    "L/XL": {"ripley": 16990, "externo": 199990},
}
FULF_STORAGE = [
    "XXXS: $0,3/día + $1.000 / $2.600 por venta",
    "S: $7/día + $4.500 por venta",
    "M1: $20/día + $6.800 por venta",
    "XXL: $260/día + $8.500 por venta",
    "XXXL: $400/día + $11.000 por venta",
]
FLOTA_ENV = {  # Ripley – Envíame (RM)
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

# ── Motor de puntuación consistente ──────────────────────────────────────────
def rank_modalidades(tamano, region, volumen, tiene_bodega, alta_rotacion,
                     retiro_tienda, foco_control_marca):
    en_RM = (region == "RM")
    es_peq = tamano in ["SP","XXS","XS"]
    es_med = tamano in ["S","M1"]
    es_grd = tamano in ["M2","L/XL"]
    sin_bodega = (tiene_bodega == "No")

    W = {"costo":0.42, "velocidad":0.28, "control":0.20, "cobertura":0.10}
    perfiles = {
        "Operador Logístico": {"costo":0.60, "velocidad":0.50, "control":0.80, "cobertura":0.65},
        "Crossdock":          {"costo":0.80, "velocidad":0.70, "control":0.60, "cobertura":0.70},
        "Fulfillment":        {"costo":0.50, "velocidad":0.90, "control":0.40, "cobertura":0.80},
        "Flota Propia":       {"costo":0.60, "velocidad":0.70, "control":1.00, "cobertura":0.45},
    }
    if en_RM and (es_med or es_grd):
        perfiles["Crossdock"]["costo"] += 0.15
        perfiles["Crossdock"]["velocidad"] += 0.05
    if es_peq:
        perfiles["Crossdock"]["costo"] -= 0.05
    if alta_rotacion or sin_bodega:
        perfiles["Fulfillment"]["velocidad"] += 0.05
        perfiles["Fulfillment"]["cobertura"] += 0.05
        perfiles["Fulfillment"]["costo"] -= 0.05
    if foco_control_marca and en_RM and volumen >= 20:
        perfiles["Flota Propia"]["control"] += 0.05
        perfiles["Flota Propia"]["velocidad"] += 0.05
        perfiles["Flota Propia"]["costo"] += 0.05
    if (tiene_bodega == "Sí") and (es_peq or es_med):
        perfiles["Operador Logístico"]["control"] += 0.05
        perfiles["Operador Logístico"]["costo"] += 0.05

    filas = []
    for mod, p in perfiles.items():
        score = (W["costo"]*p["costo"] + W["velocidad"]*p["velocidad"]
                 + W["control"]*p["control"] + W["cobertura"]*p["cobertura"])
        filas.append({"Modalidad": mod, "score": score})
    return pd.DataFrame(filas).sort_values("score", ascending=False).reset_index(drop=True)

# ── Descripción, costos, beneficios y desventajas ────────────────────────────
def descripcion_mod(mod):
    if mod == "Operador Logístico":
        return "El seller maneja su stock y paga la primera milla. El cliente paga el despacho final."
    if mod == "Crossdock":
        return "Ripley retira/recibe en bodega del seller y distribuye. El cliente paga el despacho o retira en tienda."
    if mod == "Fulfillment":
        return "El stock queda en bodega Ripley; Ripley prepara y despacha. El cliente paga el despacho final."
    return "El seller usa su propia flota (integrada a Envíame) y define su política de cobro al cliente."

def costos_estimados(mod, tamano, region):
    rows = []
    if mod == "Operador Logístico":
        rows = [
            ("Primera milla", "Según tamaño (SP/P2/G confirmados)", "SP $1.000 · P2 $6.690 · G $12.990"),
            ("Cliente: despacho final", "Matriz por zona/tamaño/promos", "Variable (cliente)")
        ]
    elif mod == "Crossdock":
        detalle = "Despacho RM (última milla)"
        if region == "RM" and tamano in CROSSDOCK_SCL:
            r = CROSSDOCK_SCL[tamano]
            costo = f"Ripley ${r['ripley']:,} vs externos ${r['externo']:,}".replace(",", ".")
        else:
            costo = "Según zona/tamaño; retiro en tienda $0 cuando aplica"
        rows = [
            ("Primera milla", "Seller → bodega Ripley", "SP $1.000 · P2 $6.690 · G $12.990"),
            (detalle, "Comparativa válida para RM", costo),
            ("Cliente: retiro en tienda", "Cuando aplica", "$0")
        ]
    elif mod == "Fulfillment":
        rows = [
            ("Arriendo/operación CD", "Según tamaño (tabla oficial)", "Ver ejemplos abajo"),
            ("Cliente: despacho final", "Matriz por zona/tamaño/promos", "Variable (cliente)")
        ]
    elif mod == "Flota Propia":
        if region == "RM" and tamano in FLOTA_ENV:
            rows = [("Última milla RM", f"Tarifa para {tamano}", f"${FLOTA_ENV[tamano]:,}".replace(",", "."))]
        else:
            rows = [("Última milla RM", "Tarifario Envíame (SP, P1, P2, P3, M, G, SG)", "Consultar")]
        rows.append(("Operación", "Costos internos de flota", "Combustible, choferes, seguros, mantención"))
    return pd.DataFrame(rows, columns=["Concepto", "Detalle", "Costo estimado"]).reset_index(drop=True)

def beneficios_clave(mod, tamano, region, volumen, tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca):
    b = []
    if mod == "Operador Logístico":
        b += ["Control total del inventario en tu bodega.",
              "Pagas primera milla por OC y mantienes flexibilidad.",
              "Ideal para productos pequeños/medianos con rotación moderada."]
    elif mod == "Crossdock":
        b += ["Plazos más cortos y opción de retiro en tienda.",
              "Eficiente en RM; especialmente útil para medianos/grandes."]
        if retiro_tienda: b.append("Posibilidad de $0 para el cliente con retiro en tienda (cuando aplica).")
        if region == "RM" and tamano in CROSSDOCK_SCL:
            if tamano in ["SP","XXS","XS"]:
                b.append("En pequeños, la diferencia de precio vs externos es baja (competitivo).")
            else:
                b.append("En medianos/grandes, gran ventaja de costo vs externos (puede ser hasta 12×).")
    elif mod == "Fulfillment":
        b += ["Mejora conversión por mejores SLA y experiencia.",
              "Ideal si no tienes bodega propia o si la rotación es alta.",
              "Visibilidad operacional completa en el CD de Ripley."]
    elif mod == "Flota Propia":
        b += ["Máximo control y branding propio en la entrega."]
        if region == "RM" and volumen >= 20:
            b.append("Con volumen en RM, el costo unitario mejora por optimización de rutas.")
    return b

def desventajas_clave(mod, tamano, region, volumen, tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca):
    d = []
    en_RM = (region == "RM")
    es_peq = tamano in ["SP","XXS","XS"]
    if mod == "Operador Logístico":
        d += ["Tiempos algo mayores en algunos casos frente a Crossdock/Fulfillment.",
              "Menor visibilidad punta a punta comparado con Fulfillment.",
              "Necesitas gestionar tu bodega (si no tienes, no es ideal).",
              "Dependencia de la performance del operador de última milla."]
    elif mod == "Crossdock":
        d += ["Requiere coordinación con Ripley (ventanas de retiro/entrega).",
              "Depende de bodega en RM para operar de forma óptima."]
        if en_RM and es_peq:
            d.append("En tamaños pequeños la ventaja de costo vs externos es baja.")
    elif mod == "Fulfillment":
        d += ["Costos de arriendo y operación del CD de Ripley.",
              "Menor control directo del inventario (lo gestiona el CD).",
              "Exige planificación de inbound/outbound al CD.",
              "SKU de baja rotación acumulan costo de almacenamiento por día."]
    elif mod == "Flota Propia":
        d += ["Cobertura principalmente RM (nacional acotada).",
              "Requiere inversión y gestión logística (personal, vehículos, seguros, mantención).",
              "Riesgo operativo si baja el volumen (ociosas rutas/costos fijos)."]
    return d

# ── Render de fichas ─────────────────────────────────────────────────────────
def render_ficha(ordinal_txt, modalidad, score, tamano, region, volumen,
                 tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca):
    st.markdown(
        f'<div class="rank-title"><span class="rank-badge">{ordinal_txt}:</span> '
        f'<span class="rank-name">{modalidad}</span></div>',
        unsafe_allow_html=True
    )
    st.markdown(f'<div class="subdesc">{descripcion_mod(modalidad)}</div>', unsafe_allow_html=True)

    # Costos estimados
    st.markdown('<div class="section-h3">Costos estimados</div>', unsafe_allow_html=True)
    st.table(costos_estimados(modalidad, tamano, region))  # viene sin índice

    # Beneficios
    st.markdown('<div class="section-h3">Beneficios clave</div>', unsafe_allow_html=True)
    for item in beneficios_clave(modalidad, tamano, region, volumen,
                                 tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca):
        st.write(f"• {item}")

    # Desventajas
    st.markdown('<div class="section-h3">Desventajas</div>', unsafe_allow_html=True)
    for item in desventajas_clave(modalidad, tamano, region, volumen,
                                  tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca):
        st.write(f"• {item}")

    st.markdown("---")

# ── Ejecución ────────────────────────────────────────────────────────────────
if enviado:
    ranking = rank_modalidades(
        tamano, region, volumen, tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca
    )

    ordinales = {1:"Primero", 2:"Segundo", 3:"Tercero", 4:"Cuarto"}
    for i, row in ranking.iterrows():
        pos = i + 1
        render_ficha(
            ordinales.get(pos, f"#{pos}"),
            row["Modalidad"],
            row["score"],
            tamano, region, volumen, tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca
        )

    if region == "RM":
        st.info("**Clave Santiago**: en productos pequeños la diferencia de precio con externos es baja; en medianos/grandes la ventaja de Crossdock es muy significativa.")
else:
    st.info("Completa el formulario y presiona **Ver recomendaciones** para ver las fichas por operador con Beneficios y Desventajas.")
