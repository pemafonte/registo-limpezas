@echo off
REM Ativa o ambiente virtual (se usares)
cd /d "C:\Projetos\Registo de limpezas"
call venv\Scripts\activate

REM Define a secret key de produção (altera para a tua chave forte!)
set APP_SECRET_KEY=uma-chave-secreta-muito-forte

REM Arranca o servidor WSGI com Waitress na porta 8000
waitress-serve --port=8000 AppFlaskLimpeza_final_clean3_LOGIN_RBAC:app

pause