# Em Obras Guardian — Manual de operação

A skill está em `.agents/skills/emobras-guardian/SKILL.md` e é descoberta por `AGENTS.md`. Ela define um protocolo para agentes de desenvolvimento; **não é um agente autônomo em execução contínua**, nem concede credenciais ou permissões.

## Como usar
1. Solicitar ao agente: "Leia AGENTS.md e a skill emobras-guardian antes de trabalhar."
2. Informar frente, escopo e critérios de aceite; agente consulta PRs e SHA atuais.
3. Exigir branch isolada, checklist de regressão e evidências de CI.
4. Para outra instância assumir, preencher o modelo de handoff e anexar ao PR.
5. Antes de produção, executar os gates em `references/production-gates.md`.

## Frentes sugeridas
- Guardian: coordenação, revisão, segurança, CI e documentação.
- Engenheiro IA: medições, produtividade, cronograma e previsões com evidência.
- Financeiro IA: despesas, contratos, conciliação e fechamento, sem pagamentos automáticos.
- Auditor Documental IA: OCR, FOPAG e proveniência, sem inventar dados.

## Estado de referência (não autoritativo)
O projeto já possui FOPAG importada, contratos e pagamentos programados; qualquer agente deve confirmar novamente o estado do banco e o último deploy. A autorização para desenvolver uma skill não equivale a autorização para alterar dados financeiros.

## Limitações
Arquivos Markdown por si só não garantem execução das instruções por todo agente. O agente precisa carregar a skill; a aplicação Em Obras não ganha funcionalidades de IA voltadas ao usuário apenas por incorporar estes arquivos.
