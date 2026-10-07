"""
Genera img/vista_previa.png: una vista previa del reporte de Power BI hecha con
Python y los mismos datos y definiciones que las medidas de powerbi/medidas.dax.

Sirve también para verificar los números del reporte: cada indicador se calcula
igual que su medida DAX.

Uso:
    python vista_previa.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import FancyBboxPatch

import graficos as g

CARPETA = Path(__file__).resolve().parent
DATOS = CARPETA / "datos"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
INICIO_12M, FIN = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-09-30")
INICIO_ANTERIOR = pd.Timestamp("2024-10-01")


def cargar():
    colaboradores = pd.read_csv(DATOS / "colaboradores.csv", parse_dates=["fecha_ingreso", "fecha_egreso"])
    planilla = pd.read_csv(DATOS / "planilla_mensual.csv", parse_dates=["fecha_periodo"])
    planilla = planilla.merge(colaboradores[["id_colaborador", "area"]], on="id_colaborador")
    return colaboradores, planilla


# --- Las mismas definiciones que las medidas DAX ------------------------------
def meses_persona(p):
    return p["dias_trabajados"].sum() / 30


def costo_mensual_por_colaborador(p):
    return p["costo_total_bs"].sum() / meses_persona(p)


def factor_de_carga(p):
    return p["costo_total_bs"].sum() / p["basico_pagado_bs"].sum()


def pct_horas_extra(p):
    return p["monto_horas_extra_bs"].sum() / p["basico_pagado_bs"].sum()


def dotacion(p, mes):
    return p.loc[p["fecha_periodo"] == mes, "id_colaborador"].nunique()


def rotacion_voluntaria(colaboradores, p, desde, hasta):
    renuncias = colaboradores[(colaboradores["tipo_egreso"] == "Renuncia voluntaria")
                              & colaboradores["fecha_egreso"].between(desde, hasta)]
    ventana = p[p["fecha_periodo"].between(desde, hasta)]
    dotacion_promedio = ventana.groupby("fecha_periodo")["id_colaborador"].nunique().mean()
    return len(renuncias) / dotacion_promedio


def indicadores(colaboradores, planilla):
    actual = planilla[planilla["fecha_periodo"] >= INICIO_12M]
    anterior = planilla[planilla["fecha_periodo"].between(INICIO_ANTERIOR, INICIO_12M - pd.Timedelta(days=1))]
    return {
        "actual": actual,
        "costo": actual["costo_total_bs"].sum(),
        "costo_anterior": anterior["costo_total_bs"].sum(),
        "por_colaborador": costo_mensual_por_colaborador(actual),
        "por_colaborador_anterior": costo_mensual_por_colaborador(anterior),
        "factor": factor_de_carga(actual),
        "horas_extra": pct_horas_extra(actual),
        "horas_extra_anterior": pct_horas_extra(anterior),
        "horas_por_persona": actual["horas_extra"].sum() / meses_persona(actual),
        "dotacion": dotacion(planilla, pd.Timestamp("2026-09-01")),
        "dotacion_anterior": dotacion(planilla, pd.Timestamp("2025-09-01")),
        "rotacion": rotacion_voluntaria(colaboradores, planilla, INICIO_12M, FIN),
        "rotacion_anterior": rotacion_voluntaria(colaboradores, planilla, INICIO_ANTERIOR,
                                                 INICIO_12M - pd.Timedelta(days=1)),
    }


# --- Piezas del tablero -------------------------------------------------------
def tarjeta(fig, rect, etiqueta, valor, variacion=None, color_variacion=g.TINTA_2):
    ax = fig.add_axes(rect)
    ax.set_axis_off()
    ax.add_patch(FancyBboxPatch((0.005, 0.02), 0.99, 0.96, boxstyle="round,pad=0,rounding_size=0.06",
                                transform=ax.transAxes, facecolor="white", edgecolor=g.GRILLA, linewidth=1))
    ax.text(0.07, 0.80, etiqueta, transform=ax.transAxes, fontsize=10.5, color=g.TINTA_2, va="center")
    ax.text(0.07, 0.47, valor, transform=ax.transAxes, fontsize=22, fontweight="bold", color=g.TINTA, va="center")
    if variacion:
        ax.text(0.07, 0.17, variacion, transform=ax.transAxes, fontsize=10, color=color_variacion, va="center")


def variacion_texto(actual, anterior, sube_es_bueno, unidad="%"):
    cambio = (actual - anterior) / anterior if unidad == "%" else actual - anterior
    signo = "+" if cambio > 0 else "−"
    favorable = (cambio > 0) == sube_es_bueno
    if unidad == "%":
        texto = f"{signo}{g.porcentaje(abs(cambio), 1)} vs. año anterior"
    else:
        texto = f"{signo}{g.miles(abs(cambio) * 100, 1)} pp vs. año anterior"
    return texto, (g.FAVORABLE if favorable else g.CRITICO)


def titulo_panel(ax, texto, subtitulo=None, x_figura=None):
    """Título del panel, alineado a x_figura (coordenadas de la figura) si se indica."""
    caja = ax.get_position()
    x = 0 if x_figura is None else (x_figura - caja.x0) / caja.width
    ax.text(x, 1.13, texto, transform=ax.transAxes, fontsize=13, fontweight="bold", color=g.TINTA, va="bottom")
    if subtitulo:
        ax.text(x, 1.04, subtitulo, transform=ax.transAxes, fontsize=10, color=g.TINTA_2, va="bottom")


def panel_tendencia(ax, planilla):
    serie = planilla.groupby("fecha_periodo")["costo_total_bs"].sum() / 1e6
    x = np.arange(len(serie))
    ax.fill_between(x, serie.values, serie.min() * 0.97, color=g.AZUL, alpha=0.10, linewidth=0)
    ax.plot(x, serie.values, color=g.AZUL, linewidth=2, solid_capstyle="round", solid_joinstyle="round")
    ax.plot(x[-1], serie.values[-1], "o", markersize=8, color=g.AZUL, markeredgecolor=g.SUPERFICIE, markeredgewidth=2)
    ax.text(x[-1], serie.values[-1] + 0.03, f"Bs {g.miles(serie.values[-1], 2)} M", ha="right", va="bottom",
            fontsize=10.5, color=g.TINTA_2)
    ax.set_ylim(serie.min() * 0.97, serie.max() * 1.04)
    ax.set_xlim(-0.5, len(serie) - 0.5)
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    marcas = [i for i, f in enumerate(serie.index) if f.month in (1, 4, 7, 10)]
    ax.set_xticks(marcas)
    ax.set_xticklabels([f"{MESES[serie.index[i].month - 1]} {str(serie.index[i].year)[2:]}" for i in marcas])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"Bs {g.miles(v, 1)} M"))
    ax.tick_params(axis="y", colors=g.TENUE, labelsize=10)
    titulo_panel(ax, "Costo laboral por mes",
                 "Sube en verano (más horas extra) y con el incremento salarial de mayo", x_figura=0.025)


def panel_por_area(ax, actual):
    # Igual que [Costo Mensual por Colaborador] con el área como filtro
    sumas = actual.groupby("area")[["costo_total_bs", "dias_trabajados"]].sum()
    por_area = (sumas["costo_total_bs"] / (sumas["dias_trabajados"] / 30)).sort_values(ascending=False)
    g.barras_horizontales(ax, por_area.index, por_area.values, [g.AZUL] * len(por_area),
                          textos=[g.bs(v) for v in por_area.values], grosor_px=16)
    ax.tick_params(axis="y", labelsize=10.5)
    titulo_panel(ax, "Costo mensual por colaborador, por área", "Últimos 12 meses", x_figura=0.60)


def panel_composicion(ax, actual):
    partes = pd.Series({
        "Básico": actual["basico_pagado_bs"].sum(),
        "Bono de antigüedad": actual["bono_antiguedad_bs"].sum(),
        "Horas extra": actual["monto_horas_extra_bs"].sum(),
        "Aportes patronales": actual["aportes_patronales_bs"].sum(),
        "Provisiones": actual["provision_aguinaldo_bs"].sum() + actual["provision_indemnizacion_bs"].sum(),
    })
    shares = partes / partes.sum()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    ax.figure.canvas.draw()
    ancho_px = ax.get_window_extent().width
    hueco = 2 / ancho_px  # 2 px de separación entre segmentos
    inicio = 0.0
    for (nombre, share), color in zip(shares.items(), g.CATEGORICOS):
        ancho = share - hueco
        ax.add_patch(FancyBboxPatch((inicio, 0.52), ancho, 0.30, boxstyle="square,pad=0",
                                    facecolor=color, edgecolor="none"))
        luminancia = np.dot(to_rgb(color), [0.299, 0.587, 0.114])
        if share * ancho_px > 48:
            ax.text(inicio + ancho / 2, 0.67, g.porcentaje(share, 1), ha="center", va="center", fontsize=10.5,
                    color="white" if luminancia < 0.6 else g.TINTA)
        inicio += share
    # Leyenda con montos: cada elemento se ubica según el ancho real de su texto
    renderer = ax.figure.canvas.get_renderer()
    x = 0.0
    for (nombre, monto), color in zip(partes.items(), g.CATEGORICOS):
        ax.add_patch(FancyBboxPatch((x, 0.27), 0.012, 0.06, boxstyle="round,pad=0,rounding_size=0.004",
                                    facecolor=color, edgecolor="none"))
        nombre_txt = ax.text(x + 0.02, 0.30, nombre, fontsize=10, color=g.TINTA_2, va="center")
        ax.text(x + 0.02, 0.14, g.bs_compacto(monto), fontsize=10, color=g.TENUE, va="center")
        x += 0.02 + nombre_txt.get_window_extent(renderer).width / ancho_px + 28 / ancho_px
    titulo_panel(ax, "En qué se va el costo laboral",
                 f"Por cada Bs 1 de sueldo básico, la empresa gasta Bs {g.miles(partes.sum() / partes['Básico'], 2)}",
                 x_figura=0.025)


def panel_horas_extra(ax, actual):
    tabla = (actual.groupby(["area", "fecha_periodo"])[["monto_horas_extra_bs", "basico_pagado_bs"]].sum()
             .eval("monto_horas_extra_bs / basico_pagado_bs").unstack())
    tabla = tabla.loc[tabla.mean(axis=1).sort_values(ascending=False).index]
    mapa = LinearSegmentedColormap.from_list("azules", g.AZULES[:11])
    ax.imshow(tabla.values, cmap=mapa, aspect="auto", vmin=0, vmax=tabla.values.max())
    for i in range(tabla.shape[0]):
        for j in range(tabla.shape[1]):
            valor = tabla.values[i, j]
            ax.text(j, i, g.porcentaje(valor), ha="center", va="center", fontsize=9,
                    color="white" if valor > tabla.values.max() * 0.55 else g.TINTA)
    ax.set_xticks(range(tabla.shape[1]))
    ax.set_xticklabels([MESES[f.month - 1] for f in tabla.columns], fontsize=9.5)
    ax.set_yticks(range(tabla.shape[0]))
    ax.set_yticklabels(tabla.index, fontsize=10)
    ax.tick_params(length=0)
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.set_xticks(np.arange(-0.5, tabla.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, tabla.shape[0]), minor=True)
    ax.grid(which="minor", color=g.SUPERFICIE, linewidth=2)
    ax.tick_params(which="minor", length=0)
    titulo_panel(ax, "Horas extra sobre el básico, por área y mes",
                 "Oct-2025 a sep-2026. Logística y Producción cargan el pico de verano", x_figura=0.60)


def main():
    g.aplicar_estilo()
    colaboradores, planilla = cargar()
    k = indicadores(colaboradores, planilla)

    fig = plt.figure(figsize=(16, 10.4))
    fig.text(0.025, 0.965, "Costos de personal", fontsize=24, fontweight="bold", color=g.TINTA, va="top")
    fig.text(0.025, 0.925, "Embotelladora ficticia · últimos 12 meses (oct-2025 a sep-2026) · montos en bolivianos",
             fontsize=12, color=g.TINTA_2, va="top")
    fig.text(0.975, 0.965, "Vista previa del reporte de Power BI", fontsize=10.5, color=g.TENUE, va="top", ha="right")
    fig.text(0.975, 0.94, "generada con Python a partir del mismo modelo", fontsize=10.5, color=g.TENUE,
             va="top", ha="right")

    tarjetas = [
        ("Costo laboral (12 meses)", g.bs_compacto(k["costo"]),
         variacion_texto(k["costo"], k["costo_anterior"], sube_es_bueno=False)),
        ("Costo mensual por colaborador", g.bs(k["por_colaborador"]),
         variacion_texto(k["por_colaborador"], k["por_colaborador_anterior"], sube_es_bueno=False)),
        ("Factor de carga laboral", g.miles(k["factor"], 2), ("Bs por cada Bs 1 de básico", g.TINTA_2)),
        ("Horas extra sobre el básico", g.porcentaje(k["horas_extra"], 1),
         (f"{g.miles(k['horas_por_persona'], 1)} horas al mes por persona", g.TINTA_2)),
        ("Dotación a sep-2026", g.miles(k["dotacion"]),
         (f"{'+' if k['dotacion'] >= k['dotacion_anterior'] else ''}{k['dotacion'] - k['dotacion_anterior']} vs. sep-2025",
          g.TINTA_2)),
        ("Rotación voluntaria (12 meses)", g.porcentaje(k["rotacion"], 1),
         variacion_texto(k["rotacion"], k["rotacion_anterior"], sube_es_bueno=False, unidad="pp")),
    ]
    ancho, separacion, x0 = 0.150, 0.01, 0.025
    for i, (etiqueta, valor, (variacion, color)) in enumerate(tarjetas):
        tarjeta(fig, [x0 + i * (ancho + separacion), 0.765, ancho, 0.125], etiqueta, valor, variacion, color)

    panel_tendencia(fig.add_axes([0.075, 0.43, 0.48, 0.23]), planilla)
    panel_por_area(fig.add_axes([0.70, 0.43, 0.215, 0.23]), k["actual"])
    panel_composicion(fig.add_axes([0.025, 0.06, 0.53, 0.25]), k["actual"])
    panel_horas_extra(fig.add_axes([0.70, 0.06, 0.275, 0.25]), k["actual"])

    fig.text(0.025, 0.012, g.FUENTE, fontsize=9, color=g.TENUE)
    salida = CARPETA / "img" / "vista_previa.png"
    salida.parent.mkdir(exist_ok=True)
    fig.savefig(salida, dpi=120)
    print(f"Guardado: {salida.relative_to(CARPETA)}")
    print("\nValores de control (oct-2025 a sep-2026), los mismos que devuelve la consulta de powerbi/medidas.dax:")
    for nombre, valor in valores_de_control(colaboradores, planilla).items():
        print(f"  {nombre:<32}{valor:>18,.4f}")


def valores_de_control(colaboradores, planilla):
    """Las 15 cifras que devuelve el EVALUATE de powerbi/medidas.dax, calculadas con pandas."""
    actual = planilla[planilla["fecha_periodo"].between(INICIO_12M, FIN)]
    anterior = planilla[planilla["fecha_periodo"].between(INICIO_ANTERIOR, INICIO_12M - pd.Timedelta(days=1))]
    gestion = planilla[planilla["fecha_periodo"].between(pd.Timestamp("2026-04-01"), FIN)]
    egresos = colaboradores[colaboradores["fecha_egreso"].between(INICIO_12M, FIN)]
    renuncias = (egresos["tipo_egreso"] == "Renuncia voluntaria").sum()
    dotacion_promedio = actual.groupby("fecha_periodo")["id_colaborador"].nunique().mean()
    costo, costo_anterior = actual["costo_total_bs"].sum(), anterior["costo_total_bs"].sum()
    return {
        "Costo Laboral": costo,
        "Costo Últimos 12 Meses": costo,
        "Costo Año Anterior": costo_anterior,
        "Var % Interanual": costo / costo_anterior - 1,
        "Costo Acumulado Gestión": gestion["costo_total_bs"].sum(),
        "Costo Mensual por Colaborador": costo_mensual_por_colaborador(actual),
        "Factor de Carga Laboral": factor_de_carga(actual),
        "% Horas Extra sobre Básico": pct_horas_extra(actual),
        "Horas Extra por Colaborador": actual["horas_extra"].sum() / meses_persona(actual),
        "% Ausentismo": actual["dias_ausencia"].sum() / actual["dias_trabajados"].sum(),
        "Dotación": dotacion(planilla, pd.Timestamp("2026-09-01")),
        "Dotación Promedio": dotacion_promedio,
        "Egresos": len(egresos),
        "Renuncias": renuncias,
        "Rotación Voluntaria %": renuncias / dotacion_promedio,
    }


if __name__ == "__main__":
    main()
