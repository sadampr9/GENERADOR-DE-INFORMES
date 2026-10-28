import os
from pathlib import Path
from datetime import datetime

def check_mtimes():
    path = Path(r"C:\Users\sperezr\Documents\Proyectos\GENERADOR DE INFORMES\output\graficos")
    print(f"Checking files in: {path}")
    for f in path.glob("*.png"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        print(f"  {f.name}: modified at {mtime.strftime('%Y-%m-%d %H:%M:%S')} (size: {f.stat().st_size} bytes)")

if __name__ == "__main__":
    check_mtimes()
