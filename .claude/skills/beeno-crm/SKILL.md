---
name: beeno-crm
description: "Consultar dados do Beeno CRM (somente leitura) e criar notas em negocios (deals). Skill standalone que chama a API REST do Beeno diretamente — nao depende do MCP beeno-mcp. Use sempre que o usuario quiser listar/ler/buscar contatos, deals, empresas, produtos, tarefas, formularios, pipelines, propriedades, segmentos, ou ler notas — e tambem quando quiser registrar/criar/adicionar uma nota, anotacao, comentario ou interacao em um negocio especifico do Beeno. NAO use para criar ou atualizar entidades alem de notas em deals, para deletar nada, ou para enviar mensagens. Triggers: beeno, crm beeno, contato beeno, deal, negocio, empresa, pipeline, produto, tarefa, formulario, nota no deal, anotar no negocio, registrar ligacao, registrar reuniao, registrar email no deal, comentario no negocio, historico do deal, buscar negocio, listar contatos, ver tarefas, propriedades do crm, segmento de contatos."
---

# Beeno CRM — Leitura + Notas em Deals (Standalone)

Skill **standalone** que fala direto com a API REST do Beeno. Sem dependencia do MCP `beeno-mcp` — funciona com qualquer projeto que tenha as credenciais no `.env`.

**Escopo restrito por design:** todas as 21 operacoes de leitura do CRM + uma unica operacao de escrita (criar nota em deal). Outras escritas nao estao implementadas no client; tentativas sao bloqueadas.

## Credenciais

Lidas automaticamente do `.env` no diretorio atual ou em diretorios pai:

```bash
BEENO_DOMAIN=https://acme.beeno.com.br       # obrigatorio
BEENO_API_KEY=sua-api-key-aqui                # obrigatorio
BEENO_API_KEY_NAME=ELOZ-APIKEY                # opcional, default ELOZ-APIKEY
```

Ou via argumentos diretos ao instanciar o cliente.

## Uso (Python)

```python
import sys, os
# Ajustar para a localizacao real da skill (CWD do projeto / global do usuario)
sys.path.insert(0, os.path.join('.claude', 'skills', 'beeno-crm', 'scripts'))

from beeno_client import BeenoClient, make_filter

client = BeenoClient()  # le credenciais do .env

# Listar deals (paginado)
deals = client.deals_list(limit=20, sort='date_modified', order='desc')

# Ler um deal especifico
deal = client.deals_read('12345')

# Buscar deals por filtro
filters = [make_filter('stage_id', 'IN', values=['10', '20'])]
results = client.deals_search(filters=filters, fetch_all=True, max_results=500)

# Listar notas de um deal
notas = client.notes_list('deal', '12345')

# Criar nota em deal (UNICA escrita permitida)
nova_nota = client.create_deal_note(
    deal_id='12345',
    text='Liguei pro cliente, ele pediu retorno amanha.',
    note_type='call'
)
```

### Credenciais diretas (sem .env)
```python
client = BeenoClient(
    domain='https://acme.beeno.com.br',
    api_key='...',
    api_key_name='ELOZ-APIKEY',
    auto_load_env=False,
)
```

## API do client — referencia rapida

### Contatos (3)
- `contacts_list(limit?, cursor?, campaign_id?, segment_id?, properties?, sort?, order?, include_associations?)`
- `contacts_read(contact_id)`
- `contacts_search(filters, properties?, limit?, cursor?, sort?, order?, fetch_all?, max_results?)`

### Negocios / Deals (3)
- `deals_list(limit?, cursor?, sort?, order?, properties?, include_associations?)`
- `deals_read(deal_id)`
- `deals_search(filters, properties?, limit?, cursor?, sort?, order?, fetch_all?, max_results?)`

### Empresas (3)
- `companies_list(limit?, cursor?, sort?, order?, properties?, include_associations?)`
- `companies_read(company_id)`
- `companies_search(filters, properties?, limit?, cursor?, sort?, order?, fetch_all?, max_results?)`

### Produtos (3)
- `products_list(limit?, cursor?, sort?, order?)`
- `products_read(product_id)`
- `products_search(filters, limit?, cursor?, sort?, order?, fetch_all?, max_results?)`

### Tarefas (3)
- `tasks_list(limit?, cursor?, sort?, order?)`
- `tasks_read(task_id)`
- `tasks_search(filters, limit?, cursor?, sort?, order?, fetch_all?, max_results?)`

### Formularios (2)
- `forms_list(limit?, cursor?)`
- `forms_read(form_id)`

### Outras leituras (4)
- `pipelines_list()` — todos os pipelines com stages
- `notes_list(from_object, from_object_id)` — `from_object` aceita `"deal"` ou `"contact"`
- `properties_list(object_type, filter_text?, include_options?)` — `object_type`: `"deal" | "contact" | "company"`
- `segments_list(limit?, cursor?, sort?, order?)`

### Escrita (1)
- `create_deal_note(deal_id, text, note_type='general', files=None)`
  - `note_type` aceita: `general | email | call | meeting | whatsapp`
  - `files` opcional: lista de `{"link": "https://...", "name": "..."}`

## Filtros (`make_filter`)

Helper para construir filtros de `*_search`:

```python
make_filter('email', 'EQ', value='joao@acme.com')
make_filter('stage_id', 'IN', values=['10', '20'])
make_filter('amount', 'GT', value='1000')
```

**Operadores:** `EQ, NEQ, GT, LT, GTE, LTE, IN, NOT_IN, HAS_PROPERTY, NOT_HAS_PROPERTY, CONTAINS_TOKEN, NOT_CONTAINS_TOKEN`.

Use `propertyName` = **alias** (nome interno) obtido via `properties_list(object_type)`.

## Escolha do `note_type`

Infira do contexto do que o usuario relatou:

| Tipo | Quando usar |
|------|-------------|
| `call` | ligacao telefonica |
| `email` | troca de e-mail |
| `meeting` | reuniao presencial ou online |
| `whatsapp` | conversa por WhatsApp |
| `general` | anotacao livre / qualquer outro caso |

Sem indicacao clara, use `general`.

## Fluxos comuns

### Buscar deal por nome e registrar uma ligacao
```python
filters = [make_filter('name', 'CONTAINS_TOKEN', value='Acme')]
results = client.deals_search(filters=filters)
# Confirmar com o usuario qual deal antes de criar a nota
client.create_deal_note(
    deal_id=results['results'][0]['id'],
    text='Liguei para alinhar reuniao da proxima semana.',
    note_type='call',
)
```

### Visao geral de um negocio
```python
deal = client.deals_read('12345')
notas = client.notes_list('deal', '12345')
tarefas = client.tasks_search(
    filters=[make_filter('deal_id', 'EQ', value='12345')]
)
```

### Descobrir propriedades antes de filtrar
```python
# Antes de filtrar deals por algo customizado, descubra o alias correto:
props = client.properties_list('deal', filter_text='origem')
# -> [{'alias': 'origin_source', 'label': 'Origem', 'type': 'select', ...}]
```

## Escopo — o que NAO fazer

Esta skill **nao expoe** (e o client nao implementa):

- Criar/atualizar/deletar contatos, deals, empresas, produtos, tarefas, pipelines, propriedades, segmentos
- Criar nota em contato (`create_deal_note` aceita apenas deals)
- Deletar notas
- Associations (vincular/desvincular entidades)
- Automation (adicionar contatos a fluxos)
- Communications / WhatsApp

Se o usuario pedir uma dessas operacoes, **explique o escopo da skill** e sugira que ele use o MCP `beeno-mcp` em modo readwrite (`BEENO_READONLY=false`) ou chame a API diretamente.

## Boas praticas

- **Nunca invente IDs.** Sempre obtenha via `*_list` / `*_search` / `*_read` antes de criar nota.
- **Confirme antes de criar** quando houver ambiguidade no deal alvo ou quando o texto for sensivel/longo.
- **Liste notas existentes** (`notes_list`) antes de criar uma nova para evitar duplicacao quando fizer sentido.
- **Reporte o ID retornado** apos criar a nota, para que o usuario possa rastrear.
- **Use `fetch_all=True` com cuidado** — pode trazer ate 500 paginas; combine com `max_results=N` quando souber o limite necessario.

## Referencia detalhada

- [references/api_endpoints.md](references/api_endpoints.md) — mapa completo de endpoints, query params, body shapes e operadores de filtro.
