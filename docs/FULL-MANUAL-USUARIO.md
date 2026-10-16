# Manual do usuário — Aggilli Obras Full (conteúdo preparatório)

**Atenção:** as telas e operações descritas abaixo são fluxos-alvo do módulo Full; não afirmar que estão disponíveis na versão atual.

## Para o administrador da construtora
1. Contratar/ativar Full e verificar a organização.
2. Concluir onboarding financeiro no provedor habilitado, sem compartilhar senhas.
3. Definir responsáveis: solicitante, aprovador financeiro e auditor.
4. Associar obras, centros de custo, contratos e clientes à organização correta.

## Receber de clientes
1. Criar cobrança vinculada à obra e ao cliente.
2. Conferir valor e vencimento; emitir link/checkout quando a função estiver habilitada.
3. Aguardar confirmação do provedor; não considerar pago apenas por retorno visual do navegador.
4. Consultar comprovante, histórico e conciliação.

## Pagar empreiteiros e fornecedores
1. Cadastrar obrigação e anexar contrato/nota/comprovante.
2. Conciliar saldo contratual; divergência bloqueia liberação.
3. Validar beneficiário, titularidade e autorização.
4. Solicitar e aprovar pagamento por pessoa autorizada.
5. Acompanhar status do provedor e registrar comprovante de liquidação.

## Situações e erros
- **Pendente de habilitação:** recurso indisponível na Stripe; não há envio de dinheiro.
- **Contrato divergente:** conciliar documentos antes de aprovar.
- **Destinatário não verificado:** completar KYC/KYB.
- **Pagamento em processamento:** não repetir manualmente; verificar idempotência/status.
- **Falha/estorno:** investigar evento e registrar reconciliação; não marcar como pago.
- **Plano Professional:** acesso a pagamentos automáticos não habilitado.

## Segurança
Nunca enviar API keys, senhas ou dados bancários completos pelo chat. Use apenas os fluxos oficiais de autenticação. Comprovantes e extratos devem ser protegidos por permissões e retenção LGPD.
