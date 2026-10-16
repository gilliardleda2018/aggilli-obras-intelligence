# Roadmap executável — Aggilli Obras Full

## Fase F00 — Governança e contratos (em andamento)
- [x] Visão e segmentação Professional/Full documentadas
- [x] Conta Stripe auditada em modo leitura
- [x] Política fail-closed isolada criada no PR #24
- [ ] Confirmação da elegibilidade Stripe e Global Payouts
- [ ] CI do PR #24, revisão de segurança e aprovação

## F01 — Licenciamento por organização
- Entitlements server-side, plano, limites, status, feature flags e auditoria.
- Upgrade/downgrade sem perda de dados; Professional não depende da Stripe.
- Testes multiempresa e concorrência.

## F02 — Persistência financeira aditiva
- Accounts, receivables, payables, attempts, recipients, webhook inbox, ledger, approvals.
- Decimal/centavos e constraints; migração reversível e validação PostgreSQL.
- Nunca reaproveitar registros FOPAG divergentes como pagamento confirmado.

## F03 — Recebimentos
- Onboarding de organização, Checkout/PaymentIntents/Connect conforme elegibilidade.
- Webhook próprio Aggilli Obras; validação de assinatura, replay e idempotência.
- Reconciliação de pagamento, falha, estorno, disputa e reembolso.

## F04 — Pagamentos a fornecedores / Global Payouts
- Confirmar produto, países, funding, requisitos KYC/KYB, limites e preços com Stripe.
- Adaptador de provedor desacoplado, modo simulado e habilitação por organização.
- Aprovação maker-checker, beneficiário verificado, saldo conciliado, idempotência.
- Bloquear integralmente execução real enquanto a capacidade não estiver aprovada.

## F05 — UX e manual
- Preservar identidade visual; adicionar recursos apenas quando disponíveis.
- Status transparente: programado, aprovado, processando, pago, falhou, estornado.
- Comprovantes, exportação e histórico; suporte a auditoria.

## F06 — Homologação e lançamento
- Testes sandbox e negativos, isolamento multiempresa, concorrência e falhas de webhook.
- Homologação de produção controlada com autorização de valor e destinatário.
- Segurança, monitoramento, suporte, documentação comercial e release notes.

## Regra de handoff
Cada fase deve registrar PR, SHA, arquivos, testes, evidências, riscos, estado de deploy, responsável e próxima ação. Nunca declarar concluído sem comprovação. Coordenação assíncrona com OCR/PR #19 para arquivos compartilhados.
