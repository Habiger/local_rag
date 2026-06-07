from pathlib import Path

# data/ — runtime storage directory inside the backend (app/).
# Created on startup; stores incoming PDFs under their original filename.
# PDFs with the same name are treated as identical and not overwritten.
PDF_STORAGE_DIR = Path(__file__).parent.parent / "data"
