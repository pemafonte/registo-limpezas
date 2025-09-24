# Registo de Limpezas - Deploy no Render

Sistema de registo de limpezas de viaturas desenvolvido em Flask, preparado para deploy na plataforma Render.

## 📋 Arquivos para Deploy

Foram criados os seguintes arquivos no seu diretório de projeto:

1. **`app.py`** - Versão base para deploy (você deve copiar o código completo do arquivo original)
2. **`requirements_render.txt`** - Dependências para o Render
3. **`render.yaml`** - Configuração automática do Render
4. **`README_DEPLOY.md`** - Este arquivo com instruções

## 🚀 Instruções de Deploy

### Passo 1: Preparar o Código

1. **Copie todo o conteúdo** do arquivo `AppFlaskLimpeza_final_clean3_LOGIN_RBAC.py` 
2. **Cole no arquivo** `app.py` (substituindo o conteúdo atual)
3. **Faça estas alterações no final do arquivo `app.py`**:

```python
# Substitua a linha final:
# if __name__ == "__main__":
#     app.run(debug=True)

# Por esta:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
```

### Passo 2: Criar Repositório Git

```bash
# No diretório do projeto:
git init
git add .
git commit -m "Preparar para deploy no Render"
git branch -M main
git remote add origin https://github.com/pemafonte/app.git
git push -u origin main
```

### Passo 3: Deploy no Render

1. **Acesse**: https://dashboard.render.com
2. **Novo serviço**: "New +" → "Blueprint"
3. **Conecte o repositório** Git
4. **O Render criará automaticamente**:
   - Aplicação web
   - Base de dados PostgreSQL
   - Todas as configurações

### Passo 4: Acesso Inicial

- **URL**: Fornecida pelo Render após deploy
- **Login**: admin
- **Password**: 1234

## 📁 Localização dos Arquivos

Os arquivos foram criados em:
```
C:\Projetos\Registo de limpezas\
├── app.py                    (para completar)
├── requirements_render.txt   (pronto)
├── render.yaml              (pronto)
└── README_DEPLOY.md         (este arquivo)
```

## ⚠️ Importante

- Mantenha o arquivo original como backup
- Altere a password do admin após primeiro login
- Configure as variáveis de ambiente no Render se necessário

---
**Desenvolvido por Pedro Fonte**