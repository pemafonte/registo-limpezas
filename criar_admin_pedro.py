# criar_admin_pedro.py
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).parent / "base_dados.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS funcionarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    nome TEXT,
    role TEXT DEFAULT 'leitura',
    ativo INTEGER DEFAULT 1,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# cria ou atualiza Pedro.fonte como admin (password inicial 1234)
pwd = generate_password_hash("1234")
cur.execute("SELECT id FROM funcionarios WHERE username=?", ("Pedro.fonte",))
row = cur.fetchone()
if row:
    cur.execute("UPDATE funcionarios SET password=?, role='admin', ativo=1 WHERE id=?", (pwd, row[0]))
    print("Utilizador 'Pedro.fonte' atualizado para admin.")
else:
    cur.execute(
        "INSERT INTO funcionarios (username,password,nome,role,ativo) VALUES (?,?,?,?,1)",
        ("Pedro.fonte", pwd, "Pedro Fonte", "admin")
    )
    print("Utilizador 'Pedro.fonte' criado como admin.")

conn.commit()
conn.close()
print("OK.")
