# Importação de dados reais — Tuntum (MA)

## Fontes fornecidas
- Relato de serviços e programação de pagamentos enviado pelo contratante em 14/10/2026.
- FOPAG SEMANAL 28 AGOSTO 2026.pdf (uma página).

## Situação
Dados transcritos para `frontend/lib/tuntum-data.ts`, exibidos como referência no dashboard. Não há persistência ou conciliação bancária nessa importação.

## Valores da FOPAG
- Mão de obra: R$ 11.950,00.
- Outras despesas: R$ 19.620,87.
- Total programado: R$ 31.570,87.
- Total de contratos na folha: R$ 730.169,72.
- Adiantamentos na folha: R$ 195.790,00.
- Saldo registrado na folha: R$ 534.379,72.

## Divergências para conferência
- Posto Ana Luiza: relato menciona R$ 935,00; itens somam R$ 985,87; folha R$ 985,87.
- Renata: relato menciona R$ 1.800,00 e duas parcelas de R$ 1.600,00; folha R$ 1.600,00.
- Juarez: relato menciona R$ 2.000,00; folha R$ 1.500,00.
- Laércio: relato aponta Casa BDC; FOPAG antiga aponta Tabocal.
- Cabiludo e José das Cruz executaram atividades em múltiplas obras; valores precisam ser rateados.
- Nomes Casa Barra/Casa BDC, Aider/Aide e JK Metalúrgica/Kleyton exigem padronização confirmada.

## Requisitos do sistema
1. Carteira de obras por unidade, com centros de custo.
2. Abas por obra: materiais, mão de obra, atividades, FOPAG semanal, balanceamento.
3. Darlan registra pedidos, despesas e comprovantes; Denise registra pagamentos efetivados, com trilha de auditoria.
4. Separar solicitação, aprovação, programação, pagamento e baixa de saldo.
5. Ratear despesas entre obras com aprovação, sem dupla contagem.
6. Fechar FOPAG por semana e permitir exportação, conciliação e revisão.
7. Não inferir percentual físico de conclusão a partir de pagamentos.
8. Acesso somente a usuários autorizados; nunca expor dados reais em demo pública.

## Limitação atual
Frontend exibe registros importados em código e não implementa formulários persistentes, conciliação, rateio ou autorização multiusuário. Não publicar a demonstração com dados reais em ambiente público.
