# Grafo de Investigacao Politica Brasileira

MVP para ingestao curada de dados politicos e financeiros em um grafo local, com staging manual, aprovacao via CLI, persistencia em Kuzu/SQLite e leitura por FastAPI.

## Estrutura

```text
.
├── api/
├── cli/
├── core/
├── db/
├── pipeline/
├── data/
│   ├── approved/
│   ├── graph.kuzu
│   ├── rejected/
│   └── staging/
├── tests/
└── web/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download pt_core_news_lg
export ANTHROPIC_API_KEY=... # obrigatório para extrair nós/arestas automaticamente
```

## Running locally

### 1. Start the Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download pt_core_news_lg
export ANTHROPIC_API_KEY=...
```

### 2. Use the CLI to generate and review staging files

```bash
python -m cli.main ingest --url "https://pt.wikipedia.org/wiki/Esc%C3%A2ndalo_do_Banco_Master"
python -m cli.main review
python -m cli.main review --file data/staging/<arquivo>.json
python -m cli.main approve --file data/staging/<arquivo>.json
```

You can also ingest a local file:

```bash
python -m cli.main ingest --file ./algum-artigo.txt
```

### 3. Run the API

```bash
uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`.

### 4. Run the frontend

```bash
cd web
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173` and will call the API at `http://localhost:8000` by default.

### 5. Run tests

```bash
python -m unittest discover -s tests
cd web && npm run build
```

## Fluxo do MVP

1. `ingest` limpa texto, extrai entidades/resumo auxiliares e, se a URL for da Wikipedia, coleta referencias por parsing direto do HTML.
2. Para URLs da Wikipedia, o staging agora tambem salva `referencias_wikipedia_vinculadas`, segmentando cada paragrafo em blocos ancorados pelas notas inline e registrando:
   - `trecho_artigo`
   - `numero_nota`
   - `referencia_correspondente`
   - `claim_estruturada` derivada deterministicamente do trecho
3. A etapa `llm` usa `texto_resumido`, entidades e fontes candidatas para preencher automaticamente `nos`, `arestas` e uma selecao inicial de `fontes`.
4. O comando gera um JSON em `data/staging/`.
5. O operador revisa principalmente a selecao de `fontes`/`fonte_ids`, corrigindo eventuais associacoes antes da aprovacao.
6. `approve` valida o payload, persiste fontes em SQLite e grafo em Kuzu, e move o arquivo para `data/approved/`.

## Comandos

```bash
python -m cli.main ingest --url "https://pt.wikipedia.org/wiki/Esc%C3%A2ndalo_do_Banco_Master"
python -m cli.main ingest --file ./algum-artigo.txt
python -m cli.main review
python -m cli.main review --file data/staging/20260510T120000.json
python -m cli.main approve --file data/staging/20260510T120000.json
python -m cli.main reject --file data/staging/20260510T120000.json
python -m cli.main source add --url https://exemplo.com --titulo "Fonte manual"
python -m cli.main source list
uvicorn api.main:app --reload
```

## Observacoes

- `approve` exige que toda aresta tenha ao menos um `fonte_id` valido.
- `ingest` falha explicitamente se `ANTHROPIC_API_KEY` nao estiver configurada.
- O banco Kuzu e criado como arquivo local em `data/graph.kuzu`.
- No staging manual, use `tipo_no` para o tipo do no e `tipo_relacao` para o tipo da aresta quando houver ambiguidade com o campo `tipo` do proprio schema.
- `fontes` dentro do staging podem ser persistidas junto com a aprovacao, desde que tenham `id` explicito quando forem referenciadas por arestas.
- `fontes_sugeridas` servem apenas como apoio para a curadoria humana.
- `referencias_wikipedia_vinculadas` conecta cada nota da Wikipedia ao trecho exato do artigo e a uma claim estruturada, para reduzir associacoes manuais incorretas entre arestas e fontes.
- O frontend em `web/` consome a API local e usa Cytoscape para visualizacao.
- Os filtros da UI incluem uma opcao para esconder componentes desconectados do nucleo Master/Vorcaro.
