# ──────────────────────────────────────────────────────────────────────────────
# APP DE OPERADORES LOGÍSTICOS — v2 (formulario, sin Excel)
# ──────────────────────────────────────────────────────────────────────────────
import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Recomendación de Operadores (v2)", layout="wide")
st.title("Operadores Logísticos — Recomendador (Formulario)")

# ── Datos confirmados que usaremos en explicaciones/costos ────────────────────
# Comparativa de despacho Santiago: Crossdock vs operadores externos
CROSSDOCK_SCL = {
    "SP":   {"ripley": 3990,  "externo": 3990},
    "XXS":  {"ripley": 4990,  "externo": 7990},
    "XS":   {"ripley": 9990,  "externo": 14990},
    "S":    {"ripley": 9990,  "externo": 19990},
    "M1":   {"ripley": 10990, "externo": 39990},
    "M2":   {"ripley": 13990, "externo": 79990},
    "L/XL": {"ripley": 16990, "externo": 199990},
}

# Fulfillment: almacenamiento + cofinanciamiento (tabla oficial compartida)
FULF_STORAGE = [
    "XXXS: $0,3/día + $1.000 / $2.600 por venta",
    "S: $7/día + $4.500 por venta",
    "M1: $20/día + $6.800 por venta",
    "XXL: $260/día + $8.500 por venta",
    "XXXL: $400/día + $11.000 por venta",
]

# Flota propia (Ripley – Envíame) RM
FLOTA_ENV = {
    "SP": 3200, "P1": 3200, "P2": 4990, "P3": 5990, "M": 5990, "G": 6990, "SG": 18740
}

# ── Formulario de entrada (sin archivos) ──────────────────────────────────────
with st.form("selector"):
    st.subheader("Tu escenario")

    colA, colB, colC = st.columns(3)
    with colA:
        tamano = st.selectbox(
            "Tamaño del producto",
            ["SP","XXS","XS","S","M1","M2","L/XL"],
            help="Usaremos esta tabla de tamaños para la comparativa de Santiago."
        )
        region = st.selectbox("Región de operación principal", ["RM","Otra"])
        volumen = st.number_input("Órdenes diarias (promedio)", min_value=0, step=1, value=10)

    with colB:
        tiene_bodega = st.radio("¿Tienes bodega propia?", ["Sí","No"], index=0)
        alta_rotacion = st.checkbox("Alta rotación", value=True,
                                    help="Ventas frecuentes / reposición rápida")
        necesita_velocidad = st.checkbox("Necesito velocidad de entrega", value=True)

    with colC:
        retiro_tienda = st.checkbox("Ofrecer retiro en tienda", value=True)
        foco_control_marca = st.checkbox("Quiero máximo control/branding de entrega", value=False)
        cobertura_nacional = st.checkbox("Necesito cobertura nacional", value=True)

    enviado = st.form_submit_button("Ver recomendaciones")

# ── Motor de decisión (coherente/consistente) ────────────────────────────────
def puntuar_modalidades(
    tamano, region, volumen, tiene_bodega, alta_rotacion, necesita_velocidad,
    retiro_tienda, foco_control_marca, cobertura_nacional
):
    """
    Devuelve un DataFrame con score y explicación por modalidad.
    Criterios ponderados de forma consistente con lo acordado:
    - Productos grandes en RM favorecen Crossdock (costos confirmados muy inferiores a externos).
    - Alta rotación y/o sin bodega favorece Fulfillment (a pesar del arriendo).
    - Control/branding y alto volumen en RM favorecen Flota Propia (Envíame).
    - Si ya tiene bodega y productos pequeños/medianos, Operador Logístico es natural.
    """
    # Normalizaciones y flags
    en_RM = (region == "RM")
    sin_bodega = (tiene_bodega == "No")
    es_pequeno = tamano in ["SP","XXS","XS"]
    es_mediano = tamano in ["S","M1"]
    es_grande  = tamano in ["M2","L/XL"]

    # Base de criterios
    # pesos "globales" (no visibles en UI, pero coherentes con decisiones):
    W = {
        "costo": 0.40,        # sensibilidad a costo total
        "velocidad": 0.25,    # tiempos de entrega / experiencia
        "control": 0.20,      # control del seller / branding
        "cobertura": 0.15,    # alcance geográfico / capilaridad
    }

    # Perfil por modalidad (valores base entre 0..1 antes de ajustar por inputs)
    perfiles = {
        "Operador Logístico": {"costo": 0.6, "velocidad": 0.5, "control": 0.8, "cobertura": 0.6},
        "Crossdock":          {"costo": 0.8, "velocidad": 0.7, "control": 0.6, "cobertura": 0.7},
        "Fulfillment":        {"costo": 0.5, "velocidad": 0.9, "control": 0.4, "cobertura": 0.8},
        "Flota Propia":       {"costo": 0.6, "velocidad": 0.7, "control": 1.0, "cobertura": 0.4},
    }

    # Ajustes por contexto (coherencia con lo conversado)
    # Tamaño/Región:
    if en_RM and (es_mediano or es_grande):
        # Crossdock gana en costo de forma marcada en RM para medianos/grandes
        perfiles["Crossdock"]["costo"] += 0.15
        perfiles["Crossdock"]["velocidad"] += 0.05
    if es_pequeno:
        # En pequeños, la diferencia de costo vs externos es baja: bajamos ventaja relativa
        perfiles["Crossdock"]["costo"] -= 0.05

    # Rotación / Bodega
    if alta_rotacion or sin_bodega:
        # Fulfillment sube por SLA/velocidad y simplicidad operativa
        perfiles["Fulfillment"]["velocidad"] += 0.05
        perfiles["Fulfillment"]["cobertura"] += 0.05
        perfiles["Fulfillment"]["costo"] -= 0.05  # el costo relativo “se compensa” por eficiencia

    # Control / Branding
    if foco_control_marca and en_RM and volumen >= 20:
        perfiles["Flota Propia"]["control"] += 0.05
        perfiles["Flota Propia"]["velocidad"] += 0.05
        # costo mejora con volumen (optimización de rutas):
        perfiles["Flota Propia"]["costo"] += 0.05

    # Cobertura nacional
    if cobertura_nacional:
        perfiles["Flota Propia"]["cobertura"] -= 0.1  # limitada a RM
        perfiles["Operador Logístico"]["cobertura"] += 0.05
        perfiles["Fulfillment"]["cobertura"] += 0.05

    # Si ya tiene bodega y productos pequeños/medianos → Operador Logístico gana lógica
    if (tiene_bodega == "Sí") and (es_pequeno or es_mediano):
        perfiles["Operador Logístico"]["control"] += 0.05
        perfiles["Operador Logístico"]["costo"] += 0.05

    # Calcular score final por modalidad
    filas = []
    for mod, p in perfiles.items():
        score = (
            W["costo"]     * p["costo"] +
            W["velocidad"] * p["velocidad"] +
            W["control"]   * p["control"] +
            W["cobertura"] * p["cobertura"]
        )

        # Explicación breve (top drivers)
        drivers = sorted(p.items(), key=lambda x: x[1], reverse=True)
        top2 = [drivers[0][0].capitalize(), drivers[1][0].capitalize()]
        filas.append({"Modalidad": mod, "score": score, "top": top2, "perfil": p})

    df = pd.DataFrame(filas).sort_values("score", ascending=False).reset_index(drop=True)
    return df

# ── Render de resultados ─────────────────────────────────────────────────────
def explicar_costos_y_desventajas(modalidad, tamano, region, volumen):
    if modalidad == "Crossdock":
        # Comparativa para Santiago solamente si RM:
        if region == "RM" and tamano in CROSSDOCK_SCL:
            r = CROSSDOCK_SCL[tamano]
            nota = "En pequeños la diferencia es baja; en medianos/grandes la brecha es muy significativa."
            return (
                "Desventajas: requiere coordinación con Ripley; depende de bodega en RM.\n"
                f"Costos (Santiago): Ripley ${r['ripley']:,} vs operadores externos ${r['externo']:,}. {nota}"
            )
        else:
            return "Desventajas: requiere coordinación con Ripley; depende de bodega en RM."
    elif modalidad == "Fulfillment":
        lista = " • " + "\n • ".join(FULF_STORAGE)
        return (
            "Desventajas: costos de arriendo/operación; menor control directo del inventario.\n"
            f"Costos confirmados (almacenamiento + cofinanciamiento):\n{lista}"
        )
    elif modalidad == "Flota Propia":
        # Mostrar tarifa solo si el tamaño coincide con el tarifario
        if tamano in FLOTA_ENV:
            return (
                "Desventajas: limitado a RM; requiere organización logística; menor cobertura nacional.\n"
                f"Tarifa última milla (RM) para {tamano}: ${FLOTA_ENV[tamano]:,}"
            )
        else:
            return (
                "Desventajas: limitado a RM; requiere organización logística; menor cobertura nacional.\n"
                "Tarifario confirmado disponible (SP, P1, P2, P3, M, G, SG)."
            )
    else:  # Operador Logístico
        return (
            "Desventajas: tiempos algo mayores en algunos casos; menor visibilidad de punta a punta.\n"
            "Costos confirmados primera milla: SP $1.000, P2 $6.690, G $12.990."
        )

# ── Lógica de ejecución ──────────────────────────────────────────────────────
if enviado:
    ranking = puntuar_modalidades(
        tamano, region, volumen, tiene_bodega, alta_rotacion, necesita_velocidad,
        retiro_tienda, foco_control_marca, cobertura_nacional
    )

    st.success("Recomendaciones generadas según tu escenario.")
    ordinal = {1:"Primero",2:"Segundo",3:"Tercero",4:"Cuarto"}

    for i, row in ranking.iterrows():
        pos = i + 1
        mod = row["Modalidad"]
        st.subheader(f"**{ordinal.get(pos, f'#{pos}')}** — {mod}")
        st.write(f"**Score:** {row['score']:.3f}")
        st.caption(f"Fortalezas: {', '.join(row['top'])}.")
        st.text(explorar := explicar_costos_y_desventajas(mod, tamano, region, volumen))
        st.divider()

    # Tabla resumen compacta
    with st.expander("Ver resumen (scores y drivers)"):
        vista = ranking[["Modalidad","score","top"]].copy()
        vista["score"] = vista["score"].round(3)
        st.dataframe(vista, use_container_width=True)

else:
    st.info("Completa el formulario y presiona **Ver recomendaciones** para ver el orden sugerido.")


# ── Render ───────────────────────────────────────────────────────────────────
if enviado:
    ranking = puntuar_modalidades(
        tamano, region, volumen, tiene_bodega,
        alta_rotacion, necesita_velocidad,
        retiro_tienda, foco_control_marca, cobertura_nacional
    )

    st.success("Recomendaciones generadas según tu escenario.")
    ordinal = {1:"Primero",2:"Segundo",3:"Tercero",4:"Cuarto"}

    for i, row in ranking.iterrows():
        pos = i + 1
        mod = row["Modalidad"]
        st.subheader(f"**{ordinal.get(pos, f'#{pos}')}** — {mod}")
        st.write(f"**Score:** {row['score']:.3f}")

        # Ventajas, Desventajas y Notas/Costos
        ventajas, desventajas = ventajas_y_desventajas(
            mod, tamano, region, volumen, tiene_bodega,
            alta_rotacion, necesita_velocidad, retiro_tienda,
            foco_control_marca, cobertura_nacional
        )

        # Separamos: ventajas / desventajas, y mandamos los costos/notas a la tercera col
        notas = []
        ven = []
        des = []
        for v in ventajas:
            if "Tarifa" in v or "$" in v:
                notas.append(v); ven.append("")
            else:
                ven.append(v)
        for d in desventajas:
            if "Tarifa" in d or "$" in d:
                notas.append(d); des.append("")
            else:
                des.append(d)

        # Normalizamos largos
        max_len = max(len(ven), len(des), len(notas))
        ven += [""]*(max_len - len(ven))
        des += [""]*(max_len - len(des))
        notas += [""]*(max_len - len(notas))

        df_comp = pd.DataFrame({
            "Ventajas": ven,
            "Desventajas": des,
            "Notas/Costos": notas
        })

        st.table(df_comp)
        st.divider()

    if region == "RM":
        st.info("**Clave Santiago**: En productos pequeños la diferencia de precio con externos es baja; en medianos/grandes la ventaja de Crossdock (Ripley) es muy significativa.")

else:
    st.info("Completa el formulario y presiona **Ver recomendaciones** para ver el orden sugerido con tablas comparativas por operador.")
