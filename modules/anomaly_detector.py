import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging

logger = logging.getLogger("reniec_anomalias")

@dataclass
class AnomalyReport:
    bursts: pd.DataFrame
    high_volume: pd.DataFrame
    illegal_hours: pd.DataFrame
    repeated_dni: pd.DataFrame
    periodic: pd.DataFrame
    triangulation: list[dict]
    severity_score: int          # 0-100, calculado por ponderación
    summary_text: str            # Párrafo resumen generado automáticamente

def detect_bursts(df: pd.DataFrame, threshold: int = 10) -> pd.DataFrame:
    """
    Agrupa por (ruc, cod_usuario) en ventanas rodantes de 60 segundos.
    Marcar si en alguna ventana el conteo supera threshold.
    """
    logger.info("Iniciando detección de ráfagas...")
    
    # Asegurar que existan ruc y cod_usuario
    temp_df = df.copy()
    if "ruc" not in temp_df.columns:
        temp_df["ruc"] = "SIN_RUC"
    if "cod_usuario" not in temp_df.columns:
        # Fallback a nombre_usuario, o a "USUARIO_UNICO"
        if "nombre_usuario" in temp_df.columns:
            temp_df["cod_usuario"] = temp_df["nombre_usuario"]
        else:
            temp_df["cod_usuario"] = "USUARIO_UNICO"

    # Para usar rolling de 60s, necesitamos que el índice sea la fecha
    temp_df = temp_df.set_index("fecha_consulta").sort_index()

    bursts_list = []
    # Agrupar por ruc y cod_usuario
    grouped = temp_df.groupby(["ruc", "cod_usuario"])
    for (ruc, cod_user), group in grouped:
        # Contar en ventana rodante de 60 segundos
        rolling_count = group["dni_consultado"].rolling("60s").count()
        # Filtrar los que superan el umbral
        burst_points = rolling_count[rolling_count > threshold]
        
        if not burst_points.empty:
            # Para evitar redundancias excesivas en el mismo minuto, agrupamos por minuto de ráfaga
            burst_points_df = burst_points.reset_index()
            burst_points_df["fecha_minuto"] = burst_points_df["fecha_consulta"].dt.floor("min")
            idx_max = burst_points_df.groupby("fecha_minuto")["dni_consultado"].idxmax()
            representative_bursts = burst_points_df.loc[idx_max]
            
            for _, row in representative_bursts.iterrows():
                bursts_list.append({
                    "ruc": ruc,
                    "cod_usuario": cod_user,
                    "window_start": row["fecha_consulta"],
                    "count": int(row["dni_consultado"])
                })

    if not bursts_list:
        return pd.DataFrame(columns=["ruc", "cod_usuario", "window_start", "count"])
        
    return pd.DataFrame(bursts_list)

def detect_high_volume(df: pd.DataFrame, threshold: int = 100) -> pd.DataFrame:
    """
    Agrupa por (ruc, cod_usuario, hora). Marcar si un usuario individual supera threshold consultas/hora.
    """
    logger.info("Iniciando detección de volumen inusual por hora por usuario...")
    temp_df = df.copy()
    if "ruc" not in temp_df.columns:
        temp_df["ruc"] = "SIN_RUC"
    if "cod_usuario" not in temp_df.columns:
        if "nombre_usuario" in temp_df.columns:
            temp_df["cod_usuario"] = temp_df["nombre_usuario"]
        else:
            temp_df["cod_usuario"] = "USUARIO_UNICO"
        
    temp_df["hora_periodo"] = temp_df["fecha_consulta"].dt.floor("h")
    
    grouped = temp_df.groupby(["ruc", "cod_usuario", "hora_periodo"]).size().reset_index(name="count")
    high_vol = grouped[grouped["count"] > threshold]
    
    return high_vol.reset_index(drop=True)

def detect_illegal_hours(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hora entre 00:00–04:59 → MADRUGADA
    Domingo → DOMINGO
    Retornar filas con flag de tipo de anomalía horaria.
    """
    logger.info("Iniciando detección de horarios ilegítimos...")
    temp_df = df.copy()
    
    temp_df["hora"] = temp_df["fecha_consulta"].dt.hour
    temp_df["dia_semana"] = temp_df["fecha_consulta"].dt.dayofweek # 6 es Domingo
    
    is_madrugada = (temp_df["hora"] >= 0) & (temp_df["hora"] < 5)
    is_domingo = temp_df["dia_semana"] == 6
    
    illegal_rows = temp_df[is_madrugada | is_domingo].copy()
    
    if illegal_rows.empty:
        illegal_rows["tipo_anomalia"] = pd.Series(dtype=str)
    else:
        # Generar razones de manera vectorizada
        reasons_madrugada = np.where((illegal_rows["hora"] >= 0) & (illegal_rows["hora"] < 5), "MADRUGADA", "")
        reasons_domingo = np.where(illegal_rows["dia_semana"] == 6, "DOMINGO", "")
        
        combined = np.where(
            (reasons_madrugada != "") & (reasons_domingo != ""),
            "MADRUGADA+DOMINGO",
            np.where(reasons_madrugada != "", "MADRUGADA", reasons_domingo)
        )
        illegal_rows["tipo_anomalia"] = combined
    
    # Retornar columnas relevantes para reporte
    cols_to_keep = ["ruc", "cod_usuario", "fecha_consulta", "dni_consultado", "tipo_anomalia"]
    # Asegurar que existan
    for c in cols_to_keep:
        if c not in illegal_rows.columns:
            illegal_rows[c] = "N/A"
            
    return illegal_rows[cols_to_keep].reset_index(drop=True)

def detect_repeated_dni(df: pd.DataFrame, threshold: int = 50) -> pd.DataFrame:
    """
    Agrupa por (ruc, dni_consultado).
    Marcar DNIs consultados más de UMBRAL_DNI veces.
    """
    logger.info("Iniciando detección de DNI repetido...")
    temp_df = df.copy()
    if "ruc" not in temp_df.columns:
        temp_df["ruc"] = "SIN_RUC"
        
    total_consultas = len(temp_df)
    if total_consultas == 0:
        return pd.DataFrame(columns=["ruc", "dni_consultado", "count", "porcentaje_del_total"])
        
    grouped = temp_df.groupby(["ruc", "dni_consultado"]).size().reset_index(name="count")
    repeated = grouped[grouped["count"] > threshold].copy()
    repeated["porcentaje_del_total"] = (repeated["count"] / total_consultas) * 100
    
    return repeated.sort_values(by="count", ascending=False).reset_index(drop=True)

def detect_periodic_patterns(df: pd.DataFrame, std_threshold: float = 2.0, min_count: int = 20) -> pd.DataFrame:
    """
    Para cada (ruc, cod_usuario), calcular intervalos entre consultas consecutivas.
    Si la desviación estándar de los intervalos (en segundos) es < 2.0 y hay >= 20 consultas
    -> marcar como automatizado.
    """
    logger.info("Iniciando detección de patrones periódicos...")
    temp_df = df.copy().sort_values(by="fecha_consulta")
    if "ruc" not in temp_df.columns:
        temp_df["ruc"] = "SIN_RUC"
    if "cod_usuario" not in temp_df.columns:
        if "nombre_usuario" in temp_df.columns:
            temp_df["cod_usuario"] = temp_df["nombre_usuario"]
        else:
            temp_df["cod_usuario"] = "USUARIO_UNICO"
            
    periodic_list = []
    
    grouped = temp_df.groupby(["ruc", "cod_usuario"])
    for (ruc, cod_user), group in grouped:
        if len(group) < min_count:
            continue
            
        # Calcular diferencias en segundos
        intervals = group["fecha_consulta"].diff().dropna().dt.total_seconds()
        
        if len(intervals) >= min_count - 1:
            std_dev = intervals.std()
            mean_interval = intervals.mean()
            
            if std_dev < std_threshold:
                periodic_list.append({
                    "ruc": ruc,
                    "cod_usuario": cod_user,
                    "total_consultas": len(group),
                    "intervalo_promedio_seg": round(mean_interval, 2),
                    "desviacion_estandar": round(std_dev, 2)
                })
                
    if not periodic_list:
        return pd.DataFrame(columns=["ruc", "cod_usuario", "total_consultas", "intervalo_promedio_seg", "desviacion_estandar"])
        
    return pd.DataFrame(periodic_list)

def detect_triangulation(df: pd.DataFrame, dni_info_dict: dict) -> list[dict]:
    """
    Cruzar DNIs repetidos con la lista de directivos/propietarios del RUC investigado.
    Si el DNI consultado frecuentemente coincide con un directivo del mismo RUC -> flag TRIANGULACION.
    dni_info_dict mapea dni string -> objeto DNIInfo (o dict con info del dni)
    """
    logger.info("Iniciando detección de triangulación...")
    triangulations = []
    
    # dni_info_dict contiene claves dni con es_directivo_ruc = True
    for dni, info in dni_info_dict.items():
        # Si es un objeto de clase DNIInfo o un diccionario, extraemos sus atributos/claves
        es_directivo = getattr(info, "es_directivo_ruc", False) or (isinstance(info, dict) and info.get("es_directivo_ruc", False))
        if es_directivo:
            # Buscar en el DataFrame cuántas veces fue consultado por ese RUC
            # Agrupamos por ruc
            ruc_counts = df[df["dni_consultado"] == dni].groupby("ruc").size()
            nombre = getattr(info, "nombre_completo", "Nombre Desconocido") or (isinstance(info, dict) and info.get("nombre_completo", "Nombre Desconocido"))
            for ruc, cnt in ruc_counts.items():
                triangulations.append({
                    "ruc": ruc,
                    "dni": dni,
                    "nombre": nombre,
                    "count": cnt,
                    "detalle": f"El DNI {dni} ({nombre}), que pertenece a un directivo/propietario del RUC {ruc}, fue consultado {cnt} veces."
                })
                
    return triangulations

def run_all_detections(df: pd.DataFrame, args) -> AnomalyReport:
    """
    Ejecuta todas las detecciones de anomalías y consolida el reporte.
    """
    # Leer umbrales de argumentos CLI o configuraciones globales
    umb_rafaga = getattr(args, "umbral_rafaga", 10)
    umb_volumen = getattr(args, "umbral_volumen", 100)
    umb_dni = getattr(args, "umbral_dni", 50)
    
    bursts = detect_bursts(df, umb_rafaga)
    high_volume = detect_high_volume(df, umb_volumen)
    illegal_hours = detect_illegal_hours(df)
    repeated_dni = detect_repeated_dni(df, umb_dni)
    periodic = detect_periodic_patterns(df, min_count=20)
    
    # El análisis de triangulación inicial es vacío, se actualiza después de investigar DNIs
    triangulation = []
    
    # Calcular severity_score (0-100)
    score = 0
    if not bursts.empty:
        score += 25
    if not high_volume.empty:
        score += 25
    if not illegal_hours.empty:
        score += 15
    if not repeated_dni.empty:
        score += 15
    if not periodic.empty:
        score += 20
        
    severity_score = min(score, 100)
    
    # Generar summary_text interpretativo
    ruc_principal = df["ruc"].iloc[0] if not df.empty else "N/A"
    total_consultas = len(df)
    
    summary = (
        f"Durante el periodo de análisis, la empresa con RUC {ruc_principal} realizó un total de {total_consultas} consultas. "
        f"El análisis forense determinó un Nivel de Severidad de {severity_score}/100. "
    )
    
    anomalias_list = []
    if not bursts.empty:
        anomalias_list.append(f"{len(bursts)} eventos de ráfagas (consultas masivas en menos de 60 segundos)")
    if not high_volume.empty:
        anomalias_list.append(f"{len(high_volume)} horas con volumen de consultas inusualmente alto")
    if not illegal_hours.empty:
        anomalias_list.append(f"{len(illegal_hours)} consultas en horarios ilegítimos (madrugadas o domingos)")
    if not repeated_dni.empty:
        anomalias_list.append(f"{len(repeated_dni)} DNI(s) consultados repetidamente por encima del umbral de {umb_dni} veces")
    if not periodic.empty:
        anomalias_list.append(f"{len(periodic)} patrones de consulta automatizada periódica (bots)")
        
    if anomalias_list:
        summary += "Se identificaron los siguientes patrones sospechosos: " + ", ".join(anomalias_list) + "."
    else:
        summary += "No se detectaron patrones anómalos significativos en base a los umbrales configurados."
        
    return AnomalyReport(
        bursts=bursts,
        high_volume=high_volume,
        illegal_hours=illegal_hours,
        repeated_dni=repeated_dni,
        periodic=periodic,
        triangulation=triangulation,
        severity_score=severity_score,
        summary_text=summary
    )
