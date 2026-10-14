# Arquitetura — Aggilli Obras Intelligence

## Objetivo
SaaS multiempresa para obras públicas e privadas, com gestão físico-financeira, materiais, medições e fiscalização.

## Stack proposta
- Frontend: Next.js, TypeScript, Tailwind
- Backend: FastAPI (Python)
- Banco: PostgreSQL
- Arquivos: armazenamento S3 compatível
- Jobs: worker assíncrono para relatórios e alertas

## Entidades do domínio
Organization, Membership, User, Project, WorkStage, ServiceItem, Measurement, MeasurementEvidence, Material, StockMovement, BudgetItem, AuditEvent.

## Isolamento e segurança
- Toda operação de domínio deve ser autorizada no servidor com escopo de organização e obra.
- Não confiar em organization_id enviado pelo cliente como prova de autorização.
- Papéis iniciais: OWNER, ADMIN, ENGINEER, INSPECTOR, FIELD_OPERATOR, VIEWER.
- Histórico imutável de aprovação e revisão de medições.
- Arquivos privados e URLs assinadas de curta duração.

## Regras de medição
Cada serviço possui unidade, quantidade prevista, peso e quantidades medidas. Avanço físico = soma das contribuições ponderadas dos serviços aprovados. Não misturar avanço físico e desembolso financeiro. Registrar revisão e evidências, evitar dupla contagem e impedir medições negativas sem estorno auditável.

## Integrações futuras
SINAPI/SICRO, BIM, mapas, notificações e IA preditiva. Nenhuma previsão automatizada substitui medição aprovada.
