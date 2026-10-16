# Google Maps — acompanhamento da correção

Responsável: Claude (branch `claude/maps-fix`). Frente OCR (PR #19, GPT-6) não foi tocada.
Última atualização: 2026-10-16.

## 1. Diagnóstico inicial (auditoria somente leitura)

| Ponto auditado | Onde | Situação |
|---|---|---|
| Carregamento da Maps JavaScript API (`v=weekly`, `libraries=marker`, `loading=async`) | `frontend/lib/google-maps.ts` | correto |
| Chave do navegador lida no servidor e passada como prop (páginas `force-dynamic`) | `app/(app)/mapa`, `app/(app)/obras/[id]/localizacao` | correto |
| Chave do servidor só no backend (Geocoding) | `backend/app/geo.py` | correto; 503 sem chave, 429 cota, 502 falha |
| Frontend → backend (server actions com token, mensagens por status) | `frontend/lib/geo-actions.ts` | correto |
| Persistência (Numeric(9,6), origem, place ID, quem confirmou, renovação 30 dias) | `models.py`, migração `0011` | correto |
| Produção: `GOOGLE_MAPS_SERVER_KEY` na API, `GOOGLE_MAPS_BROWSER_KEY` e `GOOGLE_MAPS_MAP_ID` no web | `infra/aws/obras.yaml` | mapeamento correto no modelo |
| Local: `.local/maps.env` lido por `dev/run-local.ps1` | — | chaves presentes (formato válido; valores não expostos) |

## 2. Evidências (ambiente local, chaves reais, navegador)

- `/mapa` carrega o mapa; `/obras/{id}/localizacao`: busca "Praça da Matriz, Centro" retornou 2 candidatos — Tuntum‑MA e
  **"Centro, Luziânia - GO"** (outro estado). A consulta enviada ao Google tinha só `components=country:BR`.
- Confirmar o candidato de Tuntum gravou o ponto (origem GEOCODED); Street View encontrou imagem de 09/2024.
- No `/mapa`, cada marcador foi criado **duas vezes** (avisos do Maps JS em dobro): o efeito que monta os marcadores
  dependia de um array recriado a cada renderização (`located`), então qualquer nova renderização limpava os marcadores,
  recriava o agrupador e reposicionava o mapa (`fitBounds`), desfazendo o zoom/arraste do usuário.
- Console: avisos de API descontinuada no canal `weekly` — `PinElement.element` (usar o próprio `PinElement`).
- Console: erro de hidratação React #418 em **todas** as páginas (inclusive `/obras`), portanto fora do módulo de mapas.

## 3. Causas identificadas

1. **Geocodificação retorna homônimos de outros estados** (comprovado acima). Testado `components=country:BR|locality:<município>`:
   o Google trata `locality` só como preferência e **continuou** devolvendo Luziânia‑GO; a mudança foi revertida. O aviso
   "município encontrado difere do cadastrado" já impede a confirmação desapercebida. Melhoria real exigiria a UF da obra
   (campo inexistente hoje — mudança de modelo, fora deste escopo).
2. **Efeito do mapa geral com dependência instável** → marcadores reconstruídos e viewport reiniciado a cada renderização.
3. **Street View frágil**: panorama criado dentro de um elemento oculto (`display:none`), um novo panorama a cada ponto,
   sem tratamento de falha de carregamento e com a data anterior exibida durante a troca de ponto.
4. **Uso de propriedade descontinuada** (`PinElement.element`) no canal `weekly`, que pode deixar de funcionar.

5. **Causa da falha em produção (comprovada em 2026-10-16, com login do usuário)**: em
   `https://emobras.aggillintelligence.com.br/mapa` o Google responde `InvalidKeyMapError` / `InvalidKey` e mostra
   "Ops! Algo deu errado". A chave enviada ao navegador tem 9 caracteres e é exatamente o texto provisório `PREENCHER`
   do modelo `infra/aws/obras.yaml` (`AppSecret`). Ou seja, `GOOGLE_MAPS_BROWSER_KEY` **nunca foi preenchida** no Secrets
   Manager. Pelo mesmo modelo, `GOOGLE_MAPS_SERVER_KEY` provavelmente também está como `PREENCHER` (geocodificação falharia
   com `REQUEST_DENIED` → 502 "O serviço de geocodificação do Google não respondeu"). Não é defeito de código.

## 4. Arquivos alterados

- `frontend/components/portfolio-map.tsx` — `located`/`missing` memorizados; `content: pin`.
- `frontend/components/location-editor.tsx` — Street View: promessa com tratamento de `ZERO_RESULTS`, contêiner exibido antes
  de criar o panorama, panorama reutilizado (`setPano`), `catch` na carga; `content: PinElement`.

Sem mudança de layout, CSS, navegação, contratos de API, persistência ou permissões.

## 5. Testes

- Backend `pytest`: 71 passaram, 2 ignorados.
- Frontend `npm run lint` (`tsc --noEmit`): sem erros.
- Navegador local após a correção: ver §6.
- CI do PR: ver §6/descrição do PR.

## 6. Validação pós-correção (local)

Build de produção local (`next build` + `next start`), chaves reais, navegador:
- `/mapa`: mapa renderiza, 1 marcador (`gmp-advanced-marker`) na obra localizada; após recarregar, o marcador é criado
  **uma vez** (antes: duas).
- `/obras/{id}/localizacao`: mapa satélite com o ponto confirmado; Street View visível (`display:block`), imagem de 09/2024.
- Geocodificação: candidatos com avisos, como antes.
- O aviso `PinElement.element` continua no console mesmo usando o `PinElement` direto — vem de dentro do Maps JS/agrupador,
  não do nosso código.

## 7. Riscos e pendências

- **Ação do usuário (produção)**: no Secrets Manager (`us-east-1`, segredo do site/API da pilha `obras`), substituir
  `PREENCHER` por chaves reais em `GOOGLE_MAPS_BROWSER_KEY` e `GOOGLE_MAPS_SERVER_KEY` e forçar novo deploy dos serviços
  web e api no ECS (os segredos só são lidos na partida da tarefa). Conferir também que a chave do navegador aceita o referenciador `https://emobras.aggillintelligence.com.br/*`,
  que a chave do servidor (restrita por IP) aceita o IP de saída do NAT/Fargate, e preencher `GoogleMapsMapId`
  (sem ele a produção usa `DEMO_MAP_ID`, só para desenvolvimento).
- `marker.addListener("click")` gera aviso de descontinuação; a troca por `gmp-click` aguarda tipos atualizados
  (`@types/google.maps` 3.66 não declara o evento no `AdvancedMarkerElement`).

## 8. Dependências de outras frentes

- Corrida em `forecast_runs` (restrição única) gerou 500 em `/intelligence/portfolio` com requisições simultâneas; o
  mesmo `project_intelligence` é chamado por `/map/projects`. Se ocorrer no mapa, a página mostra "Entre para ver o mapa"
  em vez de erro. Módulo de inteligência — registrado, **não** alterado aqui.
- Erro de hidratação React #418 é global (layout/compartilhado) — registrado, **não** alterado aqui.
- Nenhum arquivo do OCR alterado.

## 9. Estado de homologação

Correção em branch isolada, aguardando CI, validação em produção e aprovação do usuário. Não houve deploy.
