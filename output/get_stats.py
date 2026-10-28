import pandas as pd
from pathlib import Path
from modules.data_loader import load_excel
from modules.anomaly_detector import run_all_detections

# Simulating argparse namespace
class Args:
    umbral_rafaga = 10
    umbral_volumen = 100
    umbral_dni = 50

def run_stats():
    filepath = r"C:\Users\sperezr\Documents\Proyectos\GENERADOR DE INFORMES\LD_AUTOFIN_SAC_FEB2026.xlsx"
    df, metadata = load_excel(filepath)
    report = run_all_detections(df, Args())
    
    # G1: daily stats
    df["fecha_dia"] = df["fecha_consulta"].dt.date
    daily = df.groupby("fecha_dia").size()
    print("G1 Stats:")
    print(f"  Rango fechas: {df['fecha_consulta'].min()} a {df['fecha_consulta'].max()}")
    print(f"  Pico diario: {daily.idxmax()} con {daily.max()} consultas")
    print(f"  Promedio diario: {daily.mean():.2f} consultas")
    
    # G2: hourly stats
    df["hora"] = df["fecha_consulta"].dt.hour
    hourly = df.groupby("hora").size()
    print("\nG2 Stats:")
    print(f"  Hora pico: {hourly.idxmax()}:00 con {hourly.max()} consultas")
    print(f"  Distribución horas pico: {hourly.sort_values(ascending=False).head(3).to_dict()}")
    
    # G3: day of week stats
    df["dia_semana_num"] = df["fecha_consulta"].dt.dayofweek
    weekday_map = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    dow = df.groupby("dia_semana_num").size()
    print("\nG3 Stats:")
    for num, count in dow.items():
        print(f"  {weekday_map[num]}: {count}")
        
    # G4: user stats
    user_counts = df["cod_usuario"].value_counts()
    print("\nG4 Stats:")
    print(f"  Usuarios únicos: {df['cod_usuario'].nunique()}")
    print(f"  Top usuarios: {user_counts.head(5).to_dict()}")
    
    # G5: burst stats
    print("\nG5 Stats:")
    print(f"  Total ráfagas: {len(report.bursts)}")
    if not report.bursts.empty:
        max_burst = report.bursts.loc[report.bursts["count"].idxmax()]
        print(f"  Pico ráfaga: {max_burst['count']} consultas en 60s el {max_burst['window_start']} por {max_burst['cod_usuario']}")
        
    # G6: high volume stats
    print("\nG6 Stats:")
    print(f"  Horas con volumen inusual (>100): {len(report.high_volume)}")
    if not report.high_volume.empty:
        print(f"  Promedio en horas pico: {report.high_volume['count'].mean():.2f} consultas/hora")
        print(f"  Pico por hora: {report.high_volume['count'].max()} consultas")
        
    # G7 & G8: repeated dni stats
    print("\nG7 & G8 Stats:")
    print(f"  Total DNIs repetidos (>50): {len(report.repeated_dni)}")
    if not report.repeated_dni.empty:
        print(f"  Top 5 DNIs: {report.repeated_dni.head(5).to_dict(orient='records')}")
        
    # G9: periodic stats
    print("\nG9 Stats:")
    print(f"  Usuarios con patrón periódico: {len(report.periodic)}")
    if not report.periodic.empty:
        print(f"  Detalle periodicidad: {report.periodic.head(5).to_dict(orient='records')}")
        
    # G10: heatmap / illegal hours stats
    print("\nG10 Stats:")
    print(f"  Consultas ilegítimas totales: {len(report.illegal_hours)}")
    if not report.illegal_hours.empty:
        types = report.illegal_hours["tipo_anomalia"].value_counts()
        print(f"  Por tipo anomalía: {types.to_dict()}")

if __name__ == "__main__":
    run_stats()
