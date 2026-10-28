"""
Versión ejecutiva (para público no técnico) del análisis de un DNI consultado.
Reutiliza la carga y las métricas de analizar_dni.py.

Uso:
    python analizar_dni_ejecutivo.py "data/4. PIDE_UNI_SA_OCT2026.xlsx"
    python analizar_dni_ejecutivo.py archivo.xlsx --dni 73018031
    python analizar_dni_ejecutivo.py archivo.xlsx --top 3 --salida output/analisis_dni_ejecutivo

Genera en <salida>/<archivo>/<dni>/:
    A_reloj_24h.png         ¿A qué horas consulta? (reloj de 24 h)
    B_mapa_calor.png        ¿Qué días y horas? (grilla día x hora)
    C_zoom_1_hora.png       ¿Cómo se ve una hora real? (metrónomo vs desorden)
    D_cifras_clave.png      Las 4 cifras que resumen el caso
Y, comparando todos los DNIs analizados, en <salida>/<archivo>/_resumen/:
    E_autoconsulta.png      ¿Cuántos usuarios consultan su propio DNI? (usuarios con más volumen)
    F_intervalos_comparados.png  Intervalos repetidos de cada DNI, lado a lado
"""
import argparse
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analizar_dni import C_BOT, C_HUM, cargar, intervalos, metricas, moda_redondeada

C_NOCHE = "#7f1d1d"
plt.rcParams.update({"font.size": 13, "axes.titlesize": 16, "axes.titleweight": "bold"})


def titulo(fig, texto, sub):
    """Título y subtítulo anclados arriba (en pulgadas); devuelve el borde superior útil para tight_layout."""
    h = fig.get_figheight()
    fig.text(0.5, 1 - 0.2 / h, texto, ha="center", va="top", fontsize=19, weight="bold")
    fig.text(0.5, 1 - 0.7 / h, sub, ha="center", va="top", fontsize=13, color="#444")
    return 1 - 1.2 / h


DIAS_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def pct_hora(g):
    return g["fecha"].dt.hour.value_counts(normalize=True).reindex(range(24), fill_value=0) * 100


# ------------------------------------------------------------------ A. reloj
def g_reloj(g_t, g_r, dni, ruta):
    fig, axs = plt.subplots(1, 2, subplot_kw={"projection": "polar"}, figsize=(13, 7.5))
    datos = [(f"Consultas normales\n(resto de DNIs)", g_r, C_HUM), (f"DNI {dni}", g_t, C_BOT)]
    tope = max(pct_hora(g).max() for _, g, _ in datos) * 1.1
    for ax, (nombre, g, color) in zip(axs, datos):
        p = pct_hora(g)
        theta = np.arange(24) / 24 * 2 * np.pi
        cols = [C_NOCHE if h < 5 else color for h in range(24)]
        ax.bar(theta, p.values, width=2 * np.pi / 24 * .9, color=cols, alpha=.9, align="edge")
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_xticks(np.arange(0, 24, 3) / 24 * 2 * np.pi)
        ax.set_xticklabels([f"{h} h" for h in range(0, 24, 3)])
        ax.set_ylim(0, tope)
        ax.set_yticklabels([])
        ax.set_title(nombre, pad=18)
        noche = p[:5].sum()
        ax.text(0.5, -0.1, f"{noche:.0f}% de sus consultas es de madrugada (0–5 h)",
                transform=ax.transAxes, ha="center", fontsize=13, color=C_NOCHE, weight="bold")
    top = titulo(fig, "¿A qué horas consulta?",
           "Cada barra es una hora del día; más larga = más consultas. Barras oscuras = madrugada (0–5 h)")
    fig.tight_layout(rect=(0, 0.02, 1, top))
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ B. mapa de calor
def grilla(g, dias):
    t = g.assign(dia=g["fecha"].dt.normalize(), hora=g["fecha"].dt.hour)
    return t.groupby(["dia", "hora"]).size().unstack(fill_value=0).reindex(index=dias, columns=range(24), fill_value=0)


def g_mapa(g_t, g_r, dni, ruta):
    dias = pd.date_range(min(g_t.fecha.min(), g_r.fecha.min()).normalize(),
                         max(g_t.fecha.max(), g_r.fecha.max()).normalize())
    fig, axs = plt.subplots(1, 2, figsize=(14, 8), sharey=True)
    for ax, (nombre, g, cmap) in zip(axs, [("Consultas normales (resto de DNIs)", g_r, "Blues"),
                                           (f"DNI {dni}", g_t, "Reds")]):
        m = grilla(g, dias)
        ax.imshow(m.values, aspect="auto", cmap=cmap, vmin=0, vmax=max(np.percentile(m.values[m.values > 0], 99), 1), interpolation="nearest")
        ax.set_title(nombre, pad=24)
        ax.set_xticks(range(0, 24, 3))
        ax.set_xticklabels([f"{h} h" for h in range(0, 24, 3)])
        ax.set_xlabel("Hora del día")
        ax.axvline(4.5, color="k", lw=1, ls="--")
        ax.text(2, -1.0, "madrugada", ha="center", va="center", fontsize=10, color="white", weight="bold", bbox=dict(fc=C_NOCHE, ec="none", pad=1.5))
        # fines de semana resaltados en el eje Y
        ax.set_yticks(range(len(dias)))
        ax.set_yticklabels([f"{DIAS_ES[d.dayofweek]} {d:%d/%m}" for d in dias], fontsize=9)
        for lab, d in zip(ax.get_yticklabels(), dias):
            if d.dayofweek >= 5:
                lab.set_color(C_BOT)
                lab.set_weight("bold")
    top = titulo(fig, "¿Qué días y a qué horas?",
           "Cada cuadro es una hora de un día; cada panel con su propia escala; más oscuro = más consultas. Días en rojo = fin de semana")
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ C. zoom 1 hora
def ventana_zoom(g_t, g_r):
    """Hora (día+hora) donde el DNI tiene más consultas; desempata con más actividad del resto."""
    h_r = g_r["fecha"].dt.floor("h").value_counts()
    t = g_t.assign(h=g_t["fecha"].dt.floor("h"))
    stats = t.groupby("h")["fecha"].agg(n="size", sd=lambda f: f.diff().dt.total_seconds().std())
    stats = stats[stats["n"] >= 4]
    if stats.empty:
        return t["h"].value_counts().index[0]
    # la hora más regular (menor desviación de intervalos); a igualdad, la que tenga más actividad del resto
    return min(stats.index, key=lambda h: (round(stats.loc[h, "sd"], 1), -h_r.get(h, 0)))


def g_zoom(g_t, g_r, dni, ruta):
    ini = ventana_zoom(g_t, g_r)
    fin = ini + pd.Timedelta(hours=1)
    fig, ax = plt.subplots(figsize=(14, 5))
    for y, (nombre, g, c) in enumerate([(f"DNI {dni}", g_t, C_BOT), ("Consultas normales\n(resto de DNIs)", g_r, C_HUM)]):
        w = g[(g["fecha"] >= ini) & (g["fecha"] < fin)]
        minutos = (w["fecha"] - ini).dt.total_seconds() / 60
        ax.scatter(minutos, np.full(len(w), y), s=140, color=c, edgecolor="white", zorder=3)
        ax.text(61, y, f"{len(w)} consultas", va="center", fontsize=13, weight="bold", color=c)
    ax.set_yticks([0, 1])
    ax.set_yticklabels([f"DNI {dni}", "Consultas normales\n(resto de DNIs)"])
    ax.set_ylim(-.7, 1.7)
    ax.set_xlim(-1, 72)
    ax.set_xticks(range(0, 61, 10))
    ax.set_xlabel(f"Minutos dentro de la hora  ({ini:%d/%m/%Y %H:%M} – {fin:%H:%M})")
    for x in range(0, 61, 10):
        ax.axvline(x, color="#ccc", lw=.8, zorder=1)
    ax.spines[["top", "right"]].set_visible(False)
    top = titulo(fig, "Una hora real, al detalle",
           "Cada punto es una consulta. El DNI sospechoso cae a intervalos exactos, como un metrónomo")
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ D. cifras clave
def g_cifras(g_t, g_r, dni, ruta):
    mt, mr = metricas(g_t), metricas(g_r)
    for m, g in ((mt, g_t), (mr, g_r)):
        f = g["fecha"]
        m["pct_oficina"] = float(((f.dt.dayofweek < 5) & f.dt.hour.between(8, 17)).mean()) * 100
    items = [
        ("Intervalos idénticos entre consultas\n(siempre el mismo tiempo)", "pct_en_moda"),
        ("Consultas de madrugada\n(0–5 h)", "pct_madrugada_0_5h"),
        ("Consultas en fin de semana", "pct_fin_de_semana"),
        ("Consultas en horario de oficina\n(lun–vie, 8–18 h)", "pct_oficina"),
    ]
    fig, axs = plt.subplots(1, 4, figsize=(16, 6.5))
    for ax, (nombre, k) in zip(axs, items):
        vals = [mr[k], mt[k]]
        es_horas = False
        tope = 24 if es_horas else 100
        b = ax.bar(["Normal", f"DNI\n{dni}"], vals, color=[C_HUM, C_BOT], width=.6)
        for r, v in zip(b, vals):
            ax.text(r.get_x() + r.get_width() / 2, v + tope * .02, f"{v:.0f}" if es_horas else f"{v:.1f}%",
                    ha="center", fontsize=16, weight="bold")
        ax.set_ylim(0, tope * 1.15)
        ax.set_title(nombre, fontsize=13)
        ax.set_yticks([])
        ax.spines[["top", "right", "left"]].set_visible(False)
    top = titulo(fig, "Las 4 cifras que resumen el caso", "Azul = comportamiento normal · Rojo = DNI analizado")
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ E/F. comparativos
def norm_dni(serie):
    return serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(8)


def g_autoconsulta(df, dnis, ruta, n_usuarios=10):
    """% de consultas de cada usuario que van a su propio DNI. Requiere columna de usuario con DNI."""
    usr = norm_dni(df["usuario"])
    if not usr.str.fullmatch(r"\d{8}").mean() > .5:
        print("  (sin DNI de usuario en los datos: se omite E_autoconsulta)")
        return False
    t = df.assign(usr=usr, propio=usr == df["dni"])
    por_u = t.groupby("usr").agg(total=("dni", "size"), propio=("propio", "sum"))
    por_u["pct"] = por_u["propio"] / por_u["total"] * 100
    sel = por_u.sort_values("total", ascending=False).head(n_usuarios).iloc[::-1]
    fig, ax = plt.subplots(figsize=(13, 0.6 * len(sel) + 2.6))
    cols = [C_BOT if u in dnis else C_HUM for u in sel.index]
    b = ax.barh([f"{u}" for u in sel.index], sel["pct"], color=cols)
    for r, (u, row) in zip(b, sel.iterrows()):
        ax.text(row["pct"] + 1, r.get_y() + r.get_height() / 2,
                f"{row['pct']:.1f}%  ({int(row['propio']):,} de {int(row['total']):,} consultas)", va="center", fontsize=12)
    ax.set_xlim(0, 135)
    ax.set_xticks(range(0, 101, 25))
    ax.set_xticklabels([f"{v}%" for v in range(0, 101, 25)])
    ax.set_xlabel("% de sus consultas dirigidas a su propio DNI")
    ax.set_ylabel("DNI del usuario (ordenados por volumen)")
    ax.spines[["top", "right"]].set_visible(False)
    top = titulo(fig, "¿Cuántos usuarios se consultan a sí mismos?",
                 "Los %d usuarios con más consultas. Rojo = usuario cuyo DNI es de los más repetidos" % len(sel))
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return True


def g_intervalos_comparados(df, dnis, ruta):
    n = len(dnis)
    fig, axs = plt.subplots(n, 1, figsize=(13, 2.6 * n + 1.6), sharex=True, squeeze=False)
    todos = [intervalos(df[df["dni"] == d]) for d in dnis]
    todos = [iv[iv > 0] for iv in todos]
    allv = np.concatenate([iv for iv in todos if len(iv)])
    bins = np.logspace(np.log10(max(allv.min(), .5)), np.log10(allv.max() + 1), 60)
    for ax, d, iv in zip(axs[:, 0], dnis, todos):
        ax.hist(iv, bins=bins, color=C_BOT, edgecolor="white")
        ax.set_xscale("log")
        ax.set_ylabel("Consultas")
        ax.set_title(f"DNI {d}  ·  {len(iv) + 1:,} consultas", loc="left", fontsize=13)
        ax.spines[["top", "right"]].set_visible(False)
        if len(iv):
            c = pd.Series(np.round(iv)).value_counts()
            for rank, (seg, k) in enumerate(c.head(2).items()):
                if k >= 50:
                    ax.axvline(max(seg, 1), color="k", ls="--", lw=1)
                    etq = f"{seg/60:.1f} min" if seg >= 120 else f"{seg:.0f} s"
                    ax.annotate(f"{etq}\n({k:,} veces)",
                                (max(seg, 1), ax.get_ylim()[1] * (.95 - .4 * rank)), xytext=(5, 0), textcoords="offset points", fontsize=11, va="top")
    ticks = [t for t in (1, 10, 60, 600, 3600, 21600, 86400) if allv.min() / 2 <= t <= allv.max() * 2]
    axs[-1, 0].set_xticks(ticks)
    axs[-1, 0].set_xticklabels([f"{t} s" if t < 60 else f"{t/60:.0f} min" if t < 3600 else f"{t/3600:.0f} h" for t in ticks])
    axs[-1, 0].set_xlabel("Tiempo entre consultas consecutivas (escala log)")
    top = titulo(fig, "¿Cada cuánto consulta cada DNI?",
                 "Las rayas marcan los tiempos que más se repiten. Una persona no deja un patrón tan marcado ni un corte tan brusco")
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def resumen(df, dnis, carpeta):
    carpeta.mkdir(parents=True, exist_ok=True)
    g_autoconsulta(df, dnis, carpeta / "E_autoconsulta.png")
    g_intervalos_comparados(df, dnis, carpeta / "F_intervalos_comparados.png")
    print(f"  Resumen comparativo -> {carpeta}")


# ------------------------------------------------------------------ principal
def analizar(df, dni, carpeta):
    g_t, g_r = df[df["dni"] == dni], df[df["dni"] != dni]
    if len(g_t) < 3 or len(g_r) < 3:
        print(f"  DNI {dni}: datos insuficientes, se omite.")
        return
    carpeta.mkdir(parents=True, exist_ok=True)
    g_reloj(g_t, g_r, dni, carpeta / "A_reloj_24h.png")
    g_mapa(g_t, g_r, dni, carpeta / "B_mapa_calor.png")
    g_zoom(g_t, g_r, dni, carpeta / "C_zoom_1_hora.png")
    g_cifras(g_t, g_r, dni, carpeta / "D_cifras_clave.png")
    print(f"  DNI {dni}: {len(g_t):,} consultas -> {carpeta}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--dni", help="DNI a analizar (por defecto, el más repetido)")
    ap.add_argument("--top", type=int, default=1, help="analiza los N DNIs más repetidos (sin --dni)")
    ap.add_argument("--salida", default="output/analisis_dni_ejecutivo")
    ap.add_argument("--hoja", default=0)
    ap.add_argument("--col-fecha")
    ap.add_argument("--col-dni")
    ap.add_argument("--col-usuario")
    args = ap.parse_args()
    if isinstance(args.hoja, str) and args.hoja.isdigit():
        args.hoja = int(args.hoja)

    df = cargar(args.archivo, args)
    nombre = Path(args.archivo).stem
    print(f"{nombre}: {len(df):,} registros, {df['dni'].nunique():,} DNIs distintos")
    dnis = [args.dni.strip().zfill(8)] if args.dni else list(df["dni"].value_counts().head(args.top).index)
    base = Path(args.salida) / re.sub(r"[^\w\-. ]", "_", nombre)
    for d in dnis:
        analizar(df, d, base / d)
    resumen(df, dnis, base / "_resumen")


if __name__ == "__main__":
    main()
