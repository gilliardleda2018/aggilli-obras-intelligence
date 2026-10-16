# Protocolo de colaboração entre instâncias

## Regra de propriedade
- Um agente por frente e branch; nunca dois escritores no mesmo arquivo sem handoff explícito.
- Identificar autor, módulo, branch, PR, base SHA, arquivos tocados e estado de testes no PR.
- Outros agentes podem auditar em leitura, mas não sobrescrever commits de uma frente.
- Antes de editar: verificar PRs abertos, commits recentes e arquivos compartilhados.
- Se houver conflito, registrar comentário no PR responsável, solicitar decisão e aguardar; não resolver silenciosamente descartando trabalho alheio.
- Coordenação é **assíncrona via GitHub e documentação**, não comunicação direta presumida entre sessões.

## Handoff verificável
1. Abrir `references/handoff.md` e preencher o checkpoint.
2. Distinguir **observado**, **inferido**, **não verificado** e **bloqueado**.
3. Referenciar evidências (commit SHA, workflow, logs sem segredos, testes).
4. Identificar pendências e próxima ação única, com responsável.
5. Ao assumir: confirmar a base atual e a situação do PR antes de executar.

## Frentes críticas
- OCR: preservar trabalho paralelo e contratos documentais.
- Mapas: mudanças somente na frente geográfica, chaves sempre no Secrets Manager.
- FOPAG: fonte canônica imutável; pagamentos programados não são liquidados.
- Autenticação: não remover guards para restaurar dados; investigar sessão e autorização.
- Deploy: não afirmar que CI verde significa publicação concluída.

## Política de arquivos compartilhados
Mudanças em `AGENTS.md`, `.github/workflows/*`, modelos, migrações, `frontend/lib/data.ts` e arquivos de infraestrutura exigem revisão do impacto transversal.
