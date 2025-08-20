# ──────────────────────────────────────────────────────────────────────────────
# APP DE OPERADORES LOGÍSTICOS — v6
# Formato de ficha por operador: título (ordinal en fucsia), descripción,
# "Costos estimados" (tabla sin índice), "Ejemplos de almacenamiento/venta"
# para Fulfillment, "Beneficios clave" y "Desventajas".
# Sin archivos ni Excel.
# ──────────────────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Recomendación de Operadores (v6)", layout="wide")
st.title("Operadores Logísticos — Recomendador")

# ── Estilos globales (títulos y tablas) ───────────────────────────────────────
st.markdown(
    """
    <style>
    .rank-title { font-size: 40px; font-weight: 800; margin: 8px 0 0 0; }
    .rank-badge { color: #E91E63; }       /* fucsia estilo Ripley */
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

# ── Datos confirmados para costos / notas ─────────────────────────────────────
# Comparativa de despacho para la Región Metropolitana (Crossdock vs operadores externos)
CROSSDOCK_SCL = {
    "SP":   {"ripley": 3990,  "externo": 3990},
    "XXS":  {"ripley": 4990,  "externo": 7990},
    "XS":   {"ripley": 9990,  "externo": 14990},
    "S":    {"ripley": 9990,  "externo": 19990},
    "M1":   {"ripley": 10990, "externo": 39990},
    "M2":   {"ripley": 13990, "externo": 79990},
    "L/XL": {"ripley": 16990, "externo": 199990},
}

# Fulfillment: almacenamiento (arriendo) + cofinanciamiento por venta (tabla oficial)
FULF_STORAGE = [
    "XXXS: $0,3 por día + $1.000 / $2.600 por venta",
    "S: $7 por día + $4.500 por venta",
    "M1: $20 por día + $6.800 por venta",
    "XXL: $260 por día + $8.500 por venta",
    "XXXL: $400 por día + $11.000 por venta",
]

# Flota propia (Ripley – Envíame) para la Región Metropolitana
FLOTA_ENV = {
    "SP": 3200, "P1": 3200, "P2": 4990, "P3": 5990, "M": 5990, "G": 6990, "SG": 18740
}

# ── Formulario (sin archivos) ────────────────────────────────────────────────
with st.form("selector"):
    st.subheader("Tu escenario")

    colA, colB, colC = st.columns(3)
    with colA:
        tamano = st.selectbox("Tamaño del producto", ["SP", "XXS", "XS", "S", "M1", "M2", "L/XL"])
        region = st.selectbox("Región de operación principal", ["Región Metropolitana", "Otra región"])
        volumen = st.number_input("Órdenes diarias (promedio)", min_value=0, step=1, value=10)
    with colB:
        tiene_bodega = st.radio("¿Tienes bodega propia?", ["Sí", "No"], index=0)
        alta_rotacion = st.checkbox("Alta rotación (ventas frecuentes)", value=True)
    with colC:
        retiro_tienda = st.checkbox("Ofrecer retiro en tienda", value=True)
        foco_control_marca = st.checkbox("Quiero máximo control y branding en la entrega", value=False)

    enviado = st.form_submit_button("Ver recomendaciones")

# ── Motor de puntuación (consistente con decisiones previas) ─────────────────
def rank_modalidades(tamano, region, volumen, tiene_bodega, alta_rotacion,
                     retiro_tienda, foco_control_marca):
    en_region_metropolitana = (region == "Región Metropolitana")
    es_pequeno = tamano in ["SP", "XXS", "XS"]
    es_mediano = tamano in ["S", "M1"]
    es_grande  = tamano in ["M2", "L/XL"]
    sin_bodega = (tiene_bodega == "No")

    # Pesos globales (costo, velocidad, control, cobertura)
    pesos = {"costo": 0.42, "velocidad": 0.28, "control": 0.20, "cobertura": 0.10}

    perfiles = {
        "Operador Logístico": {"costo": 0.60, "velocidad": 0.50, "control": 0.80, "cobertura": 0.65},
        "Crossdock":          {"costo": 0.80, "velocidad": 0.70, "control": 0.60, "cobertura": 0.70},
        "Fulfillment":        {"costo": 0.50, "velocidad": 0.90, "control": 0.40, "cobertura": 0.80},
        "Flota Propia":       {"costo": 0.60, "velocidad": 0.70, "control": 1.00, "cobertura": 0.45},
    }

    # Ajustes por contexto:
    if en_region_metropolitana and (es_mediano or es_grande):
        perfiles["Crossdock"]["costo"] += 0.15
        perfiles["Crossdock"]["velocidad"] += 0.05
    if es_pequeno:
        # En tamaños pequeños la diferencia de precio frente a operadores externos es baja.
        perfiles["Crossdock"]["costo"] -= 0.05

    if alta_rotacion or sin_bodega:
        perfiles["Fulfillment"]["velocidad"] += 0.05
        perfiles["Fulfillment"]["cobertura"] += 0.05
        perfiles["Fulfillment"]["costo"] -= 0.05

    if foco_control_marca and en_region_metropolitana and volumen >= 20:
        perfiles["Flota Propia"]["control"] += 0.05
        perfiles["Flota Propia"]["velocidad"] += 0.05
        perfiles["Flota Propia"]["costo"] += 0.05  # el volumen ayuda a optimizar rutas y costo unitario

    if (tiene_bodega == "Sí") and (es_pequeno or es_mediano):
        perfiles["Operador Logístico"]["control"] += 0.05
        perfiles["Operador Logístico"]["costo"] += 0.05

    # Cálculo del puntaje compuesto
    filas = []
    for modalidad, p in perfiles.items():
        score = (pesos["costo"] * p["costo"] +
                 pesos["velocidad"] * p["velocidad"] +
                 pesos["control"] * p["control"] +
                 pesos["cobertura"] * p["cobertura"])
        filas.append({"Modalidad": modalidad, "score": score})
    return pd.DataFrame(filas).sort_values("score", ascending=False).reset_index(drop=True)

# ── Descripción, costos, beneficios y desventajas ────────────────────────────
def descripcion_mod(modalidad: str) -> str:
    if modalidad == "Operador Logístico":
        return "El vendedor maneja su stock y paga la primera milla. El cliente paga el despacho final."
    if modalidad == "Crossdock":
        return "Ripley retira o recibe en la bodega del vendedor y distribuye. El cliente paga el despacho final o puede retirar en tienda."
    if modalidad == "Fulfillment":
        return "El stock queda en la bodega de Ripley; Ripley prepara y despacha. El cliente paga el despacho final."
    # Flota Propia
    return "El vendedor usa su propia flota (integrada a Envíame) y define su política de cobro al cliente."

def costos_estimados(modalidad: str, tamano: str, region: str):
    """
    Devuelve:
      - Para Operador Logístico, Crossdock y Flota Propia: DataFrame base (sin índice).
      - Para Fulfillment: (DataFrame base, DataFrame de ejemplos por tamaño).
    """
    if modalidad == "Operador Logístico":
        base = pd.DataFrame(
            [
                ("Primera milla", "Según tamaño (SP / P2 / G confirmados)", "SP $1.000 · P2 $6.690 · G $12.990"),
                ("Cliente: despacho final", "Matriz por zona, tamaño y promociones", "Variable (cliente)"),
            ],
            columns=["Concepto", "Detalle", "Costo estimado"],
        )
        return base.reset_index(drop=True)

    if modalidad == "Crossdock":
        detalle = "Despacho Región Metropolitana (última milla)"
        if (region == "Región Metropolitana") and (tamano in CROSSDOCK_SCL):
            r = CROSSDOCK_SCL[tamano]
            costo = f"Ripley ${r['ripley']:,} vs operadores externos ${r['externo']:,}".replace(",", ".")
        else:
            costo = "Según zona y tamaño; retiro en tienda $0 cuando aplica"
        base = pd.DataFrame(
            [
                ("Primera milla", "Bodega del vendedor → bodega de Ripley", "SP $1.000 · P2 $6.690 · G $12.990"),
                (detalle, "Comparativa válida para la Región Metropolitana", costo),
                ("Cliente: retiro en tienda", "Cuando aplica", "$0"),
            ],
            columns=["Concepto", "Detalle", "Costo estimado"],
        )
        return base.reset_index(drop=True)

    if modalidad == "Fulfillment":
        base = pd.DataFrame(
            [
                ("Arriendo y operación de centro de distribución", "Según tamaño (tabla oficial)", "Ejemplos más abajo"),
                ("Cliente: despacho final", "Matriz por zona, tamaño y promociones", "Variable (cliente)"),
            ],
            columns=["Concepto", "Detalle", "Costo estimado"],
        ).reset_index(drop=True)

        ejemplos = pd.DataFrame(
            [s.split(": ") for s in FULF_STORAGE],
            columns=["Tamaño", "Costo estimado"],
        ).reset_index(drop=True)

        return base, ejemplos

    # Flota Propia
    if (region == "Región Metropolitana") and (tamano in FLOTA_ENV):
        base = pd.DataFrame(
            [
                ("Última milla Región Metropolitana", f"Tarifa para {tamano}", f"${FLOTA_ENV[tamano]:,}".replace(",", ".")),
                ("Operación", "Costos internos de flota", "Combustible, conductores, seguros, mantención"),
            ],
            columns=["Concepto", "Detalle", "Costo estimado"],
        )
    else:
        base = pd.DataFrame(
            [
                ("Última milla Región Metropolitana", "Tarifario Envíame (SP, P1, P2, P3, M, G, SG)", "Consultar"),
                ("Operación", "Costos internos de flota", "Combustible, conductores, seguros, mantención"),
            ],
            columns=["Concepto", "Detalle", "Costo estimado"],
        )
    return base.reset_index(drop=True)

def beneficios_clave(modalidad, tamano, region, volumen, tiene_bodega, alta_rotacion,
                     retiro_tienda, foco_control_marca):
    beneficios = []
    if modalidad == "Operador Logístico":
        beneficios += [
            "Control total del inventario en tu bodega.",
            "Pagas primera milla por orden de compra y mantienes flexibilidad.",
            "Ideal para productos pequeños o medianos con rotación moderada.",
        ]
    elif modalidad == "Crossdock":
        beneficios += [
            "Plazos de entrega más cortos y opción de retiro en tienda.",
            "Operación eficiente en la Región Metropolitana; especialmente útil para productos medianos o grandes.",
        ]
        if retiro_tienda:
            beneficios.append("Posibilidad de $0 para el cliente con retiro en tienda (cuando aplica).")
        if (region == "Región Metropolitana") and (tamano in CROSSDOCK_SCL):
            if tamano in ["SP", "XXS", "XS"]:
                beneficios.append("En productos pequeños la diferencia de precio versus operadores externos es baja (competitivo).")
            else:
                beneficios.append("En productos medianos o grandes, gran ventaja de costo versus operadores externos (puede ser hasta 12×).")
    elif modalidad == "Fulfillment":
        beneficios += [
            "Mejora la conversión por mejores niveles de servicio (SLA) y experiencia de entrega.",
            "Ideal si no tienes bodega propia o si la rotación es alta.",
            "Mayor visibilidad operacional (inventario, preparación y despacho) desde el centro de distribución de Ripley.",
        ]
    elif modalidad == "Flota Propia":
        beneficios += [
            "Máximo control y branding propio en la entrega.",
        ]
        if (region == "Región Metropolitana") and (volumen >= 20):
            beneficios.append("Con volumen en la Región Metropolitana, el costo unitario mejora por optimización de rutas.")
    return beneficios

def desventajas_clave(modalidad, tamano, region, volumen, tiene_bodega, alta_rotacion,
                      retiro_tienda, foco_control_marca):
    desventajas = []
    en_rm = (region == "Región Metropolitana")
    es_pequeno = tamano in ["SP", "XXS", "XS"]

    if modalidad == "Operador Logístico":
        desventajas += [
            "Tiempos de entrega algo mayores en algunos casos frente a Crossdock o Fulfillment.",
            "Menor visibilidad punta a punta comparado con Fulfillment.",
            "Necesitas gestionar tu bodega (si no tienes bodega, no es ideal).",
            "Dependencia de la performance del operador de última milla.",
        ]
    elif modalidad == "Crossdock":
        desventajas += [
            "Requiere coordinación con Ripley (ventanas de retiro y entrega).",
            "Depende de contar con bodega en la Región Metropolitana para operar de forma óptima.",
        ]
        if en_rm and es_pequeno:
            desventajas.append("En tamaños pequeños la ventaja de costo versus operadores externos es baja.")
    elif modalidad == "Fulfillment":
        desventajas += [
            "Costos de arriendo y operación del centro de distribución de Ripley.",
            "Menor control directo del inventario (lo gestiona el centro de distribución).",
            "Exige planificación de entrada y salida de productos del centro de distribución.",
            "Los productos de baja rotación acumulan costo de almacenamiento por día.",
        ]
    elif modalidad == "Flota Propia":
        desventajas += [
            "Cobertura principalmente en la Región Metropolitana (alcance nacional acotado).",
            "Requiere inversión y gestión logística (personal, vehículos, seguros y mantención).",
            "Riesgo operativo si baja el volumen (rutas ociosas y costos fijos).",
        ]
    return desventajas

# ── Render de fichas ─────────────────────────────────────────────────────────
def render_ficha(ordinal_txt, modalidad, score, tamano, region, volumen,
                 tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca):
    # Título grande
    st.markdown(
        f'<div class="rank-title"><span class="rank-badge">{ordinal_txt}:</span> '
        f'<span class="rank-name">{modalidad}</span></div>',
        unsafe_allow_html=True
    )
    # Descripción breve
    st.markdown(f'<div class="subdesc">{descripcion_mod(modalidad)}</div>', unsafe_allow_html=True)

    # Costos estimados (y ejemplos si es Fulfillment)
    st.markdown('<div class="section-h3">Costos estimados</div>', unsafe_allow_html=True)
    costos = costos_estimados(modalidad, tamano, region)
    if isinstance(costos, tuple):
        base, ejemplos = costos
        st.table(base)        # sin índice
        st.markdown('<div class="section-h3">Ejemplos de almacenamiento y cofinanciamiento por venta</div>', unsafe_allow_html=True)
        st.table(ejemplos)    # sin índice
    else:
        st.table(costos)      # sin índice

    # Beneficios clave
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

    ordinales = {1: "Primero", 2: "Segundo", 3: "Tercero", 4: "Cuarto"}
    for i, row in ranking.iterrows():
        posicion = i + 1
        render_ficha(
            ordinales.get(posicion, f"#{posicion}"),
            row["Modalidad"],
            row["score"],
            tamano, region, volumen, tiene_bodega, alta_rotacion, retiro_tienda, foco_control_marca
        )

    if region == "Región Metropolitana":
        st.info("Clave para Santiago: en productos pequeños la diferencia de precio frente a operadores externos es baja; en productos medianos o grandes la ventaja de Crossdock es muy significativa.")
else:
    st.info("Completa el formulario y presiona “Ver recomendaciones” para ver las fichas por operador con costos, ejemplos (en Fulfillment), beneficios y desventajas.")
