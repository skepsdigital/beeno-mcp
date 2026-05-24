# Beeno CRM — Referencia de Endpoints

Mapa de todos os endpoints HTTP que a skill encapsula, agrupados por entidade.
Base URL: `${BEENO_DOMAIN}/api/v1`. Header de autenticacao: `ELOZ-APIKEY: <BEENO_API_KEY>`
(nome do header customizavel via `BEENO_API_KEY_NAME`).

## Indice
- [Contatos](#contatos)
- [Negocios (Deals)](#negocios-deals)
- [Empresas](#empresas)
- [Produtos](#produtos)
- [Tarefas](#tarefas)
- [Notas](#notas)
- [Pipelines](#pipelines)
- [Formularios](#formularios)
- [Propriedades](#propriedades)
- [Segmentos](#segmentos)
- [Filtros de busca](#filtros-de-busca)

## Contatos

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/contacts` | `contacts_list(...)` |
| GET | `/contacts/{id}` | `contacts_read(id)` |
| POST | `/contacts/search` | `contacts_search(filters, ...)` |

Query params suportados em `list`: `limit`, `cursor`, `campaignId`, `segmentId`,
`properties` (CSV de aliases), `sort`, `order`, `includeAssociations`.

## Negocios (Deals)

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/deals` | `deals_list(...)` |
| GET | `/deals/{id}` | `deals_read(id)` |
| POST | `/deals/search` | `deals_search(filters, ...)` |

## Empresas

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/companies` | `companies_list(...)` |
| GET | `/companies/{id}` | `companies_read(id)` |
| POST | `/companies/search` | `companies_search(filters, ...)` |

## Produtos

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/products` | `products_list(...)` |
| GET | `/products/{id}` | `products_read(id)` |
| POST | `/products/search` | `products_search(filters, ...)` |

Propriedades filtraveis: `id, name, price, sku, frequency, unit_cost, url, months_term, description, updatedAt`.

## Tarefas

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/tasks` | `tasks_list(...)` |
| GET | `/tasks/{id}` | `tasks_read(id)` |
| POST | `/tasks/search` | `tasks_search(filters, ...)` |

Propriedades filtraveis: `id, name, due_date, owner_id, task_type, source, description, priority` (0=baixa, 1=media, 2=alta).

## Notas

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/notes/{fromObject}/{fromObjectId}` | `notes_list(from_object, from_object_id)` |
| POST | `/notes/deal/{dealId}` | `create_deal_note(deal_id, text, note_type, files?)` |

`fromObject` aceita `"deal"` ou `"contact"` (apenas para leitura).
Criacao via skill e **restrita a deals** (escopo da skill).

**Body de criacao de nota:**
```json
{
  "properties": {
    "text": "Conteudo da nota",
    "type": "general | email | call | meeting | whatsapp",
    "files": [{ "link": "https://...", "name": "opcional" }]
  }
}
```

## Pipelines

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/deals/pipelines` | `pipelines_list()` |

Retorna todos os pipelines com seus stages (necessario para entender em qual etapa um deal esta).

## Formularios

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/forms` | `forms_list(...)` |
| GET | `/forms/{id}` | `forms_read(id)` |

## Propriedades

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/properties/{objectType}` | `properties_list(object_type, filter_text?, include_options?)` |

`objectType`: `"deal"`, `"contact"` ou `"company"`.

Cada propriedade tem:
- `alias` — **nome interno** (use em filtros como `propertyName`)
- `label` — nome de exibicao
- `type` — `text, textarea, number, date, datetime, time, select, multiselect, user, currency`
- `group` — grupo logico (ex: `core`)
- `optionsCount` (so para `select`/`multiselect`)

Use `properties_list("deal", filter_text="email")` para filtrar localmente por substring.

## Segmentos

| Metodo | Endpoint | Funcao do client |
|--------|----------|-----------------|
| GET | `/segments` | `segments_list(...)` |

## Filtros de busca

Os endpoints `*_search` aceitam um array `filters`. Cada item tem:

```json
{
  "propertyName": "alias_da_propriedade",
  "operator": "EQ",
  "value": "valor_unico"
}
```

ou, para `IN` / `NOT_IN`:

```json
{
  "propertyName": "stage_id",
  "operator": "IN",
  "values": ["10", "20", "30"]
}
```

**Operadores disponiveis:**

| Operador | Uso |
|----------|-----|
| `EQ` | igual |
| `NEQ` | diferente |
| `GT` / `GTE` | maior / maior-ou-igual |
| `LT` / `LTE` | menor / menor-ou-igual |
| `IN` / `NOT_IN` | dentro / fora de uma lista (`values`) |
| `HAS_PROPERTY` / `NOT_HAS_PROPERTY` | propriedade existe / nao existe |
| `CONTAINS_TOKEN` / `NOT_CONTAINS_TOKEN` | contem / nao contem termo |

**Conditions sao AND.** Para OR, faca buscas separadas e combine no codigo.

**Paginacao automatica:** passe `fetch_all=True` (e opcionalmente `max_results=N`) para os metodos `*_search` para receber todas as paginas concatenadas. Limite por seguranca: 500 paginas.
