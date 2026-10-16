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


## Aggilli Obras Full — documentação oficial em preparação

O módulo financeiro premium **Full** está em desenvolvimento, com ativação de pagamentos reais condicionada à elegibilidade do provedor e à homologação. Consulte:

- [Visão oficial do produto](docs/FULL-VISAO-OFICIAL.md)
- [Roadmap de implementação](docs/FULL-ROADMAP-IMPLEMENTACAO.md)
- [Manual do usuário — conteúdo preparatório](docs/FULL-MANUAL-USUARIO.md)
- [Proposta comercial modelo](docs/FULL-PROPOSTA-COMERCIAL.md)
- [Auditoria Stripe e elegibilidade (PR #23)](https://github.com/gilliardleda2018/aggilli-obras-intelligence/pull/23)

Nenhum recurso de Global Payouts deve ser anunciado como ativo antes da confirmação formal da Stripe.
