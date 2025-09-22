import re
from pathlib import Path

# Caminho para o teu ficheiro
FILENAME = "AppFlaskLimpeza_final_clean3_LOGIN_RBAC.py"

# Lê o ficheiro original
with open(FILENAME, encoding="utf-8") as f:
    code = f.read()

# Faz backup
Path(FILENAME + ".bak").write_text(code, encoding="utf-8")

# Regex para encontrar cur.execute("...?", ...) ou cur.executemany("...?", ...)
def replace_placeholders(match):
    sql = match.group(1)
    # Só troca se houver pelo menos um ?
    if "?" not in sql:
        return match.group(0)
    # Troca todos os ? por %s, mas só se não estiverem dentro de aspas simples
    # (para casos como ...WHERE campo='?'...)
    def repl(m):
        return "%s" if m.group(0) == "?" else m.group(0)
    new_sql = re.sub(r"\?", repl, sql)
    return match.group(0).replace(sql, new_sql)

pattern = re.compile(r"""(cur\.execute(?:many)?\(\s*["']{1,3}.*?["']{1,3})""", re.DOTALL)

# Troca os placeholders
new_code = re.sub(
    r'(cur\.execute(?:many)?\(\s*["\']{1,3})(.*?)(["\']{1,3}\s*,)',
    lambda m: m.group(1) + m.group(2).replace("?", "%s") + m.group(3),
    code,
    flags=re.DOTALL
)

# Escreve o ficheiro alterado
with open(FILENAME, "w", encoding="utf-8") as f:
    f.write(new_code)

print("Placeholders trocados! Backup criado como", FILENAME + ".bak")