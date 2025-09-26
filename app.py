# AppFlaskLimpeza.py

from __future__ import annotations
import os, json, io, csv
from pathlib import Path
from datetime import datetime, date
import sys

print("DEBUG: Iniciando importações...")

try:
    from flask import (
        Flask, request, render_template, redirect, url_for, session, send_from_directory, send_file, flash, Response, abort
    )
    print("DEBUG: Flask importado com sucesso")
except Exception as e:
    print(f"ERRO CRÍTICO: Falha ao importar Flask: {e}")
    sys.exit(1)

try:
    from werkzeug.security import check_password_hash, generate_password_hash
    from werkzeug.utils import secure_filename
    print("DEBUG: Werkzeug importado com sucesso")
except Exception as e:
    print(f"ERRO CRÍTICO: Falha ao importar Werkzeug: {e}")
    sys.exit(1)

try:
    import sqlite3
    print("DEBUG: SQLite3 importado com sucesso")
except Exception as e:
    print(f"ERRO CRÍTICO: Falha ao importar SQLite3: {e}")
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
    print("DEBUG: psycopg2 importado com sucesso")
except ImportError:
    psycopg2 = None
    print("DEBUG: psycopg2 não disponível - usando SQLite")

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "base_dados.db"
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"
TEMPLATES_DIR = BASE_DIR / "templates"
OVERWRITE_TEMPLATES = False
APP_TITLE = "Registo Limpezas de Viaturas Grupo Tejo"
APP_SIGNATURE = "Created by Pedro Fonte"

ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".pdf"}

print("DEBUG: Criando aplicação Flask...")
app = Flask(__name__)
print("DEBUG: Flask app criado com sucesso")

app.secret_key = os.environ.get("APP_SECRET_KEY", "dev-key-please-change")
print("DEBUG: Secret key configurada")

UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
print("DEBUG: Diretórios criados com sucesso")

print("### DB em uso:", DB_PATH)
print("DEBUG: Variáveis de ambiente:")
print(f"  DATABASE_URL: {'[DEFINIDA]' if os.environ.get('DATABASE_URL') else '[NÃO DEFINIDA]'}")
print(f"  PORT: {os.environ.get('PORT', '5000')}")


# -----------------------------------------------------------------------------
# Templates auto-criados (para ser plug-and-play)
# -----------------------------------------------------------------------------
def write_templates():
    files: dict[str, str] = {}
    
    files["home.html"] = """{% extends "base.html" %}
{% block content %}
<div id="protoModal" style="display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,.3);z-index:999;">
  <div style="background:#fff;padding:24px;max-width:600px;margin:60px auto;border-radius:8px;box-shadow:0 2px 12px #0002;">
    <h3>Viaturas limpas por protocolo</h3>
    <div id="protoModalContent"></div>
    <button class="btn" onclick="document.getElementById('protoModal').style.display='none'">Fechar</button>
  </div>
</div>
  <h2>Dashboard</h2>

{% set CH = charts %}
<!-- KPI Cards -->
<div class="kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:.5rem 0 1rem;">
  <div class="card" style="padding:10px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;">
    <div class="muted" style="font-size:.85rem;color:#6b7280;">Registos hoje</div>
    <div style="font-size:1.6rem;font-weight:700;">{{ CH.kpi_today }}</div>
  </div>
  <div class="card" style="padding:10px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;">
    <div class="muted" style="font-size:.85rem;color:#6b7280;">Registos últimos 7 dias</div>
    <div style="font-size:1.6rem;font-weight:700;">{{ CH.kpi_week }}</div>
  </div>
  <div class="card" style="padding:10px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;">
    <div class="muted" style="font-size:.85rem;color:#6b7280;">Registos este mês</div>
    <div style="font-size:1.6rem;font-weight:700;">{{ CH.kpi_month }}</div>
  </div>
  <div class="card" style="padding:10px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;">
    <div class="muted" style="font-size:.85rem;color:#6b7280;">Viaturas limpas hoje</div>
    <div style="font-size:1.6rem;font-weight:700;">{{ CH.kpi_today_veh }}</div>
  </div>
</div>
  
  {% set CH = charts %}
    <div class="grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px">
      <div class="card">
    <h3 style="margin:0 0 .5rem">Viaturas distintas por protocolo</h3>
    <canvas id="chart_proto" height="90"></canvas>
    <ul class="muted" style="display:flex;flex-wrap:wrap;gap:.75rem;margin:.5rem 0 0;padding:0;list-style:none">
      {% for i in range(CH.proto_labels|length) %}
        <li>{{ CH.proto_labels[i] }}: <b>{{ CH.proto_values[i] }}</b></li>
      {% endfor %}
    </ul>
    <div style="text-align:right;margin-top:.5rem;">
      <button class="btn btn-primary" type="button" onclick="showProtoModal();event.stopPropagation();">Ver lista</button>
    </div>
  </div>

    <div class="card">
      <h3 style="margin:0 0 .5rem">Média de dias desde última limpeza</h3>
      <canvas id="chart_avg_days" height="90"></canvas>
      <div class="muted">Frota: <b>{{ CH.fleet_size }}</b> — Média: <b>{{ CH.avg_days }}</b> dias</div>
    </div>
    
    <div class="card">
      <h3 style="margin:0 0 .5rem">Limpezas por local</h3>
      <canvas id="chart_local" height="90"></canvas>
      <ul class="muted" style="display:flex;flex-wrap:wrap;gap:.75rem;margin:.5rem 0 0;padding:0;list-style:none">
        {% for i in range(CH.local_labels|length) %}
          <li>{{ CH.local_labels[i] }}: <b>{{ CH.local_values[i] }}</b></li>
        {% endfor %}
      </ul>
    </div>

    <div class="card">
      <h3 style="margin:0 0 .5rem">Limpezas por funcionário</h3>
      <canvas id="chart_func" height="90"></canvas>
      <ul class="muted" style="display:flex;flex-wrap:wrap;gap:.75rem;margin:.5rem 0 0;padding:0;list-style:none">
        {% for i in range(CH.func_labels|length) %}
          <li>{{ CH.func_labels[i] }}: <b>{{ CH.func_values[i] }}</b></li>
        {% endfor %}
      </ul>
    </div>
  </div>

  {% raw %}
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    const CH = {{ charts | tojson }};
    const viaturas = {{ viaturas | tojson }};
    const protocolos = {{ protocolos | tojson }};

    function bar(id, labels, data, title){
      const ctx = document.getElementById(id).getContext('2d');
      const valueLabel = {
        id: 'valueLabel',
        afterDatasetsDraw(chart, args, pluginOptions) {
          const {ctx, chartArea: {top}, scales: {x, y}} = chart;
          ctx.save();
          ctx.font = '12px system-ui, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillStyle = '#111';
          chart.data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            meta.data.forEach((bar, index) => {
              const val = dataset.data[index];
              if (val == null) return;
              const posY = Math.min(bar.y, y.getPixelForValue(val)) - 4;
              ctx.fillText(String(val), bar.x, posY);
            });
          });
          ctx.restore();
        }
      };
      new Chart(ctx, {
        type: 'bar',
        data: { labels: labels, datasets: [{ label: title, data: data }] },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
        },
        plugins: [valueLabel]
      });
    }

    bar('chart_proto', CH.proto_labels, CH.proto_values, '');
    (function(){
      const ctx = document.getElementById('chart_avg_days').getContext('2d');
      const valueLabel = {
        id: 'valueLabel',
        afterDatasetsDraw(chart, args, pluginOptions) {
          const {ctx, chartArea: {top}, scales: {x, y}} = chart;
          ctx.save();
          ctx.font = '12px system-ui, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillStyle = '#111';
          chart.data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            meta.data.forEach((bar, index) => {
              const val = dataset.data[index];
              if (val == null) return;
              const posY = Math.min(bar.y, y.getPixelForValue(val)) - 4;
              ctx.fillText(String(val), bar.x, posY);
            });
          });
          ctx.restore();
        }
      };
      new Chart(ctx, {
        type: 'bar',
        data: { labels: ['Média'], datasets: [{ label: 'Dias', data: [CH.avg_days] }] },
        options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
        plugins: [valueLabel]
      });
    })();
    bar('chart_local', CH.local_labels, CH.local_values, '');
    bar('chart_func', CH.func_labels, CH.func_values, '');

    function showProtoModal() {
      let html = "";
      protocolos.forEach(p => {
        html += `<h4>${p.nome}</h4><ul>`;
        viaturas.forEach(v => {
          // Aqui pode filtrar as viaturas limpas por protocolo, se tiver esse dado
          html += `<li>${v.matricula} ${v.descricao ? "— " + v.descricao : ""}</li>`;
        });
        html += "</ul>";
      });
      document.getElementById("protoModalContent").innerHTML = html;
      document.getElementById("protoModal").style.display = "block";
    }
  </script>
  {% endraw %}
  {% endblock %}
"""



    files["login.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Login</h2>
  <form method="post" class="card" style="max-width:480px;">
  <div class="row">
    <label>Utilizador
      <input type="text" name="username" required>
    </label>
    <label>Password
      <input type="password" name="password" required>
    </label>
  </div>
  <button class="btn btn-primary" type="submit">Entrar</button>
  </form>
{% endblock %}
"""

    files["403.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Acesso negado</h2>
  <p>Não tem permissões para aceder a esta página.</p>
  <p>
    <a class="btn" href="{{ url_for('home') }}">Ir para o início</a>
    {% if can('registos:view') %}<a class="btn" href="{{ url_for('registos') }}">Ver registos</a>{% endif %}
  </p>
{% endblock %}
"""

    files["protocolos.html"] = """{% extends "base.html" %}
{% block content %}
   <h2>Protocolos</h2>
   {% if can('protocolos:edit') %}
     <p><a class="btn btn-primary" href="{{ url_for('protocolo_novo') }}">Novo Protocolo</a></p>
   {% endif %}
   <table>
     <thead>
       <tr>
         <th>Nome</th>
         <th>Passos</th>
         <th>Frequência (dias)</th>
         <th>Ativo</th>
        {% if can('protocolos:edit') %}<th style="width:200px;">Ações</th>{% endif %}
       </tr>
     </thead>
     <tbody>
       {% for p in protocolos %}
       <tr>
         <td>{{ p.nome }}</td>
         <td>
          {% set data = p.passos_json|loadjson %}
          {% if data and data.passos %}
            <ol>
              {% for step in data.passos %}
                <li>{{ step }}</li>
              {% endfor %}
            </ol>
          {% else %}
            <span class="muted">sem passos</span>
          {% endif %}
        </td>
        <td>{{ p.frequencia_dias or "—" }}</td>
        <td>{{ "Sim" if p.ativo==1 else "Não" }}</td>
        {% if can('protocolos:edit') %}
        <td>
          <a class="btn" href="{{ url_for('protocolo_editar', pid=p.id) }}">Editar</a>
          <form method="post" action="{{ url_for('protocolo_apagar', pid=p.id) }}"
                onsubmit="return confirm('Apagar protocolo {{ p.nome }}?');"
                style="display:inline-block;margin-left:6px;">
            <button class="btn btn-danger" type="submit">Apagar</button>
          </form>
        </td>
        {% endif %}
       </tr>
       {% endfor %}
     </tbody>
   </table>
{% endblock %}
"""


    files["protocolos_form.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>{% if modo == 'novo' %}Novo Protocolo{% else %}Editar Protocolo{% endif %}</h2>
  <form method="post">
    <div class="row">
      <label>Nome <input type="text" name="nome" value="{{ form.nome }}" required></label>
      <label>Frequência (dias) <input type="number" name="frequencia_dias" min="0" step="1" value="{{ form.frequencia_dias }}"></label>
      <label>Ativo
        <select name="ativo">
          <option value="1" {% if form.ativo == 1 %}selected{% endif %}>Sim</option>
          <option value="0" {% if form.ativo != 1 %}selected{% endif %}>Não</option>
        </select>
      </label>
    </div>
    <div class="row" style="grid-template-columns: 1fr;">
      <label>Passos (um por linha)
        <textarea name="passos" rows="10" placeholder="Inspeção interior
        Aspirar
        Desinfetar superfícies">{{ form.passos }}</textarea>
      </label>
    </div>
    <p>
      <button class="btn btn-primary" type="submit">{% if modo == 'novo' %}Criar{% else %}Guardar{% endif %}</button>
      <a class="btn" href="{{ url_for('protocolos') }}">Cancelar</a>
    </p>
  </form>
{% endblock %}
"""

    files["anexos.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Anexos do registo #{{ registo_id }}</h2>
  {% if anexos %}
    <ul>
      {% for a in anexos %}
        <li><a href="{{ url_for('download_anexo', anexo_id=a.id) }}">{{ a.caminho }}</a> <span class="muted">({{ a.tipo }})</span></li>
      {% endfor %}
    </ul>
  {% else %}
    <div class="card">Sem anexos.</div>
  {% endif %}
{% endblock %}
"""

    files["admin.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Administração</h2>
  <ul>
    {% if can('users:manage') %}<li><a href="{{ url_for('admin_users') }}">Utilizadores</a></li>{% endif %}
    {% if can('roles:manage') %}<li><a href="{{ url_for('admin_roles') }}">Perfis (roles)</a></li>{% endif %}
    {% if can('viaturas:import') %}<li><a href="{{ url_for('admin_import_viaturas') }}">Importar viaturas (CSV)</a></li>{% endif %}
    {% if can('protocolos:view') %}<li><a href="{{ url_for('protocolos') }}">Protocolos</a></li>{% endif %}
  </ul>
{% endblock %}
"""

    files["admin_users.html"] = """{% extends "base.html" %}
+{% block content %}
+  <h2>Utilizadores</h2>
+  <p><a class="btn btn-primary" href="{{ url_for('admin_user_new') }}">Novo utilizador</a></p>
+  <table>
+    <thead>
+      <tr>
+        <th>Username</th>
+        <th>Nome</th>
+        <th>Perfil</th>
+        <th>Região</th>
+        <th>Ativo</th>
+        <th>Criado</th>
+        <th style="width:240px;">Ações</th>
+      </tr>
+    </thead>
+    <tbody>
+      {% for u in users %}
+      <tr>
+        <td>{{ u.username }}</td>
+        <td>{{ u.nome or "—" }}</td>
+        <td>{{ u.role }}</td>
+        <td>{{ u.regiao or "—" }}</td>
+        <td>{{ "Sim" if u.ativo==1 else "Não" }}</td>
+        <td>{{ u.criado_em }}</td>
+        <td>
+          <a class="btn" href="{{ url_for('admin_user_edit', user_id=u.id) }}">Editar</a>
+          <form method="post" action="{{ url_for('admin_user_toggle', user_id=u.id) }}" style="display:inline-block;margin-left:6px;">
+            <button class="btn" type="submit">{% if u.ativo==1 %}Desativar{% else %}Ativar{% endif %}</button>
+          </form>
+          <form method="post" action="{{ url_for('admin_user_delete', user_id=u.id) }}"
+                onsubmit="return confirm('Eliminar {{ u.username }}? Esta ação é definitiva.');"
+                style="display:inline-block;margin-left:6px;">
+            <button class="btn btn-danger" type="submit"
+                    {% if u.username == session['username'] %}disabled{% endif %}>Apagar</button>
+          </form>
+        </td>
+      </tr>
+      {% endfor %}
+    </tbody>
+  </table>
+{% endblock %}
+"""

    files["admin_user_form.html"] = """{% extends "base.html" %}
 {% block content %}
   <h2>Novo Utilizador</h2>
   <form method="post">
     <div class="row">
       <label>Username <input name="username" required></label>
       <label>Nome <input name="nome" placeholder="opcional"></label>
      <label>Região <input name="regiao" placeholder="ex.: Região Norte"></label>
       <label>Password <input name="password" type="password" required></label>
       <label>Perfil
         <select name="role" required>
           {% for r in roles %}<option value="{{ r }}">{{ r }}</option>{% endfor %}
         </select>
      </label>
      <label>Ativo
        <select name="ativo">
          <option value="1" selected>Sim</option>
          <option value="0">Não</option>
        </select>
      </label>
    </div>
    <p><button class="btn btn-primary" type="submit">Criar</button>
       <a class="btn" href="{{ url_for('admin_users') }}">Cancelar</a></p>
  </form>
{% endblock %}
"""

    files["admin_roles.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Perfis (roles)</h2>
  <p><a class="btn btn-primary" href="{{ url_for('admin_role_new') }}">Novo perfil</a></p>

  <h3>Perfis base</h3>
  <ul>{% for r in base_roles %}<li>{{ r }} <span class="muted">(predefinido)</span></li>{% endfor %}</ul>

  <h3>Perfis em BD</h3>
  {% if db_roles %}
    <ul>{% for r in db_roles %}<li>{{ r }}</li>{% endfor %}</ul>
  {% else %}
    <div class="card">Ainda não existem perfis personalizados.</div>
  {% endif %}
{% endblock %}
"""

    files["admin_role_form.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Novo Perfil</h2>
  <form method="post">
    <div class="row">
      <label>Nome do perfil (minúsculas) <input name="name" required></label>
    </div>
    <div class="row" style="grid-template-columns: 1fr;">
      <fieldset class="card">
        <legend>Permissões</legend>
        {% for p in perms %}
          <label style="display:block;margin:.25rem 0;">
            <input type="checkbox" name="perms" value="{{ p }}"> {{ p }}
          </label>
        {% endfor %}
      </fieldset>
    </div>
    <p><button class="btn btn-primary" type="submit">Criar</button>
       <a class="btn" href="{{ url_for('admin_roles') }}">Cancelar</a></p>
  </form>
{% endblock %}
"""

    files["admin_import_viaturas.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Importar Viaturas (CSV)</h2>
  <p class="muted">Formato recomendado (cabeçalho): <code>matricula,descricao,filial,num_frota,ativo</code></p>
  <form method="post" enctype="multipart/form-data">
    <div class="row">
      <label>Ficheiro CSV <input type="file" name="ficheiro" accept=".csv" required></label>
    </div>
    <p><button class="btn btn-primary" type="submit">Importar</button>
       <a class="btn" href="{{ url_for('admin_panel') }}">Cancelar</a></p>
  </form>
{% endblock %}
"""
    files["registos.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Registos de Limpeza</h2>
  {% if can('registos:create') %}
  <p><a class="btn btn-primary" href="{{ url_for('novo_registo') }}">Novo Registo</a></p>
  {% endif %}
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Data/Hora</th>
        <th>Matrícula</th>
        <th>Protocolo</th>
        <th>Operador</th>
        <th>Local</th>
        <th style="width:160px;">Ações</th>
      </tr>
    </thead>
    <tbody>
      {% for r in registos %}
      <tr>
        <td>{{ r.registo_id }}</td>
        <td>{{ r.data_hora }}</td>
        <td>{{ r.matricula }}</td>
        <td>{{ r.protocolo }}</td>
        <td>{{ r.funcionario }}</td>
        <td>{{ r.local }}</td>
        <td>
          <a class="btn" href="{{ url_for('registo_detalhe', rid=r.registo_id) }}">Ver</a>
          {% if can('registos:delete') %}
          <form method="post" action="{{ url_for('registo_apagar', rid=r.registo_id) }}"
                onsubmit="return confirm('Apagar registo #{{ r.registo_id }}?');"
                style="display:inline-block;margin-left:6px;">
            <button class="btn btn-danger" type="submit">Apagar</button>
          </form>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
"""
    files["novo_registo.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Novo Registo</h2>
  <form method="post" enctype="multipart/form-data">
    <div class="row">
      <label>Viatura
        <select name="viatura_id" required>
          <option value="">— selecione —</option>
          {% for v in viaturas %}
            <option value="{{ v.id }}">{{ v.matricula }}{% if v.num_frota %} — {{ v.num_frota }}{% endif %}{% if limpa_hoje_map[v.id] %} ★{% endif %}</option>
          {% endfor %}
        </select>
      </label>
      <label>Protocolo
        <select name="protocolo_id" required>
          <option value="">— selecione —</option>
          {% for p in protocolos %}<option value="{{ p.id }}">{{ p.nome }}</option>{% endfor %}
        </select>
      </label>
      <label>Estado
        <select name="estado">
          <option value="concluido">Concluído</option>
          <option value="em_progresso">Em progresso</option>
        </select>
      </label>
    </div>
    <div class="row">
      <label>Local <input name="local" placeholder="p.ex.: Parque A"></label>
      <label>Hora Início <input name="hora_inicio" placeholder="HH:MM"></label>
      <label>Hora Fim <input name="hora_fim" placeholder="HH:MM"></label>
    </div>
    <div class="row" style="grid-template-columns:1fr;">
      <label>Observações
        <textarea name="observacoes" rows="3"></textarea>
      </label>
    </div>
    <div class="row" style="align-items:center;">
      <label><input type="checkbox" name="extra_autorizada" value="1"> Limpeza extra autorizada (segunda limpeza no mesmo dia)</label>
      <label>Responsável <input name="responsavel_autorizacao" placeholder="nome do responsável"></label>
    </div>
    <div class="row">
      <label>Ficheiros (opcional) <input type="file" name="ficheiros" multiple></label>
    </div>
    <p>
      <button class="btn btn-primary" type="submit">Criar</button>
      <a class="btn" href="{{ url_for('registos') }}">Cancelar</a>
    </p>
  </form>
{% endblock %}
"""
    for name, content in files.items():
        path = TEMPLATES_DIR / name
        if OVERWRITE_TEMPLATES or not path.exists():
            path.write_text(content, encoding="utf-8")

    

# -----------------------------------------------------------------------------
# Helpers / filtros
# -----------------------------------------------------------------------------
def get_conn():
    db_url = os.environ.get("DATABASE_URL")
    try:
        if db_url and psycopg2:
            # Heroku/PostgreSQL with timeout settings
            print(f"DEBUG: Conectando ao PostgreSQL: {db_url[:50]}...")
            conn = psycopg2.connect(
                db_url, 
                cursor_factory=psycopg2.extras.RealDictCursor,
                connect_timeout=10,  # 10 second timeout
                options='-c statement_timeout=30000'  # 30 second statement timeout
            )
            print("DEBUG: Conexão PostgreSQL estabelecida com sucesso")
            return conn
        else:
            # Local/SQLite
            print(f"DEBUG: Conectando ao SQLite: {DB_PATH}")
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            conn.row_factory = sqlite3.Row
            print("DEBUG: Conexão SQLite estabelecida com sucesso")
            return conn
    except Exception as e:
        print(f"ERRO CRÍTICO na conexão com banco: {e}")
        import traceback
        traceback.print_exc()
        raise

def is_postgres(conn):
    return hasattr(conn, "server_version")  # True para psycopg2, False para sqlite3

def sql_placeholder(conn):
    return "%s" if is_postgres(conn) else "?"

def sql_datetime(conn, field):
    """Helper para função datetime() compatível com PostgreSQL e SQLite"""
    if is_postgres(conn):
        return f"({field})::timestamp::text"  # PostgreSQL: cast to timestamp then to text
    else:
        return f"datetime({field})"  # SQLite: função datetime()

def fix_datetime_in_sql(conn, sql):
    """Substitui datetime() por sintaxe compatível baseada no tipo de banco"""
    if is_postgres(conn):
        import re
        # Substitui datetime(campo) por (campo)::timestamp
        return re.sub(r'datetime\(([^)]+)\)', r'(\1)::timestamp', sql)
    return sql

def sql_today_condition(conn, date_field):
    """Retorna condição SQL para comparar um campo de data com hoje"""
    if is_postgres(conn):
        return f"({date_field})::date = CURRENT_DATE"
    else:
        return f"date({date_field}) = date('now','localtime')"

def sql_month_format(conn, date_field):
    """Retorna função SQL para formatar data como YYYY-MM"""
    if is_postgres(conn):
        return f"TO_CHAR({date_field}, 'YYYY-MM')"
    else:
        return f"strftime('%Y-%m', {date_field})"

def sql_date(conn, date_field):
    """Retorna função SQL para extrair data de um timestamp"""
    if is_postgres(conn):
        return f"({date_field})::date"
    else:
        return f"date({date_field})"

def fix_sql_placeholders(conn, sql):
    """Converte placeholders ? para %s se for PostgreSQL"""
    if is_postgres(conn):
        return sql.replace('?', '%s')
    return sql

def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTS

@app.template_filter("loadjson")
def _filter_loadjson(value):
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

# -----------------------------------------------------------------------------
# RBAC (com perfis dinâmicos em BD)
# -----------------------------------------------------------------------------
PERMISSIONS = {
    "admin": {"*"},
    "gestor": {
        "dashboard:view","viaturas:view","protocolos:view","protocolos:edit",
        "registos:view","registos:create","registos:edit","export:excel",
        "viaturas:import","users:manage","roles:manage","admin:panel"
    },
    "operador": {"viaturas:view","protocolos:view","registos:view","registos:create","registos:edit","export:excel"},
    "leitura":  {"dashboard:view","viaturas:view","protocolos:view","registos:view"},
}
KNOWN_PERMS = sorted({p for perms in PERMISSIONS.values() for p in perms if p != "*"})

def normalize_role(role: str) -> str:
    r = (role or "leitura").lower().strip()
    return r if r in PERMISSIONS else "leitura"

def get_db_role_perms(role: str) -> set[str]:
    role = (role or "").strip().lower()
    if not role:
        return set()
    conn = get_conn()
    ph = sql_placeholder(conn)
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM roles WHERE LOWER(name)={ph}", (role,))
    r = cur.fetchone()
    if not r:
        conn.close()
        return set()
    cur.execute(f"SELECT perm FROM role_permissions WHERE role_id={ph}", (r["id"],))
    perms = {row["perm"] for row in cur.fetchall()}
    conn.close()
    return perms

def has_perm(role: str, perm: str) -> bool:
    role = normalize_role(role)
    perms = PERMISSIONS.get(role, set())
    if "*" in perms: return True
    if perm in perms: return True
    if ":" in perm and (perm.split(":",1)[0] + ":*") in perms: return True
    return False

def user_can(perm: str) -> bool:
    return has_perm(normalize_role(session.get("role")), perm)

def require_perm(perm: str):
    from functools import wraps
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            if not user_can(perm):
                flash("Sem permissões para esta ação.", "danger")
                return redirect(url_for("sem_permissao"))
            return fn(*args, **kwargs)
        return wrapper
    return deco

@app.context_processor
def inject_can():
    return {
        "can": user_can,
        "signature": APP_SIGNATURE,
        "app_title": APP_TITLE,
    }

def ensure_custo_limpeza_in_protocolos():
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'protocolos'")
            cols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(protocolos)")
            cols = {r["name"] for r in cur.fetchall()}
            
        if "custo_limpeza" not in cols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_custo_limpeza")
                cur.execute("ALTER TABLE protocolos ADD COLUMN custo_limpeza REAL DEFAULT 25")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_custo_limpeza")
                conn.commit()
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_custo_limpeza")
                    except:
                        pass
                try:
                    conn.rollback()
                except:
                    pass
    except Exception:
        pass
    finally:
        conn.close()

try:
    ensure_custo_limpeza_in_protocolos()
except Exception as e:
    print(f"ERRO em ensure_custo_limpeza_in_protocolos: {e}")

def ensure_regiao_in_registos_limpeza():
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'registos_limpeza'")
            cols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(registos_limpeza)")
            cols = {r["name"] for r in cur.fetchall()}
            
        if "regiao" not in cols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_regiao")
                cur.execute("ALTER TABLE registos_limpeza ADD COLUMN regiao TEXT")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_regiao")
                conn.commit()
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_regiao")
                    except:
                        pass
                try:
                    conn.rollback()
                except:
                    pass
    except Exception:
        pass
    finally:
        conn.close()

try:
    ensure_regiao_in_registos_limpeza()
except Exception as e:
    print(f"ERRO em ensure_regiao_in_registos_limpeza: {e}")
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# Esquema / seed
# -----------------------------------------------------------------------------
def ensure_schema_on_boot():
    print("DEBUG: Iniciando ensure_schema_on_boot()")
    try:
        conn = get_conn()
        cur = conn.cursor()
        print("DEBUG: Conexão estabelecida para schema")
        
        # Definir sintaxe correta baseado no tipo de banco
        if is_postgres(conn):
            id_field = "id SERIAL PRIMARY KEY"
            text_type = "TEXT"
            timestamp_default = "CURRENT_TIMESTAMP"
            print("DEBUG: Usando sintaxe PostgreSQL")
        else:
            id_field = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            text_type = "TEXT"  
            timestamp_default = "CURRENT_TIMESTAMP"
            print("DEBUG: Usando sintaxe SQLite")
    except Exception as e:
        print(f"ERRO CRÍTICO em ensure_schema_on_boot() - conexão: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Tabelas principais
    try:
        print("DEBUG: Criando tabela viaturas...")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS viaturas (
                {id_field},
                matricula TEXT NOT NULL UNIQUE,
                descricao TEXT,
                filial TEXT,
                num_frota TEXT,
                ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("DEBUG: Tabela viaturas criada com sucesso")
    except Exception as e:
        print(f"ERRO ao criar tabela viaturas: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        print("DEBUG: Criando tabela protocolos...")
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS protocolos (
            {id_field},
            nome TEXT NOT NULL UNIQUE,
            passos_json TEXT NOT NULL,
            frequencia_dias INTEGER,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
        print("DEBUG: Tabela protocolos criada com sucesso")
    except Exception as e:
        print(f"ERRO ao criar tabela protocolos: {e}")
        import traceback
        traceback.print_exc()
    
    # Criar funcionarios ANTES de registos_limpeza (para foreign key)
    try:
        print("DEBUG: Criando tabela funcionarios...")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS funcionarios (
                {id_field},
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                nome TEXT,
                role TEXT DEFAULT 'leitura',
                email TEXT,
                ativo INTEGER DEFAULT 1,
                regiao TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("DEBUG: Tabela funcionarios criada com sucesso")
    except Exception as e:
        print(f"ERRO ao criar tabela funcionarios: {e}")
        import traceback
        traceback.print_exc()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS registos_limpeza (
            {id_field},
            viatura_id INTEGER NOT NULL,
            protocolo_id INTEGER NOT NULL,
            funcionario_id INTEGER NOT NULL,
            data_hora TEXT NOT NULL,
            estado TEXT DEFAULT 'concluido',
            observacoes TEXT,
            local TEXT,
            hora_inicio TEXT,
            hora_fim TEXT,
            extra_autorizada INTEGER DEFAULT 0,
            responsavel_autorizacao TEXT,
            verificacao_limpeza TEXT, 
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (viatura_id) REFERENCES viaturas(id) ON DELETE RESTRICT,
            FOREIGN KEY (protocolo_id) REFERENCES protocolos(id) ON DELETE RESTRICT,
            FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id) ON DELETE RESTRICT
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS anexos (
            {id_field},
            registo_id INTEGER NOT NULL,
            caminho TEXT NOT NULL,
            tipo TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (registo_id) REFERENCES registos_limpeza(id) ON DELETE CASCADE
        )
    """)
    # ...existing code...
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS pedidos_autorizacao (
        {id_field},
        viatura_id INTEGER NOT NULL,
        funcionario_id INTEGER NOT NULL,
        data_pedido TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        validado INTEGER DEFAULT 0,
        validado_por INTEGER,
        data_validacao TEXT,
        FOREIGN KEY (viatura_id) REFERENCES viaturas(id),
        FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id),
        FOREIGN KEY (validado_por) REFERENCES funcionarios(id)
    )
""")
# ...existing code...
    # Perfis dinâmicos
    cur.execute(f"""CREATE TABLE IF NOT EXISTS roles (
        {id_field},
        name TEXT NOT NULL UNIQUE
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS role_permissions (
        role_id INTEGER NOT NULL,
        perm TEXT NOT NULL,
        UNIQUE(role_id, perm),
        FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
    )""")

    # Índices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_funcionarios_username ON funcionarios(username)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_viaturas_matricula ON viaturas(matricula)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_viaturas_num_frota ON viaturas(num_frota)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registos_data ON registos_limpeza(data_hora)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registos_viatura ON registos_limpeza(viatura_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registos_protocolo ON registos_limpeza(protocolo_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registos_funcionario ON registos_limpeza(funcionario_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registos_local ON registos_limpeza(local)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_anexos_registo ON anexos(registo_id)")
    
    # (Re)criar view detalhe
    cur.execute("DROP VIEW IF EXISTS vw_registos_detalhe")
    cur.execute("""
        CREATE VIEW vw_registos_detalhe AS
        SELECT
            r.id as registo_id,
            r.data_hora,
            r.hora_inicio,
            r.hora_fim,
            r.estado,
            r.observacoes,
            r.local,
            r.extra_autorizada,
            r.responsavel_autorizacao,
            v.matricula,
            v.num_frota,
            v.descricao as viatura_desc,
            v.filial,
            p.nome as protocolo,
            p.frequencia_dias,
            f.username as user,
            f.nome as funcionario
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        JOIN protocolos p ON p.id = r.protocolo_id
        JOIN funcionarios f ON f.id = r.funcionario_id
    """)

    # Seeds
    cur.execute("SELECT COUNT(*) as count FROM funcionarios WHERE username='admin'")
    result = cur.fetchone()
    count = result['count'] if isinstance(result, dict) else result[0]
    if count == 0:
        placeholder = sql_placeholder(conn)
        cur.execute(
            f"INSERT INTO funcionarios (username,password,nome,role,ativo) VALUES ({placeholder},{placeholder},{placeholder},{placeholder},1)",
            ("admin", generate_password_hash("1234"), "Administrador", "admin")
        )
    cur.execute("SELECT 1 FROM funcionarios WHERE username='Pedro.fonte'")
    if not cur.fetchone():
        placeholder = sql_placeholder(conn)
        cur.execute(
            f"INSERT INTO funcionarios (username,password,nome,role,ativo) VALUES ({placeholder},{placeholder},{placeholder},{placeholder},1)",
            ("Pedro.fonte", generate_password_hash("1234"), "Pedro Fonte", "admin")
        )
    cur.execute("""
        UPDATE funcionarios
           SET role='leitura'
         WHERE role IS NULL OR TRIM(LOWER(role)) NOT IN ('admin','gestor','operador','leitura')
    """)

    cur.execute("SELECT COUNT(*) as count FROM viaturas")
    result = cur.fetchone()
    count = result['count'] if isinstance(result, dict) else result[0]
    if count == 0:
        placeholder = sql_placeholder(conn)
        for viatura in [
            ("AA-00-AA", "Autocarro Urbano", "Sede", "101"),
            ("BB-11-BB", "Autocarro Suburbano", "Filial Norte", "102"),
        ]:
            cur.execute(
                f"INSERT INTO viaturas (matricula, descricao, filial, num_frota, ativo) VALUES ({placeholder},{placeholder},{placeholder},{placeholder},1)",
                viatura
            )
    
    # Garantir coluna regiao em funcionarios
    try:
        if is_postgres(conn):
            # PostgreSQL: verificar colunas via information_schema
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'funcionarios'")
            cols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            # SQLite: usar PRAGMA
            cur.execute("PRAGMA table_info(funcionarios)")
            cols = {r["name"] for r in cur.fetchall()}
            
        if "email" not in cols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_email_col")
                cur.execute("ALTER TABLE funcionarios ADD COLUMN email TEXT")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_email_col")
            except Exception:
                if is_postgres(conn):
                    cur.execute("ROLLBACK TO SAVEPOINT add_email_col")
                pass
    except Exception:
        cols = set()
    if "regiao" not in cols:
        try: 
            if is_postgres(conn):
                cur.execute("SAVEPOINT add_regiao_col")
            cur.execute("ALTER TABLE funcionarios ADD COLUMN regiao TEXT")
            if is_postgres(conn):
                cur.execute("RELEASE SAVEPOINT add_regiao_col")
        except Exception: 
            if is_postgres(conn):
                try:
                    cur.execute("ROLLBACK TO SAVEPOINT add_regiao_col")
                except:
                    pass
            pass

    # Garantir colunas extra em viaturas
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'viaturas'")
            vcols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(viaturas)")
            vcols = {r["name"] for r in cur.fetchall()}
        if "limpeza_validada" not in vcols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_limpeza_validada")
                cur.execute("ALTER TABLE viaturas ADD COLUMN limpeza_validada INTEGER DEFAULT 0")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_limpeza_validada")
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_limpeza_validada")
                    except:
                        pass
        for col in ("regiao","operacao","marca","modelo","tipo_protocolo"):
            if col not in vcols:
                try:
                    if is_postgres(conn):
                        cur.execute(f"SAVEPOINT add_{col}_col")
                    cur.execute(f"ALTER TABLE viaturas ADD COLUMN {col} TEXT")
                    if is_postgres(conn):
                        cur.execute(f"RELEASE SAVEPOINT add_{col}_col")
                except Exception:
                    if is_postgres(conn):
                        try:
                            cur.execute(f"ROLLBACK TO SAVEPOINT add_{col}_col")
                        except:
                            pass
        if "verificacao_limpeza" not in vcols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_verificacao_col")
                cur.execute("ALTER TABLE viaturas ADD COLUMN verificacao_limpeza TEXT DEFAULT NULL")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_verificacao_col")
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_verificacao_col")
                    except:
                        pass  

    except Exception:
        pass

    

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS alertas (
        {id_field},
        viatura_id INTEGER NOT NULL,
        funcionario_origem_id INTEGER,
        destinatario_id INTEGER,
        data_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        motivo TEXT NOT NULL,
        detalhes TEXT,
        lido INTEGER DEFAULT 0,
        FOREIGN KEY (viatura_id) REFERENCES viaturas(id) ON DELETE CASCADE,
        FOREIGN KEY (funcionario_origem_id) REFERENCES funcionarios(id) ON DELETE SET NULL,
        FOREIGN KEY (destinatario_id) REFERENCES funcionarios(id) ON DELETE CASCADE
    )
""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alertas_dest ON alertas(destinatario_id, lido)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alertas_viat ON alertas(viatura_id, data_hora)")
    
    # Verificação adicional de coluna regiao (caso não tenha sido criada antes)
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'funcionarios'")
            cols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(funcionarios)")
            cols = {r["name"] for r in cur.fetchall()}
            
        if "regiao" not in cols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_regiao_backup")
                cur.execute("ALTER TABLE funcionarios ADD COLUMN regiao TEXT")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_regiao_backup")
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_regiao_backup")
                    except:
                        pass
    except Exception:
        pass    

    cur.execute("SELECT COUNT(*) as count FROM protocolos")
    result = cur.fetchone()
    count = result['count'] if isinstance(result, dict) else result[0]
    if count == 0:
        placeholder = sql_placeholder(conn)
        prot1 = {"passos": ["Inspeção interior", "Aspirar", "Desinfetar superfícies", "Vidros interiores", "Check final"]}
        prot2 = {"passos": ["Inspeção exterior", "Lavagem chassis", "Vidros exteriores", "Verificar níveis", "Check final"]}
        cur.execute(f"INSERT INTO protocolos (nome, passos_json, frequencia_dias, ativo) VALUES ({placeholder},{placeholder},{placeholder},1)",
                    ("Interior Standard", json.dumps(prot1, ensure_ascii=False), 7))
        cur.execute(f"INSERT INTO protocolos (nome, passos_json, frequencia_dias, ativo) VALUES ({placeholder},{placeholder},{placeholder},1)",
                    ("Exterior Standard", json.dumps(prot2, ensure_ascii=False), 14))
    else:
        cur.execute("UPDATE protocolos SET frequencia_dias=7  WHERE frequencia_dias IS NULL AND nome LIKE 'Interior%'")
        cur.execute("UPDATE protocolos SET frequencia_dias=14 WHERE frequencia_dias IS NULL AND nome LIKE 'Exterior%'")

    print("DEBUG: Fazendo commit das tabelas criadas...")
    conn.commit()
    conn.close()
    print("DEBUG: ensure_schema_on_boot() finalizada - tabelas commitadas")

print("DEBUG: Chamando ensure_schema_on_boot()...")
try:
    ensure_schema_on_boot()
    print("DEBUG: ensure_schema_on_boot() concluída com sucesso")
except Exception as e:
    print(f"ERRO CRÍTICO na inicialização do schema: {e}")
    import traceback
    traceback.print_exc()
    print("ATENÇÃO: Schema não foi inicializado - aplicação pode falhar")

# -----------------------------------------------------------------------------
def ensure_destinatario_id():
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'pedidos_autorizacao'")
            cols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(pedidos_autorizacao)")
            cols = {r["name"] for r in cur.fetchall()}
            
        if "destinatario_id" not in cols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_destinatario_id")
                cur.execute("ALTER TABLE pedidos_autorizacao ADD COLUMN destinatario_id INTEGER")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_destinatario_id")
                conn.commit()
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_destinatario_id")
                    except:
                        pass
                try:
                    conn.rollback()
                except:
                    pass
    except Exception:
        pass
    finally:
        conn.close()

try:
    ensure_destinatario_id()
except Exception as e:
    print(f"ERRO em ensure_destinatario_id: {e}")

def add_verificacao_limpeza_column():
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'registos_limpeza'")
            cols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(registos_limpeza)")
            cols = {r["name"] for r in cur.fetchall()}
            
        if "verificacao_limpeza" not in cols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_verificacao_limpeza")
                cur.execute("ALTER TABLE registos_limpeza ADD COLUMN verificacao_limpeza TEXT")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_verificacao_limpeza")
                conn.commit()
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_verificacao_limpeza")
                    except:
                        pass
                try:
                    conn.rollback()
                except:
                    pass
    except Exception:
        pass
    finally:
        conn.close()

try:
    add_verificacao_limpeza_column()
except Exception as e:
    print(f"ERRO em add_verificacao_limpeza_column: {e}")

def ensure_num_frota_in_pedidos_autorizacao():
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'pedidos_autorizacao'")
            cols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(pedidos_autorizacao)")
            cols = {r["name"] for r in cur.fetchall()}
            
        if "num_frota" not in cols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_num_frota")
                cur.execute("ALTER TABLE pedidos_autorizacao ADD COLUMN num_frota TEXT")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_num_frota")
                conn.commit()
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_num_frota")
                    except:
                        pass
                try:
                    conn.rollback()
                except:
                    pass
    except Exception:
        pass
    finally:
        conn.close()

try:
    ensure_num_frota_in_pedidos_autorizacao()
except Exception as e:
    print(f"ERRO em ensure_num_frota_in_pedidos_autorizacao: {e}")
def ensure_comentarios_verificacao_in_registos_limpeza():
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'registos_limpeza'")
            cols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(registos_limpeza)")
            cols = {r["name"] for r in cur.fetchall()}
            
        if "comentarios_verificacao" not in cols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_comentarios_verificacao")
                cur.execute("ALTER TABLE registos_limpeza ADD COLUMN comentarios_verificacao TEXT")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_comentarios_verificacao")
                conn.commit()
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_comentarios_verificacao")
                    except:
                        pass
                try:
                    conn.rollback()
                except:
                    pass
    except Exception:
        pass
    finally:
        conn.close()

try:
    ensure_comentarios_verificacao_in_registos_limpeza()
except Exception as e:
    print(f"ERRO em ensure_comentarios_verificacao_in_registos_limpeza: {e}")

def ensure_empresa_in_funcionarios():
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'funcionarios'")
            cols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(funcionarios)")
            cols = {r["name"] for r in cur.fetchall()}
            
        if "empresa" not in cols:
            try:
                if is_postgres(conn):
                    cur.execute("SAVEPOINT add_empresa")
                cur.execute("ALTER TABLE funcionarios ADD COLUMN empresa TEXT")
                if is_postgres(conn):
                    cur.execute("RELEASE SAVEPOINT add_empresa")
                conn.commit()
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT add_empresa")
                    except:
                        pass
                try:
                    conn.rollback()
                except:
                    pass
    except Exception:
        pass
    finally:
        conn.close()

try:
    ensure_empresa_in_funcionarios()
except Exception as e:
    print(f"ERRO em ensure_empresa_in_funcionarios: {e}")
# Rota de teste para debug
@app.route("/debug")
def debug_route():
    try:
        db_url = os.environ.get("DATABASE_URL")
        return f"""
        <h1>Debug Info</h1>
        <p>DATABASE_URL: {'[DEFINIDA]' if db_url else '[NÃO DEFINIDA]'}</p>
        <p>psycopg2: {'Disponível' if psycopg2 else 'Não disponível'}</p>
        <p>Python Version: {sys.version}</p>
        <p>App funcionando!</p>
        """
    except Exception as e:
        return f"Erro: {e}"

# Autenticação
# -----------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        conn = get_conn()
        cur = conn.cursor()
        ph = sql_placeholder(conn)
        # Compatível com SQLite e PostgreSQL
        if is_postgres(conn):
            cur.execute(f"SELECT * FROM funcionarios WHERE username = {ph} AND ativo=1", (username,))
        else:
            cur.execute(f"SELECT * FROM funcionarios WHERE username = {ph} COLLATE NOCASE AND ativo=1", (username,))
        user = cur.fetchone()
        conn.close()

        valid = False
        if user:
            dbpwd = user["password"]
            try:
                valid = check_password_hash(dbpwd, password)
            except Exception:
                valid = False
            if not valid and dbpwd == password:  # fallback legado
                valid = True

        if valid:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = normalize_role(user["role"])

            flash(f"Bem vindo, {user['nome'] or user['username']}!", "info")

            def _first_allowed(role):
                if has_perm(role, "dashboard:view"):   return "home"
                if has_perm(role, "registos:view"):    return "registos"
                if has_perm(role, "viaturas:view"):    return "viaturas"
                if has_perm(role, "protocolos:view"):  return "protocolos"
                return "sem_permissao"

            return redirect(url_for(_first_allowed(session["role"])))

        flash("Credenciais inválidas.", "danger")

    return render_template("login.html", signature=APP_SIGNATURE)

@app.route("/logout")
def logout():
    session.clear()
    flash("Sessão terminada.", "info")
    return redirect(url_for("login"))

@app.route("/sem-permissao")
def sem_permissao():
    return render_template("403.html", signature=APP_SIGNATURE), 403

# -----------------------------------------------------------------------------
# Dashboard (/)
# -----------------------------------------------------------------------------

def get_counts(col):
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    cur.execute(f"SELECT {col} AS k, COUNT(*) AS n FROM viaturas WHERE {col} IS NOT NULL AND TRIM({col})<>'' GROUP BY {col} ORDER BY n DESC, k")
    rows = cur.fetchall()
    conn.close()
    return [r["k"] for r in rows], [r["n"] for r in rows]

@app.route("/")
@login_required
@require_perm("dashboard:view")
def home():
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    mes = request.args.get("mes")
    user_role = session.get("role")
    user_id = session.get("user_id")
    regiao_gestor = None

    # Se for gestor, obter a sua região
    if user_role == "gestor":
        cur.execute(f"SELECT regiao FROM funcionarios WHERE id={ph}", (user_id,))
        row = cur.fetchone()
        regiao_gestor = (row["regiao"] or "").strip() if row else None

    reg_labels, reg_values = get_counts("regiao")
    op_labels, op_values   = get_counts("operacao")
    mar_labels, mar_values = get_counts("marca")
    mod_labels, mod_values = get_counts("modelo")
    tip_labels, tip_values = get_counts("tipo_protocolo")
    
    # Helper para adicionar filtro de região e mês
    def filtro_mes_regiao(sql, params, alias_registos="r", alias_viaturas="v"):
        if mes:
            month_format = sql_month_format(conn, f"{alias_registos}.data_hora")
            sql += f" AND {month_format} = {ph}"
            params.append(mes)
        if regiao_gestor:
            sql += f" AND {alias_viaturas}.regiao = {ph}"
            params.append(regiao_gestor)
        return sql, params

    # Protocolos
    cur.execute("SELECT id, nome, COALESCE(frequencia_dias, 0) AS frequencia_dias FROM protocolos WHERE ativo=1 ORDER BY nome")
    protocolos = [dict(r) for r in cur.fetchall()]

    # Viaturas (filtradas por região se gestor/operador)
    viaturas_sql = "SELECT id, matricula, descricao, filial, num_frota, regiao FROM viaturas WHERE ativo=1"
    viaturas_params = []
    regiao_user = None
    if user_role in ("gestor", "operador"):
        cur.execute(f"SELECT regiao FROM funcionarios WHERE id={ph}", (user_id,))
        row = cur.fetchone()
        regiao_user = (row["regiao"] or "").strip() if row and row["regiao"] else None
        if regiao_user:
            viaturas_sql += f" AND regiao = {ph}"
            viaturas_params.append(regiao_user)
    viaturas_sql += " ORDER BY filial, matricula"
    cur.execute(viaturas_sql, viaturas_params)
    viaturas = [dict(r) for r in cur.fetchall()]

    # Funções de data para cada motor
    if is_postgres(conn):
        dt_now = "CURRENT_DATE"
        dt_fmt = "TO_CHAR(r.data_hora::timestamp, 'YYYY-MM')"
        dt_eq = "= TO_CHAR(CURRENT_DATE, 'YYYY-MM')"
        dt_today = "= CURRENT_DATE"
        dt_7days = ">= CURRENT_DATE - INTERVAL '6 days'"
        date_func = "r.data_hora::date"  # Para PostgreSQL
    else:
        dt_now = "date('now','localtime')"
        dt_fmt = "strftime('%Y-%m', r.data_hora)"
        dt_eq = "= strftime('%Y-%m', 'now','localtime')"
        dt_today = "= date('now','localtime')"
        dt_7days = ">= date('now','-6 days','localtime')"
        date_func = "date(r.data_hora)"  # Para SQLite

    # Última limpeza por viatura/protocolo (filtrada por região)
    datetime_func = sql_datetime(conn, "r.data_hora")
    last_map_sql = f"""
        SELECT r.viatura_id, r.protocolo_id, MAX({datetime_func}) AS ult
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE 1=1
    """
    last_map_params = []
    if regiao_gestor:
        last_map_sql += f" AND v.regiao = {ph}"
        last_map_params.append(regiao_gestor)
    last_map_sql += " GROUP BY r.viatura_id, r.protocolo_id"
    cur.execute(last_map_sql, last_map_params)
    last_map = {(r["viatura_id"], r["protocolo_id"]): r["ult"] for r in cur.fetchall()}

    # Última (qualquer) por viatura (filtrada por região)
    last_any_sql = f"""
        SELECT v.id as viatura_id, MAX({datetime_func}) AS ult
        FROM viaturas v
        LEFT JOIN registos_limpeza r ON v.id = r.viatura_id
        WHERE v.ativo=1
    """
    last_any_params = []
    if user_role in ("gestor", "operador") and regiao_user:
        last_any_sql += f" AND v.regiao = {ph}"
        last_any_params.append(regiao_user)
    last_any_sql += " GROUP BY v.id"
    cur.execute(last_any_sql, last_any_params)
    last_any = {r["viatura_id"]: r["ult"] for r in cur.fetchall()}

    # Limpezas hoje (por região se gestor)
    limpezas_hoje_sql = f"""
        SELECT r.viatura_id, COUNT(*) as n
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE {date_func} {dt_today}
    """
    limpezas_hoje_params = []
    if regiao_gestor:
        limpezas_hoje_sql += f" AND v.regiao = {ph}"
        limpezas_hoje_params.append(regiao_gestor)
    limpezas_hoje_sql += " GROUP BY r.viatura_id"
    cur.execute(limpezas_hoje_sql, limpezas_hoje_params)
    limpezas_hoje = {r["viatura_id"]: r["n"] for r in cur.fetchall()}
    for v in viaturas:
        v["limpeza_repetida"] = limpezas_hoje.get(v["id"], 0) > 1

    # Limpezas hoje (por região se gestor/operador)
    limpas_hoje_sql = f"""
        SELECT r.viatura_id, COUNT(*) as n
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE {date_func} {dt_today}
    """
    limpas_hoje_params = []
    if user_role in ("gestor", "operador"):
        if regiao_user:
            limpas_hoje_sql += f" AND v.regiao = {ph}"
            limpas_hoje_params.append(regiao_user)
    limpas_hoje_sql += " GROUP BY r.viatura_id"
    cur.execute(limpas_hoje_sql, limpas_hoje_params)
    limpas_hoje_map = {r["viatura_id"]: r["n"] for r in cur.fetchall()}

    for v in viaturas:
        v["limpa_hoje"] = v["id"] in limpas_hoje_map
        v["limpeza_repetida"] = limpas_hoje_map.get(v["id"], 0) > 1

    # KPI: registos hoje (total de registos de limpeza criados hoje)
    kpi_today_sql = f"""
        SELECT COUNT(*) AS n
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE {date_func} {dt_today}
    """
    kpi_today_params = []
    if user_role in ("gestor", "operador"):
        if regiao_user:
            kpi_today_sql += f" AND v.regiao = {ph}"
            kpi_today_params.append(regiao_user)
    cur.execute(kpi_today_sql, kpi_today_params)
    result = cur.fetchone()
    kpi_today = result["n"] if isinstance(result, dict) else result[0]

    # KPI: viaturas limpas hoje (viaturas distintas limpas pelo menos uma vez hoje)
    kpi_today_veh_sql = f"""
        SELECT COUNT(DISTINCT r.viatura_id) AS n
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE date(r.data_hora){dt_today}
    """
    kpi_today_veh_params = []
    if user_role in ("gestor", "operador"):
        if regiao_user:
            kpi_today_veh_sql += f" AND v.regiao = {ph}"
            kpi_today_veh_params.append(regiao_user)
    cur.execute(kpi_today_veh_sql, kpi_today_veh_params)
    result = cur.fetchone()
    kpi_today_veh = result["n"] if isinstance(result, dict) else result[0]

    # KPI: total de limpezas hoje (inclui extra)
    kpi_total_limpezas_sql = f"""
        SELECT COUNT(*) AS n
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE date(r.data_hora){dt_today}
    """
    kpi_total_limpezas_params = []
    if user_role in ("gestor", "operador"):
        if regiao_user:
            kpi_total_limpezas_sql += f" AND v.regiao = {ph}"
            kpi_total_limpezas_params.append(regiao_user)
    cur.execute(kpi_total_limpezas_sql, kpi_total_limpezas_params)
    result = cur.fetchone()
    kpi_total_limpezas = result["n"] if isinstance(result, dict) else result[0]

    # KPI: registos últimos 7 dias
    kpi_week_sql = f"""
        SELECT COUNT(*) AS n
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE date(r.data_hora) {dt_7days}
    """
    kpi_week_params = []
    if regiao_gestor:
        kpi_week_sql += f" AND v.regiao = {ph}"
        kpi_week_params.append(regiao_gestor)
    cur.execute(kpi_week_sql, kpi_week_params)
    result = cur.fetchone()
    kpi_week = result["n"] if isinstance(result, dict) else result[0]

    # KPI: registos este mês
    kpi_month_sql = f"""
        SELECT COUNT(*) AS n
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE {dt_fmt} {dt_eq}
    """
    kpi_month_params = []
    if regiao_gestor:
        kpi_month_sql += f" AND v.regiao = {ph}"
        kpi_month_params.append(regiao_gestor)
    cur.execute(kpi_month_sql, kpi_month_params)
    result = cur.fetchone()
    kpi_month = result["n"] if isinstance(result, dict) else result[0]

    # Limpezas por local
    sql_local = """
        SELECT COALESCE(r.local,'(Sem local)') as label, COUNT(*) as qty
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE 1=1
    """
    params_local = []
    sql_local, params_local = filtro_mes_regiao(sql_local, params_local)
    sql_local += " GROUP BY COALESCE(r.local,'(Sem local)') ORDER BY qty DESC, label"
    cur.execute(sql_local, params_local)
    chart_local = [(r["label"], r["qty"]) for r in cur.fetchall()]

    # Limpezas por funcionário
    sql_func = """
        SELECT f.username as label, COUNT(*) as qty
        FROM registos_limpeza r
        JOIN funcionarios f ON f.id = r.funcionario_id
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE 1=1
    """
    params_func = []
    sql_func, params_func = filtro_mes_regiao(sql_func, params_func)
    sql_func += " GROUP BY r.funcionario_id, f.username ORDER BY qty DESC, label"
    cur.execute(sql_func, params_func)
    chart_func = [(r["label"], r["qty"]) for r in cur.fetchall()]

    # Viaturas distintas por protocolo
    sql_proto = """
        SELECT p.nome as label, COUNT(DISTINCT r.viatura_id) as qty
        FROM registos_limpeza r
        JOIN protocolos p ON p.id = r.protocolo_id
        JOIN viaturas v ON v.id = r.viatura_id
        WHERE 1=1
    """
    params_proto = []
    sql_proto, params_proto = filtro_mes_regiao(sql_proto, params_proto)
    sql_proto += " GROUP BY r.protocolo_id, p.nome ORDER BY p.nome"
    cur.execute(sql_proto, params_proto)
    chart_proto = [(r["label"], r["qty"]) for r in cur.fetchall()]

    # ...restante código igual...
    # (continua igual ao teu original a partir daqui)

    # Média de dias desde última limpeza
    hoje = date.today()
    dias_por_viatura = []
    for v in viaturas:
        iso = last_any.get(v["id"])
        if not iso:
           continue
        # Handle both string (SQLite) and datetime (PostgreSQL) formats
        if isinstance(iso, str):
            dt = datetime.fromisoformat(iso).date()
        else:
            # Assume it's already a datetime object from PostgreSQL
            dt = iso.date() if hasattr(iso, 'date') else iso
        dias_por_viatura.append((hoje - dt).days)
    media_dias_ultima = round(sum(dias_por_viatura)/len(dias_por_viatura), 2) if dias_por_viatura else 0.0
    total_viaturas = len(viaturas)

    # Limpezas por duração (mantém original)
    cur.execute("""
        SELECT r.protocolo_id, p.nome AS nome, r.data_hora, r.hora_inicio, r.hora_fim
        FROM registos_limpeza r
        JOIN protocolos p ON p.id = r.protocolo_id
        WHERE r.hora_inicio IS NOT NULL AND r.hora_fim IS NOT NULL
    """)
    from collections import defaultdict
    sum_min, cnt_min = defaultdict(int), defaultdict(int)
    for r in cur.fetchall():
        try:
            d = datetime.fromisoformat(r["data_hora"]).date()
            h1 = datetime.fromisoformat(f"{d} {r['hora_inicio']}:00")
            h2 = datetime.fromisoformat(f"{d} {r['hora_fim']}:00")
            mins = max(0, int((h2 - h1).total_seconds()//60))
            sum_min[r["nome"]] += mins; cnt_min[r["nome"]] += 1
        except Exception:
            pass
    chart_dur = [(nome, round(sum_min[nome]/cnt_min[nome],1)) for nome in sorted(sum_min.keys())]

    # Top 10 atraso
    rows_atraso = []
    rows_top10 = []
    all_last_any_days = []
    for v in viaturas:
        iso_any = last_any.get(v["id"])
        if not iso_any: continue
        dta = datetime.fromisoformat(iso_any).date()
        all_last_any_days.append({
            "num_frota": v.get("num_frota") or "",
            "matricula": v["matricula"],
            "filial": v.get("filial") or "",
            "dias_sem_limpeza": (hoje - dta).days,
            "ultima_qualquer": datetime.fromisoformat(iso_any).isoformat(sep=" "),
        })
    rows_top10 = sorted(all_last_any_days, key=lambda r: (r["dias_sem_limpeza"], r["matricula"]))[:10]

    for v in viaturas:
        vinfo = {
            "num_frota": v.get("num_frota") or "",
            "matricula": v["matricula"],
            "filial": v.get("filial") or "",
            "ultima_qualquer": None,
            "dias_sem_limpeza": None,
            "por_protocolo": {},
            "delta_protocolos": None,
            "tem_atraso": False,
            "atraso_por_dias": 0,
            "limpa_hoje": v["id"] in limpas_hoje_map,
        }
        last_dates, max_over, algum_atraso = [], 0, False

        for p in protocolos:
            iso = last_map.get((v["id"], p["id"]))
            last_dt = datetime.fromisoformat(iso) if iso else None
            dias = (hoje - last_dt.date()).days if last_dt else None
            freq = int(p["frequencia_dias"]) if p["frequencia_dias"] else None
            atraso, overdue_by = False, 0

            if last_dt:
                last_dates.append(last_dt)
                if freq and dias is not None and dias > freq:
                    atraso, overdue_by = True, dias - freq
            else:
                if freq:
                    atraso, overdue_by = True, 10_000

            if atraso:
                algum_atraso = True
                max_over = max(max_over, overdue_by)

            vinfo["por_protocolo"][p["id"]] = {
                "nome": p["nome"],
                "ultima": last_dt.isoformat(sep=" ") if last_dt else None,
                "dias": dias,
                "freq": freq,
                "atraso": atraso,
            }

        if last_dates:
            ultima = max(last_dates)
            vinfo["ultima_qualquer"] = ultima.isoformat(sep=" ")
            vinfo["dias_sem_limpeza"] = (hoje - ultima.date()).days
            if len(last_dates) >= 2:
                vinfo["delta_protocolos"] = abs((max(last_dates).date()) - (min(last_dates).date())).days

        vinfo["tem_atraso"] = algum_atraso
        vinfo["atraso_por_dias"] = max_over
        if vinfo["tem_atraso"]:
            rows_atraso.append(vinfo)

    rows_atraso.sort(key=lambda r: (-r["atraso_por_dias"], r["matricula"]))

    charts = {
        "kpi_today": kpi_today,
        "kpi_week": kpi_week,
        "kpi_month": kpi_month,
        "kpi_today_veh": kpi_today_veh,
        "kpi_total_limpezas": kpi_total_limpezas,
        "proto_labels": [l for (l, _) in chart_proto],
        "proto_values": [v for (_, v) in chart_proto],
        "avg_days": media_dias_ultima,
        "fleet_size": total_viaturas,
        "local_labels": [l for (l, _) in chart_local],
        "local_values": [v for (_, v) in chart_local],
        "func_labels": [l for (l, _) in chart_func],
        "func_values": [v for (_, v) in chart_func],
        "dur_labels": [l for (l, _) in chart_dur],
        "dur_values": [v for (_, v) in chart_dur],
        "reg_labels": reg_labels, "reg_values": reg_values,
        "op_labels":  op_labels,  "op_values":  op_values,
        "mar_labels": mar_labels, "mar_values": mar_values,
        "mod_labels": mod_labels, "mod_values": mod_values,
        "tip_labels": tip_labels, "tip_values": tip_values,
    }

    # Viaturas limpas por protocolo (hoje, filtradas por região se gestor)
    viaturas_proto_sql = f"""
        SELECT r.protocolo_id, p.nome as protocolo_nome, v.matricula, v.num_frota, v.descricao
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        JOIN protocolos p ON p.id = r.protocolo_id
        WHERE {date_func} {dt_today}
    """
    viaturas_proto_params = []
    if regiao_gestor:
        viaturas_proto_sql += f" AND v.regiao = {ph}"
        viaturas_proto_params.append(regiao_gestor)
    viaturas_proto_sql += " ORDER BY p.nome, v.matricula"
    cur.execute(viaturas_proto_sql, viaturas_proto_params)
    viaturas_por_protocolo = {}
    for row in cur.fetchall():
        pid = row["protocolo_id"]
        nome = row["protocolo_nome"]
        if pid not in viaturas_por_protocolo:
            viaturas_por_protocolo[pid] = {"nome": nome, "viaturas": []}
        viaturas_por_protocolo[pid]["viaturas"].append({
            "matricula": row["matricula"],
            "num_frota": row["num_frota"] or "",
            "descricao": row["descricao"] or ""
        })

    # Pedidos de autorização pendentes (para gestor/admin)
    pedidos_pendentes = []
    if user_role in ["admin", "gestor"]:
        gestor_id = user_id
        ph = sql_placeholder(conn)
        today_condition = sql_today_condition(conn, "pa.data_pedido")
        cur.execute(f"""
            SELECT pa.id, v.matricula, v.num_frota, f.nome as operador
            FROM pedidos_autorizacao pa
            JOIN viaturas v ON v.id = pa.viatura_id
            JOIN funcionarios f ON f.id = pa.funcionario_id
            WHERE pa.validado=0 AND pa.destinatario_id={ph} AND {today_condition}
            ORDER BY pa.data_pedido DESC
        """, (gestor_id,))
        pedidos_pendentes = [dict(r) for r in cur.fetchall()]

    conn.close()

    for v in viaturas:
        if "limpeza_validada" not in v:
            v["limpeza_validada"] = 0

    return render_template("home.html",
        charts=charts,
        protocolos=protocolos,
        rows=rows_atraso,
        top10=rows_top10,
        signature=APP_SIGNATURE,
        viaturas=viaturas,
        viaturas_por_protocolo=viaturas_por_protocolo,
        pedidos_pendentes=pedidos_pendentes,
        mes=mes
    )
@app.route("/pedidos_autorizacao")
@login_required
@require_perm("dashboard:view")
def pedidos_autorizacao():
    gestor_id = session.get("user_id")
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    # Usando função auxiliar para condição de data de hoje
    today_condition = sql_today_condition(conn, "pa.data_pedido")
    cur.execute(f"""
        SELECT pa.id, v.matricula, v.num_frota, f.nome as operador
        FROM pedidos_autorizacao pa
        JOIN viaturas v ON v.id = pa.viatura_id
        JOIN funcionarios f ON f.id = pa.funcionario_id
        WHERE pa.validado=0 AND pa.destinatario_id={ph} AND {today_condition}
        ORDER BY pa.data_pedido DESC
    """, (gestor_id,))
    pedidos = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("pedidos_autorizacao.html", pedidos=pedidos, signature=APP_SIGNATURE)

@app.route("/api/pedidos_pendentes")
@login_required
@require_perm("dashboard:view")
def api_pedidos_pendentes():
    """API endpoint para buscar pedidos pendentes (para auto-refresh)"""
    user_role = session.get("role")
    user_id = session.get("user_id")
    
    if user_role not in ["admin", "gestor"]:
        return {"pedidos": []}
    
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    today_condition = sql_today_condition(conn, "pa.data_pedido")
    
    cur.execute(f"""
        SELECT pa.id, v.matricula, v.num_frota, f.nome as operador, pa.data_pedido
        FROM pedidos_autorizacao pa
        JOIN viaturas v ON v.id = pa.viatura_id
        JOIN funcionarios f ON f.id = pa.funcionario_id
        WHERE pa.validado=0 AND pa.destinatario_id={ph} AND {today_condition}
        ORDER BY pa.data_pedido DESC
    """, (user_id,))
    
    pedidos = []
    for row in cur.fetchall():
        pedidos.append({
            "id": row["id"],
            "matricula": row["matricula"],
            "num_frota": row["num_frota"],
            "operador": row["operador"],
            "data_pedido": row["data_pedido"].strftime("%H:%M") if row["data_pedido"] else ""
        })
    
    conn.close()
    return {"pedidos": pedidos, "count": len(pedidos)}

@app.route("/api/meus_pedidos_status")
@login_required
def api_meus_pedidos_status():
    """API endpoint para operador verificar status dos seus pedidos"""
    user_id = session.get("user_id")
    
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    today_condition = sql_today_condition(conn, "pa.data_pedido")
    
    # Busca pedidos do usuário de hoje (validados e pendentes)
    cur.execute(f"""
        SELECT pa.id, pa.validado, pa.data_validacao, v.matricula, v.num_frota,
               g.nome as gestor_nome, pa.data_pedido
        FROM pedidos_autorizacao pa
        JOIN viaturas v ON v.id = pa.viatura_id
        LEFT JOIN funcionarios g ON g.id = pa.validado_por
        WHERE pa.funcionario_id={ph} AND {today_condition}
        ORDER BY pa.data_pedido DESC
    """, (user_id,))
    
    pedidos = []
    autorizados_recentes = 0
    
    for row in cur.fetchall():
        pedido = {
            "id": row["id"],
            "validado": bool(row["validado"]),
            "matricula": row["matricula"],
            "num_frota": row["num_frota"], 
            "gestor_nome": row["gestor_nome"],
            "data_pedido": row["data_pedido"].strftime("%H:%M") if row["data_pedido"] else "",
            "data_validacao": row["data_validacao"].strftime("%H:%M") if row["data_validacao"] else ""
        }
        pedidos.append(pedido)
        
        # Conta autorizações dos últimos 2 minutos (para notificação)
        if row["validado"] and row["data_validacao"]:
            from datetime import datetime, timedelta
            if datetime.now() - row["data_validacao"] < timedelta(minutes=2):
                autorizados_recentes += 1
    
    conn.close()
    return {
        "pedidos": pedidos, 
        "total": len(pedidos),
        "autorizados": len([p for p in pedidos if p["validado"]]),
        "pendentes": len([p for p in pedidos if not p["validado"]]),
        "autorizados_recentes": autorizados_recentes
    }

@app.route("/auto-refresh.js")
def auto_refresh_js():
    """Serve JavaScript para auto-refresh dos pedidos pendentes"""
    js_content = """
// Auto-refresh para pedidos pendentes no dashboard e status de autorizações
(function() {
    let refreshInterval;
    let lastCount = 0;
    let lastAutorizados = 0;
    
    function updatePedidosPendentes() {
        fetch('/api/pedidos_pendentes')
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('pedidos-pendentes-container');
                if (!container) return;
                
                // Se o número de pedidos mudou, atualiza a interface
                if (data.count !== lastCount) {
                    lastCount = data.count;
                    
                    // Atualiza o contador no badge
                    const badge = document.querySelector('.pedidos-badge');
                    if (badge) {
                        badge.textContent = data.count;
                        badge.style.display = data.count > 0 ? 'inline' : 'none';
                    }
                    
                    // Atualiza a lista de pedidos
                    if (data.pedidos.length > 0) {
                        let html = '<div class="alert alert-warning"><h5>Pedidos de Autorização Pendentes:</h5><ul>';
                        data.pedidos.forEach(p => {
                            html += `<li><strong>${p.matricula}</strong> (${p.num_frota}) - ${p.operador}`;
                            html += ` <small>(${p.data_pedido})</small>`;
                            html += ` <a href="/validar_pedido_autorizacao/${p.id}" class="btn btn-sm btn-success" onclick="return confirm('Autorizar limpeza extra?')">Autorizar</a></li>`;
                        });
                        html += '</ul></div>';
                        container.innerHTML = html;
                    } else {
                        container.innerHTML = '';
                    }
                    
                    // Atualiza título da página
                    const originalTitle = document.title.replace(/^\(\d+\) /, '');
                    if (data.count > 0) {
                        document.title = `(${data.count}) ${originalTitle}`;
                    } else {
                        document.title = originalTitle;
                    }
                    
                    // Mostra notificação se há novos pedidos e notificações estão ativadas
                    if (data.count > 0 && window.lastNotifiedCount !== data.count && notificationsEnabled()) {
                        showNotification(`${data.count} pedido(s) de autorização pendente(s)`);
                        window.lastNotifiedCount = data.count;
                    }
                }
            })
            .catch(error => console.log('Erro ao buscar pedidos:', error));
    }
    
    function updateMeusPedidosStatus() {
        fetch('/api/meus_pedidos_status')
            .then(response => response.json())
            .then(data => {
                // Atualiza contador no título para operadores
                const originalTitle = document.title.replace(/^\(\d+\) /, '');
                if (data.autorizados_recentes > 0) {
                    document.title = `(${data.autorizados_recentes}) ${originalTitle}`;
                } else if (data.pendentes > 0) {
                    document.title = `(${data.pendentes}⏳) ${originalTitle}`;
                } else {
                    document.title = originalTitle;
                }
                
                // Atualiza área de status dos pedidos (se existir)
                const statusContainer = document.getElementById('meus-pedidos-status');
                if (statusContainer) {
                    let html = '';
                    if (data.pedidos.length > 0) {
                        html += '<div class="card mt-3"><div class="card-header"><h6>Meus Pedidos de Hoje</h6></div><div class="card-body">';
                        data.pedidos.forEach(p => {
                            const status = p.validado ? 
                                `<span class="badge bg-success">✅ Autorizado por ${p.gestor_nome} às ${p.data_validacao}</span>` : 
                                `<span class="badge bg-warning">⏳ Pendente</span>`;
                            html += `<div class="d-flex justify-content-between align-items-center border-bottom py-2">
                                <span><strong>${p.matricula}</strong> (${p.num_frota}) - ${p.data_pedido}</span>
                                ${status}
                            </div>`;
                        });
                        html += '</div></div>';
                    }
                    statusContainer.innerHTML = html;
                }
                
                // Notifica sobre autorizações recentes
                if (data.autorizados_recentes > 0 && lastAutorizados !== data.autorizados_recentes && notificationsEnabled()) {
                    showNotification(`🎉 ${data.autorizados_recentes} pedido(s) autorizado(s)! Já pode efetuar limpeza extra.`, 'success');
                    lastAutorizados = data.autorizados_recentes;
                }
            })
            .catch(error => console.log('Erro ao buscar status dos pedidos:', error));
    }
    
    function showNotification(message, type = 'info') {
        // Cria notificação visual simples
        const notification = document.createElement('div');
        const alertClass = type === 'success' ? 'alert-success' : 'alert-info';
        const icon = type === 'success' ? '🎉' : '🔔';
        const title = type === 'success' ? 'Pedido Autorizado!' : 'Nova solicitação!';
        
        notification.className = `alert ${alertClass} alert-dismissible`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1050; min-width: 300px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);';
        notification.innerHTML = `
            <strong>${icon} ${title}</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" onclick="this.parentElement.remove()"></button>
        `;
        document.body.appendChild(notification);
        
        // Tenta tocar som de notificação (se permitido pelo browser)
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hUEAtGn+Lvt2UnAC+C1/HHdSsFKH/N8Nh+NgUZab3o45JAEApRo+PwuGIaAjOH2fPBCy0EJHjI7Ox9OAUWVbLm4x1LFAtKq+3tv2IkAyh9VPHBdOEWvvz25'></audio>");
            audio.volume = 0.3;
            audio.play().catch(() => {}); // Ignora erros se som não funcionar
        } catch (e) {}
        
        // Remove após 8 segundos
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 8000);
    }
    
    // Função para alternar notificações
    window.toggleNotifications = function() {
        const enabled = localStorage.getItem('notificationsEnabled') !== 'false';
        localStorage.setItem('notificationsEnabled', (!enabled).toString());
        const btn = document.getElementById('toggle-notifications-btn');
        if (btn) {
            btn.textContent = enabled ? '🔔 Ativar Notificações' : '🔕 Desativar Notificações';
            btn.className = enabled ? 'btn btn-outline-secondary btn-sm' : 'btn btn-warning btn-sm';
        }
        return !enabled;
    };
    
    // Verifica se notificações estão habilitadas
    function notificationsEnabled() {
        return localStorage.getItem('notificationsEnabled') !== 'false';
    }
    
    // Detecta tipo de usuário através de elementos na página
    function detectUserType() {
        // Se existe container de pedidos pendentes, é gestor/admin
        if (document.getElementById('pedidos-pendentes-container')) {
            return 'gestor';
        }
        // Se existe botão de novo registo, é operador
        if (document.querySelector('a[href*="novo"]') || document.querySelector('a[href*="registo"]')) {
            return 'operador';
        }
        return 'unknown';
    }
    
    // Inicia o auto-refresh quando a página carrega
    document.addEventListener('DOMContentLoaded', function() {
        // Verifica se estamos na página principal
        if (window.location.pathname === '/' || window.location.pathname === '/home') {
            const userType = detectUserType();
            
            // Adiciona botão para controlar notificações
            const nav = document.querySelector('.navbar-nav');
            if (nav && !document.getElementById('toggle-notifications-btn')) {
                const li = document.createElement('li');
                li.className = 'nav-item';
                const enabled = notificationsEnabled();
                li.innerHTML = `<button id="toggle-notifications-btn" class="${enabled ? 'btn btn-warning btn-sm' : 'btn btn-outline-secondary btn-sm'}" onclick="toggleNotifications()" style="margin: 5px;">${enabled ? '🔕 Desativar Notificações' : '🔔 Ativar Notificações'}</button>`;
                nav.appendChild(li);
            }
            
            // Adiciona container para status dos pedidos do operador se não existir
            if (userType === 'operador') {
                const main = document.querySelector('main') || document.querySelector('.container');
                if (main && !document.getElementById('meus-pedidos-status')) {
                    const statusDiv = document.createElement('div');
                    statusDiv.id = 'meus-pedidos-status';
                    main.insertBefore(statusDiv, main.firstChild);
                }
            }
            
            // Inicia verificações baseado no tipo de usuário
            if (userType === 'gestor') {
                updatePedidosPendentes(); // Primeira verificação
                refreshInterval = setInterval(updatePedidosPendentes, 30000); // A cada 30 segundos
            } else if (userType === 'operador') {
                updateMeusPedidosStatus(); // Primeira verificação
                refreshInterval = setInterval(updateMeusPedidosStatus, 20000); // A cada 20 segundos (mais rápido para operadores)
            }
        }
    });
    
    // Para o refresh quando sair da página
    window.addEventListener('beforeunload', function() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
        }
    });
})();
"""
    response = Response(js_content, mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route("/validar_pedido_autorizacao/<int:pedido_id>", methods=["POST"])
@login_required
@require_perm("dashboard:view")
def validar_pedido_autorizacao(pedido_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    
    # Busca dados do pedido antes de autorizar (para log/notificação)
    cur.execute(f"""
        SELECT pa.funcionario_id, v.matricula, v.num_frota, f.nome as operador_nome
        FROM pedidos_autorizacao pa
        JOIN viaturas v ON v.id = pa.viatura_id  
        JOIN funcionarios f ON f.id = pa.funcionario_id
        WHERE pa.id={ph}
    """, (pedido_id,))
    pedido_info = cur.fetchone()
    
    # Compatível com SQLite e PostgreSQL para timestamp
    if is_postgres(conn):
        cur.execute(f"UPDATE pedidos_autorizacao SET validado=1, validado_por={ph}, data_validacao=NOW() WHERE id={ph}", (session["user_id"], pedido_id))
    else:
        cur.execute(f"UPDATE pedidos_autorizacao SET validado=1, validado_por={ph}, data_validacao=CURRENT_TIMESTAMP WHERE id={ph}", (session["user_id"], pedido_id))
    
    conn.commit()
    conn.close()
    
    if pedido_info:
        flash(f"Pedido autorizado para {pedido_info['operador_nome']} - {pedido_info['matricula']} ({pedido_info['num_frota']})!", "success")
    else:
        flash("Pedido autorizado!", "success")
        
    return redirect(url_for("pedidos_autorizacao"))

# -----------------------------------------------------------------------------
# Viaturas
# -----------------------------------------------------------------------------
@app.route("/viaturas/exportar")
@login_required
@require_perm("viaturas:view")
def exportar_viaturas_csv():
    q_matricula = (request.args.get("matricula") or "").strip()
    q_num_frota = (request.args.get("num_frota") or "").strip()
    f_regiao = (request.args.get("regiao") or "").strip()
    f_operacao = (request.args.get("operacao") or "").strip()
    f_marca = (request.args.get("marca") or "").strip()
    f_modelo = (request.args.get("modelo") or "").strip()
    f_ativo = (request.args.get("ativo") or "").strip()

    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    where = ["1=1"]
    params = []
    if q_matricula:
        where.append(f"v.matricula LIKE {ph}")
        params.append(f"%{q_matricula}%")
    if q_num_frota:
        where.append(f"(v.numero_frota = {ph} OR v.num_frota = {ph})")
        params.extend([q_num_frota, q_num_frota])
    if f_regiao:
        where.append(f"COALESCE(v.regiao,'') = {ph}")
        params.append(f_regiao)
    if f_operacao:
        where.append(f"COALESCE(v.operacao,'') = {ph}")
        params.append(f_operacao)
    if f_marca:
        where.append(f"COALESCE(v.marca,'') = {ph}")
        params.append(f_marca)
    if f_modelo:
        where.append(f"COALESCE(v.modelo,'') = {ph}")
        params.append(f_modelo)
    if f_ativo in ("0", "1"):
        where.append(f"v.ativo = {ph}")
        params.append(int(f_ativo))

    cur.execute(f"""
    SELECT v.id, v.matricula, v.num_frota,
           v.regiao, v.operacao, v.marca, v.modelo, v.tipo_protocolo,
           v.descricao, v.filial, v.ativo, v.criado_em
    FROM viaturas v
    WHERE { " AND ".join(where) }
    ORDER BY v.matricula
    """, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    import io, csv as _csv
    sio = io.StringIO()
    headers = ["matricula", "nº de frota", "Região", "Operação", "Marca", "Modelo", "Tipo de Protocolo", "Ativo",
               "descricao", "filial", "num_frota", "criado_em", "id"]
    w = _csv.writer(sio, delimiter=';')
    w.writerow(headers)
    for r in rows:
        w.writerow([
            r["matricula"], r["num_frota"] or "", r["regiao"] or "", r["operacao"] or "",
            r["marca"] or "", r["modelo"] or "", r["tipo_protocolo"] or "",
            "Sim" if int(r["ativo"] or 0) else "Não", r["descricao"] or "", r["filial"] or "",
            r["num_frota"] or "", r["criado_em"] or "", r["id"],
        ])
    data = sio.getvalue().encode("utf-8-sig")
    return send_file(io.BytesIO(data), mimetype="text/csv; charset=utf-8", as_attachment=True, download_name="viaturas_export.csv")


@app.route("/viaturas", methods=["GET", "POST"])
@login_required
@require_perm("viaturas:view")
def viaturas():
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)

    # filtros
    q_matricula = (request.args.get("matricula") or "").strip()
    q_num_frota = (request.args.get("num_frota") or "").strip()
    f_regiao = (request.args.get("regiao") or "").strip()
    f_operacao = (request.args.get("operacao") or "").strip()
    f_marca = (request.args.get("marca") or "").strip()
    f_modelo = (request.args.get("modelo") or "").strip()
    f_tipo = (request.args.get("tipo_protocolo") or "").strip()
    f_ativo = (request.args.get("ativo") or "").strip()
    f_filial = (request.args.get("filial") or "").strip()

    # Se for gestor, força filtro pela sua região
    if session.get("role") in ("gestor", "operador"):
        cur.execute(f"SELECT regiao FROM funcionarios WHERE id={ph}", (session.get("user_id"),))
        row = cur.fetchone()
        regiao_user = (row["regiao"] or "").strip() if row else ""
        if regiao_user:
            f_regiao = regiao_user

    if request.method == "POST":
        matricula = (request.form.get("matricula") or "").strip()
        num_frota = (request.form.get("num_frota") or "").strip()
        regiao = (request.form.get("regiao") or "").strip()
        operacao = (request.form.get("operacao") or "").strip()
        marca = (request.form.get("marca") or "").strip()
        modelo = (request.form.get("modelo") or "").strip()
        tipo_protocolo = (request.form.get("tipo_protocolo") or "").strip()
        descricao = (request.form.get("descricao") or "").strip()
        filial = (request.form.get("filial") or "").strip()
        ativo = 1

        if not matricula:
            flash("A matrícula é obrigatória.", "danger")
        else:
            # Verifica se já existe viatura com esta matrícula
            cur.execute(f"SELECT id FROM viaturas WHERE matricula = {ph}", (matricula,))
            existe = cur.fetchone()
            if existe:
                flash("Já existe uma viatura com essa matrícula. Verifique a lista existente.", "danger")
            else:
                try:
                    cur.execute(f"""
                        INSERT INTO viaturas (matricula, num_frota, regiao, operacao, marca, modelo, tipo_protocolo, descricao, filial, ativo)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    """, (matricula, num_frota, regiao, operacao, marca, modelo, tipo_protocolo, descricao, filial, ativo))
                    conn.commit()
                    flash("Viatura inserida com sucesso.", "success")
                except Exception as e:
                    flash(f"Erro ao inserir viatura: {e}", "danger")
                
    if not f_ativo:
        f_ativo = "1"

    where = ["1=1"]
    params = []
    if q_matricula:
        where.append(f"v.matricula LIKE {ph}"); params.append(f"%{q_matricula}%")
    if q_num_frota:
        where.append(f"(v.numero_frota = {ph} OR v.num_frota = {ph})"); params.extend([q_num_frota, q_num_frota])
    if f_regiao:
        where.append(f"COALESCE(v.regiao,'') = {ph}"); params.append(f_regiao)
    if f_operacao:
        where.append(f"COALESCE(v.operacao,'') = {ph}"); params.append(f_operacao)
    if f_marca:
        where.append(f"COALESCE(v.marca,'') = {ph}"); params.append(f_marca)
    if f_modelo:
        where.append(f"COALESCE(v.modelo,'') = {ph}"); params.append(f_modelo)
    if f_tipo:
        where.append(f"COALESCE(v.tipo_protocolo,'') = {ph}"); params.append(f_tipo)
    if f_ativo in ("0", "1"):
        where.append(f"v.ativo = {ph}"); params.append(int(f_ativo))
    if f_filial:
        where.append(f"COALESCE(v.filial,'') = {ph}"); params.append(f_filial)

    datetime_func = sql_datetime(conn, "data_hora")
    datetime_func_r = sql_datetime(conn, "r.data_hora")
    cur.execute(f"""
        WITH last AS (
          SELECT r.*
          FROM registos_limpeza r
          JOIN (
            SELECT viatura_id, MAX({datetime_func}) AS ult
            FROM registos_limpeza GROUP BY viatura_id
          ) m ON m.viatura_id=r.viatura_id AND {datetime_func_r}=m.ult
        ),
        verificados AS (
          SELECT viatura_id, COUNT(*) AS n
          FROM registos_limpeza
          WHERE verificacao_limpeza IS NOT NULL AND TRIM(verificacao_limpeza) <> ''
          GROUP BY viatura_id
        )
        SELECT v.id, v.matricula, v.descricao, v.filial,
               v.num_frota,
               v.regiao, v.operacao, v.marca, v.modelo, v.tipo_protocolo, v.ativo,
               l.local AS ultima_local, l.hora_inicio, l.hora_fim,
               f.username AS ultima_user
        FROM viaturas v
        LEFT JOIN last l ON l.viatura_id = v.id
        LEFT JOIN funcionarios f ON f.id = l.funcionario_id
        LEFT JOIN verificados ver ON ver.viatura_id = v.id
        WHERE { " AND ".join(where) }
        ORDER BY v.filial, v.matricula
    """, params)
    vs = [dict(row) for row in cur.fetchall()]
    
    cur.execute("SELECT id, nome, frequencia_dias FROM protocolos WHERE UPPER(nome) IN ('PROTOCOLO B', 'PROTOCOLO C')")
    protocolos_bc = {r["nome"].upper(): dict(r) for r in cur.fetchall()}

    hoje = date.today()
    for v in vs:
        v["tem_atraso"] = False
        for nome in ("PROTOCOLO B", "PROTOCOLO C"):
            prot = protocolos_bc.get(nome)
            if not prot:
                v[f"dias_{nome.replace(' ', '_').lower()}"] = None
                v[f"freq_{nome.replace(' ', '_').lower()}"] = None
                continue
            date_sql = sql_date(conn, "r.data_hora")
            cur.execute(f"""
                SELECT MAX({date_sql}) as ult
                FROM registos_limpeza r
                WHERE r.viatura_id={ph} AND r.protocolo_id={ph}
            """, (v["id"], prot["id"]))
            result = cur.fetchone()
            ult = result["ult"] if isinstance(result, dict) else result[0]
            if ult:
                # Handle both string (SQLite) and datetime (PostgreSQL) formats
                if isinstance(ult, str):
                    dias = (hoje - datetime.fromisoformat(ult).date()).days
                else:
                    # Assume it's already a datetime object from PostgreSQL
                    dt = ult.date() if hasattr(ult, 'date') else ult
                    dias = (hoje - dt).days
            else:
                dias = None
            v[f"dias_{nome.replace(' ', '_').lower()}"] = dias
            v[f"freq_{nome.replace(' ', '_').lower()}"] = prot["frequencia_dias"]
            # Verifica atraso
            if dias is not None and prot["frequencia_dias"] is not None and dias > prot["frequencia_dias"]:
                v["tem_atraso"] = True

    # Ordenar: primeiro as viaturas com atraso, depois as restantes
    vs = sorted(vs, key=lambda v: (not v["tem_atraso"], v["matricula"]))

    def _opts(col):
        cur.execute(f"SELECT DISTINCT {col} AS v FROM viaturas WHERE {col} IS NOT NULL AND TRIM({col})<>'' ORDER BY 1")
        return [r["v"] for r in cur.fetchall()]

    filtros = {
        "regiao": _opts("regiao"),
        "operacao": _opts("operacao"),
        "marca": _opts("marca"),
        "modelo": _opts("modelo"),
        "tipo_protocolo": _opts("tipo_protocolo"),
        "filial": _opts("filial"),
    }

    conn.close()
    
    return render_template("viaturas.html", viaturas=vs, filtros=filtros, signature=APP_SIGNATURE)
    
@app.route("/registos/<int:registo_id>/verificar", methods=["GET", "POST"])
@login_required
@require_perm("dashboard:view")
def verificar_limpeza(registo_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    if request.method == "POST":
        verificacao = request.form.get("verificacao_limpeza")
        cur.execute(f"UPDATE registos_limpeza SET verificacao_limpeza={ph} WHERE id={ph}", (verificacao, registo_id))
        conn.commit()
        conn.close()
        flash("Verificação de limpeza registada.", "success")
        return redirect(url_for("registos"))
    cur.execute(f"SELECT * FROM registos_limpeza WHERE id={ph}", (registo_id,))
    registo = cur.fetchone()
    conn.close()
    if not registo:
        flash("Registo não encontrado.", "danger")
        return redirect(url_for("registos"))
    return render_template("verificar_limpeza.html", registo=registo, signature=APP_SIGNATURE)

@app.route("/registos/<int:rid>", methods=["GET", "POST"])
@login_required
@require_perm("registos:view")
def registo_detalhe(rid):
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    if request.method == "POST" and user_can("dashboard:view"):
        # Observações e anexos
        nova_obs = (request.form.get("observacoes") or "").strip()
        cur.execute(f"UPDATE registos_limpeza SET observacoes={ph} WHERE id={ph}", (nova_obs, rid))
        # Comentários da verificação
        comentarios_verificacao = (request.form.get("comentarios_verificacao") or "").strip()
        cur.execute(f"UPDATE registos_limpeza SET comentarios_verificacao={ph} WHERE id={ph}", (comentarios_verificacao, rid))
        # Anexos
        files = request.files.getlist("ficheiros")
        if files:
            day_dir = UPLOAD_DIR / datetime.now().strftime("%Y-%m-%d")
            day_dir.mkdir(parents=True, exist_ok=True)
            for f in files:
                if not f or f.filename == "": continue
                if not allowed_file(f.filename): continue
                fname = secure_filename(f.filename)
                path = day_dir / fname
                i = 1
                stem, suf = Path(fname).stem, Path(fname).suffix
                while path.exists():
                    path = day_dir / f"{stem}_{i}{suf}"; i += 1
                f.save(path)
                cur.execute(
                    f"INSERT INTO anexos (registo_id, caminho, tipo) VALUES ({ph}, {ph}, {ph})",
                    (rid, str(path.relative_to(BASE_DIR)), "foto" if suf.lower() != ".pdf" else "pdf")
                )
        conn.commit()
        flash("Observações, comentários e anexos atualizados.", "success")
        return redirect(url_for("registo_detalhe", rid=rid))

    cur.execute(f"""
        SELECT r.*, v.matricula, v.num_frota, p.nome as protocolo, f.nome as funcionario
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        JOIN protocolos p ON p.id = r.protocolo_id
        JOIN funcionarios f ON f.id = r.funcionario_id
        WHERE r.id = {ph}
    """, (rid,))
    registo = cur.fetchone()
    cur.execute(f"SELECT id, caminho, tipo FROM anexos WHERE registo_id={ph} ORDER BY id", (rid,))
    anexos = [dict(r) for r in cur.fetchall()]
    conn.close()
    if not registo:
        flash("Registo não encontrado.", "danger")
        return redirect(url_for("registos"))
    return render_template("registo_detalhe.html", registo=registo, anexos=anexos, signature=APP_SIGNATURE)

@app.route("/viaturas/<int:viatura_id>/editar", methods=["GET", "POST"])
@login_required
@require_perm("viaturas:import")
def editar_viatura(viatura_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    if request.method == "POST":
        regiao = request.form.get("regiao") or None
        verificacao_limpeza = request.form.get("verificacao_limpeza") or None
        # Só admin pode alterar a região
        if session.get("role") == "admin":
            cur.execute(
                f"UPDATE viaturas SET regiao={ph}, verificacao_limpeza={ph} WHERE id={ph}",
                (regiao, verificacao_limpeza, viatura_id)
            )
        else:
            cur.execute(
                f"UPDATE viaturas SET verificacao_limpeza={ph} WHERE id={ph}",
                (verificacao_limpeza, viatura_id)
            )
        conn.commit()
        conn.close()
        flash("Viatura atualizada.", "success")
        return redirect(url_for("viaturas"))
    cur.execute(f"SELECT * FROM viaturas WHERE id={ph}", (viatura_id,))
    viatura = cur.fetchone()
    conn.close()
    if not viatura:
        flash("Viatura não encontrada.", "danger")
        return redirect(url_for("viaturas"))
    return render_template("viatura_form.html", viatura=viatura, user_role=session.get("role"))

@app.route("/viaturas/<int:viatura_id>/apagar", methods=["POST"])
@login_required
@require_perm("viaturas:import")
def apagar_viatura(viatura_id):
    # Apenas gestor ou admin pode apagar
    if session.get("role") not in {"admin", "gestor"}:
        flash("Sem permissões para apagar viaturas.", "danger")
        return redirect(url_for("viaturas"))
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    try:
        cur.execute(f"DELETE FROM viaturas WHERE id={ph}", (viatura_id,))
        conn.commit()
        conn.close()
        flash("Viatura eliminada.", "success")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()
        flash("Não foi possível eliminar a viatura (pode estar em uso).", "danger")
    return redirect(url_for("viaturas"))
# -----------------------------------------------------------------------------
# Importação de viaturas via Dashboard (não-admin)
# -----------------------------------------------------------------------------
@app.route("/viaturas/importar", methods=["GET","POST"])
@login_required
@require_perm("viaturas:import")
def importar_viaturas():
    if request.method == "GET":
        return render_template("admin_import_viaturas.html", signature=APP_SIGNATURE)

    file = request.files.get("ficheiro")
    if not file or file.filename == "":
        flash("Selecione um ficheiro CSV.", "danger")
        return redirect(url_for("importar_viaturas"))

    raw = file.read()

    def _read_csv_text_with_encoding_guess_bytes(raw_bytes: bytes):
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return raw_bytes.decode(enc), enc
            except UnicodeDecodeError:
                continue
        return raw_bytes.decode("latin-1", "replace"), "latin-1"

    text, enc = _read_csv_text_with_encoding_guess_bytes(raw)
    sample = text[:4096]
    delim = ";" if sample.count(";") >= sample.count(",") else ","

    reader = csv.reader(io.StringIO(text), delimiter=delim)
    try:
        header = next(reader)
    except StopIteration:
        flash("CSV vazio.", "danger")
        return redirect(url_for("importar_viaturas"))

    import unicodedata, re as _re
    def _norm(h: str) -> str:
        s = (h or "").strip().lower()
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        s = s.replace("º", "o")
        s = _re.sub(r"[^a-z0-9]+", " ", s).strip()
        aliases = {
            "mat": "matricula", "matricula": "matricula",
            "n viat": "num_frota", "no viat": "num_frota", "n viatura": "num_frota",
            "n frota": "num_frota", "num frota": "num_frota", "numero frota": "num_frota",
            "regiao": "regiao", "operacao": "operacao",
            "marca": "marca", "modelo": "modelo",
            "ativo": "ativo",
            "tipo protocolo": "tipo_protocolo",
            "tipo de protocolo": "tipo_protocolo",
            "protocolo": "tipo_protocolo",
        }
        return aliases.get(s, s)

    nh = [_norm(h) for h in header]
    wanted = ("matricula","num_frota","regiao","operacao","marca","modelo","tipo_protocolo","ativo")
    idx = {k: (nh.index(k) if k in nh else -1) for k in wanted}
    if idx["matricula"] == -1:
        flash("O CSV precisa da coluna 'Mat.' ou 'Matrícula'.", "danger")
        return redirect(url_for("importar_viaturas"))

    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    # garantir colunas
    try:
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'viaturas'")
            vcols = {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(viaturas)")
            vcols = {r["name"] for r in cur.fetchall()}
    except Exception:
        vcols = set()
    for col in ("regiao","operacao","marca","modelo"):
        if col not in vcols:
            try:
                if is_postgres(conn):
                    cur.execute(f"SAVEPOINT add_{col}_vcol")
                cur.execute(f"ALTER TABLE viaturas ADD COLUMN {col} TEXT")
                if is_postgres(conn):
                    cur.execute(f"RELEASE SAVEPOINT add_{col}_vcol")
            except Exception:
                if is_postgres(conn):
                    try:
                        cur.execute(f"ROLLBACK TO SAVEPOINT add_{col}_vcol")
                    except:
                        pass

    def _as_bool(v):
        s = (str(v or "").strip().lower())
        if s in {"1","true","t","y","yes","sim","s"}: return 1
        if s in {"0","false","f","n","no","nao","não"}: return 0
        return 1

    ins = upd = 0
    for row in reader:
        def val(key):
            i = idx[key]
            return (row[i].strip() if i != -1 and i < len(row) else "")

        m = val("matricula")
        if not m:
            continue

        num_frota = val("num_frota") or None
        regiao    = val("regiao") or None
        operacao  = val("operacao") or None
        marca     = val("marca") or None
        modelo    = val("modelo") or None
        ativo     = _as_bool(val("ativo"))
        tipo_protocolo = val("tipo_protocolo") or None

        cur.execute(f"SELECT id FROM viaturas WHERE matricula={ph}", (m,))
        ex = cur.fetchone()
        if ex:
            cur.execute(f"""
                UPDATE viaturas SET 
                  num_frota=COALESCE({ph}, num_frota),
                  regiao=COALESCE({ph}, regiao),
                  operacao=COALESCE({ph}, operacao),
                  marca=COALESCE({ph}, marca),
                  modelo=COALESCE({ph}, modelo),
                  tipo_protocolo=COALESCE({ph}, tipo_protocolo),
                  ativo={ph}
                WHERE id={ph}
            """, (num_frota, regiao, operacao, marca, modelo, tipo_protocolo, ativo, ex["id"]))
            upd += 1
        else:
            cur.execute(f"""
                INSERT INTO viaturas
                  (matricula, num_frota, regiao, operacao, marca, modelo, tipo_protocolo, ativo)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
            """, (m, num_frota, regiao, operacao, marca, modelo, tipo_protocolo, ativo))
            ins += 1

    conn.commit()
    conn.close()
    flash(f"Importação concluída (encoding: {enc}): {ins} inseridas, {upd} atualizadas.", "success")
    return redirect(url_for("viaturas"))

    return render_template("admin_import_viaturas.html", signature=APP_SIGNATURE)

@app.route("/admin/viaturas/upload_csv", methods=["GET","POST"])
def admin_viaturas_upload_csv():
    return redirect(url_for("admin_import_viaturas"))

@app.route("/viaturas/<int:viatura_id>/ativar_desativar", methods=["POST"])
@login_required
@require_perm("viaturas:import")
def ativar_desativar_viatura(viatura_id):
    if session.get("role") not in {"admin", "gestor"}:
        flash("Sem permissões para alterar estado da viatura.", "danger")
        return redirect(url_for("viaturas"))
    conn = get_conn()
    cur = conn.cursor()
    ph = sql_placeholder(conn)
    cur.execute(f"SELECT ativo FROM viaturas WHERE id={ph}", (viatura_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        flash("Viatura não encontrada.", "danger")
        return redirect(url_for("viaturas"))
    novo_estado = 0 if row["ativo"] else 1
    cur.execute(f"UPDATE viaturas SET ativo={ph} WHERE id={ph}", (novo_estado, viatura_id))
    conn.commit()
    conn.close()
    flash(f"Viatura {'ativada' if novo_estado else 'desativada'}.", "success")
    return redirect(url_for("viaturas"))

@app.route("/viaturas/exportar_excel")
@login_required
@require_perm("viaturas:view")
def exportar_viaturas_excel():
    try:
        from pandas_config import PANDAS_AVAILABLE, pd
        
        if not PANDAS_AVAILABLE:
            flash("Funcionalidade Excel não está disponível no momento.", "error")
            return redirect(url_for("viaturas"))
        
        print("DEBUG: Iniciando exportação viaturas Excel")
        conn = get_conn()
        cur = conn.cursor()
        
        # Check if viaturas table has data first
        cur.execute("SELECT COUNT(*) as count FROM viaturas")
        count_result = cur.fetchone()
        viaturas_count = count_result["count"]
        print(f"DEBUG: Total viaturas na tabela: {viaturas_count}")
        
        # Use COALESCE for potentially missing columns
        cur.execute("""
            SELECT 
                id, 
                matricula, 
                COALESCE(num_frota, '') as num_frota, 
                COALESCE(regiao, '') as regiao, 
                COALESCE(operacao, '') as operacao, 
                COALESCE(marca, '') as marca, 
                COALESCE(modelo, '') as modelo, 
                COALESCE(tipo_protocolo, '') as tipo_protocolo, 
                COALESCE(descricao, '') as descricao, 
                COALESCE(filial, '') as filial, 
                ativo, 
                criado_em
            FROM viaturas
            ORDER BY matricula
        """)
        rows = [dict(r) for r in cur.fetchall()]
        print(f"DEBUG: Rows fetched from viaturas: {len(rows)}")
        if rows:
            print(f"DEBUG: First row: {rows[0]}")
        
        conn.close()
        
        if not rows:
            print("DEBUG: No viaturas data - creating empty DataFrame")
            # Create empty DataFrame with proper columns
            df = pd.DataFrame(columns=[
                "id", "matricula", "num_frota", "regiao", "operacao", 
                "marca", "modelo", "tipo_protocolo", "descricao", "filial", "ativo", "criado_em"
            ])
        else:
            df = pd.DataFrame(rows)
            
        print(f"DEBUG: DataFrame shape: {df.shape}")
        print(f"DEBUG: DataFrame columns: {list(df.columns)}")
        if not df.empty:
            print(f"DEBUG: DataFrame head:\n{df.head()}")

        fname = EXPORT_DIR / f"viaturas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(fname, index=False, sheet_name="Viaturas")
        print(f"DEBUG: Excel file created: {fname}")
        return send_file(fname, as_attachment=True)
        
    except Exception as e:
        print(f"❌ ERRO na exportação viaturas Excel: {str(e)}")
        print(f"❌ Tipo do erro: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback completo: {traceback.format_exc()}")
        flash(f"Erro na exportação: {str(e)}", "error")
        return redirect(url_for("viaturas"))
# -----------------------------------------------------------------------------
# Protocolos (listar / editar / novo)
# -----------------------------------------------------------------------------
@app.route("/protocolos")
@login_required
@require_perm("protocolos:view")
def protocolos():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM protocolos ORDER BY nome")
    ps = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("protocolos.html", protocolos=ps, signature=APP_SIGNATURE)

from sqlite3 import IntegrityError

def _passos_to_json(texto: str) -> str:
    passos = [ln.strip() for ln in (texto or "").splitlines() if ln.strip()]
    return json.dumps({"passos": passos}, ensure_ascii=False)

def _json_to_passos_text(passos_json: str) -> str:
    try:
        data = json.loads(passos_json or "{}")
        return "\n".join(data.get("passos", []))
    except Exception:
        return ""

@app.route("/protocolos/novo", methods=["GET", "POST"])
@login_required
@require_perm("protocolos:edit")
def protocolo_novo():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        freq = request.form.get("frequencia_dias")
        ativo = 1 if request.form.get("ativo") == "1" else 0
        passos_txt = request.form.get("passos", "")
        custo_limpeza = request.form.get("custo_limpeza")
        try:
            custo_limpeza = float(custo_limpeza) if custo_limpeza not in (None, "") else 25
        except Exception:
            custo_limpeza = 25

        if not nome:
            flash("Indique o nome do protocolo.", "danger")
            return redirect(url_for("protocolo_novo"))

        try:
            frequencia = int(freq) if (freq or "").strip() != "" else None
            if frequencia is not None and frequencia < 0: raise ValueError
        except ValueError:
            flash("Frequência (dias) inválida.", "danger")
            return redirect(url_for("protocolo_novo"))

        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(fix_sql_placeholders(
                "INSERT INTO protocolos (nome, passos_json, frequencia_dias, ativo, custo_limpeza) VALUES (?,?,?,?,?)"
            ), (nome, _passos_to_json(passos_txt), frequencia, ativo, custo_limpeza))
            conn.commit()
            flash("Protocolo criado com sucesso.", "info")
            return redirect(url_for("protocolos"))
        except IntegrityError:
            flash("Já existe um protocolo com esse nome.", "danger")
            return redirect(url_for("protocolo_novo"))
        finally:
            conn.close()

    return render_template("protocolos_form.html", modo="novo", form={
        "nome": "", "frequencia_dias": "", "passos": "", "ativo": 1, "custo_limpeza": ""
    }, signature=APP_SIGNATURE)

@app.route("/protocolos/<int:pid>/editar", methods=["GET", "POST"])
@login_required
@require_perm("protocolos:edit")
def protocolo_editar(pid: int):
    conn = get_conn()
    cur = conn.cursor()
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        freq = request.form.get("frequencia_dias")
        ativo = 1 if request.form.get("ativo") == "1" else 0
        passos_txt = request.form.get("passos", "")
        custo_limpeza = request.form.get("custo_limpeza")
        try:
            custo_limpeza = float(custo_limpeza) if custo_limpeza not in (None, "") else 25
        except Exception:
            custo_limpeza = 25

        if not nome:
            flash("Indique o nome do protocolo.", "danger")
            conn.close()
            return redirect(url_for("protocolo_editar", pid=pid))

        try:
            frequencia = int(freq) if (freq or "").strip() != "" else None
            if frequencia is not None and frequencia < 0:
                raise ValueError
        except ValueError:
            flash("Frequência (dias) inválida.", "danger")
            conn.close()
            return redirect(url_for("protocolo_editar", pid=pid))

        try:
            cur.execute(fix_sql_placeholders(conn, """
                UPDATE protocolos
                   SET nome=?, passos_json=?, frequencia_dias=?, ativo=?, custo_limpeza=?
                 WHERE id=?
            """), (nome, _passos_to_json(passos_txt), frequencia, ativo, custo_limpeza, pid))
            if cur.rowcount == 0:
                flash("Protocolo não encontrado.", "danger")
            else:
                flash("Protocolo atualizado.", "info")
            conn.commit()
            return redirect(url_for("protocolos"))
        except IntegrityError:
            flash("Já existe um protocolo com esse nome.", "danger")
            return redirect(url_for("protocolo_editar", pid=pid))
        finally:
            conn.close()

    ph = sql_placeholder(conn)
    cur.execute(f"SELECT * FROM protocolos WHERE id={ph}", (pid,))
    p = cur.fetchone()
    conn.close()
    if not p:
        flash("Protocolo não encontrado.", "danger")
        return redirect(url_for("protocolos"))

    form = {
        "nome": p["nome"],
        "frequencia_dias": "" if p["frequencia_dias"] is None else int(p["frequencia_dias"]),
        "passos": _json_to_passos_text(p["passos_json"]),
        "ativo": p["ativo"],
        "custo_limpeza": p["custo_limpeza"] if "custo_limpeza" in p.keys() else ""
    }
    return render_template("protocolos_form.html", modo="editar", pid=pid, form=form, signature=APP_SIGNATURE)
# -----------------------------------------------------------------------------
# --- ADMIN: MIGRAÇÕES -------------------------------------------------------
@app.route("/admin/run_migrations")
def admin_run_migrations():
    if not session.get("is_admin"):
        return redirect(url_for("sem_permissao"))

    conn = get_conn()
    cur = conn.cursor()

    # Helper para ver colunas
    def cols(table):
        if is_postgres(conn):
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table,))
            return {r['column_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
        else:
            return {r[1] for r in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}

    done = []

    # 1) Criar tabela protocolos (se não existir)
    if is_postgres(conn):
        id_field = "id SERIAL PRIMARY KEY"
    else:
        id_field = "id INTEGER PRIMARY KEY AUTOINCREMENT"
        
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS protocolos (
            {id_field},
            nome TEXT NOT NULL UNIQUE,
            ativo INTEGER NOT NULL DEFAULT 1
        );
    """)
    done.append("Tabela 'protocolos' OK")

    # 2) Garantir coluna protocolo_id em viaturas
    viat_cols = cols("viaturas")
    if "protocolo_id" not in viat_cols:
        cur.execute("ALTER TABLE viaturas ADD COLUMN protocolo_id INTEGER NULL;")
        done.append("Coluna 'viaturas.protocolo_id' criada")
        
        # garantir coluna 'conteudo' em protocolos
    prot_cols = cols("protocolos")
    if "conteudo" not in prot_cols:
        cur.execute("ALTER TABLE protocolos ADD COLUMN conteudo TEXT DEFAULT '' ;")
        done.append("Coluna 'protocolos.conteudo' criada")

    # 3) Migrar 'Dop' -> 'Regiao'
    viat_cols = cols("viaturas")
    has_dop = "Dop" in viat_cols
    has_regiao = "Regiao" in viat_cols

    if has_dop and not has_regiao:
        # Tentar rename nativo (SQLite >= 3.25)
        try:
            cur.execute("ALTER TABLE viaturas RENAME COLUMN Dop TO Regiao;")
            done.append("Coluna 'Dop' renomeada para 'Regiao'")
            has_dop, has_regiao = False, True
        except Exception:
            # Fallback seguro: criar Regiao, copiar valores de Dop
            cur.execute("ALTER TABLE viaturas ADD COLUMN Regiao TEXT;")
            cur.execute("""
                UPDATE viaturas SET Regiao = Dop
                WHERE (Regiao IS NULL OR TRIM(Regiao) = '')
                  AND Dop IS NOT NULL AND TRIM(Dop) <> '';
            """)
            done.append("Criada 'Regiao' e copiados valores de 'Dop' (fallback)")
            has_dop, has_regiao = True, True

    elif has_dop and has_regiao:
        # Copiar conteúdos se Regiao estiver vazia
        cur.execute("""
            UPDATE viaturas SET Regiao = Dop
            WHERE (Regiao IS NULL OR TRIM(Regiao) = '')
              AND Dop IS NOT NULL AND TRIM(Dop) <> '';
        """)
        done.append("Sincronizados valores de 'Dop' → 'Regiao'")

        # Tentar remover 'Dop' (SQLite >= 3.35) — opcional
        try:
            cur.execute("ALTER TABLE viaturas DROP COLUMN Dop;")
            done.append("Coluna 'Dop' removida")
        except Exception:
            done.append("Não foi possível remover 'Dop' (ignorado)")

    elif not has_dop and not has_regiao:
        # Nenhuma existe? Criar Regiao vazia para normalizar
        cur.execute("ALTER TABLE viaturas ADD COLUMN Regiao TEXT;")
        done.append("Coluna 'Regiao' criada (não existia 'Dop')")

    conn.commit()

    # Seed opcional de protocolos (só se estiver vazio)
    result = conn.execute("SELECT COUNT(*) FROM protocolos;").fetchone()
    # Handle both SQLite (tuple) and PostgreSQL (dict-like) results
    qtd = result[0] if isinstance(result, tuple) else list(result.values())[0]
    if qtd == 0:
        conn.executemany(fix_sql_placeholders(conn,
            "INSERT INTO protocolos (nome, ativo) VALUES (?,1);"
        ), [("Interior Básico",), ("Exterior Completo",), ("Desinfeção",)])
        conn.commit()
        done.append("Protocolos base inseridos")

    flash("Migrações concluídas: " + " | ".join(done), "success")
    return redirect(url_for("admin_protocolos"))


# stos (lista / novo / anexos)
# -----------------------------------------------------------------------------


@app.route("/solicitar_autorizacao/<int:viatura_id>", methods=["POST"])
@login_required
def solicitar_autorizacao(viatura_id):
    funcionario_id = session.get("user_id")
    conn = get_conn()
    cur = conn.cursor()

    # Obter região e número de frota da viatura
    sql = "SELECT regiao, num_frota FROM viaturas WHERE id=?"
    sql = fix_sql_placeholders(conn, sql)
    cur.execute(sql, (viatura_id,))
    row = cur.fetchone()
    regiao = (row["regiao"] or "").strip() if row and row["regiao"] else None
    num_frota = row["num_frota"] if row else None

    destinatario_id = None
    
    # Primeiro tenta encontrar gestor na mesma região
    if regiao:
        sql = "SELECT id FROM funcionarios WHERE role='gestor' AND ativo=1 AND regiao=?"
        sql = fix_sql_placeholders(conn, sql)
        cur.execute(sql, (regiao,))
        gestor = cur.fetchone()
        if gestor:
            destinatario_id = gestor["id"]
    
    # Se não encontrou gestor na região, procura qualquer gestor ativo
    if not destinatario_id:
        sql = "SELECT id FROM funcionarios WHERE role='gestor' AND ativo=1"
        sql = fix_sql_placeholders(conn, sql)
        cur.execute(sql)
        gestor = cur.fetchone()
        if gestor:
            destinatario_id = gestor["id"]
    
    # Se ainda não encontrou, tenta administradores
    if not destinatario_id:
        sql = "SELECT id FROM funcionarios WHERE role='admin' AND ativo=1"
        sql = fix_sql_placeholders(conn, sql)
        cur.execute(sql)
        admin = cur.fetchone()
        if admin:
            destinatario_id = admin["id"]

    if not destinatario_id:
        flash("Não foi possível identificar um gestor ou administrador para autorizar esta solicitação. Contacte o administrador do sistema.", "danger")
        conn.close()
        return redirect(url_for("novo_registo"))

    # Verifica se já existe pedido pendente hoje
    today_condition = sql_today_condition(conn, "data_pedido")
    cur.execute(fix_sql_placeholders(conn, f"""
        SELECT 1 FROM pedidos_autorizacao
        WHERE viatura_id=? AND funcionario_id=? AND {today_condition} AND validado=0
    """), (viatura_id, funcionario_id))
    if not cur.fetchone():
        cur.execute(fix_sql_placeholders(conn,
            "INSERT INTO pedidos_autorizacao (viatura_id, num_frota, funcionario_id, destinatario_id) VALUES (?,?,?,?)"
        ), (viatura_id, num_frota, funcionario_id, destinatario_id))
        conn.commit()
        flash("Pedido de autorização enviado ao gestor da região.", "info")
    else:
        flash("Já existe um pedido pendente para esta viatura hoje.", "warning")
    conn.close()
    return redirect(url_for("novo_registo"))

@app.route("/registos/novo", methods=["GET", "POST"])
@login_required
def novo_registo():
    if not user_can("registos:create"):
        flash("Sem permissões para criar registos.", "danger")
        return redirect(url_for("sem_permissao"))

    conn = get_conn()
    cur = conn.cursor()

    # Obter a região do operador (se existir)
    user_id = session.get("user_id")
    user_role = session.get("role")
    regiao_operador = None
    if user_role in ("operador", "gestor"):
        sql = "SELECT regiao FROM funcionarios WHERE id=?"
        sql = fix_sql_placeholders(conn, sql)
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        regiao_operador = (row["regiao"] or "").strip() if row and row["regiao"] else None

    # GET: mostra o formulário
    if request.method == "GET":
        # Filtrar viaturas pela região do operador, se existir
        viaturas_sql = "SELECT id, matricula, descricao, num_frota FROM viaturas WHERE ativo=1"
        viaturas_params = []
        if regiao_operador:
            viaturas_sql += " AND regiao = ?"
            viaturas_params.append(regiao_operador)
        viaturas_sql += " ORDER BY matricula"
        
        # Fix parameter placeholders for PostgreSQL
        viaturas_sql = fix_sql_placeholders(conn, viaturas_sql)
        cur.execute(viaturas_sql, viaturas_params)
        vs = [dict(row) for row in cur.fetchall()]

        cur.execute("SELECT id, nome, passos_json, frequencia_dias FROM protocolos WHERE ativo=1 ORDER BY nome")
        ps = [dict(row) for row in cur.fetchall()]
        today_condition_limpeza = sql_today_condition(conn, "data_hora")
        cur.execute(f"SELECT DISTINCT viatura_id FROM registos_limpeza WHERE {today_condition_limpeza}")
        limpas_hoje = {r["viatura_id"] for r in cur.fetchall()}
        cur.execute(fix_sql_placeholders(conn, "SELECT id, nome FROM funcionarios WHERE role='gestor' AND ativo=1"))
        gestores = [dict(row) for row in cur.fetchall()]
        # Viaturas autorizadas a limpeza extra hoje
        today_condition_pedido = sql_today_condition(conn, "data_pedido")
        cur.execute(f"""
            SELECT viatura_id FROM pedidos_autorizacao
            WHERE validado=1 AND {today_condition_pedido}
        """)
        viaturas_autorizadas = {r["viatura_id"] for r in cur.fetchall()}
        conn.close()
        limpa_hoje_map = {v["id"]: (v["id"] in limpas_hoje) for v in vs}
        return render_template(
            "novo_registo.html",
            viaturas=vs,
            protocolos=ps,
            limpa_hoje_map=limpa_hoje_map,
            signature=APP_SIGNATURE,
            gestores=gestores,
            viaturas_autorizadas=viaturas_autorizadas
        )

    # POST: processa o formulário
    viatura_id = request.form.get("viatura_id")
    protocolo_id = request.form.get("protocolo_id")
    estado = request.form.get("estado", "concluido")
    observacoes = (request.form.get("observacoes") or "").strip()
    local = (request.form.get("local") or "").strip()
    hora_inicio = datetime.now().strftime("%H:%M")
    funcionario_id = session.get("user_id")

    if not (viatura_id and protocolo_id):
        flash("Selecione viatura e protocolo.", "danger")
        conn.close()
        return redirect(url_for("novo_registo"))
    
    # Verifica se já foi limpa hoje
    today_condition = sql_today_condition(conn, "data_hora")
    sql = f"""
        SELECT COUNT(*) FROM registos_limpeza
        WHERE viatura_id = ? AND {today_condition}
    """
    sql = fix_sql_placeholders(conn, sql)
    cur.execute(sql, (viatura_id,))
    result = cur.fetchone()
    # Handle both SQLite (tuple) and PostgreSQL (dict-like) results
    if result is None:
        count_value = 0
    elif hasattr(result, 'keys'):  # PostgreSQL dict-like result
        count_value = list(result.values())[0]
    else:  # SQLite tuple result
        count_value = result[0]
    ja_limpo_hoje = count_value > 0

    pedido_autorizado = pedido_autorizado_hoje(viatura_id, funcionario_id)
    extra_autorizada = 1 if pedido_autorizado else 0
    responsavel_autorizacao = None
    if pedido_autorizado:
        today_condition = sql_today_condition(conn, "pa.data_pedido")
        cur.execute(fix_sql_placeholders(conn, f"""
            SELECT f.nome
            FROM pedidos_autorizacao pa
            JOIN funcionarios f ON f.id = pa.destinatario_id
            WHERE pa.viatura_id=? AND pa.funcionario_id=? AND pa.validado=1 AND {today_condition}
            ORDER BY pa.data_pedido DESC LIMIT 1
        """), (viatura_id, funcionario_id))
        row = cur.fetchone()
        responsavel_autorizacao = row["nome"] if row else None

    # validação de horas
    def _is_hhmm(s):
        import re
        return bool(re.fullmatch(r"[0-2]\d:[0-5]\d", s))
    if hora_inicio and not _is_hhmm(hora_inicio):
        flash("Hora de início inválida (use HH:MM).", "danger")
        conn.close()
        return redirect(url_for("novo_registo"))
    
    # Se já foi limpa hoje e não tem autorização, pede autorização
    if ja_limpo_hoje and not pedido_autorizado:
        flash("Viatura já efetuou limpeza hoje, solicite autorização para limpeza extra.", "warning")
        cur.execute("SELECT id, matricula, descricao, num_frota FROM viaturas WHERE ativo=1 ORDER BY matricula")
        vs = [dict(row) for row in cur.fetchall()]
        cur.execute("SELECT id, nome FROM protocolos WHERE ativo=1 ORDER BY nome")
        ps = [dict(row) for row in cur.fetchall()]
        today_condition_limpeza = sql_today_condition(conn, "data_hora")
        cur.execute(f"SELECT DISTINCT viatura_id FROM registos_limpeza WHERE {today_condition_limpeza}")
        limpas_hoje = {r["viatura_id"] for r in cur.fetchall()}
        cur.execute(fix_sql_placeholders(conn, "SELECT id, nome FROM funcionarios WHERE role='gestor' AND ativo=1"))
        gestores = [dict(row) for row in cur.fetchall()]
        today_condition_pedido = sql_today_condition(conn, "data_pedido")
        cur.execute(f"""
            SELECT viatura_id FROM pedidos_autorizacao
            WHERE validado=1 AND {today_condition_pedido}
        """)
        viaturas_autorizadas = {r["viatura_id"] for r in cur.fetchall()}
        conn.close()
        limpa_hoje_map = {v["id"]: (v["id"] in limpas_hoje) for v in vs}
        return render_template(
            "novo_registo.html",
            viaturas=vs,
            protocolos=ps,
            limpa_hoje_map=limpa_hoje_map,
            signature=APP_SIGNATURE,
            mostrar_botao_autorizacao=True,
            viatura_id=viatura_id,
            gestores=gestores,
            viaturas_autorizadas=viaturas_autorizadas
        )

    # inserir registo
    # Obter a região atual da viatura
    sql = "SELECT regiao FROM viaturas WHERE id=?"
    sql = fix_sql_placeholders(conn, sql)
    cur.execute(sql, (viatura_id,))
    row = cur.fetchone()
    regiao_viatura = (row["regiao"] or "") if row else None

    sql = """
        INSERT INTO registos_limpeza
        (viatura_id, protocolo_id, funcionario_id, data_hora, estado, observacoes,
        local, hora_inicio, hora_fim, extra_autorizada, responsavel_autorizacao, regiao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    sql = fix_sql_placeholders(conn, sql)
    cur.execute(sql, (
        viatura_id, protocolo_id, funcionario_id,
        datetime.now().isoformat(timespec="seconds"),
        estado, observacoes, (local or None),
        (hora_inicio or None), None,
        extra_autorizada, responsavel_autorizacao,
        regiao_viatura
    ))

    registo_id = cur.lastrowid
    # Preencher tipo_protocolo na viatura
    cur.execute(fix_sql_placeholders(conn, """
        UPDATE viaturas
        SET tipo_protocolo = (
            SELECT nome FROM protocolos WHERE id = ?
        )
        WHERE id = ?
    """), (protocolo_id, viatura_id))

    # anexos
    files = request.files.getlist("ficheiros")
    if files:
        day_dir = UPLOAD_DIR / datetime.now().strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            if not f or f.filename == "": continue
            if not allowed_file(f.filename): continue
            fname = secure_filename(f.filename)
            path = day_dir / fname
            i = 1
            stem, suf = Path(fname).stem, Path(fname).suffix
            while path.exists():
                path = day_dir / f"{stem}_{i}{suf}"; i += 1
            f.save(path)
            cur.execute(fix_sql_placeholders(conn,
                "INSERT INTO anexos (registo_id, caminho, tipo) VALUES (?, ?, ?)"
            ), (registo_id, str(path.relative_to(BASE_DIR)), "foto" if suf.lower() != ".pdf" else "pdf"))

    if pedido_autorizado:
        today_condition = sql_today_condition(conn, "data_pedido")
        cur.execute(fix_sql_placeholders(conn, f"""
            DELETE FROM pedidos_autorizacao
            WHERE viatura_id=? AND funcionario_id=? AND validado=1 AND {today_condition}
        """), (viatura_id, funcionario_id))
    conn.commit()
    conn.close()
    flash(f"Registo #{registo_id} criado com sucesso.", "info")
    return redirect(url_for("registos"))    

def pedido_autorizado_hoje(viatura_id, funcionario_id):
    conn = get_conn()
    cur = conn.cursor()
    today_condition = sql_today_condition(conn, "data_pedido")
    sql = f"""
        SELECT 1 FROM pedidos_autorizacao
         WHERE viatura_id=? AND funcionario_id=? AND validado=1 AND {today_condition}
    """
    sql = fix_sql_placeholders(conn, sql)
    cur.execute(sql, (viatura_id, funcionario_id))
    res = cur.fetchone()
    conn.close()
    return bool(res)

@app.route("/registos/em_progresso")
@login_required
@require_perm("registos:view")
def registos_em_progresso():
    conn = get_conn()
    cur = conn.cursor()
    query = """
        SELECT r.id as registo_id, r.data_hora, v.matricula, v.num_frota,
               p.nome as protocolo, f.nome as funcionario, r.local, r.hora_inicio
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        JOIN protocolos p ON p.id = r.protocolo_id
        JOIN funcionarios f ON f.id = r.funcionario_id
        WHERE r.estado='em_progresso' AND (r.hora_fim IS NULL OR r.hora_fim='')
        ORDER BY datetime(r.data_hora) DESC, r.id DESC
    """
    cur.execute(fix_datetime_in_sql(conn, query))
    registos = [dict(row) for row in cur.fetchall()]
    conn.close()
    return render_template("registos_em_progresso.html", registos=registos, signature=APP_SIGNATURE)

@app.route("/registos/<int:registo_id>/finalizar", methods=["POST"])
@login_required
@require_perm("registos:edit")
def finalizar_registo(registo_id):
    hora_fim = datetime.now().strftime("%H:%M")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(fix_sql_placeholders(conn, """
        UPDATE registos_limpeza
        SET hora_fim=?, estado='concluido'
        WHERE id=?
    """), (hora_fim, registo_id))
    conn.commit()
    conn.close()
    flash("Registo finalizado.", "success")
    return redirect(url_for("registos_em_progresso"))

@app.route("/validar_limpeza/<int:viatura_id>", methods=["POST"])
@login_required
@require_perm("dashboard:view")
def validar_limpeza(viatura_id):
    conn = get_conn()
    cur = conn.cursor()
    sql = "UPDATE viaturas SET limpeza_validada=1 WHERE id=?"
    sql = fix_sql_placeholders(conn, sql)
    cur.execute(sql, (viatura_id,))
    conn.commit()
    conn.close()
    flash("Limpeza extra autorizada! Operador notificado.", "success")
    return redirect(url_for("home"))

@app.route("/registos/<int:rid>/apagar", methods=["POST"])
@login_required
@require_perm("registos:delete")
def registo_apagar(rid: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(fix_sql_placeholders(conn, "DELETE FROM registos_limpeza WHERE id=?"), (rid,))
        conn.commit()
        conn.close()
        flash("Registo eliminado.", "success")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()
        flash("Não foi possível eliminar o registo.", "danger")
    return redirect(url_for("registos"))

@app.route("/registos/<int:registo_id>/anexos")
@login_required
@require_perm("registos:view")
def ver_anexos(registo_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(fix_sql_placeholders(conn, "SELECT id, caminho, tipo FROM anexos WHERE registo_id=? ORDER BY id"), (registo_id,))
    anex = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("anexos.html", registo_id=registo_id, anexos=anex, signature=APP_SIGNATURE)

@app.route("/anexos/<int:anexo_id>")
@login_required
@require_perm("registos:view")
def download_anexo(anexo_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(fix_sql_placeholders(conn, "SELECT caminho FROM anexos WHERE id=?"), (anexo_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        abort(404)
    path = BASE_DIR / row["caminho"]
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True)

@app.route("/exportar_contabilidade_excel")
@login_required
def exportar_contabilidade_excel():
    try:
        from pandas_config import PANDAS_AVAILABLE, pd
        
        if not PANDAS_AVAILABLE:
            print("DEBUG: Pandas não está disponível")
            flash("Funcionalidade Excel não está disponível no momento.", "error")
            return redirect(url_for("contabilidade"))
            
        print("DEBUG: Iniciando exportação contabilidade Excel")
        
        mes = request.args.get("mes")
        protocolo_id = request.args.get("protocolo_id")
        regiao = request.args.get("regiao")
        empresa = request.args.get("empresa")

        print(f"DEBUG: Parâmetros - mes: {mes}, protocolo_id: {protocolo_id}, regiao: {regiao}, empresa: {empresa}")

        # Só admin pode exportar todas as regiões
        user_id = session.get("user_id")
        user_role = session.get("role")
        regiao_user = None
        if user_role in ("gestor",):
            conn = get_conn()
            cur = conn.cursor()
            placeholder = sql_placeholder(conn)
            cur.execute(f"SELECT regiao FROM funcionarios WHERE id={placeholder}", (user_id,))
            row = cur.fetchone()
            regiao_user = (row["regiao"] or "").strip() if row and row["regiao"] else None
            conn.close()
            regiao = regiao_user  # força filtro pela região do gestor
            print(f"DEBUG: Gestor região limitada a: {regiao}")

        conn = get_conn()
        cur = conn.cursor()
        
        # Check database type for debugging
        is_pg = is_postgres(conn)
        print(f"DEBUG: Using PostgreSQL: {is_pg}")
        
        date_sql = sql_date(conn, "r.data_hora") 
        placeholder = sql_placeholder(conn)
        
        # Build query with fallbacks for potentially missing columns
        sql = f"""
            SELECT 
                {date_sql} as data, 
                v.matricula, 
                COALESCE(v.num_frota, '') as num_frota, 
                COALESCE(v.regiao, '') as regiao, 
                p.nome as protocolo, 
                COALESCE(p.custo_limpeza, 0.0) as custo_limpeza, 
                f.nome as funcionario, 
                COALESCE(f.empresa, '') as empresa, 
                COALESCE(r.local, '') as local
            FROM registos_limpeza r
            JOIN viaturas v ON v.id = r.viatura_id
            JOIN protocolos p ON p.id = r.protocolo_id
            JOIN funcionarios f ON f.id = r.funcionario_id
            WHERE 1=1
        """
        params = []
        
        if mes:
            month_format = sql_month_format(conn, "r.data_hora")
            sql += f" AND {month_format} = ?"
            params.append(mes)
            
        if protocolo_id:
            sql += " AND p.id = ?"
            params.append(protocolo_id)
            
        if regiao:
            sql += " AND v.regiao = ?"
            params.append(regiao)
            
        if empresa:
            sql += " AND f.empresa = ?"
            params.append(empresa) 

        # Use sql_date helper for cross-database compatibility
        order_date_sql = sql_date(conn, "r.data_hora")
        sql += f" ORDER BY v.regiao ASC, {order_date_sql} ASC, r.id ASC"
        
        # Fix SQL placeholders for the database type before using with pandas
        sql = fix_sql_placeholders(conn, sql)
        
        print(f"DEBUG: SQL query for contabilidade export: {sql}")
        print(f"DEBUG: Parameters: {params}")
        
        # Execute query manually to avoid pandas/psycopg2 compatibility issues
        try:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            print(f"DEBUG: Manual query returned {len(rows)} rows")
            
            if rows:
                print(f"DEBUG: First row data: {dict(rows[0])}")
                # Convert rows to list of dictionaries
                data_rows = [dict(row) for row in rows]
                df = pd.DataFrame(data_rows)
            else:
                print("DEBUG: Query returned no rows - checking if tables have data...")
                # Check if tables have any data
                cur.execute("SELECT COUNT(*) as count FROM registos_limpeza")
                registos_count = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM viaturas")
                viaturas_count = cur.fetchone()["count"] 
                cur.execute("SELECT COUNT(*) as count FROM protocolos")
                protocolos_count = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM funcionarios")
                funcionarios_count = cur.fetchone()["count"]
                print(f"DEBUG: Table counts - registos: {registos_count}, viaturas: {viaturas_count}, protocolos: {protocolos_count}, funcionarios: {funcionarios_count}")
                
                # Create empty DataFrame with correct column structure
                df = pd.DataFrame(columns=[
                    'data', 'matricula', 'num_frota', 'regiao', 'protocolo', 
                    'custo_limpeza', 'funcionario', 'empresa', 'local'
                ])
                
        except Exception as manual_e:
            print(f"DEBUG: Manual query failed: {manual_e}")
            conn.close()
            raise manual_e
        print(f"DEBUG: DataFrame shape: {df.shape}")
        if not df.empty:
            print(f"DEBUG: DataFrame columns: {list(df.columns)}")
            print(f"DEBUG: First few rows:\n{df.head()}")
        conn.close()

        # Gerar id_regiao sequencial por região (do mais antigo para o mais recente)
        if not df.empty:
            print("DEBUG: Processando DataFrame...")
            df = df.sort_values(["regiao", "data"])
            df["id_regiao"] = (
                df.groupby("regiao").cumcount() + 1
            ).apply(lambda x: f"{x:03d}")
            df["id_regiao"] = df["regiao"].fillna("—") + "-" + df["id_regiao"]
            # Ordena para exportar do mais recente para o mais antigo
            df = df.sort_values(["data"], ascending=[False])
            print("DEBUG: DataFrame processado com sucesso")
            
            cols = [
                "id_regiao", "data", "matricula", "num_frota", "regiao", "protocolo",
                "custo_limpeza", "funcionario", "empresa", "local"
            ]
            df = df[cols]
        else:
            print("DEBUG: DataFrame vazio - criando DataFrame com colunas vazias")
            # Criar DataFrame vazio com as colunas corretas
            cols = [
                "id_regiao", "data", "matricula", "num_frota", "regiao", "protocolo",
                "custo_limpeza", "funcionario", "empresa", "local"
            ]
            df = pd.DataFrame(columns=cols)

        print("DEBUG: Criando arquivo Excel...")
        fname = EXPORT_DIR / f"contabilidade_{mes or 'todos'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(fname, index=False, sheet_name="Contabilidade")
        print(f"DEBUG: Arquivo criado: {fname}")
        
        return send_file(fname, as_attachment=True)
        
    except Exception as e:
        print(f"❌ ERRO na exportação contabilidade Excel: {str(e)}")
        print(f"❌ Tipo do erro: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback completo: {traceback.format_exc()}")
        flash(f"Erro na exportação: {str(e)}", "error")
        return redirect(url_for("contabilidade"))
# -----------------------------------------------------------------------------
# Administração (utilizadores, perfis, import de viaturas)
# -----------------------------------------------------------------------------
@app.route("/admin")
@login_required
def admin_panel():
    # Bloquear gestores
    if session.get("role") == "gestor":
        flash("Sem permissões para Administração.", "danger")
        return redirect(url_for("sem_permissao"))
    if not (user_can("users:manage") or user_can("roles:manage") or user_can("viaturas:import")):
        flash("Sem permissões para Administração.", "danger")
        return redirect(url_for("sem_permissao"))
    return render_template("admin.html", signature=APP_SIGNATURE)

@app.route("/admin/users")
@login_required
@require_perm("users:manage")
def admin_users():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, username, nome, role, regiao, ativo, criado_em FROM funcionarios ORDER BY username")
    users = [dict(r) for r in cur.fetchall()]
    conn.close()
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT name FROM roles ORDER BY name")
    db_roles = [r["name"] for r in cur.fetchall()]
    conn.close()
    base_roles = sorted(PERMISSIONS.keys())
    roles = sorted(set(base_roles + db_roles))
    return render_template("admin_users.html", users=users, roles=roles, signature=APP_SIGNATURE)


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@require_perm("users:manage")
def admin_user_toggle(user_id):
    me = session.get("user_id")
    if user_id == me:
        flash("Não pode desativar a sua própria conta.", "warning")
        return redirect(url_for("admin_users"))
    conn = get_conn(); cur = conn.cursor()
    cur.execute(fix_sql_placeholders(conn, "SELECT role, ativo FROM funcionarios WHERE id=?"), (user_id,))
    u = cur.fetchone()
    if not u:
        conn.close(); flash("Utilizador não encontrado.", "danger"); return redirect(url_for("admin_users"))
    if (u["role"] or "").lower() == "admin" and u["ativo"] == 1:
        placeholder = sql_placeholder(conn)
        cur.execute(f"SELECT COUNT(*) AS n FROM funcionarios WHERE LOWER(role)='admin' AND ativo=1 AND id<>{placeholder}", (user_id,))
        if cur.fetchone()["n"] == 0:
            conn.close(); flash("Não pode desativar o último admin ativo.", "danger"); return redirect(url_for("admin_users"))
    # Use the helper function to handle parameter placeholders correctly
    sql = "UPDATE funcionarios SET ativo = CASE WHEN ativo=1 THEN 0 ELSE 1 END WHERE id=?"
    sql = fix_sql_placeholders(conn, sql)
    cur.execute(sql, (user_id,))
    conn.commit(); conn.close()
    flash("Estado do utilizador atualizado.", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/reset_password", methods=["GET", "POST"])
@login_required
@require_perm("users:manage")
def admin_user_reset_password(user_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(fix_sql_placeholders(conn, "SELECT id, username, nome FROM funcionarios WHERE id=?"), (user_id,))
    user = cur.fetchone()
    if not user:
        conn.close()
        flash("Utilizador não encontrado.", "danger")
        return redirect(url_for("admin_users"))
    if request.method == "POST":
        new_password = request.form.get("new_password") or ""
        if not new_password:
            flash("A nova password é obrigatória.", "danger")
        else:
            # Use the helper function to handle parameter placeholders correctly
            sql = "UPDATE funcionarios SET password=? WHERE id=?"
            sql = fix_sql_placeholders(conn, sql)
            cur.execute(sql, (generate_password_hash(new_password), user_id))
            conn.commit()
            flash("Password redefinida com sucesso.", "success")
            conn.close()
            return redirect(url_for("admin_users"))
    conn.close()
    return render_template("admin_user_reset_password.html", user=user, signature=APP_SIGNATURE)

@app.route("/admin/users/novo", methods=["GET", "POST"])
@login_required
@require_perm("users:manage")
def admin_user_new():
    roles = sorted(PERMISSIONS.keys())
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip()
        role = normalize_role(request.form.get("role"))
        ativo = 1 if request.form.get("ativo") == "1" else 0
        regiao = (request.form.get("regiao") or "").strip()
        empresa = (request.form.get("empresa") or "").strip() if role == "operador" else None
        password = request.form.get("password") or ""
        if not username or not password:
            flash("Username e password são obrigatórios.", "danger")
            return redirect(url_for("admin_user_new"))
        conn = get_conn(); cur = conn.cursor()
        try:
            # Use the helper function to handle parameter placeholders correctly
            sql = "INSERT INTO funcionarios (username, nome, role, ativo, regiao, password, email, empresa) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            sql = fix_sql_placeholders(conn, sql)
            
            cur.execute(
                sql,
                (username, nome or username, role, ativo, regiao, generate_password_hash(password), email, empresa)
            )
            conn.commit(); flash("Utilizador criado.", "success")
            return redirect(url_for("admin_users"))
        except Exception as e:
            # Handle both SQLite IntegrityError and PostgreSQL IntegrityError
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg or "already exists" in error_msg:
                flash("Username já existe.", "danger")
            else:
                flash(f"Erro ao criar utilizador: {str(e)}", "danger")
            return redirect(url_for("admin_user_new"))
        finally:
            conn.close()
    return render_template("admin_user_form.html", roles=roles, signature=APP_SIGNATURE)

@app.route("/admin/users/<int:user_id>/editar", methods=["GET","POST"])
@login_required
@require_perm("users:manage")
def admin_user_edit(user_id):
    conn = get_conn(); cur = conn.cursor()
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip()
        role = normalize_role(request.form.get("role"))
        ativo = 1 if request.form.get("ativo") == "1" else 0
        regiao = (request.form.get("regiao") or "").strip()
        empresa = (request.form.get("empresa") or "").strip() if role == "operador" else None
        if not username:
            flash("Username é obrigatório.", "danger"); conn.close()
            return redirect(url_for("admin_user_edit", user_id=user_id))
        try:
            # Use the helper function to handle parameter placeholders correctly
            sql = "UPDATE funcionarios SET username=?, nome=?, role=?, ativo=?, regiao=?, email=?, empresa=? WHERE id=?"
            sql = fix_sql_placeholders(conn, sql)
            
            cur.execute(
                sql,
                (username, nome or username, role, ativo, regiao, email, empresa, user_id)
            )
            conn.commit(); flash("Utilizador atualizado.", "info")
            return redirect(url_for("admin_users"))
        except Exception as e:
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg or "already exists" in error_msg:
                flash("Username já existe.", "danger")
            else:
                flash(f"Erro ao atualizar utilizador: {str(e)}", "danger")
            conn.close()
            return redirect(url_for("admin_user_edit", user_id=user_id))
    placeholder = sql_placeholder(conn)
    cur.execute(f"SELECT * FROM funcionarios WHERE id={placeholder}", (user_id,))
    u = cur.fetchone(); conn.close()
    if not u:
        flash("Utilizador não encontrado.", "danger")
        return redirect(url_for("admin_users"))
    roles = sorted(PERMISSIONS.keys())
    return render_template("admin_user_form.html", roles=roles, user=u, signature=APP_SIGNATURE)

@app.route("/admin/roles")
@login_required
@require_perm("roles:manage")
def admin_roles():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT name FROM roles ORDER BY name")
    db_roles = [r["name"] for r in cur.fetchall()]
    conn.close()
    base_roles = sorted(PERMISSIONS.keys())
    return render_template("admin_roles.html", base_roles=base_roles, db_roles=db_roles, signature=APP_SIGNATURE)

@app.route("/admin/roles/novo", methods=["GET","POST"])
@login_required
@require_perm("roles:manage")
def admin_role_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip().lower()
        perms = request.form.getlist("perms")
        if not name:
            flash("Nome do perfil obrigatório.", "danger"); return redirect(url_for("admin_role_new"))
        conn = get_conn(); cur = conn.cursor()
        try:
            cur.execute(fix_sql_placeholders(conn, "INSERT INTO roles (name) VALUES (?)"), (name,))
            role_id = cur.lastrowid
            cur.executemany(fix_sql_placeholders(conn, "INSERT INTO role_permissions (role_id, perm) VALUES (?,?)"), [(role_id, p) for p in perms])
            conn.commit(); flash("Perfil criado.", "info")
            return redirect(url_for("admin_roles"))
        except sqlite3.IntegrityError:
            flash("Esse perfil já existe.", "danger")
            return redirect(url_for("admin_role_new"))
        finally:
            conn.close()
    return render_template("admin_role_form.html", perms=KNOWN_PERMS, signature=APP_SIGNATURE)

# ...existing code...
from pandas_config import PANDAS_AVAILABLE, pd
import io
@app.route("/admin/alterar_regiao_viatura", methods=["GET", "POST"])
@login_required
def admin_alterar_regiao_viatura():
    if session.get("role") != "admin":
        flash("Apenas administradores podem alterar a região de viaturas.", "danger")
        return redirect(url_for("admin_panel"))

    conn = get_conn(); cur = conn.cursor()
    if request.method == "POST":
        viatura_id = request.form.get("viatura_id")
        nova_regiao = request.form.get("nova_regiao", "").strip()
        if viatura_id and nova_regiao:
            cur.execute(fix_sql_placeholders(conn, "UPDATE viaturas SET regiao=? WHERE id=?"), (nova_regiao, viatura_id))
            conn.commit()
            flash("Região da viatura atualizada.", "success")
        else:
            flash("Selecione uma viatura e indique a nova região.", "danger")
        conn.close()
        return redirect(url_for("admin_alterar_regiao_viatura"))

    cur.execute("SELECT id, matricula, regiao FROM viaturas ORDER BY matricula")
    viaturas = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("admin_alterar_regiao_viatura.html", viaturas=viaturas, signature=APP_SIGNATURE)
# ...existing code...
@app.route("/admin/import/viaturas", methods=["GET","POST"])
@login_required
@require_perm("viaturas:import")
def admin_import_viaturas():
    def _str(v):
        return str(v).strip() if v is not None else None

    if request.method == "POST":
        file = request.files.get("ficheiro")
        if not file or file.filename == "":
            flash("Selecione um ficheiro CSV ou Excel.", "danger")
            return redirect(url_for("admin_import_viaturas"))
        filename = file.filename.lower()
        if filename.endswith(".xlsx"):
            df = pd.read_excel(file)
            rows = df.to_dict(orient="records")
            fieldnames = [c.lower() for c in df.columns]
        elif filename.endswith(".csv"):
            data = file.read().decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(data))
            rows = list(reader)
            fieldnames = [h.lower() for h in reader.fieldnames or []]
        else:
            flash("Ficheiro deve ser .csv ou .xlsx", "danger")
            return redirect(url_for("admin_import_viaturas"))

        required = {"matricula"}
        if not fieldnames or not required.issubset(set(fieldnames)):
            flash("Ficheiro precisa, no mínimo, da coluna 'matricula'.", "danger")
            return redirect(url_for("admin_import_viaturas"))

        conn = get_conn(); cur = conn.cursor()
        ins, upd = 0, 0
        for row in rows:
            matricula = _str(row.get("matricula") or row.get("MATRICULA"))
            if not matricula: continue
            num_frota = _str(row.get("num_frota") or row.get("NUM_FROTA"))
            regiao = _str(row.get("regiao") or row.get("REGIAO"))
            operacao = _str(row.get("operacao") or row.get("OPERACAO"))
            marca = _str(row.get("marca") or row.get("MARCA"))
            modelo = _str(row.get("modelo") or row.get("MODELO"))
            tipo_protocolo = _str(row.get("tipo_protocolo") or row.get("TIPO_PROTOCOLO"))
            descricao = _str(row.get("descricao") or row.get("DESCRICAO"))
            filial = _str(row.get("filial") or row.get("FILIAL"))
            ativo = row.get("ativo") or row.get("ATIVO")
            ativo = 1 if str(ativo).strip().lower() in {"1","true","sim","yes","y"} else 1  # default 1

            cur.execute(fix_sql_placeholders(conn, "SELECT id FROM viaturas WHERE matricula=?"), (matricula,))
            ex = cur.fetchone()
            if ex:
                cur.execute("""UPDATE viaturas
                               SET num_frota=?, regiao=?, operacao=?, marca=?, modelo=?, tipo_protocolo=?, descricao=?, filial=?, ativo=?
                               WHERE id=?""",
                            (num_frota, regiao, operacao, marca, modelo, tipo_protocolo, descricao, filial, ativo, ex["id"]))
                upd += 1
            else:
                cur.execute(fix_sql_placeholders(conn, """INSERT INTO viaturas (matricula, num_frota, regiao, operacao, marca, modelo, tipo_protocolo, descricao, filial, ativo)
                               VALUES (?,?,?,?,?,?,?,?,?,?)"""),
                            (matricula, num_frota, regiao, operacao, marca, modelo, tipo_protocolo, descricao, filial, ativo))
                ins += 1
        conn.commit(); conn.close()
        flash(f"Importação concluída: {ins} inseridas, {upd} atualizadas.", "info")
        return redirect(url_for("viaturas"))

    return render_template("admin_import_viaturas.html", signature=APP_SIGNATURE)


# --- UTILIZADORES: LISTAR & APAGAR -----------------------------------------
@app.route("/admin/utilizadores")
def admin_utilizadores():
    return redirect(url_for("admin_users"))

@app.route("/admin/utilizadores/delete/<int:user_id>", methods=["POST"])
def admin_utilizadores_delete(user_id):
    if not session.get("is_admin"):
        return redirect(url_for("sem_permissao"))
    conn = get_conn()
    conn.execute(fix_sql_placeholders(conn, "DELETE FROM utilizadores WHERE id = ?;"), (user_id,))
    conn.commit()
    flash("Utilizador eliminado com sucesso.", "success")
    return redirect(url_for("admin_utilizadores"))

# --- PROTOCOLOS (Separador dedicado) ----------------------------------------
@app.route("/admin/protocolos")
def admin_protocolos():
    return redirect(url_for("protocolos"))

@app.route("/admin/protocolos/new", methods=["POST"])
def admin_protocolos_new():
    if not session.get("is_admin"):
        return redirect(url_for("sem_permissao"))
    nome = request.form.get("nome", "").strip()
    conteudo = request.form.get("conteudo", "").strip()
    if not nome:
        flash("Indica um nome para o protocolo.", "warning")
        return redirect(url_for("admin_protocolos"))
    conn = get_conn()
    conn.execute(fix_sql_placeholders(conn, "INSERT INTO protocolos (nome, conteudo, ativo) VALUES (?,?,1);"),
                (nome, conteudo))
    conn.commit()
    flash("Protocolo criado.", "success")
    return redirect(url_for("admin_protocolos"))

@app.route("/admin/protocolos/<int:pid>/edit", methods=["POST"])
def admin_protocolos_edit(pid):
    if not session.get("is_admin"):
        return redirect(url_for("sem_permissao"))
    nome = request.form.get("nome", "").strip()
    conteudo = request.form.get("conteudo", "").strip()
    ativo = 1 if request.form.get("ativo") == "on" else 0
    conn = get_conn()
    conn.execute(fix_sql_placeholders(conn, "UPDATE protocolos SET nome=?, conteudo=?, ativo=? WHERE id=?;"),
                (nome, conteudo, ativo, pid))
    conn.commit()
    flash("Protocolo atualizado.", "success")
    return redirect(url_for("admin_protocolos"))

@app.route("/protocolos/<int:pid>/apagar", methods=["POST"])
@login_required
@require_perm("protocolos:edit")
def protocolo_apagar(pid: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        # Limpar referências ao protocolo nas viaturas
        cur.execute(fix_sql_placeholders(conn, "UPDATE viaturas SET tipo_protocolo=NULL WHERE tipo_protocolo IN (SELECT nome FROM protocolos WHERE id=?)"), (pid,))
        # Apagar o protocolo
        cur.execute(fix_sql_placeholders(conn, "DELETE FROM protocolos WHERE id=?"), (pid,))
        conn.commit()
        conn.close()
        flash("Protocolo eliminado.", "success")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()
        flash("Não foi possível eliminar o protocolo (pode estar em uso).", "danger")
    return redirect(url_for("protocolos"))

@app.route("/contabilidade")
@login_required
def contabilidade():
    if session.get("role") not in {"admin", "gestor"}:
        flash("Sem permissões para aceder à contabilidade.", "danger")
        return redirect(url_for("home"))

    mes = request.args.get("mes")
    protocolo_id = request.args.get("protocolo_id")
    regiao = request.args.get("regiao")
    empresa = request.args.get("empresa")

    # Só admin pode ver todas as regiões
    user_id = session.get("user_id")
    user_role = session.get("role")
    regiao_user = None
    if user_role == "gestor":
        conn = get_conn()
        cur = conn.cursor()
        sql = "SELECT regiao FROM funcionarios WHERE id=?"
        sql = fix_sql_placeholders(conn, sql)
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        regiao_user = (row["regiao"] or "").strip() if row and row["regiao"] else None
        conn.close()
        regiao = regiao_user  # força filtro pela região do gestor

    conn = get_conn()
    cur = conn.cursor()
    date_sql = sql_date(conn, "r.data_hora")
    sql = f"""
        SELECT r.id as registo_id, {date_sql} as data, 
               COALESCE(r.regiao, v.regiao) as regiao, 
               v.matricula, v.num_frota,
               p.nome as protocolo, p.custo_limpeza, f.nome as funcionario, f.empresa, r.local
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        JOIN protocolos p ON p.id = r.protocolo_id
        JOIN funcionarios f ON f.id = r.funcionario_id
        WHERE 1=1
    """
    params = []
    if mes:
        month_format = sql_month_format(conn, "r.data_hora")
        sql += f" AND {month_format} = ?"
        params.append(mes)
    if protocolo_id:
        sql += " AND p.id = ?"
        params.append(protocolo_id)
    if regiao:
        sql += " AND (COALESCE(r.regiao, v.regiao) = ?)"
        params.append(regiao)
    if empresa:
        sql += " AND f.empresa = ?"
        params.append(empresa)
    datetime_order = sql_datetime(conn, "r.data_hora")
    sql += f" ORDER BY regiao ASC, {datetime_order} ASC, r.id ASC"
    cur.execute(fix_sql_placeholders(conn, sql), params)
    registos = [dict(row) for row in cur.fetchall()]

    # Gerar id_regiao sequencial por região (do mais antigo para o mais recente)
    from collections import defaultdict
    counters = defaultdict(int)
    for r in registos:
        regiao_val = r.get("regiao") or "—"
        counters[regiao_val] += 1
        r["id_regiao"] = f"{regiao_val}-{counters[regiao_val]:03d}"
    # Para apresentação, mostra do mais recente para o mais antigo
    registos = sorted(registos, key=lambda r: (r.get("regiao") or "—", r["data"], r["registo_id"]), reverse=True)

    # Obter lista de empresas para o filtro
    cur.execute("SELECT DISTINCT empresa FROM funcionarios WHERE empresa IS NOT NULL AND TRIM(empresa)<>'' ORDER BY empresa")
    empresas = [r["empresa"] for r in cur.fetchall()]

    cur.execute("SELECT id, nome FROM protocolos WHERE ativo=1 ORDER BY nome")
    protocolos = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT regiao FROM registos_limpeza WHERE regiao IS NOT NULL AND TRIM(regiao)<>'' ORDER BY regiao")
    regioes = [r["regiao"] for r in cur.fetchall()]
    conn.close()

    total = sum(r["custo_limpeza"] or 0 for r in registos)

    return render_template(
        "contabilidade.html",
        registos=registos,
        protocolos=protocolos,
        regioes=regioes,
        empresas=empresas,
        mes=mes,
        protocolo_id=protocolo_id,
        regiao=regiao,
        empresa=empresa,
        total=total,
        signature=APP_SIGNATURE
    )

@app.route("/registos")
@login_required
@require_perm("registos:view")
def registos():
    mes = request.args.get("mes")
    conn = get_conn()
    cur = conn.cursor()

    # Obter região do utilizador (operador ou gestor)
    user_id = session.get("user_id")
    user_role = session.get("role")
    regiao_user = None
    if user_role in ("operador", "gestor"):
        sql = "SELECT regiao FROM funcionarios WHERE id=?"
        sql = fix_sql_placeholders(conn, sql)
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        regiao_user = (row["regiao"] or "").strip() if row and row["regiao"] else None

    sql = """
        SELECT r.id as registo_id, r.data_hora, r.hora_inicio, r.hora_fim, v.matricula, v.num_frota,
               p.nome as protocolo, f.nome as funcionario, r.local, r.verificacao_limpeza,
               r.extra_autorizada, v.regiao, r.observacoes
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        JOIN protocolos p ON p.id = r.protocolo_id
        JOIN funcionarios f ON f.id = r.funcionario_id
        WHERE 1=1
    """
    params = []
    if mes:
        # Use sql_month_format helper for cross-database compatibility
        month_format = sql_month_format(conn, "r.data_hora")
        sql += f" AND {month_format} = ?"
        params.append(mes)
    if regiao_user:
        sql += " AND v.regiao = ?"
        params.append(regiao_user)
    
    datetime_order = sql_datetime(conn, "r.data_hora")
    sql += f" ORDER BY v.regiao ASC, {datetime_order} ASC, r.id ASC"
    
    # Fix parameter placeholders for PostgreSQL
    sql = fix_sql_placeholders(conn, sql)
    cur.execute(sql, params)
    registos = [dict(row) for row in cur.fetchall()]
    conn.close()

    # Gerar ID sequencial por região (do mais antigo para o mais recente)
    from collections import defaultdict
    counters = defaultdict(int)
    for r in registos:
        regiao = r.get("regiao") or "—"
        counters[regiao] += 1
        r["id_regiao"] = f"{regiao}-{counters[regiao]:03d}"

    # Agora apresenta do mais recente para o mais antigo
    registos = sorted(registos, key=lambda r: (r["data_hora"], r["registo_id"]), reverse=True)

    return render_template("registos.html", registos=registos, mes=mes, signature=APP_SIGNATURE)
# -----------------------------------------------------------------------------
# Export Excel
# -----------------------------------------------------------------------------
@app.route("/export/excel")
@login_required
@require_perm("export:excel")
def export_excel():
    from pandas_config import PANDAS_AVAILABLE, pd
    
    if not PANDAS_AVAILABLE:
        flash("Funcionalidade Excel não está disponível no momento.", "error")
        return redirect(url_for("registos"))
    mes = request.args.get("mes")
    conn = get_conn()
    cur = conn.cursor()

    # Obter região do utilizador (operador ou gestor)
    user_id = session.get("user_id")
    user_role = session.get("role")
    regiao_user = None
    if user_role in ("operador", "gestor"):
        ph = sql_placeholder(conn)
        cur.execute(f"SELECT regiao FROM funcionarios WHERE id={ph}", (user_id,))
        row = cur.fetchone()
        regiao_user = (row["regiao"] or "").strip() if row and row["regiao"] else None

    sql = """
        SELECT
            r.id as id_regiao,
            r.data_hora,
            v.matricula,
            v.num_frota,
            p.nome as protocolo,
            f.nome as funcionario,
            r.local,
            r.estado,
            r.observacoes,
            r.hora_inicio,
            r.hora_fim,
            r.extra_autorizada,
            r.verificacao_limpeza,
            r.comentarios_verificacao,
            v.regiao
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        JOIN protocolos p ON p.id = r.protocolo_id
        JOIN funcionarios f ON f.id = r.funcionario_id
        WHERE 1=1
    """
    params = []
    ph = sql_placeholder(conn)
    if mes:
        month_format = sql_month_format(conn, "r.data_hora")
        sql += f" AND {month_format} = {ph}"
        params.append(mes)
    if regiao_user and user_role != "admin":
        sql += f" AND v.regiao = {ph}"
        params.append(regiao_user)
    
    datetime_order = sql_datetime(conn, "r.data_hora")
    sql += f" ORDER BY {datetime_order} DESC, r.id DESC"
    
    # Execute query manually to avoid pandas/psycopg2 compatibility issues
    print(f"DEBUG: Export excel SQL: {sql}")
    print(f"DEBUG: Export excel params: {params}")
    
    try:
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        print(f"DEBUG: Export excel manual query returned {len(rows)} rows")
        
        if rows:
            print(f"DEBUG: First export excel row: {dict(rows[0])}")
            # Convert rows to list of dictionaries
            data_rows = [dict(row) for row in rows]
            df = pd.DataFrame(data_rows)
        else:
            print("DEBUG: Export excel query returned no rows")
            # Create empty DataFrame with correct structure
            df = pd.DataFrame(columns=[
                "id_regiao", "data_hora", "matricula", "num_frota", "protocolo",
                "funcionario", "local", "estado", "observacoes", "hora_inicio", 
                "hora_fim", "extra_autorizada", "verificacao_limpeza", 
                "comentarios_verificacao", "regiao"
            ])
            
    except Exception as manual_e:
        print(f"DEBUG: Export excel manual query failed: {manual_e}")
        conn.close()
        raise manual_e
    
    conn.close()
     
    if not df.empty:
        # Ordena por regiao e data/hora ASC (mais antigo primeiro)
        df = df.sort_values(["regiao", "data_hora", "id_regiao"])
        # Gera o ID sequencial por regiao
        df["id_regiao"] = (
            df.groupby("regiao").cumcount() + 1
        ).apply(lambda x: f"{x:03d}")
        df["id_regiao"] = df["regiao"].fillna("—") + "-" + df["id_regiao"]
        # Agora ordena para exportar do mais recente para o mais antigo
        df = df.sort_values(["data_hora", "id_regiao"], ascending=[False, False])
        df["data"] = pd.to_datetime(df["data_hora"]).dt.date
        # Normalizar campo de verificação
        df['verificacao_limpeza'] = df['verificacao_limpeza'].apply(
            lambda x: "Conforme" if str(x).strip().lower() == "conforme"
            else ("Não conforme" if str(x).strip().lower() in {"não conforme", "nao conforme"} else "")
        )
        # Calcular tempo de limpeza (em minutos)
        def calc_dur(row):
            try:
                if row['hora_inicio'] and row['hora_fim']:
                    d = pd.to_datetime(row['data_hora']).date()
                    t1 = pd.to_datetime(f"{d} {row['hora_inicio']}:00")
                    t2 = pd.to_datetime(f"{d} {row['hora_fim']}:00")
                    return max(0, int((t2 - t1).total_seconds() // 60))
            except Exception:
                pass
            return None

        df['tempo_limpeza_min'] = df.apply(calc_dur, axis=1)
        df['tipo_limpeza'] = df['extra_autorizada'].apply(lambda x: "Extra" if x == 1 else "Normal")

        # Reorganizar colunas
        cols = [
            "id_regiao", "data", "matricula", "num_frota", "protocolo",
            "funcionario", "local", "estado", "observacoes",
            "hora_inicio", "hora_fim", "tempo_limpeza_min", "tipo_limpeza", "verificacao_limpeza", "comentarios_verificacao"
        ]
        df = df[cols]

    fname = EXPORT_DIR / f"registos_limpeza_{mes or 'todos'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    # Sheet principal: registos
    # Sheet secundária: protocolos
    conn = get_conn()
    df_protocolos = pd.read_sql_query("""
        SELECT nome, passos_json, frequencia_dias
        FROM protocolos
        WHERE ativo=1
        ORDER BY nome
    """, conn)
    conn.close()

    # Transformar passos_json em texto
    def passos_text(row):
        try:
            data = json.loads(row['passos_json'] or '{}')
            return "\n".join(data.get('passos', []))
        except Exception:
            return ""
    df_protocolos['passos'] = df_protocolos.apply(passos_text, axis=1)
    df_protocolos = df_protocolos[['nome', 'passos', 'frequencia_dias']]

    with pd.ExcelWriter(fname, engine="xlsxwriter") as writer:
        if not df.empty:
            df.to_excel(writer, index=False, sheet_name="Registos de Limpeza")
        df_protocolos.to_excel(writer, index=False, sheet_name="Protocolos")

    return send_file(fname, as_attachment=True)

@app.route("/export/registos_excel")
@login_required
@require_perm("export:excel")
def export_registos_excel():
    from pandas_config import PANDAS_AVAILABLE, pd
    
    if not PANDAS_AVAILABLE:
        flash("Funcionalidade Excel não está disponível no momento.", "error")
        return redirect(url_for("registos"))
    mes = request.args.get("mes")
    conn = get_conn()
    cur = conn.cursor()

    # Obter região do utilizador (operador ou gestor)
    user_id = session.get("user_id")
    user_role = session.get("role")
    regiao_user = None
    if user_role in ("operador", "gestor"):
        ph = sql_placeholder(conn)
        cur.execute(fix_sql_placeholders(conn, f"SELECT regiao FROM funcionarios WHERE id={ph}"), (user_id,))
        row = cur.fetchone()
        regiao_user = (row["regiao"] or "").strip() if row and row["regiao"] else None

    sql = """
        SELECT
            r.id as id_regiao,
            r.data_hora,
            v.matricula,
            v.num_frota,
            p.nome as protocolo,
            f.nome as funcionario,
            r.local,
            r.estado,
            r.observacoes,
            r.hora_inicio,
            r.hora_fim,
            r.extra_autorizada,
            r.verificacao_limpeza,
            r.comentarios_verificacao,
            v.regiao
        FROM registos_limpeza r
        JOIN viaturas v ON v.id = r.viatura_id
        JOIN protocolos p ON p.id = r.protocolo_id
        JOIN funcionarios f ON f.id = r.funcionario_id
        WHERE 1=1
    """
    params = []
    ph = sql_placeholder(conn)
    if mes:
        month_format = sql_month_format(conn, "r.data_hora")
        sql += f" AND {month_format} = {ph}"
        params.append(mes)
    if regiao_user and user_role != "admin":
        sql += f" AND v.regiao = {ph}"
        params.append(regiao_user)
    datetime_order = sql_datetime(conn, "r.data_hora")
    sql += f" ORDER BY {datetime_order} DESC, r.id DESC"
    
    # Debug the query
    print(f"DEBUG: Export registos SQL: {sql}")
    print(f"DEBUG: Export registos params: {params}")
    final_sql = fix_sql_placeholders(conn, sql)
    print(f"DEBUG: Final SQL after placeholders: {final_sql}")
    
    # Execute query manually to avoid pandas/psycopg2 compatibility issues
    try:
        cur = conn.cursor()
        cur.execute(final_sql, tuple(params))
        rows = cur.fetchall()
        print(f"DEBUG: Manual export query returned {len(rows)} rows")
        
        if rows:
            print(f"DEBUG: First export row: {dict(rows[0])}")
            # Convert rows to list of dictionaries
            data_rows = [dict(row) for row in rows]
            df = pd.DataFrame(data_rows)
        else:
            print("DEBUG: Export query returned no rows")
            # Create empty DataFrame with correct structure
            df = pd.DataFrame(columns=[
                "id_regiao", "data_hora", "matricula", "num_frota", "protocolo",
                "funcionario", "local", "estado", "observacoes", "hora_inicio", 
                "hora_fim", "extra_autorizada", "verificacao_limpeza", 
                "comentarios_verificacao", "regiao"
            ])
            
    except Exception as manual_e:
        print(f"DEBUG: Manual export query failed: {manual_e}")
        conn.close()
        raise manual_e
    print(f"DEBUG: DataFrame shape after pandas: {df.shape}")
    if not df.empty:
        print(f"DEBUG: DataFrame columns: {list(df.columns)}")
        print(f"DEBUG: First DataFrame row:\n{df.head(1)}")
    conn.close()

    if not df.empty:
        # Ordena por regiao e data/hora ASC (mais antigo primeiro)
        df = df.sort_values(["regiao", "data_hora", "id_regiao"])
        # Gera o ID sequencial por regiao
        df["id_regiao"] = (
            df.groupby("regiao").cumcount() + 1
        ).apply(lambda x: f"{x:03d}")
        df["id_regiao"] = df["regiao"].fillna("—") + "-" + df["id_regiao"]
        # Agora ordena para exportar do mais recente para o mais antigo
        df = df.sort_values(["data_hora", "id_regiao"], ascending=[False, False])
        # Handle datetime conversion more robustly for PostgreSQL compatibility
        try:
            df["data"] = pd.to_datetime(df["data_hora"], errors='coerce').dt.date
        except Exception as e:
            # Fallback: try to extract date from string format
            df["data"] = df["data_hora"].apply(lambda x: str(x).split('T')[0] if x else None)

        # Calcular tempo de limpeza (em minutos)
        def calc_dur(row):
            try:
                if row['hora_inicio'] and row['hora_fim']:
                    d = pd.to_datetime(row['data_hora']).date()
                    t1 = pd.to_datetime(f"{d} {row['hora_inicio']}:00")
                    t2 = pd.to_datetime(f"{d} {row['hora_fim']}:00")
                    return max(0, int((t2 - t1).total_seconds() // 60))
            except Exception:
                pass
            return None

        df['tempo_limpeza_min'] = df.apply(calc_dur, axis=1)
        df['tipo_limpeza'] = df['extra_autorizada'].apply(lambda x: "Extra" if x == 1 else "Normal")

        # Reorganizar colunas
        cols = [
            "id_regiao", "data", "matricula", "num_frota", "protocolo",
            "funcionario", "local", "estado", "observacoes",
            "hora_inicio", "hora_fim", "tempo_limpeza_min", "tipo_limpeza", "verificacao_limpeza", "comentarios_verificacao"
        ]
        df = df[cols]

    fname = EXPORT_DIR / f"registos_limpeza_{mes or 'todos'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    # Sheet principal: registos
    # Sheet secundária: protocolos
    conn = get_conn()
    df_protocolos = pd.read_sql_query("""
        SELECT nome, passos_json, frequencia_dias
        FROM protocolos
        WHERE ativo=1
        ORDER BY nome
    """, conn)
    conn.close()

    # Transformar passos_json em texto
    def passos_text(row):
        try:
            data = json.loads(row['passos_json'] or '{}')
            return "\n".join(data.get('passos', []))
        except Exception:
            return ""
    df_protocolos['passos'] = df_protocolos.apply(passos_text, axis=1)
    df_protocolos = df_protocolos[['nome', 'passos', 'frequencia_dias']]

    with pd.ExcelWriter(fname, engine="xlsxwriter") as writer:
        if not df.empty:
            df.to_excel(writer, index=False, sheet_name="Registos de Limpeza")
        df_protocolos.to_excel(writer, index=False, sheet_name="Protocolos")

    return send_file(fname, as_attachment=True)
# -----------------------------------------------------------------------------
# Arrancar
# -----------------------------------------------------------------------------

# Flag para evitar múltiplas inicializações
_schema_initialized = False

# Try to initialize schema early (but don't fail if it doesn't work)
def initialize_schema_early():
    global _schema_initialized
    if not _schema_initialized:
        try:
            print("DEBUG: Tentando inicialização precoce do schema...")
            ensure_schema_on_boot()
            _schema_initialized = True
            print("DEBUG: Inicialização precoce do schema bem-sucedida!")
        except Exception as e:
            print(f"DEBUG: Inicialização precoce falhou (será tentada no primeiro request): {e}")

# Initialize schema early when not in production or when safe to do so
if __name__ == "__main__":
    initialize_schema_early()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # When running under gunicorn, try early initialization but don't block startup
    try:
        initialize_schema_early()
    except Exception as e:
        print(f"DEBUG: Inicialização precoce sob gunicorn falhou: {e}")
# ---- Extensões de esquema (idempotentes) ----

# Health check endpoint para Render (não requer autenticação)
@app.route('/health')
def health_check():
    return {'status': 'ok', 'schema_initialized': _schema_initialized}, 200

@app.before_request
def ensure_database_ready():
    global _schema_initialized
    # Skip schema initialization for health check
    if request.endpoint == 'health_check':
        return
        
    if not _schema_initialized:
        print("DEBUG: Inicializando schema no primeiro request...")
        try:
            ensure_schema_on_boot()
            print("DEBUG: Schema inicializado com sucesso!")
            _schema_initialized = True
        except Exception as e:
            print(f"ERRO CRÍTICO na inicialização do schema via before_request: {e}")
            import traceback
            traceback.print_exc()

@app.before_request
def force_login():
    public_endpoints = {"login", "static", "sem_permissao", "debug", "health_check"}
    ep = request.endpoint or ""
    if ep.split(".")[0] in {"static"} or ep in public_endpoints:
        return
    if not session.get("user_id"):
        return redirect(url_for("login", next=request.path))


