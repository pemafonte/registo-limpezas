# AppFlaskLimpeza.py
from __future__ import annotations
import os, json, sqlite3, io, csv
from pathlib import Path
from datetime import datetime, date

from flask import (
    Flask, request, render_template, redirect, url_for, session, send_from_directory, send_file, flash, Response, abort
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import csv, io

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "base_dados.db"
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"
TEMPLATES_DIR = BASE_DIR / "templates"
OVERWRITE_TEMPLATES = True  # <- Se False, só cria se não existir
APP_TITLE = "Registo Limpezas de Viaturas Grupo Tejo"
APP_SIGNATURE = "Created by Pedro Fonte"

ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".pdf"}

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "dev-key-please-change")

UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

print("### DB em uso:", DB_PATH)

# -----------------------------------------------------------------------------
# Templates auto-criados (para ser plug-and-play)
# -----------------------------------------------------------------------------
def write_templates():
    files: dict[str, str] = {}

    files["home.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Dashboard</h2>
  <p class="muted">Viaturas com limpeza em atraso (colunas arrastáveis), Top 10 mais recentemente limpas e gráficos.</p>

  {% if can('viaturas:import') %}
    <p style="margin:.5rem 0 1rem">
      <a class="btn" href="{{ url_for('importar_viaturas') }}">Importar viaturas (CSV)</a>
    </p>
  {% endif %}

  {% if rows %}
  <table id="dash-table">
    <thead>
      <tr>
        <th class="draggable" data-colid="num_frota">Nº de frota</th>
        <th class="draggable" data-colid="matricula">Matrícula</th>
        <th class="draggable" data-colid="filial">Filial</th>
        <th class="draggable" data-colid="ultima">Última (qualquer)</th>
        <th class="draggable" data-colid="dias_sem">Dias sem limpeza</th>
        {% for p in protocolos %}
          <th class="draggable" data-colid="p-{{ p.id }}">{{ p.nome }}{% if p.frequencia_dias %} ({{ p.frequencia_dias }}d){% endif %}</th>
        {% endfor %}
        <th class="draggable" data-colid="delta">Δ protocolos (dias)</th>
        <th class="draggable" data-colid="hoje">Hoje</th>
      </tr>
    </thead>
    <tbody>
      {% for r in rows %}
        <tr>
          <td data-colid="num_frota">{{ r.num_frota or "—" }}</td>
          <td data-colid="matricula"><b>{{ r.matricula }}</b></td>
          <td data-colid="filial">{{ r.filial }}</td>
          <td data-colid="ultima">{{ r.ultima_qualquer or "—" }}</td>
          <td data-colid="dias_sem">{{ r.dias_sem_limpeza if r.dias_sem_limpeza is not none else "—" }}</td>

          {% for p in protocolos %}
            {% set info = r.por_protocolo.get(p.id) %}
            <td data-colid="p-{{ p.id }}">
              {% if info %}
                {% if info.ultima %}{{ info.ultima }}{% else %}—{% endif %}
                {% if info.dias is not none %} — {{ info.dias }}d{% endif %}
                {% if info.atraso %} <strong style="color:red">ATRASO</strong>{% endif %}
              {% else %}—{% endif %}
            </td>
          {% endfor %}

          <td data-colid="delta">{{ r.delta_protocolos if r.delta_protocolos is not none else "—" }}</td>
          <td data-colid="hoje">
            {% if r.limpa_hoje %}
              <span style="color:#b71c1c; font-weight:600">Já limpa hoje — nova limpeza requer autorização</span>
            {% else %}—{% endif %}
          </td>
        </tr>
      {% endfor %}
    </tbody>
  </table>

  {% raw %}
  <script>
    (function(){
      const KEY = "dash_col_order_v1";
      const table = document.getElementById("dash-table");
      if (!table) return;
      const head = table.tHead.rows[0];
      const ths = Array.from(head.cells);
      ths.forEach(th => { th.draggable = true; });

      function colIndexById(id){ return Array.from(head.cells).findIndex(c => c.dataset.colid === id); }
      function applyOrder(order){
        const current = Array.from(head.cells).map(c => c.dataset.colid);
        if (JSON.stringify(order) === JSON.stringify(current)) return;
        order.forEach((colid) => {
          const idx = colIndexById(colid);
          if (idx === -1) return;
          head.appendChild(head.cells[idx]);
          Array.from(table.tBodies[0].rows).forEach(tr => {
            const cell = Array.from(tr.cells).find(td => td.dataset.colid === colid);
            if (cell) tr.appendChild(cell);
          });
        });
      }
      try {
        const saved = JSON.parse(localStorage.getItem(KEY) || "null");
        if (Array.isArray(saved) && saved.length === ths.length) applyOrder(saved);
      } catch(e){}
      let srcId = null;
      head.addEventListener("dragstart", e => {
        const th = e.target.closest("th"); if (!th) return;
        srcId = th.dataset.colid; e.dataTransfer.effectAllowed="move";
      });
      head.addEventListener("dragover", e => { e.preventDefault(); e.dataTransfer.dropEffect="move"; });
      head.addEventListener("drop", e => {
        e.preventDefault();
        const dst = e.target.closest("th"); if (!dst || !srcId) return;
        const current = Array.from(head.cells).map(c => c.dataset.colid);
        const from = current.indexOf(srcId), to = current.indexOf(dst.dataset.colid);
        if (from===-1 || to===-1 || from===to) return;
        const order = current.slice(); order.splice(to, 0, order.splice(from,1)[0]);
        applyOrder(order); localStorage.setItem(KEY, JSON.stringify(order)); srcId=null;
      });
    })();
  </script>
  {% endraw %}
  {% else %}
    <div class="card">Sem atrasos 🎉</div>
  {% endif %}

  <h3 style="margin-top:2rem">Top 10 — Viaturas mais recentemente limpas</h3>
  {% if top10 %}
    <table>
      <thead><tr>
        <th>Nº de frota</th><th>Matrícula</th><th>Filial</th><th>Última limpeza</th><th>Dias desde a última</th>
      </tr></thead>
      <tbody>
        {% for r in top10 %}
          <tr>
            <td>{{ r.num_frota or "—" }}</td>
            <td><b>{{ r.matricula }}</b></td>
            <td>{{ r.filial }}</td>
            <td>{{ r.ultima_qualquer }}</td>
            <td>{{ r.dias_sem_limpeza }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <div class="card">Sem dados.</div>
  {% endif %}

  <!-- Gráficos -->
  <h3 style="margin-top:2rem">Gráficos</h3>
  <script id="charts-data" type="application/json">{{ charts | tojson }}</script>
  <div class="card"><canvas id="chart_proto" height="120"></canvas></div>
  <div class="card"><canvas id="chart_avg_days" height="120"></canvas></div>
  <div class="card"><canvas id="chart_local" height="120"></canvas></div>
  <div class="card"><canvas id="chart_func" height="120"></canvas></div>
  <div class="card"><canvas id="chart_dur" height="120"></canvas></div>

  {% raw %}
  <script>
    const CH = JSON.parse(document.getElementById('charts-data').textContent);
    function bar(id, labels, data, title){
      const ctx = document.getElementById(id).getContext('2d');
      new Chart(ctx, {
        type: 'bar',
        data: { labels: labels, datasets: [{ label: title, data: data }] },
        options: { responsive: true, plugins: { legend: { display: true } } }
      });
    }
    bar('chart_proto', CH.proto_labels, CH.proto_values, 'Viaturas que fizeram cada protocolo');
    (function(){
      const ctx = document.getElementById('chart_avg_days').getContext('2d');
      new Chart(ctx, {
        type: 'bar',
        data: { labels: ['Média (dias) — Frota: ' + CH.fleet_size], datasets: [{ label: 'Média de dias desde a última limpeza', data: [CH.avg_days] }] },
        options: { responsive: true, plugins: { legend: { display: true } }, scales: { y: { beginAtZero: true } } }
      });
    })();
    bar('chart_local', CH.local_labels, CH.local_values, 'Quantidade de limpezas por local');
    bar('chart_func', CH.func_labels, CH.func_values, 'Quantidade de limpezas por funcionário');
    bar('chart_dur', CH.dur_labels, CH.dur_values, 'Duração média (min) por protocolo');
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
    <p><button class="btn btn-primary" type="submit">Entrar</button></p>
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

    files["home.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Dashboard</h2>
  <p class="muted">Viaturas com limpeza em atraso (colunas arrastáveis), Top 10 mais recentemente limpas e gráficos.</p>

  {% if can('viaturas:import') %}
    <p style="margin:.5rem 0 1rem">
      <a class="btn" href="{{ url_for('importar_viaturas') }}">Importar viaturas (CSV)</a>
    </p>
  {% endif %}

  {% if rows %}
  <table id="dash-table">
    <thead>
      <tr>
        <th class="draggable" data-colid="num_frota">Nº de frota</th>
        <th class="draggable" data-colid="matricula">Matrícula</th>
        <th class="draggable" data-colid="filial">Filial</th>
        <th class="draggable" data-colid="ultima">Última (qualquer)</th>
        <th class="draggable" data-colid="dias_sem">Dias sem limpeza</th>
        {% for p in protocolos %}
          <th class="draggable" data-colid="p-{{ p.id }}">{{ p.nome }}{% if p.frequencia_dias %} ({{ p.frequencia_dias }}d){% endif %}</th>
        {% endfor %}
        <th class="draggable" data-colid="delta">Δ protocolos (dias)</th>
        <th class="draggable" data-colid="hoje">Hoje</th>
      </tr>
    </thead>
    <tbody>
      {% for r in rows %}
        <tr>
          <td data-colid="num_frota">{{ r.num_frota or "—" }}</td>
          <td data-colid="matricula"><b>{{ r.matricula }}</b></td>
          <td data-colid="filial">{{ r.filial }}</td>
          <td data-colid="ultima">{{ r.ultima_qualquer or "—" }}</td>
          <td data-colid="dias_sem">{{ r.dias_sem_limpeza if r.dias_sem_limpeza is not none else "—" }}</td>

          {% for p in protocolos %}
            {% set info = r.por_protocolo.get(p.id) %}
            <td data-colid="p-{{ p.id }}">
              {% if info %}
                {% if info.ultima %}{{ info.ultima }}{% else %}—{% endif %}
                {% if info.dias is not none %} — {{ info.dias }}d{% endif %}
                {% if info.atraso %} <strong style="color:red">ATRASO</strong>{% endif %}
              {% else %}—{% endif %}
            </td>
          {% endfor %}

          <td data-colid="delta">{{ r.delta_protocolos if r.delta_protocolos is not none else "—" }}</td>
          <td data-colid="hoje">
            {% if r.limpa_hoje %}
              <span style="color:#b71c1c; font-weight:600">Já limpa hoje — nova limpeza requer autorização</span>
            {% else %}—{% endif %}
          </td>
        </tr>
      {% endfor %}
    </tbody>
  </table>

  {% raw %}
  <script>
    (function(){
      const KEY = "dash_col_order_v1";
      const table = document.getElementById("dash-table");
      if (!table) return;
      const head = table.tHead.rows[0];
      const ths = Array.from(head.cells);
      ths.forEach(th => { th.draggable = true; });

      function colIndexById(id){ return Array.from(head.cells).findIndex(c => c.dataset.colid === id); }
      function applyOrder(order){
        const current = Array.from(head.cells).map(c => c.dataset.colid);
        if (JSON.stringify(order) === JSON.stringify(current)) return;
        order.forEach((colid) => {
          const idx = colIndexById(colid);
          if (idx === -1) return;
          head.appendChild(head.cells[idx]);
          Array.from(table.tBodies[0].rows).forEach(tr => {
            const cell = Array.from(tr.cells).find(td => td.dataset.colid === colid);
            if (cell) tr.appendChild(cell);
          });
        });
      }
      try {
        const saved = JSON.parse(localStorage.getItem(KEY) || "null");
        if (Array.isArray(saved) && saved.length === ths.length) applyOrder(saved);
      } catch(e){}
      let srcId = null;
      head.addEventListener("dragstart", e => {
        const th = e.target.closest("th"); if (!th) return;
        srcId = th.dataset.colid; e.dataTransfer.effectAllowed="move";
      });
      head.addEventListener("dragover", e => { e.preventDefault(); e.dataTransfer.dropEffect="move"; });
      head.addEventListener("drop", e => {
        e.preventDefault();
        const dst = e.target.closest("th"); if (!dst || !srcId) return;
        const current = Array.from(head.cells).map(c => c.dataset.colid);
        const from = current.indexOf(srcId), to = current.indexOf(dst.dataset.colid);
        if (from===-1 || to===-1 || from===to) return;
        const order = current.slice(); order.splice(to, 0, order.splice(from,1)[0]);
        applyOrder(order); localStorage.setItem(KEY, JSON.stringify(order)); srcId=null;
      });
    })();
  </script>
  {% endraw %}
  {% else %}
    <div class="card">Sem atrasos 🎉</div>
  {% endif %}

  <h3 style="margin-top:2rem">Top 10 — Viaturas mais recentemente limpas</h3>
  {% if top10 %}
    <table>
      <thead><tr>
        <th>Nº de frota</th><th>Matrícula</th><th>Filial</th><th>Última limpeza</th><th>Dias desde a última</th>
      </tr></thead>
      <tbody>
        {% for r in top10 %}
          <tr>
            <td>{{ r.num_frota or "—" }}</td>
            <td><b>{{ r.matricula }}</b></td>
            <td>{{ r.filial }}</td>
            <td>{{ r.ultima_qualquer }}</td>
            <td>{{ r.dias_sem_limpeza }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <div class="card">Sem dados.</div>
  {% endif %}

  <!-- Gráficos -->
  <h3 style="margin-top:2rem">Gráficos</h3>
  <script id="charts-data" type="application/json">{{ charts | tojson }}</script>
  <div class="card"><canvas id="chart_proto" height="120"></canvas></div>
  <div class="card"><canvas id="chart_avg_days" height="120"></canvas></div>
  <div class="card"><canvas id="chart_local" height="120"></canvas></div>
  <div class="card"><canvas id="chart_func" height="120"></canvas></div>
  <div class="card"><canvas id="chart_dur" height="120"></canvas></div>

  {% raw %}
  <script>
    const CH = JSON.parse(document.getElementById('charts-data').textContent);
    function bar(id, labels, data, title){
      const ctx = document.getElementById(id).getContext('2d');
      new Chart(ctx, {
        type: 'bar',
        data: { labels: labels, datasets: [{ label: title, data: data }] },
        options: { responsive: true, plugins: { legend: { display: true } } }
      });
    }
    bar('chart_proto', CH.proto_labels, CH.proto_values, 'Viaturas que fizeram cada protocolo');
    (function(){
      const ctx = document.getElementById('chart_avg_days').getContext('2d');
      new Chart(ctx, {
        type: 'bar',
        data: { labels: ['Média (dias) — Frota: ' + CH.fleet_size], datasets: [{ label: 'Média de dias desde a última limpeza', data: [CH.avg_days] }] },
        options: { responsive: true, plugins: { legend: { display: true } }, scales: { y: { beginAtZero: true } } }
      });
    })();
    bar('chart_local', CH.local_labels, CH.local_values, 'Quantidade de limpezas por local');
    bar('chart_func', CH.func_labels, CH.func_values, 'Quantidade de limpezas por funcionário');
    bar('chart_dur', CH.dur_labels, CH.dur_values, 'Duração média (min) por protocolo');
  </script>
  {% endraw %}
{% endblock %}
"""


    files["viaturas.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Viaturas</h2>
  <table>
    <thead>
      <tr>
        <th>Nº de frota</th><th>Matrícula</th><th>Descrição</th><th>Filial</th>
        <th>Local (última)</th><th>Duração (última)</th><th>Funcionário (última)</th><th>Ativo</th>
      </tr>
    </thead>
    <tbody>
      {% for v in viaturas %}
      <tr>
        <td>{{ v.num_frota or "—" }}</td>
        <td>{{ v.matricula }}</td>
        <td>{{ v.descricao or "" }}</td>
        <td>{{ v.filial or "" }}</td>
        <td>{{ v.ultima_local or "—" }}</td>
        <td>{% if v.hora_inicio and v.hora_fim %}{{ v.hora_inicio }} – {{ v.hora_fim }}{% else %}—{% endif %}</td>
        <td>{{ v.ultima_user or "—" }}</td>
        <td>Sim</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
"""

    files["registos.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Registos</h2>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Data</th><th>Hora início</th><th>Hora fim</th>
        <th>Matrícula</th><th>Nº frota</th><th>Protocolo</th>
        <th>Funcionário</th><th>Local</th><th>Estado</th><th>Obs</th><th>Extra</th><th>Anexos</th>
      </tr>
    </thead>
    <tbody>
      {% for r in registos %}
      <tr>
        <td>{{ r.registo_id }}</td>
        <td>{{ r.data_hora }}</td>
        <td>{{ r.hora_inicio or "—" }}</td>
        <td>{{ r.hora_fim or "—" }}</td>
        <td>{{ r.matricula }}</td>
        <td>{{ r.num_frota or "—" }}</td>
        <td>{{ r.protocolo }}</td>
        <td>{{ r.user }}</td>
        <td>{{ r.local or "—" }}</td>
        <td>{{ r.estado }}</td>
        <td>{{ r.observacoes or "" }}</td>
        <td>
          {% if r.extra_autorizada == 1 %}
            <strong>Sim</strong>{% if r.responsavel_autorizacao %} ({{ r.responsavel_autorizacao }}){% endif %}
          {% else %}Não{% endif %}
        </td>
        <td><a class="btn" href="{{ url_for('ver_anexos', registo_id=r.registo_id) }}">Ver</a></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
"""

    files["novo_registo.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Novo Registo de Limpeza</h2>

  <div id="alert-extra" class="card" style="display:none; border-color:#dc3545;">
    <b>Atenção:</b> esta viatura já foi <u>limpa hoje</u>. Nova limpeza só com <b>autorização do responsável</b>.
    Indique o nome e assinale a opção abaixo.
  </div>

  <form method="post" enctype="multipart/form-data" id="form-novo">
    <div class="row">
      <label>Nº de frota / Matrícula
        <select name="viatura_id" id="viatura_id" required>
          <option value="">-- selecione --</option>
          {% for v in viaturas %}
            <option value="{{ v.id }}">{{ v.num_frota or "—" }} — {{ v.matricula }}{% if v.descricao %} — {{ v.descricao }}{% endif %}</option>
          {% endfor %}
        </select>
      </label>

      <label>Protocolo
        <select name="protocolo_id" required>
          <option value="">-- selecione --</option>
          {% for p in protocolos %}
            <option value="{{ p.id }}">{{ p.nome }}</option>
          {% endfor %}
        </select>
      </label>

      <label>Local da limpeza
        <input type="text" name="local" placeholder="ex.: Parque Norte / Oficina / Estação">
      </label>

      <label>Hora de início
        <input type="time" name="hora_inicio" placeholder="HH:MM">
      </label>

      <label>Hora de fim
        <input type="time" name="hora_fim" placeholder="HH:MM">
      </label>

      <label>Estado
        <select name="estado">
          <option value="concluido" selected>concluido</option>
          <option value="pendente">pendente</option>
          <option value="em_execucao">em_execucao</option>
          <option value="reprovado">reprovado</option>
        </select>
      </label>

      <label>Observações
        <input type="text" name="observacoes" placeholder="opcional">
      </label>

      <label>Ficheiros (múltiplos)
        <input type="file" name="ficheiros" multiple>
      </label>
    </div>

    <div id="extra-fields" class="card" style="display:none;">
      <label><input type="checkbox" name="extra_autorizada" value="1" id="extra_autorizada"> Autorizo limpeza extra</label>
      <label>Responsável pela autorização
        <input type="text" name="responsavel_autorizacao" id="responsavel_autorizacao" placeholder="Nome do responsável">
      </label>
    </div>

    <p><button class="btn btn-primary" type="submit">Gravar</button></p>
  </form>

  <script id="limpa-hoje-data" type="application/json">{{ limpa_hoje_map | tojson }}</script>

  {% raw %}
  <script>
    const LIMPA_HOJE = JSON.parse(document.getElementById('limpa-hoje-data').textContent);
    const sel = document.getElementById("viatura_id");
    const alertBox = document.getElementById("alert-extra");
    const extraBox = document.getElementById("extra-fields");
    const chk = document.getElementById("extra_autorizada");
    const resp = document.getElementById("responsavel_autorizacao");

    function onChange(){
      const id = sel.value;
      const ja = LIMPA_HOJE[id] === true;
      alertBox.style.display = ja ? "block" : "none";
      extraBox.style.display = ja ? "block" : "none";
      resp.required = ja; chk.required = ja;
      if (!ja) { resp.value = ""; chk.checked = false; }
    }
    sel.addEventListener("change", onChange);
  </script>
  {% endraw %}
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
        {% if can('protocolos:edit') %}<th>Ações</th>{% endif %}
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
        <td><a class="btn" href="{{ url_for('protocolo_editar', pid=p.id) }}">Editar</a></td>
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
  </ul>
{% endblock %}
"""

    files["admin_users.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Utilizadores</h2>
  <p><a class="btn btn-primary" href="{{ url_for('admin_user_new') }}">Novo utilizador</a></p>
  <table>
    <thead><tr><th>Username</th><th>Nome</th><th>Perfil</th><th>Ativo</th><th>Criado</th></tr></thead>
    <tbody>
      {% for u in users %}
      <tr>
        <td>{{ u.username }}</td>
        <td>{{ u.nome or "—" }}</td>
        <td>{{ u.role }}</td>
        <td>{{ "Sim" if u.ativo==1 else "Não" }}</td>
        <td>{{ u.criado_em }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
"""

    files["admin_user_form.html"] = """{% extends "base.html" %}
{% block content %}
  <h2>Novo Utilizador</h2>
  <form method="post">
    <div class="row">
      <label>Username <input name="username" required></label>
      <label>Nome <input name="nome" placeholder="opcional"></label>
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

    for name, content in files.items():
        path = TEMPLATES_DIR / name
        if OVERWRITE_TEMPLATES or not path.exists():
            path.write_text(content, encoding="utf-8")

write_templates()

# -----------------------------------------------------------------------------
# Helpers / filtros
# -----------------------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
    "operador": {"dashboard:view","viaturas:view","protocolos:view","registos:view","registos:create"},
    "leitura":  {"dashboard:view","viaturas:view","protocolos:view","registos:view"},
}

def normalize_role(role: str) -> str:
    r = (role or "leitura").lower().strip()
    return r if r in PERMISSIONS else "leitura"

def get_db_role_perms(role: str) -> set[str]:
    role = (role or "").strip().lower()
    if not role:
        return set()
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id FROM roles WHERE LOWER(name)=?", (role,))
    r = cur.fetchone()
    if not r:
        conn.close(); return set()
    cur.execute("SELECT perm FROM role_permissions WHERE role_id=?", (r["id"],))
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


# --- CSV helpers (encoding + delimiter) ---
def _read_csv_text_with_encoding_guess_bytes(raw: bytes):
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", "replace"), "latin-1"

def _detect_delimiter(sample: str):
    # Prefer ';' for Portuguese Excel exports, fallback to comma
    semi = sample.count(";")
    comma = sample.count(",")
    return ";" if semi >= comma else ","

def _normalize_header(h: str) -> str:
    import unicodedata, re as _re
    s = (h or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = s.replace("º", "o")
    s = _re.sub(r"[^a-z0-9]+", " ", s).strip()
    # Map common aliases
    aliases = {
        "mat": "matricula",
        "matricula": "matricula",
        "matricula ": "matricula",
        "n o viat": "num_frota",
        "no viat": "num_frota",
        "n viat": "num_frota",
        "n viatura": "num_frota",
        "n de frota": "num_frota",
        "n frota": "num_frota",
        "num frota": "num_frota",
        "numero frota": "num_frota",
        "n viat ": "num_frota",
        "regiao": "regiao",
        "operacao": "operacao",
        "marca": "marca",
        "modelo": "modelo",
        "ativo": "ativo",
        "activa": "ativo",
        "activa?": "ativo",
        "activo": "ativo",
        "sim nao": "ativo",
    }
    return aliases.get(s, s)

def _as_bool(v):
    s = (str(v or "").strip().lower())
    if s in {"1","true","t","y","yes","sim","s"}: return 1
    if s in {"0","false","f","n","no","nao","não"}: return 0
    return 1  # default

def _extend_schema_viaturas():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("PRAGMA table_info(viaturas)")
    cols = { (r["name"] if isinstance(r, sqlite3.Row) else r[1]) for r in cur.fetchall() }
    for col in ("regiao","operacao","marca","modelo"):
        if col not in cols:
            try:
                cur.execute(f"ALTER TABLE viaturas ADD COLUMN {col} TEXT")
            except Exception:
                pass
    conn.commit(); conn.close()


# -----------------------------------------------------------------------------

# Esquema / seed
# -----------------------------------------------------------------------------
def ensure_schema_on_boot():
    conn = get_conn()
    cur = conn.cursor()

    # Tabelas base
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS viaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT NOT NULL UNIQUE,
            descricao TEXT,
            filial TEXT,
            num_frota TEXT,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS protocolos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            passos_json TEXT NOT NULL,
            frequencia_dias INTEGER,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS registos_limpeza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (viatura_id) REFERENCES viaturas(id) ON DELETE RESTRICT,
            FOREIGN KEY (protocolo_id) REFERENCES protocolos(id) ON DELETE RESTRICT,
            FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id) ON DELETE RESTRICT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS anexos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registo_id INTEGER NOT NULL,
            caminho TEXT NOT NULL,
            tipo TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (registo_id) REFERENCES registos_limpeza(id) ON DELETE CASCADE
        )
    """)

    # Perfis dinâmicos
    cur.execute("""CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    # Admin padrão
    cur.execute("SELECT COUNT(*) FROM funcionarios WHERE username='admin'")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO funcionarios (username,password,nome,role,ativo) VALUES (?,?,?,?,1)",
            ("admin", generate_password_hash("1234"), "Administrador", "admin")
        )
    # Admin Pedro.fonte
    cur.execute("SELECT 1 FROM funcionarios WHERE username='Pedro.fonte'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO funcionarios (username,password,nome,role,ativo) VALUES (?,?,?,?,1)",
            ("Pedro.fonte", generate_password_hash("1234"), "Pedro Fonte", "admin")
        )
    # Normalizar roles inválidos
    cur.execute("""
        UPDATE funcionarios
           SET role='leitura'
         WHERE role IS NULL OR TRIM(LOWER(role)) NOT IN ('admin','gestor','operador','leitura')
    """)

    cur.execute("SELECT COUNT(*) FROM viaturas")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO viaturas (matricula, descricao, filial, num_frota, ativo) VALUES (?,?,?,?,1)",
            [
                ("AA-00-AA", "Autocarro Urbano", "Sede", "101"),
                ("BB-11-BB", "Autocarro Suburbano", "Filial Norte", "102"),
            ]
        )

    cur.execute("SELECT COUNT(*) FROM protocolos")
    if cur.fetchone()[0] == 0:
        prot1 = {"passos": ["Inspeção interior", "Aspirar", "Desinfetar superfícies", "Vidros interiores", "Check final"]}
        prot2 = {"passos": ["Inspeção exterior", "Lavagem chassis", "Vidros exteriores", "Verificar níveis", "Check final"]}
        cur.execute("INSERT INTO protocolos (nome, passos_json, frequencia_dias, ativo) VALUES (?,?,?,1)",
                    ("Interior Standard", json.dumps(prot1, ensure_ascii=False), 7))
        cur.execute("INSERT INTO protocolos (nome, passos_json, frequencia_dias, ativo) VALUES (?,?,?,1)",
                    ("Exterior Standard", json.dumps(prot2, ensure_ascii=False), 14))
    else:
        cur.execute("UPDATE protocolos SET frequencia_dias=7  WHERE frequencia_dias IS NULL AND nome LIKE 'Interior%'")
        cur.execute("UPDATE protocolos SET frequencia_dias=14 WHERE frequencia_dias IS NULL AND nome LIKE 'Exterior%'")

    conn.commit()
    conn.close()

ensure_schema_on_boot()
_extend_schema_viaturas()

# -----------------------------------------------------------------------------
# Autenticação
# -----------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM funcionarios WHERE username = ? COLLATE NOCASE AND ativo=1", (username,))
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
@app.route("/")
@login_required
def home():
    conn = get_conn()
    cur = conn.cursor()

    # Protocolos
    cur.execute("SELECT id, nome, COALESCE(frequencia_dias, 0) AS frequencia_dias FROM protocolos WHERE ativo=1 ORDER BY nome")
    protocolos = [dict(r) for r in cur.fetchall()]

    # Viaturas
    cur.execute("SELECT id, matricula, descricao, filial, num_frota FROM viaturas WHERE ativo=1 ORDER BY filial, matricula")
    viaturas = [dict(r) for r in cur.fetchall()]

    # Última limpeza por viatura/protocolo
    cur.execute("""
        SELECT viatura_id, protocolo_id, MAX(datetime(data_hora)) AS ult
        FROM registos_limpeza
        GROUP BY viatura_id, protocolo_id
    """)
    last_map = {(r["viatura_id"], r["protocolo_id"]): r["ult"] for r in cur.fetchall()}

    # Última (qualquer) por viatura
    cur.execute("""
        SELECT viatura_id, MAX(datetime(data_hora)) AS ult
        FROM registos_limpeza
        GROUP BY viatura_id
    """)
    last_any = {r["viatura_id"]: r["ult"] for r in cur.fetchall()}

    # Limpa hoje
    cur.execute("SELECT DISTINCT viatura_id FROM registos_limpeza WHERE date(data_hora)=date('now','localtime')")
    limpas_hoje = {r["viatura_id"] for r in cur.fetchall()}

    # ----- Gráficos -----
    # viaturas distintas por protocolo
    cur.execute("""
        SELECT p.nome as label, COUNT(DISTINCT r.viatura_id) as qty
        FROM registos_limpeza r
        JOIN protocolos p ON p.id = r.protocolo_id
        GROUP BY r.protocolo_id
        ORDER BY p.nome
    """)
    chart_proto = [(r["label"], r["qty"]) for r in cur.fetchall()]

    # média de dias desde a última limpeza (por viatura)
    hoje = date.today()
    dias_por_viatura = []
    for v in viaturas:
        iso = last_any.get(v["id"])
        if not iso: continue
        dt = datetime.fromisoformat(iso).date()
        dias_por_viatura.append((hoje - dt).days)
    media_dias_ultima = round(sum(dias_por_viatura)/len(dias_por_viatura), 2) if dias_por_viatura else 0.0
    total_viaturas = len(viaturas)

    # quantidade por local
    cur.execute("""
        SELECT COALESCE(local,'(Sem local)') as label, COUNT(*) as qty
        FROM registos_limpeza
        GROUP BY COALESCE(local,'(Sem local)')
        ORDER BY qty DESC, label
    """)
    chart_local = [(r["label"], r["qty"]) for r in cur.fetchall()]

    # quantidade por funcionário
    cur.execute("""
        SELECT f.username as label, COUNT(*) as qty
        FROM registos_limpeza r
        JOIN funcionarios f ON f.id = r.funcionario_id
        GROUP BY r.funcionario_id
        ORDER BY qty DESC, label
    """)
    chart_func = [(r["label"], r["qty"]) for r in cur.fetchall()]

    # duração média por protocolo (minutos)
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

    conn.close()

    # ----- Dashboard: atrasos + top10 -----
    rows_atraso = []
    rows_top10 = []

    # top10 (menos dias sem limpeza)
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

    # atrasos por protocolo
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
            "limpa_hoje": v["id"] in limpas_hoje,
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
    }

    return render_template("home.html",
                           protocolos=protocolos,
                           rows=rows_atraso,
                           top10=rows_top10,
                           charts=charts,
                           signature=APP_SIGNATURE)

# -----------------------------------------------------------------------------
# Viaturas
# -----------------------------------------------------------------------------
# ---------------------------------------------------------------------
# Importação de viaturas via Dashboard (não-admin)
# Mostra o mesmo formulário e executa import sem passar pelo admin
# ---------------------------------------------------------------------
@app.route("/viaturas/importar", methods=["GET", "POST"])
@login_required
@require_perm("viaturas:import")  # garante que só quem tem esta permissão vê/usa
def importar_viaturas():
    if request.method == "GET":
        # Reutiliza o teu template já existente do admin
        return render_template("admin_import_viaturas.html", signature=APP_SIGNATURE)

    file = request.files.get("ficheiro")
    if not file or file.filename == "":
        flash("Selecione um ficheiro CSV.", "danger")
        return redirect(url_for("importar_viaturas"))

    # --- leitura robusta (aceita UTF-8/CP1252/Latin-1 e , ou ;) ---
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

    import csv, io, unicodedata, re
    reader = csv.reader(io.StringIO(text), delimiter=delim)

    try:
        header = next(reader)
    except StopIteration:
        flash("CSV vazio.", "danger")
        return redirect(url_for("importar_viaturas"))

    def _norm(h: str) -> str:
        s = (h or "").strip().lower()
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        s = s.replace("º", "o")
        s = re.sub(r"[^a-z0-9]+", " ", s).strip()
        aliases = {
            "mat": "matricula",
            "matricula": "matricula",
            "n viat": "num_frota",
            "no viat": "num_frota",
            "n viatura": "num_frota",
            "n frota": "num_frota",
            "num frota": "num_frota",
            "numero frota": "num_frota",
            "regiao": "regiao",
            "operacao": "operacao",
            "marca": "marca",
            "modelo": "modelo",
            "ativo": "ativo",
        }
        return aliases.get(s, s)

    nh = [_norm(h) for h in header]
    idx = {k: (nh.index(k) if k in nh else -1)
           for k in ("matricula", "num_frota", "regiao", "operacao", "marca", "modelo", "ativo")}

    if idx["matricula"] == -1:
        flash("O CSV precisa da coluna 'Mat.' ou 'Matrícula'.", "danger")
        return redirect(url_for("importar_viaturas"))

    def _as_bool(v):
        s = (str(v or "").strip().lower())
        if s in {"1","true","t","y","yes","sim","s"}: return 1
        if s in {"0","false","f","n","no","nao","não"}: return 0
        return 1

    conn = get_conn(); cur = conn.cursor()
    # (garante que as colunas novas existem; ignora se já existirem)
    try:
        cur.execute("PRAGMA table_info(viaturas)")
        cols = {r["name"] for r in cur.fetchall()}
        for col in ("regiao","operacao","marca","modelo"):
            if col not in cols:
                cur.execute(f"ALTER TABLE viaturas ADD COLUMN {col} TEXT")
    except Exception:
        pass

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

        cur.execute("SELECT id FROM viaturas WHERE matricula=?", (m,))
        ex = cur.fetchone()
        if ex:
            cur.execute("""
                UPDATE viaturas
                   SET num_frota=COALESCE(?, num_frota),
                       regiao=COALESCE(?, regiao),
                       operacao=COALESCE(?, operacao),
                       marca=COALESCE(?, marca),
                       modelo=COALESCE(?, modelo),
                       ativo=?
                 WHERE id=?""",
                (num_frota, regiao, operacao, marca, modelo, ativo, ex["id"]))
            upd += 1
        else:
            cur.execute("""
                INSERT INTO viaturas (matricula, num_frota, regiao, operacao, marca, modelo, ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (m, num_frota, regiao, operacao, marca, modelo, ativo))
            ins += 1

    conn.commit(); conn.close()
    flash(f"Importação concluída (encoding: {enc}): {ins} inseridas, {upd} atualizadas.", "info")
    return redirect(url_for("viaturas"))


@app.route("/viaturas")
@login_required
@require_perm("viaturas:view")
def viaturas():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        WITH last AS (
          SELECT r.*
          FROM registos_limpeza r
          JOIN (
            SELECT viatura_id, MAX(datetime(data_hora)) AS ult
            FROM registos_limpeza
            GROUP BY viatura_id
          ) m ON m.viatura_id = r.viatura_id AND datetime(r.data_hora) = m.ult
        )
        SELECT v.id, v.matricula, v.descricao, v.filial, v.num_frota,
               l.local AS ultima_local,
               l.hora_inicio, l.hora_fim,
               f.username AS ultima_user,
               v.ativo
        FROM viaturas v
        LEFT JOIN last l ON l.viatura_id = v.id
        LEFT JOIN funcionarios f ON f.id = l.funcionario_id
        WHERE v.ativo = 1
        ORDER BY v.filial, v.matricula
    """)
    vs = [dict(row) for row in cur.fetchall()]
    conn.close()
    return render_template("viaturas.html", viaturas=vs, signature=APP_SIGNATURE)

# -----------------------------------------------------------------------------
# Protocolos (listar / editar / novo)
# -----------------------------------------------------------------------------
@app.route("/protocolos")
@login_required
@require_perm("protocolos:view")
def protocolos():
    conn = get_conn(); cur = conn.cursor()
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

        if not nome:
            flash("Indique o nome do protocolo.", "danger")
            return redirect(url_for("protocolo_novo"))

        try:
            frequencia = int(freq) if (freq or "").strip() != "" else None
            if frequencia is not None and frequencia < 0: raise ValueError
        except ValueError:
            flash("Frequência (dias) inválida.", "danger")
            return redirect(url_for("protocolo_novo"))

        conn = get_conn(); cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO protocolos (nome, passos_json, frequencia_dias, ativo) VALUES (?,?,?,?)",
                (nome, _passos_to_json(passos_txt), frequencia, ativo),
            )
            conn.commit()
            flash("Protocolo criado com sucesso.", "info")
            return redirect(url_for("protocolos"))
        except IntegrityError:
            flash("Já existe um protocolo com esse nome.", "danger")
            return redirect(url_for("protocolo_novo"))
        finally:
            conn.close()

    return render_template("protocolos_form.html", modo="novo", form={
        "nome": "", "frequencia_dias": "", "passos": "", "ativo": 1
    }, signature=APP_SIGNATURE)

@app.route("/protocolos/<int:pid>/editar", methods=["GET", "POST"])
@login_required
@require_perm("protocolos:edit")
def protocolo_editar(pid: int):
    conn = get_conn(); cur = conn.cursor()
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        freq = request.form.get("frequencia_dias")
        ativo = 1 if request.form.get("ativo") == "1" else 0
        passos_txt = request.form.get("passos", "")

        if not nome:
            flash("Indique o nome do protocolo.", "danger"); conn.close()
            return redirect(url_for("protocolo_editar", pid=pid))

        try:
            frequencia = int(freq) if (freq or "").strip() != "" else None
            if frequencia is not None and frequencia < 0: raise ValueError
        except ValueError:
            flash("Frequência (dias) inválida.", "danger"); conn.close()
            return redirect(url_for("protocolo_editar", pid=pid))

        try:
            cur.execute("""
                UPDATE protocolos
                   SET nome=?, passos_json=?, frequencia_dias=?, ativo=?
                 WHERE id=?
            """, (nome, _passos_to_json(passos_txt), frequencia, ativo, pid))
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

    cur.execute("SELECT * FROM protocolos WHERE id=?", (pid,))
    p = cur.fetchone(); conn.close()
    if not p:
        flash("Protocolo não encontrado.", "danger")
        return redirect(url_for("protocolos"))

    form = {
        "nome": p["nome"],
        "frequencia_dias": "" if p["frequencia_dias"] is None else int(p["frequencia_dias"]),
        "passos": _json_to_passos_text(p["passos_json"]),
        "ativo": p["ativo"],
    }
    return render_template("protocolos_form.html", modo="editar", pid=pid, form=form, signature=APP_SIGNATURE)

# -----------------------------------------------------------------------------
# Registos (lista / novo / anexos)
# -----------------------------------------------------------------------------
@app.route("/registos")
@login_required
@require_perm("registos:view")
def registos():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM vw_registos_detalhe ORDER BY datetime(data_hora) DESC, registo_id DESC")
    rs = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("registos.html", registos=rs, signature=APP_SIGNATURE)

@app.route("/registos/novo", methods=["GET", "POST"])
@login_required
def novo_registo():
    if not user_can("registos:create"):
        flash("Sem permissões para criar registos.", "danger")
        return redirect(url_for("sem_permissao"))

    conn = get_conn()
    cur = conn.cursor()

    if request.method == "POST":
        viatura_id = request.form.get("viatura_id")
        protocolo_id = request.form.get("protocolo_id")
        estado = request.form.get("estado", "concluido")
        observacoes = (request.form.get("observacoes") or "").strip()
        local = (request.form.get("local") or "").strip()
        hora_inicio = (request.form.get("hora_inicio") or "").strip()
        hora_fim = (request.form.get("hora_fim") or "").strip()
        extra_autorizada = 1 if request.form.get("extra_autorizada") == "1" else 0
        responsavel_autorizacao = (request.form.get("responsavel_autorizacao") or "").strip()
        funcionario_id = session.get("user_id")

        if not (viatura_id and protocolo_id):
            flash("Selecione viatura e protocolo.", "danger"); conn.close()
            return redirect(url_for("novo_registo"))

        # validação de horas
        def _is_hhmm(s):
            import re
            return bool(re.fullmatch(r"[0-2]\d:[0-5]\d", s))
        if hora_inicio and not _is_hhmm(hora_inicio):
            flash("Hora de início inválida (use HH:MM).", "danger"); conn.close()
            return redirect(url_for("novo_registo"))
        if hora_fim and not _is_hhmm(hora_fim):
            flash("Hora de fim inválida (use HH:MM).", "danger"); conn.close()
            return redirect(url_for("novo_registo"))
        if hora_inicio and hora_fim:
            d = datetime.now().date()
            t1 = datetime.fromisoformat(f"{d} {hora_inicio}:00")
            t2 = datetime.fromisoformat(f"{d} {hora_fim}:00")
            if t2 < t1:
                flash("Hora de fim não pode ser anterior à hora de início.", "danger"); conn.close()
                return redirect(url_for("novo_registo"))

        # já foi limpa hoje?
        cur.execute("""
            SELECT COUNT(*) FROM registos_limpeza
            WHERE viatura_id = ? AND date(data_hora) = date('now','localtime')
        """, (viatura_id,))
        ja_limpo_hoje = cur.fetchone()[0] > 0
        if ja_limpo_hoje and not (extra_autorizada and responsavel_autorizacao):
            flash("Atenção: esta viatura já foi limpa hoje. Nova limpeza só com autorização do responsável (indique o nome e marque a opção).", "danger")
            conn.close(); return redirect(url_for("novo_registo"))

        # inserir
        cur.execute("""
            INSERT INTO registos_limpeza
            (viatura_id, protocolo_id, funcionario_id, data_hora, estado, observacoes,
             local, hora_inicio, hora_fim, extra_autorizada, responsavel_autorizacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            viatura_id, protocolo_id, funcionario_id,
            datetime.now().isoformat(timespec="seconds"),
            estado, observacoes, (local or None),
            (hora_inicio or None), (hora_fim or None),
            extra_autorizada, (responsavel_autorizacao or None)
        ))
        registo_id = cur.lastrowid

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
                cur.execute(
                    "INSERT INTO anexos (registo_id, caminho, tipo) VALUES (?, ?, ?)",
                    (registo_id, str(path.relative_to(BASE_DIR)), "foto" if suf.lower() != ".pdf" else "pdf")
                )

        conn.commit(); conn.close()
        flash(f"Registo #{registo_id} criado com sucesso.", "info")
        return redirect(url_for("registos"))

    # GET: selects + mapa limpa_hoje
    cur.execute("SELECT id, matricula, descricao, num_frota FROM viaturas WHERE ativo=1 ORDER BY matricula")
    vs = [dict(row) for row in cur.fetchall()]
    cur.execute("SELECT id, nome FROM protocolos WHERE ativo=1 ORDER BY nome")
    ps = [dict(row) for row in cur.fetchall()]
    cur.execute("SELECT DISTINCT viatura_id FROM registos_limpeza WHERE date(data_hora) = date('now','localtime')")
    limpas_hoje = {r["viatura_id"] for r in cur.fetchall()}
    conn.close()

    limpa_hoje_map = {v["id"]: (v["id"] in limpas_hoje) for v in vs}
    return render_template("novo_registo.html", viaturas=vs, protocolos=ps, limpa_hoje_map=limpa_hoje_map, signature=APP_SIGNATURE)

@app.route("/registos/<int:registo_id>/anexos")
@login_required
@require_perm("registos:view")
def ver_anexos(registo_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, caminho, tipo FROM anexos WHERE registo_id=? ORDER BY id", (registo_id,))
    anex = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("anexos.html", registo_id=registo_id, anexos=anex, signature=APP_SIGNATURE)

@app.route("/anexos/<int:anexo_id>")
@login_required
@require_perm("registos:view")
def download_anexo(anexo_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT caminho FROM anexos WHERE id=?", (anexo_id,))
    row = cur.fetchone(); conn.close()
    if not row: abort(404)
    path = BASE_DIR / row["caminho"]
    if not path.exists(): abort(404)
    return send_file(path, as_attachment=True)

# -----------------------------------------------------------------------------
# Administração (utilizadores, perfis, import de viaturas)
# -----------------------------------------------------------------------------
@app.route("/admin")
@login_required
def admin_panel():
    if not (user_can("users:manage") or user_can("roles:manage") or user_can("viaturas:import")):
        flash("Sem permissões para Administração.", "danger")
        return redirect(url_for("sem_permissao"))
    return render_template("admin.html", signature=APP_SIGNATURE)

@app.route("/admin/users")
@login_required
@require_perm("users:manage")
def admin_users():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, username, nome, role, ativo, criado_em FROM funcionarios ORDER BY username")
    users = [dict(r) for r in cur.fetchall()]
    conn.close()
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT name FROM roles ORDER BY name")
    db_roles = [r["name"] for r in cur.fetchall()]
    conn.close()
    base_roles = sorted(PERMISSIONS.keys())
    roles = sorted(set(base_roles + db_roles))
    return render_template("admin_users.html", users=users, roles=roles, signature=APP_SIGNATURE)

@app.route("/admin/users/novo", methods=["GET","POST"])
@login_required
@require_perm("users:manage")
def admin_user_new():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        nome = (request.form.get("nome") or "").strip()
        password = request.form.get("password") or ""
        role = normalize_role(request.form.get("role"))
        ativo = 1 if request.form.get("ativo") == "1" else 0
        if not username or not password:
            flash("Username e password são obrigatórios.", "danger")
            return redirect(url_for("admin_user_new"))
        conn = get_conn(); cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO funcionarios (username,password,nome,role,ativo) VALUES (?,?,?,?,?)",
                (username, generate_password_hash(password), nome or username, role, ativo)
            )
            conn.commit(); flash("Utilizador criado.", "info")
            return redirect(url_for("admin_users"))
        except sqlite3.IntegrityError:
            flash("Username já existe.", "danger")
            return redirect(url_for("admin_user_new"))
        finally:
            conn.close()
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT name FROM roles ORDER BY name"); db_roles = [r["name"] for r in cur.fetchall()]
    conn.close()
    roles = sorted(set(PERMISSIONS.keys()) | set(db_roles))
    return render_template("admin_user_form.html", roles=roles, signature=APP_SIGNATURE)

KNOWN_PERMS = sorted({
    "dashboard:view","viaturas:view","viaturas:import",
    "protocolos:view","protocolos:edit",
    "registos:view","registos:create","registos:edit",
    "export:excel","users:manage","roles:manage","admin:panel"
})

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
            cur.execute("INSERT INTO roles (name) VALUES (?)", (name,))
            role_id = cur.lastrowid
            cur.executemany("INSERT INTO role_permissions (role_id, perm) VALUES (?,?)", [(role_id, p) for p in perms])
            conn.commit(); flash("Perfil criado.", "info")
            return redirect(url_for("admin_roles"))
        except sqlite3.IntegrityError:
            flash("Esse perfil já existe.", "danger")
            return redirect(url_for("admin_role_new"))
        finally:
            conn.close()
    return render_template("admin_role_form.html", perms=KNOWN_PERMS, signature=APP_SIGNATURE)

@app.route("/admin/import/viaturas", methods=["GET","POST"])
@login_required
@require_perm("viaturas:import")
def admin_import_viaturas():
    if request.method == "POST":
        file = request.files.get("ficheiro")
        if not file or file.filename == "":
            flash("Selecione um ficheiro CSV.", "danger"); return redirect(url_for("admin_import_viaturas"))
        data = file.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(data))
        required = {"matricula"}
        if not reader.fieldnames or not required.issubset({(h or "").lower() for h in reader.fieldnames}):
            flash("CSV precisa, no mínimo, da coluna 'matricula'.", "danger")
            return redirect(url_for("admin_import_viaturas"))

        conn = get_conn(); cur = conn.cursor()
        ins, upd = 0, 0
        for row in reader:
            matricula = (row.get("matricula") or row.get("MATRICULA") or "").strip()
            if not matricula: continue
            descricao = (row.get("descricao") or row.get("DESCRICAO") or "").strip() or None
            filial = (row.get("filial") or row.get("FILIAL") or "").strip() or None
            num_frota = (row.get("num_frota") or row.get("NUM_FROTA") or "").strip() or None
            ativo = row.get("ativo") or row.get("ATIVO")
            ativo = 1 if str(ativo).strip().lower() in {"1","true","sim","yes","y"} else 1  # default 1

            cur.execute("SELECT id FROM viaturas WHERE matricula=?", (matricula,))
            ex = cur.fetchone()
            if ex:
                cur.execute("""UPDATE viaturas
                               SET descricao=?, filial=?, num_frota=?, ativo=?
                               WHERE id=?""", (descricao, filial, num_frota, ativo, ex["id"]))
                upd += 1
            else:
                cur.execute("""INSERT INTO viaturas (matricula, descricao, filial, num_frota, ativo)
                               VALUES (?,?,?,?,?)""", (matricula, descricao, filial, num_frota, ativo))
                ins += 1
        conn.commit(); conn.close()
        flash(f"Importação concluída: {ins} inseridas, {upd} atualizadas.", "info")
        return redirect(url_for("viaturas"))

    return render_template("admin_import_viaturas.html", signature=APP_SIGNATURE)

# -----------------------------------------------------------------------------
# Export Excel
# -----------------------------------------------------------------------------
@app.route("/export/excel")
@login_required
@require_perm("export:excel")
def export_excel():
    import pandas as pd
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM vw_registos_detalhe ORDER BY datetime(data_hora) DESC, registo_id DESC", conn)
    conn.close()
    fname = EXPORT_DIR / f"registos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(fname, index=False)
    return send_file(fname, as_attachment=True)

# -----------------------------------------------------------------------------
# Arrancar
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)


# -----------------------------------------------------------------------------
# Importação de viaturas via Dashboard (não-admin)
# -----------------------------------------------------------------------------
@app.route("/viaturas/importar", methods=["GET","POST"])
@login_required
@require_perm("viaturas:import")
def importar_viaturas():
    if request.method == "POST":
        file = request.files.get("ficheiro")
        if not file or file.filename == "":
            flash("Selecione um ficheiro CSV.", "danger"); return redirect(url_for("importar_viaturas"))
        raw = file.read()
        text, enc = _read_csv_text_with_encoding_guess_bytes(raw)
        # cortar trailing campos vazios e detetar delimitador
        delim = _detect_delimiter(text[:4096])
        # construir reader manual para ignorar milhares de colunas vazias
        import csv as _csv, io as _io
        sio = _io.StringIO(text)
        rows = []
        reader = _csv.reader(sio, delimiter=delim)
        try:
            header = next(reader)
        except StopIteration:
            flash("CSV vazio.", "danger"); return redirect(url_for("importar_viaturas"))
        # Normalizar cabeçalhos e reduzir ao núcleo conhecido
        norm_headers = [ _normalize_header(h) for h in header ]
        # indices de interesse
        wanted = ["matricula","num_frota","regiao","operacao","marca","modelo","ativo"]
        idx = { w: (norm_headers.index(w) if w in norm_headers else -1) for w in wanted }
        if idx["matricula"] == -1:
            flash("CSV requer pelo menos a coluna 'Mat.' ou 'Matricula'.", "danger"); return redirect(url_for("importar_viaturas"))
        # iterar linhas
        for row in reader:
            def val(key):
                i = idx[key]
                if i == -1 or i >= len(row): return ""
                return (row[i] or "").strip()
            rows.append({
                "matricula": val("matricula"),
                "num_frota": val("num_frota"),
                "regiao": val("regiao"),
                "operacao": val("operacao"),
                "marca": val("marca"),
                "modelo": val("modelo"),
                "ativo": val("ativo"),
            })
        # persistir
        conn = get_conn(); cur = conn.cursor()
        ins, upd = 0, 0
        for r in rows:
            m = r["matricula"]
            if not m: continue
            cur.execute("SELECT id FROM viaturas WHERE matricula=?", (m,))
            ex = cur.fetchone()
            ativo = _as_bool(r["ativo"])
            num_frota = r["num_frota"] or None
            regiao = r["regiao"] or None
            operacao = r["operacao"] or None
            marca = r["marca"] or None
            modelo = r["modelo"] or None
            if ex:
                cur.execute("""UPDATE viaturas
                                  SET num_frota=COALESCE(?, num_frota),
                                      regiao=COALESCE(?, regiao),
                                      operacao=COALESCE(?, operacao),
                                      marca=COALESCE(?, marca),
                                      modelo=COALESCE(?, modelo),
                                      ativo=?
                                WHERE id=?""",
                            (num_frota, regiao, operacao, marca, modelo, ativo, ex["id"]))
                upd += 1
            else:
                cur.execute("""INSERT INTO viaturas
                               (matricula, num_frota, regiao, operacao, marca, modelo, ativo)
                               VALUES (?,?,?,?,?,?,?)""",
                            (m, num_frota, regiao, operacao, marca, modelo, ativo))
                ins += 1
        conn.commit(); conn.close()
        flash(f"Importação concluída (encoding: {enc}): {ins} inseridas, {upd} atualizadas.", "info")
        return redirect(url_for("viaturas"))
    # GET
    return render_template("admin_import_viaturas.html", signature=APP_SIGNATURE)
