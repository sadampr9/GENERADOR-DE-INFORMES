import pandas as pd
from modules.data_loader import load_excel

def lookup_dni():
    filepath = r"C:\Users\sperezr\Documents\Proyectos\GENERADOR DE INFORMES\LD_AUTOFIN_SAC_FEB2026.xlsx"
    df, metadata = load_excel(filepath)
    
    # Filter rows where dni_consultado matches
    matching_rows = df[df["dni_consultado"] == "47066866"]
    print(f"Total matching rows: {len(matching_rows)}")
    if not matching_rows.empty:
        print("\nColumns available:")
        print(matching_rows.columns.tolist())
        print("\nFirst few matching rows:")
        print(matching_rows.head(2).to_dict(orient='records'))
    else:
        print("No matching rows found in load_excel output. Trying raw excel load...")
        raw_df = pd.read_excel(filepath)
        print("Raw Columns:", raw_df.columns.tolist())
        # Try to find if it exists under some alias
        for col in raw_df.columns:
            matches = raw_df[raw_df[col].astype(str).str.contains("47066866", na=False)]
            if not matches.empty:
                print(f"Match found in column '{col}':")
                print(matches.head(2).to_dict(orient='records'))

if __name__ == "__main__":
    lookup_dni()
