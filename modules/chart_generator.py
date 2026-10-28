import os
import matplotlib
matplotlib.use("Agg")  # Evita problemas de interfaz gráfica en entornos headless
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from modules.anomaly_detector import AnomalyReport

# Configuración de estilo
sns.set_theme(style="whitegrid", palette="muted")
FIGSIZE_WIDE = (14, 5)
FIGSIZE_SQUARE = (10, 8)
DPI = 150

def format_integer_axis(ax, axis='y'):
    """
    Formatea el eje especificado ('y' o 'x') para mostrar enteros exactos con separadores de miles
    y deshabilitar la notación científica.
    """
    formatter = ticker.FuncFormatter(lambda x, p: f'{int(x):,}')
    if axis == 'y':
        ax.yaxis.set_major_formatter(formatter)
    elif axis == 'x':
        ax.xaxis.set_major_formatter(formatter)

def load_sadam_full_series(empresa_name, ruc, servicio):
    import re
    from config import DATA_DIR
    # Todos los SADAM de data/: el BASE primero y los demás después (los más recientes sobrescriben días repetidos)
    files = sorted(DATA_DIR.glob("SADAM*.xlsx"), key=lambda f: ("BASE" not in f.name.upper(), f.stat().st_mtime))
    daily_records = {}
    
    for filepath in files:
        if not filepath.exists():
            continue
        try:
            df_raw = pd.read_excel(filepath, header=None)
            years = df_raw.iloc[2]
            months = df_raw.iloc[3]
            days = df_raw.iloc[5]
            data_rows = df_raw.iloc[7:].copy()
            
            sub_df = pd.DataFrame()
            
            if ruc:
                ruc_clean = re.sub(r'\D', '', str(ruc))
                if len(ruc_clean) >= 10:
                    ruc_prefix = ruc_clean[:10]
                    for c_idx in [3, 4, 2]:
                        mask = data_rows[c_idx].astype(str).str.contains(ruc_prefix, na=False)
                        if mask.any():
                            sub_df = data_rows[mask]
                            break
                            
            if sub_df.empty and empresa_name:
                stopwords = {'MINISTERIO', 'SUPERINTENDENCIA', 'MUNICIPALIDAD', 'BANCO', 'FINANCIERA', 'PERU', 'SAC', 'SA', 'DEL', 'DE', 'LA', 'Y', 'LOS', 'LAS'}
                emp_upper = str(empresa_name).upper()
                if 'AFP' in emp_upper and 'BANCA' in emp_upper:
                    kws = ['BANCA', 'SEGUROS']
                else:
                    kws = [w for w in re.split(r'\W+', emp_upper) if len(w) >= 3 and w not in stopwords]
                
                if kws:
                    for c_idx in [2, 3]:
                        mask_kw = pd.Series(True, index=data_rows.index)
                        for kw in kws:
                            mask_kw = mask_kw & data_rows[c_idx].astype(str).str.upper().str.contains(kw, na=False)
                        if mask_kw.any():
                            sub_df = data_rows[mask_kw]
                            break
                            
            if sub_df.empty:
                continue
                
            if servicio and not sub_df.empty:
                serv_str = str(servicio).upper()
                serv_pattern = 'LINEA DEDICADA|LD' if ('DEDICADA' in serv_str or 'LD' in serv_str) else ('INTERNET' if 'INTERNET' in serv_str else ('BIOMETR' if 'BIOMETR' in serv_str else re.escape(serv_str)))
                for c_idx in [0, 1, 4]:
                    mask_s = sub_df[c_idx].astype(str).str.contains(serv_pattern, case=False, na=False)
                    if mask_s.any():
                        sub_df = sub_df[mask_s]
                        break
                        
            for col_idx in range(5, df_raw.shape[1]):
                m = str(months[col_idx]).strip()
                d_str = str(days[col_idx]).strip()
                if m.isdigit() and len(m) == 6:
                    y_num = int(m[:4])
                    m_num = int(m[4:])
                    d_digits = ''.join(c for c in d_str if c.isdigit())
                    if d_digits:
                        try:
                            dt = pd.Timestamp(year=y_num, month=m_num, day=int(d_digits))
                            val = pd.to_numeric(sub_df[col_idx], errors='coerce').sum()
                            daily_records[dt] = val
                        except Exception:
                            pass
        except Exception:
            pass
            
    if daily_records:
        s = pd.Series(daily_records).sort_index()
        if not s.empty:
            return s
            
    return None

def generate_all(df: pd.DataFrame, report: AnomalyReport, output_dir: str) -> dict[str, str]:
    """
    Genera todos los gráficos obligatorios e identificados en el reporte de anomalías.
    Guarda los archivos en output_dir/graficos y retorna un diccionario con {chart_id: filepath_absoluto}.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    generated_charts = {}

    # Asegurar que el dataframe no esté vacío
    if df.empty:
        return generated_charts

    # Copia local del dataframe con columnas necesarias
    plot_df = df.copy()
    plot_df["hora"] = plot_df["fecha_consulta"].dt.hour
    plot_df["dia_semana"] = plot_df["fecha_consulta"].dt.day_name()
    plot_df["dia_semana_num"] = plot_df["fecha_consulta"].dt.dayofweek
    plot_df["fecha_dia"] = plot_df["fecha_consulta"].dt.date

    # G1: consumo_diario.png (Usando serie histórica 2025-2026 con formato avanzado de la imagen)
    try:
        import matplotlib.dates as mdates
        emp_name = plot_df["empresa"].iloc[0] if "empresa" in plot_df.columns else "ENTIDAD"
        ruc_val = plot_df["ruc"].iloc[0] if "ruc" in plot_df.columns else None
        serv_val = plot_df["servicio"].iloc[0] if "servicio" in plot_df.columns else "CONSULTAS EN LÍNEA VÍA LÍNEA DEDICADA"
        
        sadam_s = load_sadam_full_series(emp_name, ruc_val, serv_val)
        if sadam_s is not None and not sadam_s.empty:
            daily_series = sadam_s
        else:
            daily_series = plot_df.groupby("fecha_dia").size()
            daily_series.index = pd.to_datetime(daily_series.index)

        ma_7d = daily_series.rolling(window=7, min_periods=1).mean()
        mean_volume = daily_series.mean()

        max_hist_val = daily_series.max()
        max_hist_dt = daily_series.idxmax()

        # Pico reciente en 2026 si existe
        s_2026 = daily_series['2026-01-01':] if len(daily_series) > 60 else daily_series
        if not s_2026.empty:
            max_rec_val = s_2026.max()
            max_rec_dt = s_2026.idxmax()
        else:
            max_rec_val = max_hist_val
            max_rec_dt = max_hist_dt

        fig, ax = plt.subplots(figsize=(14, 6.5), dpi=DPI)
        fig.patch.set_facecolor('#F8F9FA')
        ax.set_facecolor('#FFFFFF')

        # Sombra / relleno bajo la curva
        ax.fill_between(daily_series.index, daily_series.values, color='#1F4068', alpha=0.08)

        # L1: Consumo Diario (Azul Oscuro)
        ax.plot(daily_series.index, daily_series.values, color='#1F4068', linewidth=1.2, label='Consumo Diario')

        # L2: Media Móvil 7d (Celeste Punteado)
        ax.plot(ma_7d.index, ma_7d.values, color='#00A8CC', linestyle=':', linewidth=1.5, label='Media Móvil 7d')

        # L3: Promedio Diario (Verde Descontinuado)
        ax.axhline(y=mean_volume, color='#16A085', linestyle='--', linewidth=1.5, label=f'Promedio Diario ({round(mean_volume, 1):,})')

        # Marcador Red Dot para Pico Máximo Histórico
        dt_hist_str = max_hist_dt.strftime('%d/%m/%Y') if hasattr(max_hist_dt, 'strftime') else str(max_hist_dt)
        ax.plot(max_hist_dt, max_hist_val, marker='o', color='#D32F2F', markersize=8, label=f'Pico Máximo Histórico: {int(max_hist_val):,} ({dt_hist_str})')

        # Marcador Orange Star para Pico Reciente
        dt_rec_lbl = max_rec_dt.strftime('%d de %B %Y') if hasattr(max_rec_dt, 'strftime') else str(max_rec_dt)
        if max_rec_dt != max_hist_dt:
            ax.plot(max_rec_dt, max_rec_val, marker='*', color='#E65100', markersize=10, label=f'Pico {dt_rec_lbl}: {int(max_rec_val):,} consultas')

        # Anotación 1: Pico Máximo Histórico (Rojo)
        dt_hist_full = max_hist_dt.strftime('%d de %B de %Y') if hasattr(max_hist_dt, 'strftime') else str(max_hist_dt)
        ax.annotate(
            f'PICO MÁXIMO HISTÓRICO\n{int(max_hist_val):,} consultas\n({dt_hist_full})',
            xy=(max_hist_dt, max_hist_val),
            xytext=(max_hist_dt + pd.Timedelta(days=35), max_hist_val * 0.88),
            arrowprops=dict(arrowstyle='->', color='#D32F2F', lw=2, connectionstyle='arc3,rad=-0.2'),
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#D32F2F', lw=1.5),
            fontsize=8, fontweight='bold', color='#D32F2F', ha='center'
        )

        # Anotación 2: Pico Reciente (Naranja) si es distinto del histórico
        if max_rec_dt != max_hist_dt:
            dt_rec_upper = max_rec_dt.strftime('%d DE %B %Y').upper() if hasattr(max_rec_dt, 'strftime') else str(max_rec_dt)
            ax.annotate(
                f'PICO {dt_rec_upper}\n{int(max_rec_val):,} consultas',
                xy=(max_rec_dt, max_rec_val),
                xytext=(max_rec_dt - pd.Timedelta(days=40), max_rec_val * 1.15 if max_rec_val < max_hist_val * 0.7 else max_rec_val * 0.85),
                arrowprops=dict(arrowstyle='->', color='#E65100', lw=2, connectionstyle='arc3,rad=-0.2'),
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#E65100', lw=1.5),
                fontsize=8, fontweight='bold', color='#E65100', ha='center'
            )

        # Títulos superiores (Header de dos líneas como en la imagen)
        plt.suptitle(f'{str(emp_name).upper()}', fontsize=12, fontweight='bold', color='#1A2530', y=0.97)
        plt.title(f'Evolución Diaria de Consumos — Servicio: {str(serv_val).upper()}', fontsize=11, fontweight='bold', color='#2C3E50', pad=12)

        start_str = daily_series.index.min().strftime('%d/%m/%Y') if hasattr(daily_series.index.min(), 'strftime') else str(daily_series.index.min())
        end_str = daily_series.index.max().strftime('%d/%m/%Y') if hasattr(daily_series.index.max(), 'strftime') else str(daily_series.index.max())
        ax.set_xlabel(f'Fecha de Consulta ({start_str} al {end_str})', fontsize=9, fontweight='bold', color='#2C3E50', labelpad=10)
        ax.set_ylabel('Cantidad de Consultas Diarias', fontsize=9, fontweight='bold', color='#2C3E50', labelpad=10)

        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{int(x):,}'))
        if len(daily_series) > 60:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
        plt.xticks(rotation=35, fontsize=8, color='#555555')
        plt.yticks(fontsize=8, color='#555555')

        ax.grid(True, linestyle=':', alpha=0.6, color='#CCCCCC')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#CCCCCC')
        ax.spines['bottom'].set_color('#CCCCCC')

        ax.legend(loc='upper left', fontsize=8, frameon=True, facecolor='white', edgecolor='#CCCCCC')

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        g1_path = out_path / "consumo_diario.png"
        plt.savefig(g1_path, dpi=DPI)
        plt.close()
        generated_charts["G1"] = str(g1_path.resolve())
    except Exception as e:
        print(f"Error generando G1: {e}")

    # G2: consumo_por_hora.png (Siempre)
    try:
        hourly_counts = plot_df.groupby("hora").size().reindex(range(24), fill_value=0)
        plt.figure(figsize=FIGSIZE_WIDE)
        ax = sns.barplot(x=hourly_counts.index, y=hourly_counts.values, color='#2ca02c')
        plt.title("Distribución de Consultas por Hora del Día", fontsize=14, fontweight="bold", pad=15)
        plt.xlabel("Hora del Día (0-23)", fontsize=12)
        plt.ylabel("Cantidad de Consultas", fontsize=12)
        format_integer_axis(ax, 'y')
        plt.xticks(range(24))
        plt.tight_layout()
        g2_path = out_path / "consumo_por_hora.png"
        plt.savefig(g2_path, dpi=DPI)
        plt.close()
        generated_charts["G2"] = str(g2_path.resolve())
    except Exception as e:
        print(f"Error generando G2: {e}")

    # G3: consumo_dia_semana.png (Siempre)
    try:
        weekday_map = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
        weekday_counts = plot_df.groupby("dia_semana_num").size().reindex(range(7), fill_value=0)
        weekday_names = [weekday_map[i] for i in range(7)]
        
        plt.figure(figsize=FIGSIZE_WIDE)
        ax = sns.barplot(x=weekday_names, y=weekday_counts.values, color='#9467bd')
        plt.title("Actividad de Consultas por Día de la Semana", fontsize=14, fontweight="bold", pad=15)
        plt.xlabel("Día de la Semana", fontsize=12)
        plt.ylabel("Cantidad de Consultas", fontsize=12)
        format_integer_axis(ax, 'y')
        
        # Anotación de valores exactos encima de cada barra
        for p in ax.patches:
            height = p.get_height()
            if height > 0:
                ax.annotate(f"{int(height):,}", (p.get_x() + p.get_width() / 2., height),
                            ha='center', va='bottom', xytext=(0, 5), textcoords='offset points', fontsize=10, fontweight='bold')
                            
        plt.tight_layout()
        g3_path = out_path / "consumo_dia_semana.png"
        plt.savefig(g3_path, dpi=DPI)
        plt.close()
        generated_charts["G3"] = str(g3_path.resolve())
    except Exception as e:
        print(f"Error generando G3: {e}")

    # G4: distribucion_usuario.png (Si hay >1 usuario único)
    if "cod_usuario" in plot_df.columns and plot_df["cod_usuario"].nunique() > 1:
        try:
            user_counts = plot_df["cod_usuario"].value_counts().head(10)
            plt.figure(figsize=FIGSIZE_SQUARE)
            ax = sns.barplot(y=user_counts.index, x=user_counts.values, orient='h', hue=user_counts.index, palette="viridis", legend=False)
            plt.title("Top 10 Usuarios por Volumen de Consultas", fontsize=14, fontweight="bold", pad=15)
            plt.xlabel("Cantidad de Consultas", fontsize=12)
            plt.ylabel("Código de Usuario", fontsize=12)
            format_integer_axis(ax, 'x')
            for p in ax.patches:
                width = p.get_width()
                if width > 0:
                    ax.annotate(f"{int(width):,}", (width, p.get_y() + p.get_height() / 2.),
                                ha='left', va='center', xytext=(5, 0), textcoords='offset points', fontsize=10, fontweight='bold')
            plt.tight_layout()
            g4_path = out_path / "distribucion_usuario.png"
            plt.savefig(g4_path, dpi=DPI)
            plt.close()
            generated_charts["G4"] = str(g4_path.resolve())
        except Exception as e:
            print(f"Error generando G4: {e}")

    # G5: rafagas_por_hora.png (Si bursts no está vacío)
    if not report.bursts.empty:
        try:
            # Graficar la distribución horaria de ráfagas
            bursts_df = report.bursts.copy()
            bursts_df["hora"] = pd.to_datetime(bursts_df["window_start"]).dt.hour
            burst_hourly = bursts_df.groupby("hora").size().reindex(range(24), fill_value=0)
            
            plt.figure(figsize=FIGSIZE_WIDE)
            ax = sns.barplot(x=burst_hourly.index, y=burst_hourly.values, color='#d62728')
            plt.title("Frecuencia de Ráfagas por Hora del Día", fontsize=14, fontweight="bold", pad=15)
            plt.xlabel("Hora del Día (0-23)", fontsize=12)
            plt.ylabel("Cantidad de Ráfagas Detectadas", fontsize=12)
            format_integer_axis(ax, 'y')
            plt.xticks(range(24))
            plt.tight_layout()
            g5_path = out_path / "rafagas_por_hora.png"
            plt.savefig(g5_path, dpi=DPI)
            plt.close()
            generated_charts["G5"] = str(g5_path.resolve())
        except Exception as e:
            print(f"Error generando G5: {e}")

    # G6: scatter_volumen_tiempo.png (Dispersión de volumen horario)
    try:
        plot_df_hv = plot_df.copy()
        plot_df_hv["hora_periodo"] = plot_df_hv["fecha_consulta"].dt.floor("h")
        hv_df = plot_df_hv.groupby("hora_periodo").size().reset_index(name="count")
        if not hv_df.empty:
            plt.figure(figsize=FIGSIZE_WIDE)
            ax = plt.gca()
            plt.scatter(hv_df["hora_periodo"], hv_df["count"], color='#ff7f0e', alpha=0.7, edgecolors='w', s=100)
            mean_val = hv_df["count"].mean()
            plt.axhline(y=mean_val, color='r', linestyle='--', label=f'Promedio ({round(mean_val,1):,})')
            plt.title("Dispersión de Volumen Horario Inusual", fontsize=14, fontweight="bold", pad=15)
            plt.xlabel("Fecha y Hora", fontsize=12)
            plt.ylabel("Consultas por Hora", fontsize=12)
            format_integer_axis(ax, 'y')
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            g6_path = out_path / "scatter_volumen_tiempo.png"
            plt.savefig(g6_path, dpi=DPI)
            plt.close()
            generated_charts["G6"] = str(g6_path.resolve())
    except Exception as e:
        print(f"Error generando G6: {e}")

    # G7: histograma_dni.png (Distribución de frecuencia de DNIs repetidos)
    try:
        dni_counts = plot_df["dni_consultado"].value_counts().reset_index()
        dni_counts.columns = ["dni_consultado", "count"]
        if not dni_counts.empty:
            plt.figure(figsize=FIGSIZE_WIDE)
            ax = plt.gca()
            sns.histplot(data=dni_counts, x="count", bins=15, kde=True, color='#8c564b')
            plt.title("Distribución de Frecuencia de DNIs Repetidos", fontsize=14, fontweight="bold", pad=15)
            plt.xlabel("Número de Consultas al Mismo DNI", fontsize=12)
            plt.ylabel("Frecuencia de DNI", fontsize=12)
            format_integer_axis(ax, 'y')
            format_integer_axis(ax, 'x')
            plt.tight_layout()
            g7_path = out_path / "histograma_dni.png"
            plt.savefig(g7_path, dpi=DPI)
            plt.close()
            generated_charts["G7"] = str(g7_path.resolve())
    except Exception as e:
        print(f"Error generando G7: {e}")

    # G8: tabla_top10_dni.png (Top 10 DNIs más consultados del dataset)
    try:
        top_dnis_series = plot_df["dni_consultado"].value_counts().head(10)
        if not top_dnis_series.empty:
            top_dnis = top_dnis_series.reset_index()
            top_dnis.columns = ["dni_consultado", "count"]
            plt.figure(figsize=FIGSIZE_WIDE)
            ax = sns.barplot(x="count", y="dni_consultado", data=top_dnis, hue="dni_consultado", palette="Reds_r", orient='h', legend=False)
            plt.title("Top 10 DNIs Más Consultados por Usuarios del Servicio", fontsize=14, fontweight="bold", pad=15)
            plt.xlabel("Número de Consultas", fontsize=12)
            plt.ylabel("Número de DNI", fontsize=12)
            format_integer_axis(ax, 'x')
            for p in ax.patches:
                width = p.get_width()
                if width > 0:
                    ax.annotate(f"{int(width):,}", (width, p.get_y() + p.get_height() / 2.),
                                ha='left', va='center', xytext=(5, 0), textcoords='offset points', fontsize=10, fontweight='bold')
            plt.tight_layout()
            g8_path = out_path / "tabla_top10_dni.png"
            plt.savefig(g8_path, dpi=DPI)
            plt.close()
            generated_charts["G8"] = str(g8_path.resolve())
    except Exception as e:
        print(f"Error generando G8: {e}")

    # G9: patron_periodico.png (Si periodic no está vacío)
    if not report.periodic.empty:
        try:
            plt.figure(figsize=FIGSIZE_WIDE)
            sns.barplot(x="desviacion_estandar", y="cod_usuario", data=report.periodic.head(10), color='#e377c2')
            plt.axvline(x=2.0, color='r', linestyle='--', label='Umbral Bots (2.0s)')
            plt.title("Desviación Estándar de Intervalos por Usuario (Patrón Periódico)", fontsize=14, fontweight="bold", pad=15)
            plt.xlabel("Desviación Estándar (segundos)", fontsize=12)
            plt.ylabel("Código de Usuario", fontsize=12)
            plt.legend()
            plt.tight_layout()
            g9_path = out_path / "patron_periodico.png"
            plt.savefig(g9_path, dpi=DPI)
            plt.close()
            generated_charts["G9"] = str(g9_path.resolve())
        except Exception as e:
            print(f"Error generando G9: {e}")

    # G10: heatmap_hora_dia.png (Si hay actividad sospechosa en madrugada o fin de semana)
    has_suspicious_hours = not report.illegal_hours.empty
    if has_suspicious_hours:
        try:
            # Crear matriz pivote hora x día de la semana
            heatmap_data = plot_df.pivot_table(index="hora", columns="dia_semana_num", values="dni_consultado", aggfunc="count").fillna(0)
            # Reindexar para asegurar todas las horas y días
            heatmap_data = heatmap_data.reindex(index=range(24), columns=range(7), fill_value=0)
            
            day_labels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            
            plt.figure(figsize=FIGSIZE_SQUARE)
            sns.heatmap(heatmap_data, xticklabels=day_labels, yticklabels=range(24), cmap="YlOrRd", annot=False, cbar=True)
            plt.title("Mapa de Calor: Intensidad de Consultas por Hora y Día", fontsize=14, fontweight="bold", pad=15)
            plt.xlabel("Día de la Semana", fontsize=12)
            plt.ylabel("Hora del Día (0-23)", fontsize=12)
            plt.tight_layout()
            g10_path = out_path / "heatmap_hora_dia.png"
            plt.savefig(g10_path, dpi=DPI)
            plt.close()
            generated_charts["G10"] = str(g10_path.resolve())
        except Exception as e:
            print(f"Error generando G10: {e}")

    return generated_charts
