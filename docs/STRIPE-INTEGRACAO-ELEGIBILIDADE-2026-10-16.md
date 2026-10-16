# Stripe — elegibilidade e integração segura (2026-10-16)

## Escopo e conta
Conta Stripe conectada: `acct_1UKLi97j9vfOPAsC`, país BR, livemode true. Consultas feitas pelo conector MCP, **somente leitura**.

**Estado real observado:**
- `charges_enabled=false`
- `payouts_enabled=false`
- capabilities: `card_payments=pending`, `boleto_payments=pending`, `transfers=pending`
- connected accounts: 0
- Dois webhooks existentes, vinculados a outros sistemas (Rebecca Hub e endpoint CloudFront). **Não reutilizar ou alterar**.
- Nenhuma cobrança, transferência, destinatário ou pagamento criado.

**Consequência:** pagamentos e repasses reais não estão habilitados. Não tentar contornar os requisitos Stripe nem assumir que Global Payouts/Connect estão liberados por haver uma conta em modo real.

## Arquitetura proposta (dois fluxos distintos)
1. **Recebimentos de clientes de obras:** modelo SaaS vertical. Cada construtora/organização é a titular comercial de seus recebimentos; avaliar Connect com contas conectadas e direct charges, ou pagamento direto na conta Stripe da própria organização. Nunca misturar recursos financeiros de empresas distintas.
2. **Pagamentos a fornecedores/empreiteiros:** não equivalem a payouts do saldo Stripe da plataforma. Verificar habilitação específica de Global Payouts ou outro provedor de pagamentos a terceiros, jurisdição, KYC, titularidade, funding e custos. Se não habilitado, manter registro interno de programação/baixa por comprovante, sem transferência automática.

## Modelo de dados mínimo (migração aditiva futura)
- `payment_provider_accounts`: organization_id, provider, provider_account_id, capabilities, verified_at.
- `receivables`: organization_id, project_id, customer_id, currency, amount_minor, status, external_reference.
- `payment_attempts`: receivable_id, provider_payment_id, idempotency_key unique, state.
- `payout_recipients`: organization_id, supplier_id, provider_recipient_id, kyc_status.
- `payables`: organization_id, project_id, supplier_id, source_contract_id, amount_minor, status, approved_by.
- `payout_attempts`: payable_id, provider_payout_id, idempotency_key unique, state.
- `provider_events`: provider_event_id unique, event_type, payload_hash, processed_at, outcome.
- `ledger_entries`: organization_id, event_id, debit, credit, currency, immutable audit trail.

## Gates obrigatórios
1. Stripe account charges/payouts capabilities ACTIVE; verificar requisitos de verificação no Dashboard.
2. Confirmar elegibilidade real de Connect e/ou Global Payouts para BR e finalidade de pagamento a empreiteiros.
3. Criar endpoint webhook **próprio do Aggilli Obras** somente após implementar assinatura Stripe, replay protection, deduplicação e trilha de auditoria. Não alterar endpoints existentes.
4. Testes sandbox: sucesso, falha, cancelamento, reembolso, disputa, webhook repetido/fora de ordem, isolamento de organização, concorrência e idempotência.
5. Testes financeiros reais somente com destinatários e valores explicitamente aprovados, após reconciliação contratual.
6. FOPAG com divergências deve permanecer bloqueada pelo PR #22 até comprovação dos saldos; não gerar pagamento real a partir de valores divergentes.
7. Nenhuma credencial Stripe no GitHub, frontend, logs ou chat; usar Secrets Manager.
8. Layout e OCR preservados. Sem merge/deploy desta integração até os gates.

## Dependências atuais
- PR #22 Draft: proteção de conciliação FOPAG, CI verde.
- PR #19 Draft: OCR independente.
- PR #20 e #21 já incorporados à main e deploy concluído.

## Fontes oficiais
- https://docs.stripe.com/connect/saas
- https://docs.stripe.com/connect/marketplace
- https://stripe.com/payouts
- https://support.stripe.com/questions/brazil-updates-to-verification-requirements-for-connected-accounts-of-platforms

## Próxima ação operacional
Concluir onboarding/verificação da conta Stripe e confirmação das capabilities; solicitar habilitação de Global Payouts, caso o produto seja elegível. Após confirmação, implementar backend e migrações aditivas em PR próprio, com testes sandbox antes de qualquer movimento financeiro real.
