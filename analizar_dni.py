"""
Análisis forense de un DNI consultado: timeline, histograma de intervalos y
comparativa bot vs humano.

Uso:
    python analizar_dni.py "data/4. PIDE_UNI_SA_OCT2026.xlsx"
    python analizar_dni.py archivo.xlsx --dni 73018031
    python analizar_dni.py archivo.xlsx --top 3 --salida output/analisis_dni
    python analizar_dni.py archivo.csv --col-fecha FEC_CONSULTA --col-dni NU_DNI_CONSULTADO

Sin --dni se analiza el DNI más repetido (--top N analiza los N primeros).
Las columnas se autodetectan (FE_CONSULTA/FEC_CONSULTA, DNI_CONSULTADO/
NU_DNI_CONSULTADO, DNI_USUARIO/NU_DOC_USUARIO) y pueden forzarse por argumento.

Genera en <salida>/<archivo>/<dni>/:
    1_timeline.png, 2_histograma_intervalos.png, 3_bot_vs_humano.png, metricas.csv
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

CANDIDATAS = {
    "fecha": ["FE_CONSULTA", "FEC_CONSULTA", "FECHA_CONSULTA", "FECHA_HORA", "FECHA"],
    "dni": ["DNI_CONSULTADO", "NU_DNI_CONSULTADO", "DNI"],
    "usuario": ["DNI_USUARIO", "NU_DOC_USUARIO", "USUARIO", "DE_USUARIO"],
}
C_BOT, C_HUM, C_GRIS = "#d62728", "#1f77b4", "#7f7f7f"
TOL_REGULAR = 0.05  # intervalo "regular" = dentro de ±5% de la moda


# --------------------------------------------------------------------------- carga
def detectar(df, clave, forzada):
    if forzada:
        if forzada not in df.columns:
            sys.exit(f"Columna '{forzada}' no existe. Disponibles: {list(df.columns)}")
        return forzada
    mapa = {c.upper().strip(): c for c in df.columns}
    for cand in CANDIDATAS[clave]:
        if cand in mapa:
            return mapa[cand]
    return None


def cargar(ruta, args):
    ruta = Path(ruta)
    df = pd.read_csv(ruta, sep=None, engine="python") if ruta.suffix.lower() in (".csv", ".txt") \
        else pd.read_excel(ruta, sheet_name=args.hoja)
    c_fecha = detectar(df, "fecha", args.col_fecha)
    c_dni = detectar(df, "dni", args.col_dni)
    c_usr = detectar(df, "usuario", args.col_usuario)
    if not c_fecha or not c_dni:
        sys.exit(f"No se detectaron columnas de fecha/DNI. Disponibles: {list(df.columns)}")
    out = pd.DataFrame({
        "fecha": pd.to_datetime(df[c_fecha], errors="coerce"),
        "dni": df[c_dni].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(8),
        "usuario": df[c_usr].astype(str) if c_usr else "—",
    }).dropna(subset=["fecha"]).sort_values("fecha").reset_index(drop=True)
    return out


# ------------------------------------------------------------------ métricas
def intervalos(g):
    """Segundos entre consultas consecutivas, calculado por usuario."""
    return g.groupby("usuario")["fecha"].diff().dt.total_seconds().dropna().to_numpy()


def moda_redondeada(iv):
    if len(iv) == 0:
        return np.nan
    valores, cuentas = np.unique(np.round(iv), return_counts=True)
    return valores[cuentas.argmax()]


def metricas(g):
    iv = intervalos(g)
    m = {"consultas": len(g), "usuarios": g["usuario"].nunique(),
         "dias_activos": g["fecha"].dt.normalize().nunique()}
    if len(iv) == 0:
        return m
    moda = moda_redondeada(iv)
    horas = g["fecha"].dt.hour
    p = np.bincount(horas, minlength=24) / len(g)
    p = p[p > 0]
    m.update({
        "intervalo_mediana_s": np.median(iv),
        "intervalo_media_s": iv.mean(),
        "intervalo_std_s": iv.std(),
        "cv_intervalo": iv.std() / iv.mean() if iv.mean() else np.nan,
        "moda_s": moda,
        "pct_en_moda": float(np.mean(np.abs(iv - moda) <= max(1, TOL_REGULAR * moda))) * 100 if moda > 0 else 0.0,
        "horas_distintas_activas": horas.nunique(),
        "pct_madrugada_0_5h": float((horas < 5).mean()) * 100,
        "pct_fin_de_semana": float((g["fecha"].dt.dayofweek >= 5).mean()) * 100,
        "entropia_horaria_bits": float(-(p * np.log2(p)).sum()),  # máx 4.58 = uniforme 24h
    })
    m["veredicto"] = veredicto(m)
    return m


def veredicto(m):
    """Puntaje simple 0-4 de automatización; es una guía, no una prueba."""
    pts = 0
    pts += m.get("pct_en_moda", 0) >= 60
    pts += m.get("cv_intervalo", 9) < 0.5 or m.get("pct_en_moda", 0) >= 80
    pts += m.get("horas_distintas_activas", 0) >= 22
    pts += m.get("pct_madrugada_0_5h", 0) >= 15
    return f"{'POSIBLE BOT' if pts >= 3 else 'PROBABLE HUMANO' if pts <= 1 else 'REVISAR'} ({pts}/4)"


# ------------------------------------------------------------------ gráficos
def fmt_seg(s):
    if s < 120:
        return f"{s:.0f} s"
    if s < 7200:
        return f"{s / 60:.1f} min"
    return f"{s / 3600:.1f} h"


def g_timeline(g, dni, titulo, ruta):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 8), height_ratios=[1, 2], sharex=True)
    dias = g["fecha"].dt.normalize().value_counts().sort_index()
    a1.bar(dias.index, dias.values, width=0.8, color=C_BOT)
    a1.set_ylabel("Consultas por día")
    a1.set_title(f"Timeline del DNI {dni} — {titulo}\n{len(g):,} consultas · "
                 f"{g['fecha'].min():%d/%m/%Y %H:%M} → {g['fecha'].max():%d/%m/%Y %H:%M}")
    hora = g["fecha"].dt.hour + g["fecha"].dt.minute / 60
    a2.scatter(g["fecha"], hora, s=6, color=C_BOT, alpha=.6)
    a2.axhspan(0, 5, color=C_GRIS, alpha=.15, label="Madrugada (0–5 h)")
    a2.set_ylim(24, 0)
    a2.set_yticks(range(0, 25, 3))
    a2.set_ylabel("Hora del día")
    a2.set_xlabel("Fecha")
    a2.legend(loc="lower right")
    for a in (a1, a2):
        a.grid(alpha=.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def bins_log(*arrs):
    todo = np.concatenate([a for a in arrs if len(a)])
    todo = todo[todo > 0]
    return np.logspace(np.log10(max(todo.min(), .5)), np.log10(todo.max() + 1), 50)


def g_histograma(iv, dni, m, ruta):
    fig, ax = plt.subplots(figsize=(11, 6))
    iv = iv[iv > 0]
    ax.hist(iv, bins=bins_log(iv), color=C_BOT, edgecolor="white")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Intervalo entre consultas consecutivas (escala log)")
    ax.set_ylabel("Frecuencia (escala log)")
    ax.set_title(f"Histograma de intervalos — DNI {dni}")
    ax.axvline(m["moda_s"], color="k", ls="--", lw=1.2,
               label=f"Moda: {fmt_seg(m['moda_s'])} ({m['pct_en_moda']:.1f}% de los intervalos)")
    ax.axvline(m["intervalo_mediana_s"], color=C_HUM, ls=":", lw=1.5,
               label=f"Mediana: {fmt_seg(m['intervalo_mediana_s'])}")
    ticks = [1, 10, 60, 600, 3600, 21600, 86400]
    ax.set_xticks([t for t in ticks if iv.min() / 2 <= t <= iv.max() * 2])
    ax.set_xticklabels([fmt_seg(t) for t in ticks if iv.min() / 2 <= t <= iv.max() * 2])
    ax.legend()
    ax.grid(alpha=.3, which="both")
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def g_comparativa(g_t, g_r, dni, mt, mr, ruta):
    iv_t, iv_r = intervalos(g_t), intervalos(g_r)
    fig, ax = plt.subplots(2, 2, figsize=(14, 9))
    et, er = f"DNI {dni} (sospechoso)", "Resto de DNIs (referencia humana)"

    # intervalos normalizados
    b = bins_log(iv_t, iv_r)
    a = ax[0, 0]
    a.hist(iv_r[iv_r > 0], bins=b, color=C_HUM, alpha=.6, weights=np.full((iv_r > 0).sum(), 100 / max(len(iv_r), 1)), label=er)
    a.hist(iv_t[iv_t > 0], bins=b, color=C_BOT, alpha=.6, weights=np.full((iv_t > 0).sum(), 100 / max(len(iv_t), 1)), label=et)
    a.set_xscale("log")
    a.set_xlabel("Intervalo (s, escala log)")
    a.set_ylabel("% de consultas")
    a.set_title("Distribución de intervalos")
    a.legend(fontsize=8)

    # perfil horario
    a = ax[0, 1]
    for g, c, e in ((g_r, C_HUM, er), (g_t, C_BOT, et)):
        pct = g["fecha"].dt.hour.value_counts(normalize=True).reindex(range(24), fill_value=0) * 100
        a.plot(pct.index, pct.values, marker="o", color=c, label=e)
    a.axvspan(-.5, 4.5, color=C_GRIS, alpha=.15)
    a.set_xticks(range(0, 24, 2))
    a.set_xlabel("Hora del día")
    a.set_ylabel("% de consultas")
    a.set_title("Perfil horario (humano: pico laboral · bot: plano 24 h)")
    a.legend(fontsize=8)

    # ECDF
    a = ax[1, 0]
    for iv, c, e in ((iv_r, C_HUM, er), (iv_t, C_BOT, et)):
        x = np.sort(iv[iv > 0])
        a.plot(x, np.arange(1, len(x) + 1) / len(x) * 100, color=c, label=e)
    a.set_xscale("log")
    a.set_xlabel("Intervalo (s, escala log)")
    a.set_ylabel("% acumulado")
    a.set_title("Distribución acumulada (salto vertical = intervalo fijo)")
    a.legend(fontsize=8)

    # tabla de métricas
    a = ax[1, 1]
    a.axis("off")
    filas = [
        ("Consultas", f"{mt['consultas']:,}", f"{mr['consultas']:,}"),
        ("Mediana intervalo", fmt_seg(mt["intervalo_mediana_s"]), fmt_seg(mr["intervalo_mediana_s"])),
        ("Coef. variación", f"{mt['cv_intervalo']:.2f}", f"{mr['cv_intervalo']:.2f}"),
        ("% en intervalo modal", f"{mt['pct_en_moda']:.1f}%", f"{mr['pct_en_moda']:.1f}%"),
        ("Horas del día activas", f"{mt['horas_distintas_activas']}/24", f"{mr['horas_distintas_activas']}/24"),
        ("% madrugada 0–5 h", f"{mt['pct_madrugada_0_5h']:.1f}%", f"{mr['pct_madrugada_0_5h']:.1f}%"),
        ("% fin de semana", f"{mt['pct_fin_de_semana']:.1f}%", f"{mr['pct_fin_de_semana']:.1f}%"),
        ("Entropía horaria (bits)", f"{mt['entropia_horaria_bits']:.2f}", f"{mr['entropia_horaria_bits']:.2f}"),
        ("Veredicto", mt["veredicto"], mr["veredicto"]),
    ]
    t = a.table(cellText=filas, colLabels=["Métrica", f"DNI {dni}", "Resto"], loc="center", cellLoc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(9)
    t.scale(1, 1.6)
    for (r, c), cell in t.get_celld().items():
        if r == 0:
            cell.set_text_props(weight="bold")
        elif c == 1:
            cell.set_facecolor("#fbe3e3")
        elif c == 2:
            cell.set_facecolor("#e3eefb")
    a.set_title("Comparativa de métricas")

    fig.suptitle("Comparativa bot vs humano", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ principal
def analizar(df, dni, carpeta, nombre):
    g_t = df[df["dni"] == dni]
    g_r = df[df["dni"] != dni]
    if len(g_t) < 3:
        print(f"  DNI {dni}: menos de 3 consultas, se omite.")
        return None
    if len(g_r) < 3:
        sys.exit("No hay suficientes registros de otros DNIs para la comparativa.")
    carpeta.mkdir(parents=True, exist_ok=True)
    mt, mr = metricas(g_t), metricas(g_r)
    g_timeline(g_t, dni, nombre, carpeta / "1_timeline.png")
    g_histograma(intervalos(g_t), dni, mt, carpeta / "2_histograma_intervalos.png")
    g_comparativa(g_t, g_r, dni, mt, mr, carpeta / "3_bot_vs_humano.png")
    pd.DataFrame([{"grupo": f"DNI {dni}", **mt}, {"grupo": "Resto", **mr}]).to_csv(
        carpeta / "metricas.csv", index=False, encoding="utf-8-sig")
    print(f"  DNI {dni}: {mt['consultas']:,} consultas · mediana {fmt_seg(mt['intervalo_mediana_s'])} · "
          f"{mt['pct_en_moda']:.1f}% en intervalo modal · {mt['veredicto']}")
    print(f"  -> {carpeta}")
    return mt


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--dni", help="DNI a analizar (por defecto, el más repetido)")
    ap.add_argument("--top", type=int, default=1, help="analiza los N DNIs más repetidos (sin --dni)")
    ap.add_argument("--salida", default="output/analisis_dni", help="carpeta base de salida")
    ap.add_argument("--hoja", default=0, help="hoja del Excel (nombre o índice)")
    ap.add_argument("--col-fecha")
    ap.add_argument("--col-dni")
    ap.add_argument("--col-usuario")
    args = ap.parse_args()
    if isinstance(args.hoja, str) and args.hoja.isdigit():
        args.hoja = int(args.hoja)

    df = cargar(args.archivo, args)
    nombre = Path(args.archivo).stem
    print(f"{nombre}: {len(df):,} registros, {df['dni'].nunique():,} DNIs distintos")
    if args.dni:
        dnis = [args.dni.strip().zfill(8)]
    else:
        dnis = list(df["dni"].value_counts().head(args.top).index)
    base = Path(args.salida) / re.sub(r"[^\w\-. ]", "_", nombre)
    for d in dnis:
        analizar(df, d, base / d, nombre)


if __name__ == "__main__":
    main()
