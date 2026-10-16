# Aggilli Obras Full — Documento mestre (proposta de produto)

Status: **planejado / fundação técnica em PR #24; não disponível comercialmente como pagamentos reais**. Data-base: 16/10/2026.

## Visão
O Aggilli Obras Intelligence oferece uma edição Professional para gestão de obras e uma edição Full com recursos financeiros premium. Full é uma licença por organização, não uma conta Stripe compartilhada entre clientes. Cada construtora conserva sua titularidade financeira, segregação de dados, responsabilidades de autorização e comprovantes.

## Edições
| Capacidade | Professional | Full (após homologação) |
|---|---|---|
| Obras, medições, contratos, FOPAG, OCR, mapas e previsibilidade | Incluído conforme módulos implantados | Incluído |
| Contas a pagar/receber e programação | Gestão e registros disponíveis conforme versão | Fluxo ampliado |
| Cobranças digitais | Não incluído | Stripe Payments/Connect quando elegível |
| Pagamentos automáticos a fornecedores | Não incluído | Global Payouts somente após habilitação específica |
| Conciliação de webhooks, trilha e aprovação | Registro interno | Automatização auditável |
| Suporte, limites e SLA | A definir | A definir |

Não publicar preço, SLA ou disponibilidade de Global Payouts antes de aprovação comercial, compliance e validação operacional.

## Fluxos separados
1. Receber de clientes: cobrança → autenticação da organização → checkout/payment intent → webhook assinado → lançamento contábil → conciliação. Para construtoras recebendo de seus próprios clientes, avaliar Stripe Connect em modelo SaaS, direct charges e responsabilidade do merchant of record.
2. Pagar fornecedores: contrato conciliado → obrigação → destinatário/KYC → aprovação do responsável financeiro → disponibilidade e elegibilidade do provedor → envio com idempotency key → status assíncrono → comprovante e baixa auditada. **Não** confundir payout do saldo Stripe com pagamento avulso a fornecedores.

## Gates técnicos
- Entitlements de plano Full validados no servidor, por organização.
- Capabilities reais do provedor verificadas periodicamente; fail closed.
- Reconciliação de contrato, centro de custo, obra e titularidade obrigatória.
- Aprovação explícita e segregação de funções; maker-checker.
- Sem pagamentos duplicados: idempotência e unique constraints; outbox/webhook inbox e reconciliação.
- Webhooks com assinatura, tolerância temporal, eventos fora de ordem e deduplicação.
- Dados bancários tokenizados no provedor; segredos no AWS Secrets Manager; nunca no frontend.
- Ledger imutável e auditoria de toda mudança de estado.
- Limites, antifraude, chargebacks, estornos, LGPD e retenção de evidências.
- Testes sandbox, concorrência, recuperação de falhas, rollback e produção com transação real de baixo valor apenas após autorização específica de valor/destinatário.

## Situação Stripe confirmada pelo MCP
Conta BR `acct_1UKLi97j9vfOPAsC`, livemode true. Em 16/10/2026: charges_enabled=false, payouts_enabled=false, card_payments/boleto_payments/transfers pending, zero contas Connect. Dois webhooks existentes pertencem a outras aplicações e não devem ser alterados. Elegibilidade de Global Payouts **não confirmada**. Solicitação de avaliação enviada pelo usuário à Stripe; aguardar resposta.

## Dependências e rastreabilidade
- PR #19: OCR de outra instância, independente.
- PR #22: proteção de importação FOPAG divergente, Draft.
- PR #23: avaliação de elegibilidade e arquitetura Stripe, Draft.
- PR #24: fundação fail-closed Full, Draft.
- PRs #20 e #21: importador e mensagens de interface, incorporados à main.
- Não alterar frontend/layout, OCR, dados financeiros reais ou infraestrutura sem revisão e homologação.

## Critérios de conclusão
Nenhuma funcionalidade de pagamento real é considerada entregue antes de elegibilidade Stripe, testes de ponta a ponta, revisão de segurança, CI verde, aceite financeiro e deploy verificado. A licença Full pode ser comercializada apenas com descrição fiel dos recursos efetivamente disponíveis.
