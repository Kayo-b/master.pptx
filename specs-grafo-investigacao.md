# Specs: Grafo de Investigação Política Brasileira

## Visão Geral

Aplicação para mapear conexões entre pessoas, organizações, órgãos, eventos, partidos, instrumentos financeiros e bens envolvidos em escândalos políticos e financeiros brasileiros.

Os dados vêm de fontes jornalísticas e documentos oficiais. Toda informação tem fonte obrigatória e nível de confiança explícito — fatos confirmados e especulações coexistem no grafo mas são sempre distinguíveis.

A fase inicial é manual e curada: um humano alimenta o pipeline, valida o output da LLM e aprova antes de persistir. Automação é fase futura.

---

## Arquitetura Geral

```
[Coleta]
    URL ou arquivo local
        ↓
[Limpeza Estrutural]
    trafilatura — extrai corpo do artigo, remove boilerplate HTML
        ↓
[Sumarização Extrativa]
    spaCy  — NER: extrai entidades (pessoas, orgs, datas, valores)
    sumy   — TextRank: seleciona frases relevantes com janela de contexto
        ↓
[Extração de Relações — LLM]
    Claude Sonnet (Claude Code, quota Pro)
    Recebe ~500 palavras, produz JSON estruturado com entidades e relações
        ↓
[Validação Humana — CLI]
    Operador revisa JSON, corrige, aprova ou descarta
        ↓
[Persistência]
    Kuzu — grafo embedded
    SQLite — tabela de fontes
        ↓
[Visualização — Web UI]
    React + Cytoscape.js
```

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem backend | Python 3.11+ |
| Limpeza HTML | `trafilatura` |
| NER | `spaCy` com modelo `pt_core_news_lg` |
| Sumarização | `sumy` (TextRank) |
| LLM | Claude Sonnet via Claude Code (Pro) |
| Banco de grafo | `kuzu` (fase inicial) → Neo4j (escala) |
| Banco de fontes | SQLite via `sqlite3` (stdlib) |
| CLI | `typer` |
| Frontend | React + Vite |
| Visualização de grafo | `cytoscape` + `react-cytoscapejs` |
| Layout de grafo | algoritmo `cose` (força física) |

---

## Estrutura do Projeto

```
/
├── pipeline/
│   ├── cleaner.py          # trafilatura: fetch + extração de texto
│   ├── extractor.py        # spaCy NER + sumy TextRank
│   ├── llm.py              # chamada ao Sonnet, prompt, parse do JSON
│   └── ingest.py           # orquestra cleaner → extractor → llm
│
├── db/
│   ├── graph.py            # kuzu: init schema, insert nós e arestas
│   ├── sources.py          # sqlite: CRUD da tabela fontes
│   └── schema.cypher       # definição completa do schema kuzu
│
├── cli/
│   └── main.py             # interface CLI com typer
│
├── api/
│   └── main.py             # FastAPI: endpoints para o frontend
│
├── web/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Graph.jsx       # Cytoscape.js wrapper
│   │   │   ├── Filters.jsx     # filtros de confiança, tipo, grau
│   │   │   ├── NodeDetail.jsx  # painel lateral com detalhes do nó
│   │   │   └── SourceList.jsx  # lista de fontes de uma relação
│   │   └── api.js          # fetch para o backend FastAPI
│   └── package.json
│
├── data/
│   ├── graph.kuzu/         # banco de grafo (gerado)
│   └── sources.db          # banco sqlite de fontes (gerado)
│
└── requirements.txt
```

---

## Schema do Banco de Grafo (Kuzu)

### Nós

```cypher
CREATE NODE TABLE Pessoa (
  id          STRING,
  nome        STRING,
  apelido     STRING,
  cargo_atual STRING,
  descricao   STRING,
  PRIMARY KEY(id)
)

CREATE NODE TABLE Organizacao (
  id        STRING,
  nome      STRING,
  tipo      STRING,
  cnpj      STRING,
  descricao STRING,
  PRIMARY KEY(id)
)

CREATE NODE TABLE Orgao (
  id        STRING,
  nome      STRING,
  sigla     STRING,
  tipo      STRING,
  descricao STRING,
  PRIMARY KEY(id)
)

CREATE NODE TABLE Partido (
  id    STRING,
  nome  STRING,
  sigla STRING,
  PRIMARY KEY(id)
)

CREATE NODE TABLE Evento (
  id          STRING,
  nome        STRING,
  tipo        STRING,
  data_inicio STRING,
  data_fim    STRING,
  descricao   STRING,
  PRIMARY KEY(id)
)

CREATE NODE TABLE InstrumentoFinanceiro (
  id        STRING,
  tipo      STRING,
  valor     STRING,
  descricao STRING,
  status    STRING,
  PRIMARY KEY(id)
)

CREATE NODE TABLE Bem (
  id             STRING,
  tipo           STRING,
  descricao      STRING,
  valor_estimado STRING,
  localizacao    STRING,
  PRIMARY KEY(id)
)
```

Valores válidos por campo:

| Nó | Campo | Valores |
|---|---|---|
| Organizacao | tipo | `banco`, `empresa`, `escritorio_advocacia`, `fundo`, `corretora`, `ong` |
| Orgao | tipo | `regulador`, `judiciario`, `policial`, `ministerio`, `legislativo` |
| Evento | tipo | `operacao_policial`, `cpi`, `julgamento`, `delacao`, `reuniao`, `contrato` |
| InstrumentoFinanceiro | status | `ativo`, `liquidado`, `investigado`, `falso` |
| InstrumentoFinanceiro | tipo | `CDB`, `carteira_credito`, `precatorio`, `titulo`, `fundo` |
| Bem | tipo | `imovel`, `aeronave`, `veiculo`, `resort`, `empresa_offshore` |

### Arestas

Toda aresta tem obrigatoriamente:
- `fonte_ids` — JSON array de IDs da tabela `fontes`: `'["f001","f002"]'`
- `confianca` — `"confirmado"` | `"investigado"` | `"especulado"`

```cypher
-- Pessoa → Organização
CREATE REL TABLE CONTROLA       (FROM Pessoa TO Organizacao, desde STRING, fonte_ids STRING, confianca STRING)
CREATE REL TABLE TRABALHOU_EM   (FROM Pessoa TO Organizacao, cargo STRING, desde STRING, ate STRING, fonte_ids STRING, confianca STRING)
CREATE REL TABLE RECEBEU_DE     (FROM Pessoa TO Organizacao, valor STRING, data STRING, descricao STRING, fonte_ids STRING, confianca STRING)
CREATE REL TABLE CONTRATOU      (FROM Pessoa TO Organizacao, valor STRING, descricao STRING, data STRING, fonte_ids STRING, confianca STRING)

-- Pessoa → Orgao
CREATE REL TABLE PRESSIONOU     (FROM Pessoa TO Orgao, meio STRING, data STRING, descricao STRING, fonte_ids STRING, confianca STRING)
CREATE REL TABLE INVESTIGADO_POR (FROM Pessoa TO Orgao, data STRING, fonte_ids STRING, confianca STRING)

-- Pessoa → Partido
CREATE REL TABLE FILIADO_A      (FROM Pessoa TO Partido, desde STRING, ate STRING, fonte_ids STRING, confianca STRING)

-- Pessoa → Evento
CREATE REL TABLE INVESTIGADO_EM (FROM Pessoa TO Evento, papel STRING, fonte_ids STRING, confianca STRING)
CREATE REL TABLE PARTICIPOU_DE  (FROM Pessoa TO Evento, papel STRING, fonte_ids STRING, confianca STRING)
CREATE REL TABLE NEGOCIOU       (FROM Pessoa TO Evento, papel STRING, resultado STRING, fonte_ids STRING, confianca STRING)

-- Pessoa → Pessoa
CREATE REL TABLE ASSOCIADO_A    (FROM Pessoa TO Pessoa, tipo STRING, descricao STRING, fonte_ids STRING, confianca STRING)

-- Pessoa → Bem
CREATE REL TABLE POSSUI         (FROM Pessoa TO Bem, desde STRING, fonte_ids STRING, confianca STRING)

-- Organização → Organização
CREATE REL TABLE TRANSFERIU_PARA (FROM Organizacao TO Organizacao, valor STRING, data STRING, fonte_ids STRING, confianca STRING)
CREATE REL TABLE VENDEU_ATIVOS_A (FROM Organizacao TO Organizacao, valor STRING, tipo_ativo STRING, data STRING, fonte_ids STRING, confianca STRING)
CREATE REL TABLE TENTOU_COMPRAR  (FROM Organizacao TO Organizacao, data STRING, resultado STRING, fonte_ids STRING, confianca STRING)

-- Organização → InstrumentoFinanceiro
CREATE REL TABLE EMITIU         (FROM Organizacao TO InstrumentoFinanceiro, data STRING, lastro STRING, fonte_ids STRING, confianca STRING)

-- Organização → Evento
CREATE REL TABLE ENVOLVIDA_EM   (FROM Organizacao TO Evento, papel STRING, fonte_ids STRING, confianca STRING)

-- Orgao → Organização
CREATE REL TABLE FISCALIZOU     (FROM Orgao TO Organizacao, resultado STRING, data STRING, fonte_ids STRING, confianca STRING)
CREATE REL TABLE LIQUIDOU       (FROM Orgao TO Organizacao, data STRING, motivo STRING, fonte_ids STRING, confianca STRING)

-- Partido → Evento
CREATE REL TABLE CITADO_EM      (FROM Partido TO Evento, contexto STRING, fonte_ids STRING, confianca STRING)
```

---

## Tabela de Fontes (SQLite)

```sql
CREATE TABLE fontes (
  id      TEXT PRIMARY KEY,
  url     TEXT NOT NULL,
  titulo  TEXT,
  autor   TEXT,
  veiculo TEXT,
  data    TEXT,
  tipo    TEXT
);
```

Valores válidos para `tipo`: `artigo`, `documento_oficial`, `relatorio`, `transcript`, `cpi`

IDs gerados como UUID v4 na inserção.

---

## Pipeline — Comportamento Esperado

### cleaner.py

- Recebe URL ou path de arquivo local (txt, pdf)
- Para URLs: usa `trafilatura.fetch_url` + `trafilatura.extract`
- Para arquivos: lê diretamente
- Retorna string de texto limpo
- Falha explicitamente se trafilatura não conseguir extrair conteúdo útil

### extractor.py

- Recebe texto limpo
- Roda spaCy `pt_core_news_lg` para NER — extrai `PER`, `ORG`, `LOC`, `DATE`, `MONEY`
- Roda TextRank via sumy para selecionar top 10 frases
- Expande cada frase top-ranked com janela de contexto de 1 frase antes e depois
- Aplica keyword boosting para frases do domínio político/financeiro
- Nunca descarta frases que contenham entidades NER — opera em modo inclusivo
- Retorna dict com `{ "entidades": [...], "texto_resumido": "..." }`

Keywords de domínio:
```python
KEYWORDS = [
  "fraude", "desvio", "investigação", "preso", "prisão", "CPI",
  "bilhões", "milhões", "contrato", "esquema", "lavagem", "corrupção",
  "operação", "delação", "sigilo", "liquidação", "rombo"
]
```

### llm.py

- Recebe o dict do extractor
- Monta prompt com o texto resumido + lista de entidades detectadas
- Chama Claude Sonnet via API Anthropic
- Instrui o modelo a responder somente em JSON, sem texto adicional
- Faz parse do JSON retornado
- Retorna estrutura validada ou lança erro descritivo se JSON inválido

Estrutura de output esperada do LLM:

```json
{
  "nos": [
    {
      "tipo": "Pessoa",
      "id": "pessoa_daniel_vorcaro",
      "nome": "Daniel Vorcaro",
      "descricao": "Controlador do Banco Master"
    }
  ],
  "arestas": [
    {
      "tipo": "CONTROLA",
      "origem_id": "pessoa_daniel_vorcaro",
      "destino_id": "org_banco_master",
      "desde": "2019",
      "confianca": "confirmado",
      "fonte_ids": []
    }
  ],
  "fontes_sugeridas": [
    {
      "url": "https://...",
      "titulo": "...",
      "veiculo": "...",
      "data": "..."
    }
  ]
}
```

### ingest.py

Orquestra o pipeline completo:
```
cleaner → extractor → llm → salva JSON em /data/staging/<timestamp>.json
```

Não persiste no banco — apenas gera o arquivo de staging para revisão humana.

---

## CLI (typer)

```
python cli/main.py ingest --url <url>
python cli/main.py ingest --file <path>
python cli/main.py review                    # lista arquivos em staging
python cli/main.py review --file <staging>   # mostra JSON formatado
python cli/main.py approve --file <staging>  # persiste no banco
python cli/main.py reject --file <staging>   # descarta
python cli/main.py source add                # adiciona fonte manualmente
python cli/main.py source list               # lista fontes cadastradas
```

O comando `approve` persiste nós e arestas no Kuzu e fontes no SQLite. Antes de persistir, valida que todos os `fonte_ids` referenciados nas arestas existem na tabela de fontes — falha se houver referência quebrada.

---

## API (FastAPI)

Endpoints mínimos para o frontend:

```
GET  /graph                          # retorna todos os nós e arestas
GET  /graph/node/{id}                # detalhes de um nó
GET  /graph/node/{id}/neighbors      # nós conectados até grau N
GET  /sources                        # lista fontes
GET  /sources/{id}                   # detalhe de uma fonte
```

Parâmetros de query para `/graph`:
- `confianca` — filtra por nível: `confirmado`, `investigado`, `especulado`
- `tipo_no` — filtra por tipo de nó
- `grau` — profundidade máxima de vizinhança (default: todos)

---

## Frontend (React)

### Componentes

`Graph.jsx`
- Wrapper do Cytoscape.js com `react-cytoscapejs`
- Layout `cose`
- Nós coloridos por tipo
- Clique em nó abre `NodeDetail`
- Clique em aresta mostra label e fontes

`Filters.jsx`
- Checkboxes de confiança (confirmado / investigado / especulado)
- Checkboxes de tipo de nó
- Slider de grau de separação a partir do nó selecionado

`NodeDetail.jsx`
- Painel lateral com propriedades do nó selecionado
- Lista de relações do nó com links para fontes

`SourceList.jsx`
- Lista de fontes de uma relação selecionada com link clicável para URL original

### Cores por tipo de nó

| Tipo | Cor |
|---|---|
| Pessoa | `#4A90D9` |
| Organização | `#E67E22` |
| Orgao | `#8E44AD` |
| Partido | `#27AE60` |
| Evento | `#E74C3C` |
| InstrumentoFinanceiro | `#F39C12` |
| Bem | `#7F8C8D` |

### Estilo de aresta por confiança

| Confiança | Estilo |
|---|---|
| confirmado | linha sólida |
| investigado | linha tracejada |
| especulado | linha pontilhada |

---

## Regras de Negócio

- Nenhum dado entra no banco sem aprovação humana explícita via CLI
- Toda aresta precisa de pelo menos um `fonte_id` válido para ser aprovada
- IDs de nós são gerados como slug do tipo + nome: `pessoa_daniel_vorcaro`, `org_banco_master`
- Entidade duplicada (mesmo ID) não gera erro — faz upsert no nó existente
- Arestas duplicadas (mesmo origem, destino, tipo) são permitidas se tiverem fontes diferentes — representam corroboração
- `confianca` nunca pode ser promovida automaticamente — só por edição humana

---

## Princípios de Implementação

- Sem comentários no código
- Sem logging excessivo — apenas erros e confirmações de ação
- Sem over-engineering — cada módulo faz uma coisa
- Complexidade adicionada incrementalmente conforme necessidade real
- Schema do banco muda via migration manual documentada, não automática
