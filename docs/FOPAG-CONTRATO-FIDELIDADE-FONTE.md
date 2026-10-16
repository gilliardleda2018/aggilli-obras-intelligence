# Contrato de fidelidade — FOPAG real de Tuntum, 28/08/2026

Status: **fonte documental reconhecida, persistência financeira de produção pendente de homologação**.

## Fonte canônica
- `backend/data/tuntum_2026-08-28.json` reproduz a FOPAG e os relatos fornecidos pelos engenheiros.
- `frontend/lib/tuntum-data.ts` é uma representação de referência para visualização histórica, **não** fonte operacional autenticada.
- `backend/scripts/import_tuntum.py` é o adaptador de importação; não usar `--apply` enquanto divergências e bloqueios não estiverem resolvidos.
- Organização de destino: `Grupo MG`. São 14 locais da fonte e 1 centro de custos compartilhados `Despesas comuns — a ratear`, totalizando 15 registros de projeto no banco.

## Estrutura original — não transformar silenciosamente
| Seção | Quantidade | Campos |
|---|---:|---|
| locations | 14 | nome da obra |
| payroll | 16 | name, work, project, amount, category, notes quando houver |
| contracts | 12 | project, name, total, advance, balance |
| suppliers | 3 | name, debt, planned |
| activities | 7 | project, description |

Preservar ortografia, acentos, categorias, referência documental, moeda BRL, competência 2026-08-28, valores e observações. Mapear para IDs internos sem renomear a fonte. Não inventar CPF/CNPJ, banco, datas de liquidação, progresso, orçamento ou coordenadas.

## Totais e divergências
| Medida | Total declarado | Soma das linhas | Tratamento |
|---|---:|---:|---|
| Contratos | R$ 730.169,72 | R$ 736.169,72 | preservar ambos, registrar diferença |
| Adiantamentos | R$ 195.790,00 | R$ 214.383,00 | preservar ambos, registrar diferença |
| FOPAG semanal | R$ 31.570,87 | verificar no dry-run | preservar origem e conciliar |
| Mão de obra | R$ 11.950,00 | verificar no dry-run | preservar origem e conciliar |
| Outras despesas | R$ 19.620,87 | verificar no dry-run | preservar origem e conciliar |

A coluna `balance` dos contratos é **saldo declarado**, não deve ser recalculada e sobrescrita com `total - advance`. Manter saldo calculado como campo derivado de auditoria, nunca como substituição do valor informado.

## Semântica operacional
- FOPAG: lançamento semanal declarado; pagamento `SCHEDULED`, nunca `PAID` sem evidência externa validada.
- Fornecedor: `debt` representa dívida relatada; `planned` representa programação e não pagamento liquidado. Evitar duplicação entre dívida e parcela semanal.
- Contrato: registrar total, adiantamento e saldo **conforme fonte**, com estado de reconciliação pendente se houver divergência.
- Compartilhados: lançar em centro de custo `COST_POOL` sem rateio automático.
- Relatos: preservar texto e associação à obra; não inferir medição ou progresso.
- Proveniência: registrar documento, data, referência única por linha, ator, timestamp e hash da fonte. Reexecução idempotente.
- Segurança: todas as consultas exigem sessão e vínculo de organização; nenhuma referência estática deve ficar disponível a visitantes anônimos.

## Gates para persistência real
1. CI e testes de importação sintética com schema/contagens/valores e casos de duplicidade.
2. Confirmar se as duas importações `PREVIEW` existentes representam esta fonte, sem duplicar lançamentos.
3. Dry-run da importação, verificando as 15 obras já cadastradas e contagens previstas.
4. Registrar divergências documentais em estrutura de revisão; **não corrigir nem suprimir**.
5. Confirmar proteção do PR #22 e política de pagamentos do PR #34 na versão implantada.
6. Snapshot/backup do banco, execução transacional idempotente e verificação pós-gravação.
7. Homologação autenticada da Central, FOPAG, contratos, financeiro e conciliação.
8. Nenhum dado real deve ser gravado se o importador não separar registros documentais divergentes dos lançamentos financeiros liberados.

## Handoff
O usuário confirmou que os dados da fonte são reais e foram fornecidos pelos engenheiros. Isso confirma a procedência declarada, mas não converte valores não conciliados em saldos liquidados. Esta documentação não autoriza inventar diferenças nem bypassar controles.
