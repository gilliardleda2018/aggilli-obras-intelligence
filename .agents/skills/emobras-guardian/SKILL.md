---
name: emobras-guardian
description: "Auditar, implementar, testar e coordenar alterações no Aggilli Obras Intelligence sem regressões, respeitando escopo, branches paralelas, segurança financeira e gates de produção. Use antes de qualquer tarefa de código, AWS, deploy, importação, mapas, OCR ou pagamentos."
---

# Em Obras Guardian — Skill oficial dos agentes

## Objetivo
Executar entregas verificáveis, sem confundir código implementado, CI aprovado, merge, deploy e funcionamento real. Trabalhar em português, com evidências e checkpoints concisos. Não assumir que um estado relatado em outro chat continua atual.

## Ativação e descoberta obrigatória
1. Identificar a solicitação, escopo autorizado, operações proibidas e critérios de aceite.
2. Consultar `main`, PRs abertos, branches, último SHA, workflows e documentação aplicável antes de modificar arquivos.
3. Verificar se outra instância trabalha no mesmo módulo. Ler `docs/COORDENACAO-FRENTES-E02-OCR.md` e registrar conflitos potenciais.
4. Inspecionar o código real e os contratos atuais. Não confiar somente em resumos antigos.
5. Se o pedido for auditoria somente leitura, não criar commits, tarefas de escrita, migrações ou deploys.

## Restrições absolutas
- Preservar layout, navegação, permissões, persistência, OCR, mapas e financeiro fora do escopo autorizado.
- Nunca inserir secrets em commits, PRs, logs, respostas ou arquivos de teste.
- Não inventar valores financeiros, percentuais de avanço, coordenadas, comprovantes ou resultados de testes.
- Nunca marcar `PAID` por mera programação, checkout aberto, simulação ou webhook não verificado.
- Não importar contratos FOPAG divergentes como despesas liquidadas. Consultar `docs/E02-FOPAG-RECONCILIATION.md` e `docs/FINANCEIRO-FECHAMENTO-NACIONAL-BR.md` quando disponíveis na branch.
- Stripe/Global Payouts não é requisito para o núcleo financeiro e só pode movimentar dinheiro quando a capacidade e a autorização específica estiverem comprovadas.
- Não interferir no PR #19 de OCR sem coordenação explícita. Outros PRs/SHAs devem ser redescobertos a cada execução.

## Fluxo de trabalho
### G0 — Baseline
Registrar SHA da `main`, branch de trabalho, PRs relacionados, CI atual e estado de produção. Conferir arquivos compartilhados.

### G1 — Plano de mudança
Definir arquivos exatos, dependências, migrações, riscos, testes, rollback e critérios objetivos. Escolher o menor patch que resolva a causa comprovada.

### G2 — Implementação
Branch isolada; commits pequenos; testes determinísticos; migrações aditivas quando necessárias. Evitar mudanças de estilo e refatorações não relacionadas.

### G3 — Verificação
Executar CI backend/frontend, testes de isolamento multiempresa, idempotência, concorrência, segurança e regressão conforme o módulo. Para banco, usar PostgreSQL de teste e comparar migrações. Não declarar E2E quando apenas unitários passaram.

### G4 — Homologação
Verificar fluxos autenticados e persistência real com dados sintéticos. Separar simulação, leitura de produção e operação financeira real. Requerer comprovantes para saldos divergentes.

### G5 — Publicação
Merge/deploy somente com autorização aplicável, gates satisfeitos e proteção dos módulos vizinhos. Confirmar SHA publicado, workflow de deploy, ECS/API/web, health e evidência funcional; rollback se houver regressão.

### G6 — Handoff
Atualizar documento de checkpoint com: objetivo, escopo, branch, PR, SHA, arquivos alterados, testes e links, resultado, riscos, bloqueios, estado de produção e próxima ação. Não anunciar sucesso não comprovado.

## Módulos e atenção especial
- **Mapas:** `docs/MAPAS.md`, `backend/app/geo.py`, componentes de mapa; chaves no AWS Secrets Manager, sem revelar valores; tarefas ECS precisam reiniciar para ler nova versão do segredo; Google Map ID e restrições de API devem ser verificados. Nunca inventar localização.
- **Financeiro/FOPAG:** contrato, adiantamento, retenção, contas a pagar/receber, conciliação e fechamento são conceitos distintos. Simulação não é pagamento real.
- **OCR:** frente paralela, contratos de extração e documentação próprios.
- **Stripe:** consultar capacidades reais via conector e manter o módulo opcional, sem reusar webhooks de outras aplicações.
- **Deploy:** verificar `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, `docs/DEPLOY-AWS.md` e infraestrutura atual; o merge pode disparar deploy/migrações.

## Resposta final padronizada
Apresentar somente fatos verificados: **implementado**, **testado**, **integrado**, **publicado**, **validado em produção**, **pendente**. Cada status precisa de evidência (SHA, workflow, consulta ou teste). Não confundir intenção com execução.

## Materiais de apoio
- [Checklist de aceitação](references/checklist.md)
- [Modelo de checkpoint](references/handoff.md)
