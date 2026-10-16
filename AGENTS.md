# Instruções de agentes — Aggilli Obras Intelligence

Antes de qualquer trabalho neste repositório, consulte a skill
[`emobras-guardian`](.agents/skills/emobras-guardian/SKILL.md).

Use-a para tarefas de implementação, auditoria, homologação, deploy e handoff. A skill não autoriza ações por si só: prevalecem o escopo do usuário, as permissões efetivas e os gates de segurança.

Pontos essenciais:
- Trabalhar em branch isolada e verificar PRs paralelos.
- Não alterar módulos fora do escopo nem sobrescrever trabalho de outra instância.
- Não declarar produção validada apenas por CI verde.
- Não executar pagamentos reais, migrações ou deploys sem autorização aplicável.
- Preservar layout e funcionalidades existentes.
- Registrar evidências e checkpoint de continuidade.
