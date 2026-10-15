# Plano de homologação integrada

## Critérios para encerrar PR #1
1. CI verde no SHA final, incluindo migrações PostgreSQL upgrade/downgrade.
2. OIDC real: JWT com assinatura, issuer, audience e exp verificados; sessão web por usuário.
3. Isolamento multiempresa: leitura, escrita, exportação e IDOR testados.
4. Concorrência: aprovação simultânea de medições e saídas de estoque no PostgreSQL.
5. Validação dos pesos, quantitativos, estornos, trilha de auditoria e migrações.
6. Testes funcionais de interface autenticada e revisão de segurança.
7. Homologação em ambiente isolado com dados sintéticos e evidências.

## Sequência
- Corrigir o modelo de sessão frontend (não utilizar token compartilhado).
- Configurar provedor OIDC e validar fluxo login/logout/callback.
- Executar testes transacionais com duas sessões reais no PostgreSQL.
- Produzir evidências dos testes e revisar PR.
- Somente então marcar ready-for-review e realizar merge.

## Não fazer
Não provisionar produção, criar usuários reais ou ativar pagamentos sem configuração e validação específicas.
