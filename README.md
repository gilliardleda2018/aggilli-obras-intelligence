# Aggilli Obras Intelligence

Plataforma SaaS de gestão e acompanhamento de obras públicas e privadas.

## Estado
Scaffold inicial demonstrativo. **Não pronto para produção**: não possui autenticação, persistência, autorização ou medições reais.

## Executar backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest -q
```
No Windows, use `.venv\\Scripts\\activate`.

## Executar frontend
```bash
cd frontend
npm install
npm run dev
```
Abra http://localhost:3000. O backend deve estar em http://localhost:8000.

## Documentação
- [Arquitetura](docs/ARQUITETURA.md)
- [Roadmap](docs/ROADMAP.md)
