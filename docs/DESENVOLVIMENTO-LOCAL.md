# Desenvolvimento local

Um comando sobe o ambiente completo. Ele cria a identidade de desenvolvimento e o banco SQLite, aplica as migrações e a importação
de referência, e inicia a API (porta 8000) e o painel (porta 3100):

```powershell
powershell -ExecutionPolicy Bypass -File dev\run-local.ps1          # mantém o banco local
powershell -ExecutionPolicy Bypass -File dev\run-local.ps1 -Reset   # recria o banco local
```

Abra http://localhost:3100/login e clique em **Entrar como usuário de desenvolvimento**.

## Identidade de desenvolvimento
- `backend/scripts/dev_identity.py` gera uma chave RSA e um JWKS em `backend/.dev/` (fora do git) e emite tokens com issuer
  `https://dev-obras.localhost`.
- A API só aceita esse JWKS por `OIDC_JWKS_FILE`, que é **ignorado quando `APP_ENV=production`**.
- O painel só oferece a entrada de desenvolvimento com `ALLOW_DEV_LOGIN=1` e em localhost. Ela grava a mesma sessão cifrada do login real.
- O usuário `dev-owner` é OWNER da organização "Grupo MG (desenvolvimento)", criada pela importação.

## Testes
```bash
cd backend && python -m pytest -q        # unitários e integração (SQLite)
cd frontend && npm run lint && npm run build
```
Os testes de PostgreSQL e as migrações (upgrade, downgrade e upgrade de novo) rodam no CI.
