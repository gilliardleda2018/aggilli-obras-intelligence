# Checklist de implementação dos agentes em novos produtos

## Levantamento inicial
- [ ] Confirmar repositório, branch padrão, HEAD e PRs em paralelo.
- [ ] Ler AGENTS.md, documentos de sincronia, fluxos atuais e modelo de permissão.
- [ ] Mapear entidades, autorizadores, datas, unidades, fontes e operações proibidas.
- [ ] Identificar onde o código está: default branch x feature branches.
- [ ] Delimitar caminhos editáveis, CI/artefatos e responsáveis.

## Guardas transversais
- [ ] Nunca inserir segredos, PII, tokens, extratos ou dados reais em logs ou fixtures.
- [ ] Adoção fail-closed quando a identidade, tenant ou origem é desconhecida.
- [ ] Nenhuma alteração financeira, fiscal, clínica/veterinária ou agropecuária automática em fase advisory.
- [ ] Sem alteração de UI por outra frente sem coordenação.
- [ ] Testes de negação de acesso e fronteira organizacional/fazenda/filial.
- [ ] Precisão de valores, unidades e datas; ausência de previsões inventadas.
- [ ] Sem writes inclusive `ForecastRun`, auditoria ou cache persistente no endpoint read-only.
- [ ] PR independente para cada domínio e testes de regressão de produção.
- [ ] Evidências separadas: unit, integração, frontend, staging, produção e aceite visual.

## Handoff portável
`repository`, `main_sha`, `branch`, `pr`, `agent`, `domain`, `scope`, `owners`, `paths`, `ci_runs`, `test_counts`, `production_evidence`, `missing`, `next_action`.

Sem inventar estado para preencher os campos. Registros desconhecidos permanecem PENDENTE/NÃO VERIFICADO.
