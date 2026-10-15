# Mapas (Marco 06) — configuração do Google Maps Platform

## O que está implementado

| Item do marco | Situação |
|---|---|
| Maps JavaScript API no painel (`/mapa`, `/obras/{id}/localizacao`) | implementado, testado sem chave; aguardando chave para teste visual |
| Geocoding por endereço, com candidatos e verificações (município, precisão, correspondência parcial, fora do Brasil) | implementado e testado (API simulada) |
| Cadastro e edição de coordenadas com origem registrada (Google, mapa, GPS no local, digitada), quem confirmou e quando | implementado e testado |
| Mapa geral das obras autorizadas, marcadores por risco, filtros (município, empresa, responsável, situação, risco), agrupamento | implementado |
| Street View com data da imagem e aviso de que não é evidência da execução; mensagem quando não há cobertura (raio 50 m) | implementado |
| Links mapa → painel da obra → localização | implementado |
| Fotos georreferenciadas, histórico fotográfico por etapa, rotas de visita (Routes API) | pendente |

Coordenadas nunca são estimadas: o resultado do Google é só um candidato até alguém confirmar. As obras de Tuntum
continuam sem coordenadas até que o endereço real seja geocodificado e conferido (ou o ponto seja marcado no local).

## Chaves (criar no projeto "mapas" do Google Cloud)

APIs a ativar: **Maps JavaScript API** e **Geocoding API**. A Routes API só será necessária com o planejamento de visitas.

1. **Chave do navegador** (`GOOGLE_MAPS_BROWSER_KEY`): restrição por *referenciadores HTTP* (`http://localhost:3100/*` e o domínio do
   painel) e por API: somente Maps JavaScript API. Ela fica visível no navegador; a proteção é a restrição.
2. **Chave do servidor** (`GOOGLE_MAPS_SERVER_KEY`): restrição por API (somente Geocoding API) e, em produção, por IP do backend.
   Nunca vai para o navegador.
3. **Map ID** (`GOOGLE_MAPS_MAP_ID`, opcional): Google Maps Platform → Gerenciamento de mapas → criar Map ID (JavaScript, vetorial).
   Sem ele usamos `DEMO_MAP_ID`, que serve só para desenvolvimento.

Defina cotas diárias e alertas de orçamento no console antes de publicar.

## Ambiente local

Crie `.local\maps.env` (a pasta é ignorada pelo git) e reinicie com `dev\run-local.ps1`:

```
GOOGLE_MAPS_SERVER_KEY=...
GOOGLE_MAPS_BROWSER_KEY=...
GOOGLE_MAPS_MAP_ID=...
```

Não cole as chaves em conversas, issues ou commits.

## Termos do Google Maps Platform

- Latitude/longitude obtidas da Geocoding API só podem ficar em cache por até 30 dias; o identificador do local (place ID) pode ser
  guardado. Por isso coordenadas de origem `GEOCODED` guardam o place ID e são renovadas por `POST /api/v1/geo/refresh` (ou
  removidas se o local deixar de existir). Pontos marcados por uma pessoa no mapa, obtidos por GPS no local ou digitados são
  dados próprios da organização.
- O endereço formatado do Google não é gravado; o endereço da obra é o informado pelo usuário.
- Street View é exibido com a data da imagem e o aviso de que não comprova a situação atual da obra.
