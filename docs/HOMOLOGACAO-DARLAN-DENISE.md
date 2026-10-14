# Homologação operacional — Darlan e Denise

## Fluxo Darlan
1. Login com identidade Descope individual.
2. Membership FIELD_OPERATOR, restrita à organização correta.
3. Abrir obra autorizada em /operacao/{project_id}.
4. Criar despesa de material, fornecedor, valor e descrição.
5. Confirmar persistência e auditoria.
6. Não permitir programar ou confirmar pagamentos.

## Fluxo Denise
1. Login com identidade Descope individual.
2. Membership ADMIN ou OWNER no modelo atual (ainda não existe papel FINANCE).
3. Abrir a obra autorizada e visualizar despesas.
4. Programar pagamento sem ultrapassar o saldo da despesa.
5. Confirmar somente com referência verificável de pagamento.
6. Impedir confirmação duplicada e acesso a outra organização.

## Estado e restrições
Formulários Next.js usam Server Actions e a sessão de usuário existente para chamar APIs.
O token obtido pela integração Descope SDK da rota /login ainda NÃO é integrado à sessão OIDC do servidor. Assim, não há E2E real concluído.
Comprovantes são somente referências textuais; upload S3 ainda não implementado.
Não provisionar usuários reais sem identificação segura e confirmação de papéis.
Não afirmar homologação real antes de testar ambos os logins, memberships, writes e logs.
