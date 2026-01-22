import os
import sqlite3
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

DB_PATH = "reports.db"
UPLOAD_DIR = "uploads"

app = FastAPI()

# Autorise le front à appeler l'API (simple pour TP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            photo_filename TEXT
        )
        """)
        con.commit()

init_db()

@app.get("/reports")
def get_reports():
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "type": r["type"],
            "description": r["description"],
            "lat": r["lat"],
            "lon": r["lon"],
            "photo_url": f"/uploads/{r['photo_filename']}" if r["photo_filename"] else None
        })
    return out

@app.post("/reports")
async def create_report(
    type: str = Form(...),
    description: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    photo: UploadFile | None = File(None),
):
    photo_filename = None

    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            raise HTTPException(status_code=400, detail="Format image non supporté.")
        photo_filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(UPLOAD_DIR, photo_filename)
        content = await photo.read()
        with open(path, "wb") as f:
            f.write(content)

    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO reports(type, description, lat, lon, photo_filename) VALUES (?, ?, ?, ?, ?)",
            (type, description, lat, lon, photo_filename),
        )
        new_id = cur.lastrowid
        con.commit()

    return {
        "id": new_id,
        "type": type,
        "description": description,
        "lat": lat,
        "lon": lon,
        "photo_url": f"/uploads/{photo_filename}" if photo_filename else None
    }

@app.delete("/reports/{report_id}")
def delete_report(report_id: int):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT photo_filename FROM reports WHERE id=?", (report_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Introuvable")

        con.execute("DELETE FROM reports WHERE id=?", (report_id,))
        con.commit()

    if row["photo_filename"]:
        path = os.path.join(UPLOAD_DIR, row["photo_filename"])
        if os.path.exists(path):
            os.remove(path)

    return {"ok": True}

@app.get("/")
def root():
    return {"api": "ok", "routes": ["/reports", "/uploads", "/docs"]}
