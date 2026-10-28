import pandas as pd

def check_excel_details():
    filepath = r"C:\Users\sperezr\Documents\Proyectos\GENERADOR DE INFORMES\LD_AUTOFIN_SAC_FEB2026.xlsx"
    xl = pd.ExcelFile(filepath)
    print("Sheets available in Excel:", xl.sheet_names)
    
    df = xl.parse(xl.sheet_names[0])
    # Check if there are non-null values in the Unnamed columns
    unnamed_cols = [c for c in df.columns if "Unnamed" in str(c)]
    for col in unnamed_cols:
        non_null = df[col].dropna()
        if not non_null.empty:
            print(f"\nUnnamed column '{col}' has {len(non_null)} non-null values. Sample:")
            print(non_null.head(10).to_dict())

if __name__ == "__main__":
    check_excel_details()
