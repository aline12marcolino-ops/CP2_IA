from pathlib import Path
from pypdf import PdfReader

for f in sorted(Path("data/docs").glob("*.pdf")):
    inicio = f.read_bytes()[:5]
    try:
        n = len(PdfReader(str(f)).pages)
        print("OK  ", f.name, "|", n, "páginas |", f.stat().st_size // 1024, "KB")
    except Exception as e:
        print("ERRO", f.name, "|", f.stat().st_size // 1024, "KB | começa com", inicio, "|", type(e).__name__)