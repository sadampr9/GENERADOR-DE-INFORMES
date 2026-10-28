import pandas as pd
from pathlib import Path

def search_all_excels():
    workspace = Path(r"C:\Users\sperezr\Documents\Proyectos\GENERADOR DE INFORMES")
    for filepath in workspace.glob("*.xlsx"):
        print(f"Searching in: {filepath.name}")
        try:
            xl = pd.ExcelFile(filepath)
            for sheet in xl.sheet_names:
                df = xl.parse(sheet)
                for col in df.columns:
                    matches = df[df[col].astype(str).str.contains("47066866", na=False)]
                    if not matches.empty:
                        print(f"  Match in sheet '{sheet}', column '{col}':")
                        print(matches.head(5).to_dict(orient='records'))
        except Exception as e:
            print(f"  Error reading {filepath.name}: {e}")

if __name__ == "__main__":
    search_all_excels()
