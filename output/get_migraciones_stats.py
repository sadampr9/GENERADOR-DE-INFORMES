import pandas as pd
from pathlib import Path
import sys

# Add the project root to import path
project_root = Path(r"c:\Users\sperezr\Documents\Proyectos\GENERADOR DE INFORMES")
sys.path.append(str(project_root))

from config import UMBRAL_RAFAGA, UMBRAL_VOLUMEN, UMBRAL_DNI_REPETIDO
from modules.data_loader import load_excel
from modules.anomaly_detector import run_all_detections

class Args:
    umbral_rafaga = UMBRAL_RAFAGA
    umbral_volumen = UMBRAL_VOLUMEN
    umbral_dni = UMBRAL_DNI_REPETIDO

def run_stats():
    filepath = project_root / "LD_MIGRACIONES_JUN2026.csv"
    print(f"Loading {filepath}...")
    df, metadata = load_excel(str(filepath))
    print(f"Loaded {len(df)} rows.")
    
    print("Running detections...")
    report = run_all_detections(df, Args())
    
    # G1: daily stats
    df["fecha_dia"] = df["fecha_consulta"].dt.date
    daily = df.groupby("fecha_dia").size()
    print("\nG1 Stats (Daily Consumption):")
    print(f"  Date range: {df['fecha_consulta'].min()} to {df['fecha_consulta'].max()}")
    print(f"  Daily counts:\n{daily}")
    print(f"  Peak day: {daily.idxmax()} with {daily.max()} queries")
    print(f"  Average daily: {daily.mean():.2f} queries")
    
    # G2: hourly stats
    df["hora"] = df["fecha_consulta"].dt.hour
    hourly = df.groupby("hora").size()
    print("\nG2 Stats (Hourly Distribution):")
    print(f"  Peak hour: {hourly.idxmax()}:00 with {hourly.max()} queries")
    print(f"  Top 5 hours:\n{hourly.sort_values(ascending=False).head(5)}")
    
    # G3: day of week stats
    df["dia_semana_num"] = df["fecha_consulta"].dt.dayofweek
    weekday_map = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    dow = df.groupby("dia_semana_num").size()
    print("\nG3 Stats (Day of Week):")
    for num, count in dow.items():
        print(f"  {weekday_map[num]}: {count}")
        
    # G4: user stats
    user_counts = df["cod_usuario"].value_counts() if "cod_usuario" in df.columns else df["de_usuario"].value_counts()
    print("\nG4 Stats (User Counts):")
    print(f"  Unique users: {df['cod_usuario'].nunique() if 'cod_usuario' in df.columns else 'N/A'}")
    print(f"  Top users:\n{user_counts.head(10)}")
    
    # G5: burst stats
    print("\nG5 Stats (Bursts):")
    print(f"  Total bursts: {len(report.bursts)}")
    if not report.bursts.empty:
        max_burst = report.bursts.loc[report.bursts["count"].idxmax()]
        print(f"  Peak burst: {max_burst['count']} queries in 60s at {max_burst['window_start']} by user {max_burst.get('cod_usuario', 'N/A')}")
        
    # G6: high volume stats
    print("\nG6 Stats (High Volume):")
    print(f"  Unusual volume hours (> {Args.umbral_volumen}): {len(report.high_volume)}")
    if not report.high_volume.empty:
        print(f"  Average in peak hours: {report.high_volume['count'].mean():.2f} queries/hour")
        print(f"  Peak hourly: {report.high_volume['count'].max()} queries")
        
    # G7 & G8: repeated DNI stats
    print("\nG7 & G8 Stats (Repeated DNI):")
    print(f"  Total repeated DNIs (> {Args.umbral_dni}): {len(report.repeated_dni)}")
    if not report.repeated_dni.empty:
        print(f"  Top 10 DNI counts:\n{report.repeated_dni.head(10)}")
        
    # G9: periodic stats
    print("\nG9 Stats (Periodic Patterns):")
    print(f"  Users with periodic patterns: {len(report.periodic)}")
    if not report.periodic.empty:
        print(f"  Periodic patterns detail:\n{report.periodic.head(10)}")
        
    # G10: illegal hours / heatmap
    print("\nG10 Stats (Illegal Hours):")
    print(f"  Total illegitimate queries: {len(report.illegal_hours)}")
    if not report.illegal_hours.empty:
        types = report.illegal_hours["tipo_anomalia"].value_counts()
        print(f"  By anomaly type: {types.to_dict()}")

if __name__ == "__main__":
    run_stats()
