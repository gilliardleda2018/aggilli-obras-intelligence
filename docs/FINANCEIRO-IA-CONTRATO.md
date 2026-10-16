# Financeiro IA — contrato de desenvolvimento (agente 3)

Status: descoberta e planejamento, não implementado.

## Missão
Auxiliar gestores na conciliação, projeção de caixa e análise de obrigações por obra e organização, sem executar pagamentos, sem inventar comprovação e sem sobrescrever saldos declarados.

## Primeira versão
1. Diagnóstico de despesas sem liquidação comprovada.
2. Conciliação de contratos com total, adiantamento e saldo declarado preservados.
3. Identificação de divergências com evidência e origem documental.
4. Alertas de pagamentos programados vencidos, sem transformar vencimento em pagamento.
5. Visão por obra, fornecedor e organização com isolamento multiempresa.
6. Recomendações consultivas, classificadas por prioridade, com código estável e rastreabilidade.

## Fontes e restrições
- PostgreSQL operacional e documento canônico `backend/data/tuntum_2026-08-28.json`.
- Contratos `labor_contracts`, despesas `expenses`, pagamentos `payments`, organização e memberships.
- Diferenças originais da FOPAG permanecem pendentes; não reconciliar por arredondamento nem substituir `reported_balance`.
- `SCHEDULED` não é `PAID`; Stripe/Global Payouts opcionais, sem habilitar movimentação nesta frente.
- Não acessar nem modificar módulos de mapas, OCR, autenticação ou Engenheiro IA.
- Não expor dados entre organizações, nem dados financeiros em rotas públicas.

## Gates de aceite
- Endpoint GET autenticado, sem escrita, com autorização por organização.
- Casos com e sem dados, pagamentos vencidos, duplicidade, saldo divergente e isolamento multiempresa.
- Testes sintéticos e CI; avaliação read-only em produção.
- Interface funcional e documentação de usuário.
- Deploy do agente isolado, sem regressão, com evidências de resposta autenticada.
- Não iniciar transações reais; aprovação específica necessária.

## Coordenação
Aplicar `AGENTS.md` e Guardian v1.4; branch isolada; não interferir nos PRs abertos de Stripe ou FOPAG.
