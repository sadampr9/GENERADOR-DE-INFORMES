# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
Analisis forense de patron BOT para DNI 09337627
Archivo: 1. LD_BIGDAVI S.A.C._OCT2026.xlsx
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

# ── Carga de datos ────────────────────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "1. LD_BIGDAVI S.A.C._OCT2026.xlsx")
DNI_OBJETIVO = "09337627"

print("=" * 70)
print(f"  ANÁLISIS FORENSE DE BOT — DNI {DNI_OBJETIVO}")
print("  Archivo: LD_BIGDAVI S.A.C._OCT2026")
print("=" * 70)

print("\n[1/7] Cargando archivo...")
df_raw = pd.read_excel(DATA_FILE, engine="openpyxl")
print(f"      Columnas detectadas: {list(df_raw.columns)}")
print(f"      Total filas en archivo: {len(df_raw):,}")

# ── Normalizar columnas usando los alias del data_loader ─────────────────────
COLUMN_ALIASES = {
    "ruc": ["RUC", "ruc", "RUC_EMPRESA", "RU_EMPRESA", "NU_RUC", "RUC_CLIENTE"],
    "empresa": ["empresa", "EMPRESA", "DE_RAZON_SOCIAL", "DE_EMPRESA", "RAZON_SOCIAL", "NOMBRE_EMPRESA"],
    "cod_usuario": ["cod_usuario", "CODIGO_USUARIO", "NU_DOC_USUARIO", "DNI_USUARIO", "DOC_USUARIO", "USUARIO", "ID_USUARIO"],
    "nombre_usuario": ["nombre_usuario", "NOMBRES_USUARIO", "DE_USUARIO", "NOMBRES", "NOMBRE_USUARIO", "NOM_USUARIO"],
    "fecha_consulta": ["fecha_consulta", "FEC_CONSULTA", "FE_CONSULTA", "FECHA_CONSULTA", "FECHAYHORA", "FECHA_Y_HORA", "FECHA"],
    "dni_consultado": ["dni_consultado", "DNI_CONSULTADO", "NU_DNI_CONSULTADO", "DNI"],
    "respuesta": ["respuesta", "RESPUESTA", "ESTADO_RESPUESTA"],
    "servicio": ["servicio", "SERVICIO", "NOMBRE_SERVICIO", "DE_SERVICIO"],
    "ip_usuario": ["ip_usuario", "DE_IP_USUARIO", "NU_IP", "IP", "IP_USUARIO", "IP_CLIENTE", "DIRECCION_IP"]
}

rename_dict = {}
for canonical, aliases in COLUMN_ALIASES.items():
    for col in df_raw.columns:
        if col.upper() in [a.upper() for a in aliases]:
            rename_dict[col] = canonical
            break

df = df_raw.rename(columns=rename_dict)
df["fecha_consulta"] = pd.to_datetime(df["fecha_consulta"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["fecha_consulta"])
df["dni_consultado"] = df["dni_consultado"].astype(str).str.split('.').str[0].str.strip().str.zfill(8)
df = df.sort_values("fecha_consulta").reset_index(drop=True)

# ── Filtrar solo el DNI objetivo ─────────────────────────────────────────────
dni_df = df[df["dni_consultado"] == DNI_OBJETIVO].copy()
total_dni = len(dni_df)
total_global = len(df)

print(f"\n[2/7] ESTADÍSTICAS GENERALES")
print(f"      Total consultas en el archivo      : {total_global:,}")
print(f"      Consultas al DNI {DNI_OBJETIVO}     : {total_dni:,}")
print(f"      Porcentaje del total                : {total_dni/total_global*100:.1f}%")

if total_dni == 0:
    print("      ⚠ No se encontraron consultas para ese DNI. Verificar normalización.")
    sys.exit(1)

fecha_primera = dni_df["fecha_consulta"].min()
fecha_ultima  = dni_df["fecha_consulta"].max()
duracion_total = (fecha_ultima - fecha_primera).total_seconds() / 3600
print(f"      Primera consulta                   : {fecha_primera}")
print(f"      Última consulta                    : {fecha_ultima}")
print(f"      Duración del rango                 : {duracion_total:.1f} horas")

# ── [A] Frecuencia por hora del día ─────────────────────────────────────────
print(f"\n[3/7] PATRÓN POR HORA DEL DÍA")
dni_df["hora"] = dni_df["fecha_consulta"].dt.hour
por_hora = dni_df.groupby("hora").size()
print(f"      Horas con actividad: {list(por_hora[por_hora > 0].index.tolist())}")
horas_madrugada = por_hora[(por_hora.index >= 0) & (por_hora.index < 5)].sum()
print(f"      Consultas en madrugada (00-04h)    : {horas_madrugada}")
for h, cnt in por_hora.items():
    if cnt > 0:
        bar = "#" * min(int(cnt / max(por_hora) * 40), 40)
        print(f"        {h:02d}h: {cnt:>5}  {bar}")

# ── [B] Frecuencia por día de semana ────────────────────────────────────────
print(f"\n[4/7] PATRÓN POR DÍA DE SEMANA")
dias = {0:"Lunes",1:"Martes",2:"Miércoles",3:"Jueves",4:"Viernes",5:"Sábado",6:"Domingo"}
dni_df["dia_semana"] = dni_df["fecha_consulta"].dt.dayofweek
por_dia = dni_df.groupby("dia_semana").size()
for d, cnt in por_dia.items():
    nombre = dias.get(d, str(d))
    bar = "#" * min(int(cnt / max(por_dia) * 40), 40)
    print(f"        {nombre:<12}: {cnt:>5}  {bar}")

# ── [C] Intervalos entre consultas ──────────────────────────────────────────
print(f"\n[5/7] ANÁLISIS DE INTERVALOS ENTRE CONSULTAS")
intervals_s = dni_df["fecha_consulta"].diff().dropna().dt.total_seconds()
print(f"      Intervalo mínimo (seg)             : {intervals_s.min():.2f}")
print(f"      Intervalo máximo (seg)             : {intervals_s.max():.2f}")
print(f"      Intervalo promedio (seg)           : {intervals_s.mean():.2f}")
print(f"      Desviación estándar (seg)          : {intervals_s.std():.2f}")
print(f"      Mediana (seg)                      : {intervals_s.median():.2f}")

# Indicadores bot: intervalos ≤ 2 seg
muy_rapidos = (intervals_s <= 2).sum()
rapidos      = (intervals_s <= 10).sum()
print(f"\n      ⚡ Intervalos ≤ 2 seg (sospechoso) : {muy_rapidos} ({muy_rapidos/len(intervals_s)*100:.1f}%)")
print(f"      ⚡ Intervalos ≤ 10 seg             : {rapidos} ({rapidos/len(intervals_s)*100:.1f}%)")

# Distribución de intervalos
bins = [0, 1, 2, 5, 10, 30, 60, 300, 3600, float("inf")]
labels = ["0-1s","1-2s","2-5s","5-10s","10-30s","30-60s","1-5min","5-60min",">60min"]
dist = pd.cut(intervals_s, bins=bins, labels=labels).value_counts().sort_index()
print(f"\n      Distribucion de intervalos:")
for label, cnt in dist.items():
    bar = "#" * min(int(cnt / max(dist) * 35), 35)
    print(f"        {label:<10}: {cnt:>5}  {bar}")

# ── [D] Ráfagas: ventana 60 segundos ────────────────────────────────────────
print(f"\n[6/7] DETECCIÓN DE RÁFAGAS (ventana 60 seg, umbral >5)")
dni_idx = dni_df.set_index("fecha_consulta").sort_index()
rolling = dni_idx["dni_consultado"].rolling("60s").count()
rafagas = rolling[rolling > 5]
print(f"      Momentos con >5 consultas en 60s   : {len(rafagas)}")
if not rafagas.empty:
    rafagas_df = rafagas.reset_index()
    rafagas_df["minuto"] = rafagas_df["fecha_consulta"].dt.floor("min")
    por_minuto = rafagas_df.groupby("minuto")["dni_consultado"].max()
    print(f"      Minutos distintos con ráfagas      : {len(por_minuto)}")
    print(f"      Top 10 minutos de mayor intensidad:")
    for ts, cnt in por_minuto.sort_values(ascending=False).head(10).items():
        print(f"        {ts}  →  {int(cnt)} consultas/60s")

# ── [E] Análisis por usuario ─────────────────────────────────────────────────
print(f"\n[7/7] ANÁLISIS POR USUARIO")
if "cod_usuario" in dni_df.columns:
    por_usuario = dni_df.groupby("cod_usuario").size().sort_values(ascending=False)
    print(f"      Usuarios distintos que consultaron  : {len(por_usuario)}")
    print(f"      Top usuarios:")
    for u, cnt in por_usuario.head(10).items():
        print(f"        {u:<30}: {cnt:>5} consultas")
else:
    print("      Columna cod_usuario no disponible")

if "ip_usuario" in dni_df.columns:
    por_ip = dni_df.groupby("ip_usuario").size().sort_values(ascending=False)
    print(f"\n      IPs distintas que consultaron       : {len(por_ip)}")
    print(f"      Top IPs:")
    for ip, cnt in por_ip.head(10).items():
        print(f"        {ip:<25}: {cnt:>5} consultas")

# ── VEREDICTO FINAL ──────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  VEREDICTO")
print("=" * 70)
indicadores_bot = 0
notas = []

if total_dni / total_global > 0.20:
    indicadores_bot += 3
    notas.append(f"⛔ CRÍTICO: {total_dni/total_global*100:.1f}% de todas las consultas son a un solo DNI")

if not intervals_s.empty:
    if intervals_s.std() < 5 and intervals_s.mean() < 60:
        indicadores_bot += 3
        notas.append(f"⛔ CRÍTICO: Intervalos extremadamente regulares (std={intervals_s.std():.2f}s, mean={intervals_s.mean():.2f}s)")
    if muy_rapidos / len(intervals_s) > 0.50:
        indicadores_bot += 2
        notas.append(f"🔴 ALTO: {muy_rapidos/len(intervals_s)*100:.1f}% de consultas en ≤2 segundos")
    elif rapidos / len(intervals_s) > 0.70:
        indicadores_bot += 1
        notas.append(f"🟡 MEDIO: {rapidos/len(intervals_s)*100:.1f}% de consultas en ≤10 segundos")

if not rafagas.empty and len(rafagas) > 100:
    indicadores_bot += 2
    notas.append(f"🔴 ALTO: {len(rafagas)} instancias de ráfagas (>5 consultas/60s)")

if horas_madrugada > 0:
    indicadores_bot += 1
    notas.append(f"🟡 MEDIO: {horas_madrugada} consultas en horario de madrugada (00-04h)")

print(f"\n  Score de riesgo BOT: {indicadores_bot}/11")
if indicadores_bot >= 6:
    print("  📌 CONCLUSIÓN: ALTAMENTE PROBABLE USO DE BOT / SCRAPER AUTOMATIZADO")
elif indicadores_bot >= 3:
    print("  📌 CONCLUSIÓN: COMPORTAMIENTO SOSPECHOSO, POSIBLE BOT")
else:
    print("  📌 CONCLUSIÓN: NO HAY SUFICIENTE EVIDENCIA DE BOT")

print("\n  Indicadores detectados:")
for n in notas:
    print(f"    {n}")

print("\n" + "=" * 70)
