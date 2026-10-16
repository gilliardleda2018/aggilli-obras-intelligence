# Especificação oficial — Fechamento financeiro nacional (Brasil)

Data-base: 16/10/2026. Status: **contrato de produto aprovado para implementação técnica, NÃO homologação de funcionalidades inexistentes**. Sem dependência de Stripe. Compatível com qualquer UF; parâmetros municipais/fiscais devem ser resolvidos por município, atividade, regime e vigência, nunca por alíquota fixa nacional.

## Regras próprias do Aggilli Obras e fundamentos normativos

- Fluxo próprio Aggilli Obras: contrato → medição → aprovação → documento fiscal → adiantamentos/retencões → título → autorização → liquidação e conciliação.
- Banco Central: API Pix para cobrança, verificação de liquidação e conciliação, sem confundir iniciação com liquidação. Fonte: https://www.bcb.gov.br/estabilidadefinanceira/pix-cobranca
- Receita Federal: retenções previdenciárias podem aplicar-se à cessão de mão de obra e empreitada conforme enquadramento; não calcular 11% indiscriminadamente. Fonte: https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/tributos/contribuicoes-previdenciarias-pf

## Escopo funcional obrigatório

1. **Cadastros**: organização/filial, obra, centro de custo, cliente, fornecedor, CPF/CNPJ, município IBGE, UF, regime tributário, dados bancários protegidos e papéis.
2. **Contratos**: valor original, aditivos assinados, medições, retenções/cauções, adiantamentos, faturamento direto, saldo contratado, saldo comprometido, saldo medido, saldo faturado, saldo liquidado; histórico imutável.
3. **FOPAG**: competência/período, itens e responsáveis, vínculos a contratos, adiantamentos e rateios; importar com prévia e hash; divergência exige resolução documental explícita.
4. **Contas a pagar**: obrigação, parcela, vencimento, NF/recibo, retenções parametrizadas, centro de custo, aprovação, programação, baixa manual ou provedor futuro; nunca `PAID` só porque foi programado.
5. **Contas a receber**: cliente, contrato, medição faturável, título, parcelas, vencimento, recebimento parcial, descontos/juros, baixa comprovada.
6. **Tesouraria**: múltiplas contas bancárias, caixa, transferências internas em partidas espelhadas, importação OFX/CSV, conciliação por valor/data/identificador, ajustes auditados e não destrutivos.
7. **Fechamento por competência**: pré-validação, divergências, bloqueios, aprovação de duas pessoas quando configurado, snapshot de saldos, trava de período, reabertura autorizada e trilha de auditoria.
8. **Relatórios**: previsto x realizado, fluxo de caixa diário/mensal, contas vencidas, aging, custo por obra, comprometido x medido x pago, retenções, fornecedores, comprovantes e exportação.
9. **Documentos**: armazenamento privado, checksum, versionamento, vínculo ao lançamento, autorização de download, retenção LGPD e trilha de acesso.
10. **Integração**: adaptador MANUAL operacional desde o início; Stripe/Global Payouts somente após habilitação, nunca requisito para fechamento.

## Estados de negócio (máquina de estados)
- Contrato: DRAFT → APPROVED → ACTIVE → CLOSED; CANCELLED com autorização, nunca exclusão histórica.
- Medição: DRAFT → SUBMITTED → APPROVED/REJECTED → INVOICED.
- Obrigação: DRAFT → VALIDATED → APPROVED → SCHEDULED → SETTLED; REJECTED/CANCELLED por transições controladas.
- Conciliação bancária: UNMATCHED → SUGGESTED → MATCHED → RECONCILED; DISPUTED para exceções.
- Fechamento: OPEN → REVIEW → APPROVED → CLOSED; REOPENED exige justificativa, autoridade e evento de auditoria.
- Valores: sempre Decimal/Numeric(16,2), sem float; dinheiro em BRL por padrão, com moeda explícita.

## Fórmulas e invariantes
- Saldo contratual calculado = contrato original + aditivos aprovados − medições liquidadas (ou outra base contratual explícita); **não confundir** com saldo declarado no documento, valor comprometido, adiantamento ou saldo de caixa.
- Adiantamento é crédito a compensar e não uma segunda despesa.
- Retenção e caução são obrigações segregadas; líquido a pagar = bruto aprovado − retenções − adiantamentos compensados + acréscimos aprovados.
- Pagamento parcial reduz obrigação aberta, sem eliminar seu histórico.
- Nunca fechar período com inconsistência não resolvida, valor sem comprovante exigido, título órfão, duplicidade ou conciliação bancária obrigatória pendente.
- Mesmo documento não pode gerar dois lançamentos idênticos; unique(source, external_id, organization_id), idempotência e locks em operações concorrentes.
- Toda consulta/ação valida organização no servidor; usuário de outra empresa recebe 404/403 sem vazamento.
- Não inventar saldo contratual da FOPAG de Tuntum. Exigir correção documentada e revisão humana.

## Regras nacionais com parametrização
- Município IBGE e UF do estabelecimento, tomador, prestador e local de execução; ISS/local de incidência depende da LC 116/2003 e legislação municipal.
- NFS-e nacional ou provedor municipal conforme competência e integração aplicável; armazenar XML, identificadores e protocolo.
- NF-e de materiais, CFOP, ICMS, substituição tributária e DIFAL conforme operação/UF/regime; sem regra fixa genérica.
- INSS, IRRF, PIS/COFINS/CSLL, ISS e outros tributos como componentes versionados por vigência, natureza, regime e enquadramento, validados por contador.
- Obra pode exigir CNO, eSocial/EFD-Reinf/DCTFWeb e obrigações específicas; sistema guarda referências, não promete emissão automática sem homologação.
- 2026: prever versionamento para mudanças da reforma tributária (IBS/CBS) sem codificar premissas definitivas.

## Modelo de persistência — migrações aditivas
financial_periods, counterparties, contracts/contract_amendments, contract_measurements, advances, retentions, payables, payable_installments, receivables, receivable_installments, bank_accounts, bank_statement_imports, bank_transactions, reconciliations, financial_approvals, settlement_evidence, financial_ledger_entries, financial_audit_events, fiscal_rule_versions.
Chaves organization_id em todos os recursos; unique constraints, FKs, índices, check constraints, timestamps e estados. Nunca alterar tabelas de OCR ou migrar destrutivamente.

## Plano de implementação sem regressão
- FN01: contratos/adiantamentos/retenções/FOPAG e validação de saldos.
- FN02: pagar/receber, parcelas, aprovação, pagamentos parciais, baixas manuais e estornos.
- FN03: contas bancárias, OFX/CSV, matching e conciliação.
- FN04: fechamento por período, bloqueios, reabertura e relatórios.
- FN05: parametrização fiscal nacional, integrações fiscais sob demanda e testes de regras por UF/município.
- FN06: interface existente com novos controles consistentes, acessibilidade, testes E2E e deploy gradual.
- FN07: adaptador Stripe opcional, após habilitação; não altera núcleo financeiro.

## Critérios de homologação
CI verde no SHA final; testes PostgreSQL transacionais e concorrentes; isolamento multiempresa; idempotência; simulação de pagamento parcial, estorno, reabertura, duplicidade, impostos parametrizados, 27 UFs e amostra de municípios; verificação de segurança, migrações e backup. Frontend sem regressões visuais. Só declarar concluído quando API, interface, testes e implantação forem comprovados.

## Coordenação
PR #19 OCR pertence a outra frente. PR #22 bloqueia FOPAG inconsistente; PR #23 Stripe; PR #24 Full; PR #25 conciliação read-only. Mudanças em arquivos compartilhados requerem revisão de conflitos e comunicação via PR.

## Implementação incremental rastreável

O módulo `app/financial_closing_rules.py` calcula liquidação parcial, retenções e adiantamentos com Decimal e impede fechamento de competência com pendências. Os testes estão em `tests/test_financial_closing_rules.py`. **É núcleo puro, não persistência de fechamento nem interface pronta.** Manter FN01–FN07 abertos até migrações, APIs, autorização, conciliação bancária, UI e testes E2E concluídos.
