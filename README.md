# Beeno MCP Server

MCP (Model Context Protocol) server para integração com a API do Beeno CRM. Permite que assistentes de IA (Claude, etc.) interajam diretamente com o Beeno para gerenciar contatos, deals, empresas e mais.

## Ferramentas Disponíveis

### Modo Completo (Read/Write) - 47 tools
| Módulo | Descrição |
|--------|-----------|
| **Contacts** | Criar, buscar, atualizar e listar contatos |
| **Deals** | Gerenciar negociações e oportunidades |
| **Companies** | Gerenciar empresas |
| **Pipelines** | Consultar pipelines e estágios, criar novos |
| **Products** | Gerenciar produtos |
| **Notes** | Adicionar notas a contatos e deals |
| **Tasks** | Criar e gerenciar tarefas |
| **Associations** | Associar entidades (contatos, deals, empresas, produtos) |
| **Properties** | Consultar e criar propriedades customizadas |
| **Segments** | Gerenciar segmentos e adicionar contatos |
| **Automation** | Disparar automações |
| **Forms** | Gerenciar formulários |
| **Communications** | Enviar mensagens (WhatsApp, etc.) |

### Modo Somente Leitura (Read-Only) - 21 tools
Quando `BEENO_READONLY=true`, apenas ferramentas de consulta estão disponíveis:
- **Contacts**: list, read, search
- **Deals**: list, read, search
- **Companies**: list, read, search
- **Pipelines**: list
- **Products**: list, read, search
- **Notes**: list
- **Tasks**: list, read, search
- **Properties**: list
- **Segments**: list
- **Forms**: list, read

## Pré-requisitos

- Node.js 18+
- Conta no [Beeno CRM](https://app.beeno.ai) com API Key

## Instalação

```bash
npm install
npm run build
```

## Configuração

O arquivo `.mcp.json.example` é o template de configuração do MCP. As credenciais são passadas diretamente via `env` no MCP — não é necessário arquivo `.env`.

**Passo 1** — Copie o template para `.mcp.json`:

```bash
cp .mcp.json.example .mcp.json
```

**Passo 2** — Ajuste o caminho do servidor Beeno de acordo com onde você clonou o projeto. No campo `args`, substitua o caminho absoluto pelo local correto no seu ambiente:

```jsonc
// Exemplo: se você clonou em C:/projetos/beeno-mcp
"beeno": {
  "command": "node",
  "args": ["C:/projetos/beeno-mcp/dist/index.js"],
  ...
}
```

**Passo 3** — Preencha suas credenciais do Beeno:

```jsonc
"env": {
  "BEENO_DOMAIN": "https://app.beeno.ai/seu-tenant-id",  // URL da sua instância
  "BEENO_API_KEY": "sua-api-key-aqui",                   // API Key gerada no Beeno
  "BEENO_READONLY": "false"                              // (opcional) Ativar modo somente leitura
}
```

### Modo Somente Leitura

Por padrão, o servidor inicia em **modo somente leitura** (21 tools de consulta). Para ativar escrita, defina explicitamente:

```jsonc
"env": {
  "BEENO_READONLY": "false"  // Libera ferramentas de write (create, update, delete)
}
```

**Exemplos de configuração:**

- **Somente leitura (padrão):** Não defina `BEENO_READONLY` ou deixe em branco
- **Somente leitura (explícito):** `"BEENO_READONLY": "true"`
- **Leitura + Escrita:** `"BEENO_READONLY": "false"`

> **Importante:** O `.mcp.json` contém credenciais sensíveis e está no `.gitignore`. Nunca faça commit deste arquivo. Apenas os `.mcp.json.example*` (sem credenciais) devem ser versionados.

## Uso

### Modo desenvolvimento

```bash
npm run dev
```

### Modo produção

```bash
npm run build
npm start
```

### Via MCP (Claude Code)

Com o `.mcp.json` configurado, o servidor é iniciado automaticamente pelo Claude Code. As ferramentas ficam disponíveis diretamente no chat.

## Exemplos de Uso

Após configurar o MCP, basta pedir em linguagem natural na sua ferramenta de IA:

> **"Busque os negócios que têm data de fechamento prevista para este mês"**
>
> O assistente vai utilizar a ferramenta de deals para filtrar negociações com `closedate` dentro do mês atual e retornar os resultados.

> **"Traga os 200 contatos mais recentes"**
>
> O assistente vai listar contatos ordenados por data de criação (`date_added`) em ordem decrescente, com limite de 200 registros.

## Estrutura do Projeto

```
beeno-mcp/
├── src/
│   ├── index.ts          # Entry point - registra tools, controla modo readonly
│   ├── client.ts         # Cliente HTTP para a API do Beeno
│   ├── schemas.ts        # Schemas Zod para validação
│   ├── types.ts          # Tipos TypeScript
│   └── tools/            # Ferramentas MCP (uma por módulo)
│       ├── contacts.ts
│       ├── deals.ts
│       ├── companies.ts
│       ├── pipelines.ts
│       ├── products.ts
│       ├── notes.ts
│       ├── tasks.ts
│       ├── associations.ts    (apenas modo write)
│       ├── properties.ts
│       ├── segments.ts
│       ├── automation.ts       (apenas modo write)
│       ├── forms.ts
│       └── communications.ts   (apenas modo write)
├── .mcp.json.example           # Template com ambas as configurações
├── .mcp.json.example.read      # Template para modo somente leitura
├── .mcp.json.example.readwrite # Template para modo read/write
├── package.json
└── tsconfig.json
```

## Arquivos de Configuração

- **`.mcp.json.example`**: Template com exemplo de ambas as configurações (read-only padrão + read/write)
- **`.mcp.json.example.read`**: Configuração para modo somente leitura (21 tools)
- **`.mcp.json.example.readwrite`**: Configuração para modo completo com escrita (47 tools)

Copie o arquivo de exemplo que melhor se adapte ao seu caso:

```bash
# Para somente leitura (padrão seguro)
cp .mcp.json.example.read .mcp.json

# Para leitura + escrita
cp .mcp.json.example.readwrite .mcp.json
```
