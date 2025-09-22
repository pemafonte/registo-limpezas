# create_user.py
import sys, sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

if len(sys.argv) < 3:
    print("Uso: python create_user.py <username> <role> [password]")
    print("roles: admin | gestor | operador | leitura")
    sys.exit(1)

username = sys.argv[1]
role = sys.argv[2].lower()
password = sys.argv[3] if len(sys.argv) > 3 else "1234"
if role not in {"admin","gestor","operador","leitura"}:
    print("Perfil inválido.")
    sys.exit(1)

DB = Path(__file__).parent / "base_dados.db"
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("SELECT 1 FROM funcionarios WHERE username=?", (username,))
if cur.fetchone():
    cur.execute("UPDATE funcionarios SET role=?, ativo=1 WHERE username=?", (role, username))
    print(f"Atualizado perfil do utilizador {username} -> {role}")
else:
    cur.execute("INSERT INTO funcionarios (username,password,nome,role,ativo) VALUES (?,?,?,?,1)",
                (username, generate_password_hash(password), username, role))
    print(f"Criado {username} com perfil {role} (password: {password})")
con.commit(); con.close()
