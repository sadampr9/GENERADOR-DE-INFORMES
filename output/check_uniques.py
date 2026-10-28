import pandas as pd
from modules.data_loader import load_excel

def check_uniques():
    filepath = r"C:\Users\sperezr\Documents\Proyectos\GENERADOR DE INFORMES\LD_AUTOFIN_SAC_FEB2026.xlsx"
    df, metadata = load_excel(filepath)
    
    total_rows = len(df)
    unique_dnis = df["dni_consultado"].nunique()
    
    print(f"Total rows: {total_rows}")
    print(f"Unique DNIs: {unique_dnis}")
    
    # Value counts of queries per DNI
    counts = df["dni_consultado"].value_counts()
    print("\nTop 15 most queried DNIs:")
    print(counts.head(15).to_dict())
    
    # Distribution of counts
    count_dist = counts.value_counts().sort_index()
    print("\nDistribution of query counts per DNI (How many DNIs were queried X times):")
    print(count_dist.head(10).to_dict())
    if len(count_dist) > 10:
         print("...")
         print(count_dist.tail(5).to_dict())

if __name__ == "__main__":
    check_uniques()
