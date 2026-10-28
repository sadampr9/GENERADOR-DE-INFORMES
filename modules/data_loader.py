import os
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger("reniec_anomalias")

# Column aliases mappings
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

def load_excel(filepath: str, servicio_default: str = "CONSULTAS EN LINEA VIA LINEA DEDICADA") -> tuple[pd.DataFrame, dict]:
    """
    Carga y normaliza el archivo de datos (Excel, CSV, TXT).
    Retorna el DataFrame normalizado y un diccionario de metadatos.
    """
    path = Path(filepath)
    if not path.exists():
        from config import DATA_DIR
        data_path = DATA_DIR / path.name
        if data_path.exists():
            path = data_path
            filepath = str(data_path)
        else:
            raise FileNotFoundError(f"El archivo no existe: {filepath}")

    ext = path.suffix.lower()
    logger.info(f"Cargando archivo {path.name} ({ext})...")

    # 1. Leer archivo según extensión
    try:
        if ext in [".xlsx", ".xls"]:
            df = pd.read_excel(filepath, engine="openpyxl")
        elif ext == ".csv":
            # Detectar separador leyendo la primera línea
            sep = ','
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
            except UnicodeDecodeError:
                with open(filepath, 'r', encoding='latin-1') as f:
                    first_line = f.readline()
            if ';' in first_line:
                sep = ';'
            elif '\t' in first_line:
                sep = '\t'
            
            # Intentar primero UTF-8, luego latin-1
            try:
                df = pd.read_csv(filepath, sep=sep, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, sep=sep, encoding="latin-1")
        elif ext in [".txt", ".tsv"]:
            # Detectar separador leyendo la primera línea
            sep = ','
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline()
            except Exception:
                with open(filepath, 'r', encoding='latin-1') as f:
                    first_line = f.readline()
            if '|' in first_line:
                sep = '|'
            elif ';' in first_line:
                sep = ';'
            elif '\t' in first_line:
                sep = '\t'
            
            try:
                df = pd.read_csv(filepath, sep=sep, engine="c", encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, sep=sep, engine="c", encoding="latin-1")
        else:
            raise ValueError(f"Formato de archivo no soportado: {ext}")
    except Exception as e:
        logger.error(f"Error al leer el archivo Excel/CSV: {str(e)}")
        raise e

    # 2. Renombrar columnas al esquema canónico interno
    rename_dict = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for col in df.columns:
            if col in aliases or col.upper() in [a.upper() for a in aliases]:
                rename_dict[col] = canonical
                break
    
    df = df.rename(columns=rename_dict)
    
    # Validar columnas obligatorias
    required_cols = ["fecha_consulta", "dni_consultado"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Columna crítica requerida ausente: '{col}' o equivalente no encontrada.")

    # Asegurar que existan todas las columnas canónicas
    if "cod_usuario" not in df.columns:
        df["cod_usuario"] = "USUARIO_UNICO"
    else:
        df["cod_usuario"] = df["cod_usuario"].fillna("USUARIO_UNICO").astype(str)

    if "nombre_usuario" not in df.columns:
        df["nombre_usuario"] = "USUARIO OPERADOR"
    else:
        df["nombre_usuario"] = df["nombre_usuario"].fillna("USUARIO OPERADOR").astype(str)

    if "ip_usuario" not in df.columns:
        df["ip_usuario"] = "0.0.0.0"
    else:
        df["ip_usuario"] = df["ip_usuario"].fillna("0.0.0.0").astype(str)

    if "respuesta" not in df.columns:
        df["respuesta"] = "HIT"
    else:
        df["respuesta"] = df["respuesta"].fillna("HIT").astype(str)

    # 3. Parsear fecha_consulta a datetime64[ns]
    # Eliminar filas con fecha_consulta nula
    initial_rows = len(df)
    df = df.dropna(subset=["fecha_consulta"])
    null_dates = initial_rows - len(df)
    if null_dates > 0:
        logger.warning(f"Se eliminaron {null_dates} filas con fecha de consulta nula.")

    df["fecha_consulta"] = pd.to_datetime(df["fecha_consulta"], dayfirst=True, errors="coerce")
    invalid_dates = df["fecha_consulta"].isna().sum()
    if invalid_dates > 0:
        logger.warning(f"Se eliminaron {invalid_dates} filas con fechas de consulta mal formateadas.")
        df = df.dropna(subset=["fecha_consulta"])

    # 4. Asignar el servicio: columna del Excel > argumento CLI > valor por defecto
    if "servicio" in df.columns:
        # Si la columna contiene valores nulos o vacíos, rellenar
        df["servicio"] = df["servicio"].fillna(servicio_default).astype(str)
    else:
        filename_upper = path.name.upper()
        if servicio_default == "CONSULTAS EN LINEA VIA LINEA DEDICADA" and ("SVB" in filename_upper or "BIOMETRICA" in filename_upper):
            df["servicio"] = "SERVICIO DE VERIFICACION BIOMETRICA"
        elif servicio_default == "CONSULTAS EN LINEA VIA LINEA DEDICADA" and "PIDE" in filename_upper:
            df["servicio"] = "PLATAFORMA INTEROPERABILIDAD DEL ESTADO - PIDE"
        else:
            df["servicio"] = servicio_default

    # 5. Convertir dni_consultado a string, rellenar con ceros a la izquierda hasta 8 caracteres
    df["dni_consultado"] = df["dni_consultado"].astype(str).str.split('.').str[0]  # Por si se importó como float
    df["dni_consultado"] = df["dni_consultado"].str.strip().str.zfill(8)

    # 6. Normalizar RUC y Empresa si están presentes
    if "ruc" in df.columns:
        df["ruc"] = df["ruc"].astype(str).str.split('.').str[0].str.strip()
    else:
        filename_upper = path.name.upper()
        if "INTERBANK" in filename_upper:
            df["ruc"] = "20100053455"
        elif "JNE" in filename_upper:
            df["ruc"] = "20131370603"
        else:
            df["ruc"] = "SIN_RUC"
        
    if "empresa" in df.columns:
        df["empresa"] = df["empresa"].fillna("EMPRESA NO ESPECIFICADA").astype(str).str.strip()
    else:
        filename_upper = path.name.upper()
        if "INTERBANK" in filename_upper:
            df["empresa"] = "BANCO INTERNACIONAL DEL PERU S.A. INTERBANK"
        elif "JNE" in filename_upper:
            df["empresa"] = "JURADO NACIONAL DE ELECCIONES"
        elif "MINEDU" in filename_upper or "MINISTERIO_DE_EDUCACION" in filename_upper:
            df["empresa"] = "MINISTERIO DE EDUCACION"
        elif "cod_usuario" in df.columns:
            # Si el campo cod_usuario contiene el nombre de la empresa (ej: archivos LD con CODIGO_USUARIO)
            sample_val = df["cod_usuario"].dropna().iloc[0] if not df["cod_usuario"].dropna().empty else ""
            if sample_val and len(sample_val) > 5 and not sample_val.isdigit():
                df["empresa"] = sample_val
            else:
                df["empresa"] = "EMPRESA NO ESPECIFICADA"
        else:
            df["empresa"] = "EMPRESA NO ESPECIFICADA"

    # 7. Ordenar el DataFrame por fecha_consulta ascendente
    df = df.sort_values(by="fecha_consulta").reset_index(drop=True)

    # 8. Obtener metadatos
    rucs_unicos = df["ruc"].unique().tolist()
    ruc_principal = rucs_unicos[0] if len(rucs_unicos) > 0 else "SIN_RUC"
    empresas_unicas = df["empresa"].unique().tolist()
    empresa_principal = empresas_unicas[0] if len(empresas_unicas) > 0 else "EMPRESA NO ESPECIFICADA"
    
    fecha_inicio = df["fecha_consulta"].min()
    fecha_fin = df["fecha_consulta"].max()
    servicios_unicos = df["servicio"].unique().tolist()
    servicio_principal = servicios_unicos[0] if len(servicios_unicos) > 0 else servicio_default

    metadata = {
        "filename": path.name,
        "total_filas": len(df),
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "rucs_unicos": rucs_unicos,
        "ruc_principal": ruc_principal,
        "empresa_principal": empresa_principal,
        "empresas_unicas": empresas_unicas,
        "servicio": servicio_principal,
        "servicios_unicos": servicios_unicos
    }

    logger.info(f"Carga exitosa. Total filas procesadas: {len(df)}")
    return df, metadata
