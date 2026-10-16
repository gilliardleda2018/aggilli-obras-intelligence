# Aggilli Intelligence — Manual de Portabilidade de Agentes v1

## Finalidade

Transformar os quatro agentes criados no Em Obras em **contratos replicáveis**, sem copiar modelos de dados, endpoints, segredos, templates de UI nem autorizações entre produtos.

**Fonte:** Em Obras `main` auditada em 17/10/2026; implantação e testes anteriores do Guardian, Engenheiro IA, Financeiro IA e Auditor Documental IA. Em Obras possui três agentes consultivos de aplicação e uma Agent Skill de engenharia. Não são processos autônomos nem compartilham automaticamente uma identidade ou acesso ao banco.

**Destinos auditados:** `gilliardleda2018/aggilli-agro` (master, FastAPI + Streamlit/SQLite, API e módulo RFID/financeiro existentes) e `gilliardleda2018/mg_transports` (main contém apenas README de planejamento; capacidades presentes em PRs/branches ainda não incorporadas). As afirmações de maturidade devem ser reconfirmadas antes da implementação.

## Contrato universal de um agente consultivo

Entrada:
- `tenant_scope` derivado do servidor (nunca do modelo);
- `subject` autenticado e permissões/empresa/fazenda/obra autorizadas;
- `source_refs` verificáveis (IDs, hashes, versões, timestamps);
- `effective_date`, moeda/unidade e timezone explícitos;
- `domain_inputs` validados por schemas locais.

Saída:
- `agent`, `version`, `mode=advisory`, `scope`, `evaluated_on`;
- `findings[]` com `code`, `severity`, `message`, `recommended_action`, `evidence`, `source_refs`;
- `missing_inputs[]`, `limitations[]`, `writes_performed=false`.

Não usar `confidence` como garantia de exatidão sem calibração e dados de validação. Não inventar conteúdo ausente. Resultados de modelo generativo são sugestões não confiáveis até verificação determinística.

## Camadas separadas

1. **Guardian (governança do desenvolvimento):** Agent Skill carregada por Codex/Claude, CI, coordenação, revisão de escopo e critérios de homologação. Não executa tarefas de negócio.
2. **Adapter de domínio:** função local que lê dados autorizados e os traduz para o contrato do agente.
3. **Motor puro:** regras/cálculos que retornam findings e não importam banco, rede ou clientes de pagamento.
4. **Orquestração read-only:** endpoint/serviço com autorização de servidor, limites de consultas e paginação.
5. **UI contextual:** painel específico Streamlit/Next.js; não reutilizar JSX em Agro ou MG.
6. **Execução de ações:** proibida na fase consultiva; requer fluxo independente de confirmação humana, autorização, transação idempotente e auditoria.

## Regras de replicação

- Não copiar `backend/app/models.py` do Em Obras para Agro ou MG.
- Mapear `Organization/Project` para `Farm/Animal/Operation` no Agro e `Company/Branch/Trip/CTe` no MG apenas quando essas entidades existirem de fato no código e schema.
- Não reutilizar cookies, tokens, MFA, secrets, ARN ou credenciais de um produto no outro.
- Não alterar `app.py`, `brand.py`, `dashboard.py` e `modulos/*` do Agro fora da coordenação descrita em `AGENTS.md` e `docs/SINCRONIA.md`.
- Não tratar branches de MG como funcionalidades existentes em `main`. PRs #39/#45/#77 demonstram frentes em desenvolvimento, não uma base financeira homologada.
- Nada de `PAID` sem evidência; XML importado não significa CT-e/MDF-e emitido; dados RFID sem commit/reconciliação não implicam pesagem definitiva.
- Testar isolamento multi-tenant, negação de acesso, idempotência, concorrência, montantes exatos/unidades, ausência de writes, regressão e reconexão offline quando aplicável.
- Sem merge ou deploy por herança de uma homologação realizada em outro repositório.

## Matriz de portabilidade

| Agente de origem | Aggilli Agro | MG Transports |
|---|---|---|
| Guardian | Guardião de branches, perfis/fazendas, RFID, Windows e sync; respeitar ownership Claude/Codex | Guardião da arquitetura modular, implantação AWS e seis módulos |
| Engenheiro IA | Técnico Agro: GMD, pesagem, consumo, manejo, nutrição; somente evidências de dados válidos | Especialista Operacional TMS: viagens, fretes, consumo, manutenção e documentos de transporte |
| Financeiro IA | Análise de receitas/despesas por fazenda, competência, custo/animal e conciliação, usando centavos inteiros | A pagar/receber, acertos, OFX, adiantamentos e conciliação por empresa/filial |
| Auditor Documental IA | Notas, comprovantes, origem de registros, anexos e imagens; não associar documento à fazenda errada | XML NF-e, CT-e, MDF-e, GNRE, canhotos; sem emissão fiscal autônoma |

## Gates P0–P8

P0 leitura do repositório alvo, branch, PRs, ownership; P1 mapeamento de entidades; P2 contrato e exemplos; P3 testes sintéticos; P4 API autorizada; P5 UI integrada; P6 CI/revisão; P7 staging/deploy confirmado e regressões; P8 aceite funcional real e documentação. Cada etapa com SHA, workflow, evidência e responsável.

## Condição de replicação
A documentação e os adaptadores são portáveis. **Não existe agente replicado em produção até que haja implementação, testes, autorização e deploy independentes no repositório destino.**
