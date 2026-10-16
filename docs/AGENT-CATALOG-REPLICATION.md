# Catálogo técnico — quatro agentes originais do Em Obras

## Tipos de agente e capacidades reais

| Agente | Caminhos principais | Entradas | Saídas | Escrita |
|---|---|---|---|---|
| Guardian | `.agents/skills/emobras-guardian/SKILL.md`, `tools/guardian/check.py`, `tools/guardian/pr_scope.py`, `.github/workflows/guardian.yml` | Diff Git, PRs, políticas declaradas e evidências CI | Alertas de integridade e escopo (escopo em modo advisory) | Não atua no banco |
| Engenheiro IA | `backend/app/engineering_advisor.py`, `backend/app/intelligence.py`, `frontend/components/engineering-advice.tsx` | Projeto autorizado, medições aprovadas, serviços, custos reais, modelos existentes | Findings de dados insuficientes, prazo/custo e serviços críticos | Nenhuma na rota advisor |
| Financeiro IA | `backend/app/financial_advisor.py`, `frontend/components/financial-diagnosis.tsx` | Organização autorizada, contratos, despesas, pagamentos | Divergências de saldo, programação vencida, pagamento acima da despesa e falta de programação | Nenhuma |
| Auditor Documental IA | `backend/app/document_advisor.py`, `frontend/components/document-audit.tsx` | Documento autorizado, OCR persistido, SHA-256, obra sugerida | Pendências de OCR, campos e obra, rastreabilidade | Nenhuma |

## Endpoints da implementação de origem

- `GET /api/v1/projects/{project_id}/engineering-advice`
- `GET /api/v1/finance-agent/diagnosis`
- `GET /api/v1/document-auditor/diagnosis`

Todos requerem dependências de autenticação, e o escopo é conferido pelo servidor. Nunca copiar essas rotas e seus modelos diretamente para o Agro ou MG.

## Estados de aceitação diferentes
- **Integrado ao código:** merge Git.
- **Testado:** execução CI do SHA.
- **Publicado:** workflow de deploy e rollout do serviço.
- **Motor validado:** teste contra base real com autorização e sem escrita.
- **E2E autenticado:** navegação e resposta efetiva com sessão real, independentemente dos anteriores.
- **Governança advisory:** a política de PR não equivale a branch protection obrigatória.

## Casos de teste replicáveis

1. Cenário de entradas ausentes devolve lista de faltantes; não devolve estimativas sem suporte.
2. Alteração em escopo de organização/fazenda/filial alheio devolve 403/404 ou coleção vazia, conforme contrato.
3. Valores `Decimal`, centavos e unidades preservados; nenhuma baixa `PAID` por suposição.
4. Documento/captura tem origem e hash quando disponíveis; não inventar identificadores.
5. Projeções repetidas com mesmos dados são determinísticas, sem efeitos colaterais na rota consultiva.
6. Rota sem autorização não retorna dados; tentativas de entrada malformada falham de forma controlada.
7. UI diferencia dados insuficientes, indisponibilidade da API e ausência de alertas.
8. Conclusão exige evidências específicas do produto e consentimento para efeitos.

## Particularidades do acervo
- `Em Obras`: FOPAG preserva saldos declarados e divergências, pagamentos `SCHEDULED`.
- `Agro`: fazenda/animal/unidade, GMD, peso, RFID, offline, permissões por perfil; não confundir inferência de voz com dado persistido.
- `MG`: empresa/filial, OFX, frete, CT-e/MDF-e, autorização fiscal e dados de terceiros; branch principal ainda somente documental na auditoria inicial.

Este catálogo é um **contrato de portabilidade**, não uma biblioteca Python publicada nem um pacote instalável. Reutilização futura pode extrair `Finding` e interfaces puras após validar versões e regras em cada domínio.
