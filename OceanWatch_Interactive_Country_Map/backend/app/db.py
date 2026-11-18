import sqlite3, json, pathlib, os
DB_PATH = os.environ.get("MPD_DB", str(pathlib.Path(__file__).parents[2] / "database" / "mpd.sqlite"))
SCHEMA = pathlib.Path(__file__).parents[2] / "database" / "schema.sql"

def conn():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); return c

def init():
    with conn() as c: c.executescript(SCHEMA.read_text())

def row(r):
    d = dict(r); d["flags"] = json.loads(d["flags"]); d["polygon"] = json.loads(d["polygon"]); return d
