import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Agregar el directorio actual al path para importar módulos correctamente
sys.path.append(str(Path(__file__).resolve().parent))

from config import (
    OUTPUT_DIR, GRAFICOS_DIR, INFORMES_DIR, TEMPLATE_PATH,
    UMBRAL_RAFAGA, UMBRAL_VOLUMEN, UMBRAL_DNI_REPETIDO
)
from modules.data_loader import load_excel
from modules.anomaly_detector import run_all_detections, detect_triangulation
from modules.dni_investigator import investigate_dnis
from modules.chart_generator import generate_all
from modules.report_builder import build_report

def setup_logging(verbose: bool = False) -> str:
    """
    Configura el sistema de logging estándar.
    Crea el log en la carpeta de salida.
    """
    # Asegurar que el directorio de salida existe
    log_dir = Path(OUTPUT_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"log_{timestamp}.txt"
    
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configurar formateador
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # Logger raíz del proyecto
    logger = logging.getLogger("reniec_anomalias")
    logger.setLevel(level)
    
    # Limpiar handlers anteriores si existen
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # Handler de archivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info("Sistema de auditoría de consumos RENIEC iniciado.")
    logger.info(f"Archivo de log creado en: {log_file}")
    
    return str(log_file)

def parse_args():
    """
    Parsea los argumentos de línea de comandos.
    """
    parser = argparse.ArgumentParser(
        description="Sistema de análisis forense y detección de anomalías en consumos de servicios RENIEC."
    )
    parser.add_argument(
        "archivo",
        nargs="?",
        default="datos_simulados.xlsx",
        help="Ruta al archivo de datos a analizar (.xlsx, .xls, .csv, .txt, .tsv)"
    )
    parser.add_argument(
        "--servicio",
        default="CONSULTAS EN LINEA VIA LINEA DEDICADA",
        help="Nombre del servicio RENIEC si no está definido en el archivo de datos"
    )
    parser.add_argument(
        "--servicio-filter",
        default=None,
        help="Filtrar el análisis a un servicio de la columna servicio/NOMBRE_SERVICIO específico"
    )
    parser.add_argument(
        "--ruc",
        default=None,
        help="Filtrar el análisis a un RUC de empresa específico"
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Fecha de inicio para filtrar los datos (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_DIR),
        help="Ruta de la carpeta de salida para reportes y gráficos"
    )
    parser.add_argument(
        "--umbral-rafaga",
        type=int,
        default=UMBRAL_RAFAGA,
        help="Umbral de consultas/minuto para detectar ráfagas"
    )
    parser.add_argument(
        "--umbral-volumen",
        type=int,
        default=UMBRAL_VOLUMEN,
        help="Umbral de consultas/hora para volumen inusual"
    )
    parser.add_argument(
        "--umbral-dni",
        type=int,
        default=UMBRAL_DNI_REPETIDO,
        help="Umbral de repeticiones para marcar un DNI"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar logs de depuración detallados (DEBUG)"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Generar datos simulados de prueba antes de correr el análisis"
    )
    
    return parser.parse_args()

def generate_simulated_excel(filepath: str) -> None:
    """
    Genera un archivo Excel simulado con patrones normales y anómalos
    para probar todas las detecciones de la auditoría.
    """
    import pandas as pd
    from datetime import datetime, timedelta
    
    print(f"Generando datos de prueba simulados en: {filepath} ...")
    records = []
    
    # 1. Consultas normales (RUC 20123456789, TECH SOLUTIONS)
    # 100 consultas distribuidas a lo largo de la semana en horario laboral (9 AM a 5 PM)
    for i in range(100):
        offset_days = i % 5  # Lunes a Viernes
        offset_hours = (i * 7) % 8 + 9  # 9 AM a 5 PM
        offset_mins = (i * 13) % 60
        query_time = datetime(2026, 6, 1, 9, 0, 0) + timedelta(days=offset_days, hours=offset_hours, minutes=offset_mins)
        records.append({
            "RUC_EMPRESA": "20123456789",
            "DE_RAZON_SOCIAL": "TECH SOLUTIONS PERU S.A.C.",
            "NU_DOC_USUARIO": "USR_NORMAL",
            "DE_USUARIO": "USUARIO NORMAL",
            "FEC_CONSULTA": query_time.strftime("%Y-%m-%d %H:%M:%S"),
            "NU_DNI_CONSULTADO": f"70{i:06d}",
            "RESPUESTA": "HIT",
            "NOMBRE_SERVICIO": "CONSULTAS EN LINEA VIA LINEA DEDICADA",
            "DE_IP_USUARIO": "192.168.1.100"
        })
        
    # 2. Ráfaga: 15 consultas en 1 minuto (Usuario: USR_RAFAGA)
    # Umbral de ráfaga es 10 consultas/min
    burst_time = datetime(2026, 6, 2, 10, 15, 0)
    for i in range(15):
        query_time = burst_time + timedelta(seconds=i * 3) # todas en 45 segundos
        records.append({
            "RUC_EMPRESA": "20123456789",
            "DE_RAZON_SOCIAL": "TECH SOLUTIONS PERU S.A.C.",
            "NU_DOC_USUARIO": "USR_RAFAGA",
            "DE_USUARIO": "OPERADOR RAFAGA",
            "FEC_CONSULTA": query_time.strftime("%Y-%m-%d %H:%M:%S"),
            "NU_DNI_CONSULTADO": f"80{i:06d}",
            "RESPUESTA": "HIT",
            "NOMBRE_SERVICIO": "CONSULTAS EN LINEA VIA LINEA DEDICADA",
            "DE_IP_USUARIO": "192.168.1.101"
        })
        
    # 3. Volumen inusual por hora: 120 consultas en 1 hora (Usuario: USR_VOLUMEN)
    # Umbral de volumen es 100 consultas/hora
    volume_time = datetime(2026, 6, 2, 14, 0, 0)
    for i in range(120):
        query_time = volume_time + timedelta(seconds=i * 25) # distribuidas en 50 minutos
        records.append({
            "RUC_EMPRESA": "20123456789",
            "DE_RAZON_SOCIAL": "TECH SOLUTIONS PERU S.A.C.",
            "NU_DOC_USUARIO": "USR_VOLUMEN",
            "DE_USUARIO": "OPERADOR VOLUMEN",
            "FEC_CONSULTA": query_time.strftime("%Y-%m-%d %H:%M:%S"),
            "NU_DNI_CONSULTADO": f"90{i:06d}",
            "RESPUESTA": "HIT",
            "NOMBRE_SERVICIO": "CONSULTAS EN LINEA VIA LINEA DEDICADA",
            "DE_IP_USUARIO": "192.168.1.102"
        })
        
    # 4. Horarios ilegítimos:
    # A. Madrugada (2:00 AM a 2:05 AM)
    night_time = datetime(2026, 6, 2, 2, 0, 0)
    for i in range(6):
        query_time = night_time + timedelta(minutes=i)
        records.append({
            "RUC_EMPRESA": "20123456789",
            "DE_RAZON_SOCIAL": "TECH SOLUTIONS PERU S.A.C.",
            "NU_DOC_USUARIO": "USR_NOCTURNO",
            "DE_USUARIO": "OPERADOR NOCTURNO",
            "FEC_CONSULTA": query_time.strftime("%Y-%m-%d %H:%M:%S"),
            "NU_DNI_CONSULTADO": f"60{i:06d}",
            "RESPUESTA": "HIT",
            "NOMBRE_SERVICIO": "CONSULTAS EN LINEA VIA LINEA DEDICADA",
            "DE_IP_USUARIO": "192.168.1.103"
        })
    # B. Domingo (2026-05-31 es domingo)
    sunday_time = datetime(2026, 5, 31, 11, 0, 0)
    for i in range(8):
        query_time = sunday_time + timedelta(minutes=i * 5)
        records.append({
            "RUC_EMPRESA": "20123456789",
            "DE_RAZON_SOCIAL": "TECH SOLUTIONS PERU S.A.C.",
            "NU_DOC_USUARIO": "USR_DOMINGO",
            "DE_USUARIO": "OPERADOR DOMINICAL",
            "FEC_CONSULTA": query_time.strftime("%Y-%m-%d %H:%M:%S"),
            "NU_DNI_CONSULTADO": f"50{i:06d}",
            "RESPUESTA": "HIT",
            "NOMBRE_SERVICIO": "CONSULTAS EN LINEA VIA LINEA DEDICADA",
            "DE_IP_USUARIO": "192.168.1.104"
        })
        
    # 5. DNI repetido: DNI 99999999 consultado 60 veces (Usuario: USR_REPETICION)
    # Umbral de DNI repetido es 50
    rep_time = datetime(2026, 6, 2, 9, 30, 0)
    for i in range(60):
        query_time = rep_time + timedelta(minutes=i * 10)
        records.append({
            "RUC_EMPRESA": "20123456789",
            "DE_RAZON_SOCIAL": "TECH SOLUTIONS PERU S.A.C.",
            "NU_DOC_USUARIO": "USR_REPETICION",
            "DE_USUARIO": "OPERADOR REPETICION",
            "FEC_CONSULTA": query_time.strftime("%Y-%m-%d %H:%M:%S"),
            "NU_DNI_CONSULTADO": "99999999",
            "RESPUESTA": "HIT",
            "NOMBRE_SERVICIO": "CONSULTAS EN LINEA VIA LINEA DEDICADA",
            "DE_IP_USUARIO": "192.168.1.105"
        })
        
    # 6. Patrón periódico (Posible automatización): 25 consultas cada 5 segundos exactos
    # Umbral: std dev < 2.0 y al menos 20 consultas
    periodic_time = datetime(2026, 6, 2, 16, 0, 0)
    for i in range(25):
        query_time = periodic_time + timedelta(seconds=i * 5)
        records.append({
            "RUC_EMPRESA": "20123456789",
            "DE_RAZON_SOCIAL": "TECH SOLUTIONS PERU S.A.C.",
            "NU_DOC_USUARIO": "USR_BOT",
            "DE_USUARIO": "BOT AUTOMATIZADO",
            "FEC_CONSULTA": query_time.strftime("%Y-%m-%d %H:%M:%S"),
            "NU_DNI_CONSULTADO": f"40{i:06d}",
            "RESPUESTA": "HIT",
            "NOMBRE_SERVICIO": "CONSULTAS EN LINEA VIA LINEA DEDICADA",
            "DE_IP_USUARIO": "192.168.1.106"
        })
        
    # 7. Triangulación: Directivo consultado frecuentemente.
    # DNI 12345678 es directivo de RUC 20123456789 en MOCK_DIRECTIVOS_POR_RUC.
    # Vamos a consultarlo 55 veces.
    triang_time = datetime(2026, 6, 2, 11, 0, 0)
    for i in range(55):
        query_time = triang_time + timedelta(minutes=i * 8)
        records.append({
            "RUC_EMPRESA": "20123456789",
            "DE_RAZON_SOCIAL": "TECH SOLUTIONS PERU S.A.C.",
            "NU_DOC_USUARIO": "USR_TRIANGULO",
            "DE_USUARIO": "OPERADOR TRIANGULO",
            "FEC_CONSULTA": query_time.strftime("%Y-%m-%d %H:%M:%S"),
            "NU_DNI_CONSULTADO": "12345678",
            "RESPUESTA": "HIT",
            "NOMBRE_SERVICIO": "CONSULTAS EN LINEA VIA LINEA DEDICADA",
            "DE_IP_USUARIO": "192.168.1.107"
        })
        
    df_simulated = pd.DataFrame(records)
    df_simulated.to_excel(filepath, index=False)
    print("Datos simulados guardados exitosamente.")

def main():
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("reniec_anomalias")
    
    target_path = Path(args.archivo)
    if not target_path.exists():
        from config import DATA_DIR
        if (DATA_DIR / target_path.name).exists():
            target_path = DATA_DIR / target_path.name
            args.archivo = str(target_path)

    if args.simulate or args.archivo == "simulate" or not target_path.exists():
        logger.info("Modo de simulación activado o archivo no encontrado. Generando datos simulados.")
        sim_path = str(DATA_DIR / "datos_simulados.xlsx") if 'DATA_DIR' in locals() else "datos_simulados.xlsx"
        generate_simulated_excel(sim_path)
        args.archivo = sim_path
        
    try:
        # Configurar directorios de salida dinámicamente según el argumento
        custom_output_dir = Path(args.output)
        graficos_path = custom_output_dir / "graficos"
        informes_path = custom_output_dir / "informes"
        
        # 1. Carga y normalización de datos
        df, metadata = load_excel(args.archivo, args.servicio)
        
        # Filtrar por fecha de inicio si se especifica
        if args.start_date:
            logger.info(f"Filtrando datos desde la fecha de inicio: {args.start_date}")
            try:
                import pandas as pd
                start_dt = pd.to_datetime(args.start_date)
                df = df[df["fecha_consulta"] >= start_dt].reset_index(drop=True)
                if df.empty:
                    logger.error(f"No se encontraron registros desde la fecha: {args.start_date}")
                    sys.exit(1)
                # Actualizar metadatos
                metadata["total_filas"] = len(df)
                metadata["fecha_inicio"] = df["fecha_consulta"].min()
                metadata["fecha_fin"] = df["fecha_consulta"].max()
            except Exception as e:
                logger.error(f"Error al parsear o filtrar por fecha de inicio: {str(e)}")
                sys.exit(1)
        
        # Filtrar por RUC si se especifica
        if args.ruc:
            logger.info(f"Filtrando datos por RUC especificado: {args.ruc}")
            df = df[df["ruc"] == str(args.ruc).strip()].reset_index(drop=True)
            if df.empty:
                logger.error(f"No se encontraron registros para el RUC: {args.ruc}")
                sys.exit(1)
            # Actualizar metadatos
            metadata["ruc_principal"] = args.ruc
            metadata["rucs_unicos"] = [args.ruc]
            if "empresa" in df.columns and not df.empty:
                metadata["empresa_principal"] = df["empresa"].iloc[0]
                metadata["empresas_unicas"] = [df["empresa"].iloc[0]]
            metadata["total_filas"] = len(df)
            metadata["fecha_inicio"] = df["fecha_consulta"].min()
            metadata["fecha_fin"] = df["fecha_consulta"].max()

        # Filtrar por servicio si se especifica
        if args.servicio_filter:
            logger.info(f"Filtrando datos por servicio especificado: {args.servicio_filter}")
            df = df[df["servicio"] == str(args.servicio_filter).strip()].reset_index(drop=True)
            if df.empty:
                logger.error(f"No se encontraron registros para el servicio: {args.servicio_filter}")
                sys.exit(1)
            # Actualizar metadatos
            metadata["servicio"] = args.servicio_filter
            metadata["servicios_unicos"] = [args.servicio_filter]
            metadata["total_filas"] = len(df)
            metadata["fecha_inicio"] = df["fecha_consulta"].min()
            metadata["fecha_fin"] = df["fecha_consulta"].max()

        # 2. Detección de anomalías
        report = run_all_detections(df, args)
        
        # 3. Investigación de DNI repetidos
        dni_infos = investigate_dnis(report.repeated_dni, metadata["ruc_principal"])
        
        # 4. Cruzar triangulación (si algún DNI de directivo coincide)
        dni_infos_dict = {info.dni: info for info in dni_infos}
        report.triangulation = detect_triangulation(df, dni_infos_dict)
        if report.triangulation:
            logger.warning(f"¡Se detectó triangulación sospechosa! Directivos consultados: {len(report.triangulation)} caso(s).")
            # Aumentar score de severidad en el reporte si hay triangulación
            report.severity_score = min(report.severity_score + 30, 100)
            report.summary_text += f" ADVERTENCIA: Se detectó triangulación sospechosa donde directivos del RUC analizado fueron consultados frecuentemente."

        # 5. Generación de gráficos visuales
        charts = generate_all(df, report, str(graficos_path))
        
        # 6. Construcción del informe Word final
        # Usamos la plantilla provista, o fallamos de forma segura buscando plantilla_informe.docx local
        local_template = Path(TEMPLATE_PATH)
        output_report_path = build_report(
            df=df,
            metadata=metadata,
            report=report,
            charts=charts,
            dni_infos=dni_infos,
            template_path=str(local_template),
            output_path=str(informes_path)
        )
        
        logger.info("=================================================================")
        logger.info(" PROCESAMIENTO FINALIZADO EXITOSAMENTE")
        logger.info(f" RUC Principal: {metadata['ruc_principal']}")
        logger.info(f" Razón Social:  {metadata['empresa_principal']}")
        logger.info(f" Nivel de Severidad: {report.severity_score}/100")
        logger.info(f" Gráficos guardados en: {graficos_path.resolve()}")
        logger.info(f" Informe Word final:    {output_report_path}")
        logger.info("=================================================================")
        
    except Exception as e:
        logger.exception(f"Ocurrió un error crítico durante la ejecución: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
