import streamlit as st
import pandas as pd

# ---------- Configuración de página ----------
st.set_page_config(page_title="Guía Logística Ripley – Ranking de Opciones", page_icon="🚚", layout="centered")

PRIMARY = "#E6007E"
BLACK = "#000000"

# ---------- Estilos ----------
st.markdown(
    f"""
    <style>
    .main .block-container {{ padding-top: 2rem; padding-bottom: 3rem; }}
    .ripley-title {{ font-weight: 800; font-size: 1.8rem; color: {BLACK}; margin-bottom: 0.2rem; }}
    .ripley-sub {{ color: #555; margin-bottom: 1.2rem; }}
    .badge {{ border: 1px solid {PRIMARY}; color: {PRIMARY}; padding: 0.2rem 0.5rem; border-radius: 8px; font-size: 0.8rem; }}
    .section-title {{ margin-top: 1.2rem; font-size: 1.1rem; font-weight: 700; }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Datos ----------
FIRST_MILE = {
    "SP": {"lt_24990": 1000, "ge_24990": 2690},
    "P1": {"flat": 4590},
    "P2": {"flat": 6690},
    "P3": {"flat": 7790},
    "M": {"flat": 8790},
    "G": {"flat": 12990},
    "SG": {"flat": 21490},
}

REVERSE = {
    "SP": 2800, "P1": 2800, "P2": 6000, "P3": 11000,
    "M": 20000, "G": 23900, "SG": 23900
}

CLASSES_INFO = {
    "SP": "Super Pequeño (ej: smartphone)",
    "P1": "Pequeño 1 (ej: bici infantil)",
    "P2": "Pequeño 2 (ej: silla de escritorio)",
    "P3": "Pequeño 3 (ej: set de 4 neumáticos)",
    "M": "Mediano (ej: congeladora)",
    "G": "Grande (ej: living)",
    "SG": "Súper Grande (ej: sofá seccional)",
}

MODALITY_EXPLAIN = {
    "Operador Logístico": "El seller maneja su stock y paga la primera milla. El cliente paga el despacho final.",
    "Crossdock": "Ripley retira en la bodega del seller. El cliente paga el despacho final o $0 si retiro en tienda.",
    "Fulfillment": "Ripley almacena y opera el inventario del seller (cofinanciado). El cliente paga el despacho final.",
}

BENEFICIOS = {
    "Operador Logístico": [
        "Control total del inventario en tu bodega.",
        "Pagas primera milla por OC y mantienes flexibilidad.",
        "Ideal para productos pequeños/medianos y rotación moderada."
    ],
    "Crossdock": [
        "Ripley retira en tu bodega: menos fricción operacional.",
        "Puedes ofrecer retiro en tienda (cliente sin costo de despacho).",
        "Útil para órdenes grandes o productos voluminosos."
    ],
    "Fulfillment": [
        "Mayor conversión por velocidad de despacho.",
        "Ripley opera almacenamiento, picking y packing.",
        "Recomendado para alta rotación o si no tienes bodega."
    ]
}

# ---------- Funciones ----------
def calcular_primera_milla(clase: str, precio: float, modalidad: str):
    if modalidad == "Fulfillment":
        return 0, "No aplica (stock en CD Ripley)."
    if clase == "SP":
        if precio < 24990:
            return FIRST_MILE["SP"]["lt_24990"], "SP < $24.990"
        else:
            return FIRST_MILE["SP"]["ge_24990"], "SP ≥ $24.990"
    return FIRST_MILE[clase]["flat"], f"{clase} tarifa fija"

def tabla_costos_modalidad(modalidad: str, clase: str, precio: float):
    pm_val, pm_nota = calcular_primera_milla(clase, precio, modalidad)
    rev_val = REVERSE[clase]
    return pd.DataFrame({
        "Concepto": ["Primera milla", "Logística inversa", "Cliente: despacho final"],
        "Detalle": [pm_nota, f"{clase} ({CLASSES_INFO[clase]})", "Matriz estándar por zona/tamaño/promos"],
        "Costo estimado": [
            "$0" if pm_val == 0 else f"${pm_val:,.0f}".replace(",", "."),
            f"${rev_val:,.0f}".replace(",", "."),
            "Variable (mismo cálculo en todas las modalidades)"
        ]
    })

def puntuar_modalidades(bodega: bool, voluminoso: bool, alta_rot: bool):
    puntajes = {"Operador Logístico": 0, "Crossdock": 0, "Fulfillment": 0}
    if not bodega:
        puntajes["Fulfillment"] += 3
    else:
        puntajes["Operador Logístico"] += 1
        if voluminoso:
            puntajes["Crossdock"] += 3
        else:
            puntajes["Operador Logístico"] += 2
        if alta_rot:
            puntajes["Fulfillment"] += 2
    if alta_rot:
        puntajes["Fulfillment"] += 1
    return sorted(puntajes.items(), key=lambda x: x[1], reverse=True)

# ---------- UI ----------
st.markdown('<div class="ripley-title">Guía Logística Ripley – Ranking de Opciones</div>', unsafe_allow_html=True)
st.markdown('<div class="ripley-sub">Responde 3 preguntas y te mostraremos todas las modalidades ordenadas de la más recomendada a la menos recomendada.</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    bodega = st.radio("¿Tienes bodega propia?", ["Sí", "No"], index=0, horizontal=True)
    voluminoso = st.radio("¿Tus productos son grandes/voluminosos?", ["Sí", "No"], index=1, horizontal=True)
with col2:
    rotacion = st.radio("¿Alta rotación y necesitas entregas rápidas?", ["Sí", "No"], index=0, horizontal=True)
    clase = st.selectbox(
        "Selecciona la clase logística más alta de tu orden",
        list(CLASSES_INFO.keys()),
        format_func=lambda k: f"{k} – {CLASSES_INFO[k]}",
        index=2
    )

precio = st.number_input("Precio referencial del producto (CLP)", min_value=0, value=29990, step=1000)

if st.button("Ver ranking"):
