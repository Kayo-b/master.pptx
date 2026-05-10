# Glossário

## Fluxo principal

### Aprovação
Etapa que persiste um arquivo de staging revisado no SQLite e no Kuzu. Só tem sucesso se todos os `fonte_ids` referenciados existirem.

### Curadoria
Etapa de revisão humana em que os dados preliminares são corrigidos, completados, aprovados ou rejeitados antes da persistência.

### Ingestão
Processo iniciado por `ingest`. Lê uma URL ou arquivo, extrai texto limpo e sinais auxiliares, e grava um JSON de staging.

### MVP manual
Fase atual do projeto. A extração estruturada é concluída por uma pessoa com apoio do Copilot CLI, em vez de um pipeline automatizado com LLM.

### Persistência
Etapa que salva fontes validadas no SQLite e os dados do grafo no Kuzu.

### Rejeição
Etapa que remove um arquivo de staging do fluxo de aprovação movendo-o para `data/rejected/`.

### Revisão
Etapa da CLI usada para inspecionar arquivos de staging antes da aprovação ou rejeição.

### Staging
Rascunho intermediário em JSON armazenado em `data/staging/`. Contém texto limpo, extrações auxiliares e dados do grafo curados manualmente antes da persistência.

## Artefatos de dados

### Arquivo aprovado
JSON de staging que já foi persistido e depois movido para `data/approved/`.

### Texto limpo
Texto do artigo ou documento após limpeza estrutural, remoção de boilerplate ou extração de texto do arquivo.

### Sinais auxiliares
Saídas de extração não finais usadas para apoiar a curadoria, como entidades, frases relevantes, texto resumido e referências da Wikipedia.

### Fonte
Referência jornalística ou oficial armazenada no SQLite. As fontes sustentam as afirmações representadas pelas arestas do grafo.

### Fonte sugerida
Referência candidata ainda não persistida, extraída automaticamente, hoje a partir das referências da Wikipedia, para ajudar a curadoria.

## Modelo de grafo

### Aresta
Relação entre dois nós do grafo. Toda aresta deve incluir `fonte_ids` e `confianca`.

### `confianca`
Nível de confiança de uma aresta. Os valores válidos são `confirmado`, `investigado` e `especulado`.

### `fonte_ids`
Lista de IDs de fontes que sustentam uma aresta.

### Snapshot do grafo
Formato de resposta da API que retorna o grafo atual como `nodes` e `edges`.

### Nó
Entidade armazenada no grafo, como `Pessoa`, `Organizacao`, `Orgao`, `Partido`, `Evento`, `InstrumentoFinanceiro` ou `Bem`.

### `tipo_no`
Campo de staging/API usado como discriminador do tipo de nó. Evita ambiguidade com schemas de nó que também possuem a propriedade `tipo`.

### `tipo_relacao`
Campo de staging/API usado como discriminador do tipo da aresta. Evita ambiguidade com schemas de aresta que também possuem a propriedade `tipo`.

### Upsert
Comportamento de inserir-ou-atualizar usado para nós. Se já existir um nó com o mesmo ID, ele é atualizado em vez de causar erro.

## Componentes do pipeline

### `cleaner.py`
Módulo do pipeline responsável por ler URLs ou arquivos locais e retornar texto limpo.

### `extractor.py`
Módulo do pipeline que gera sinais auxiliares como entidades nomeadas, frases relevantes e texto resumido.

### `ingest.py`
Orquestrador do pipeline que executa limpeza e extração, opcionalmente coleta referências da Wikipedia, e grava o JSON de staging.

### Parsing HTML da Wikipedia
Extração determinística de referências da Wikipedia por meio do parsing direto do DOM/HTML da página, sem depender de LLM como extrator primário.

## Armazenamento

### Kuzu
Banco de grafo embedded usado pelo MVP para armazenar nós e arestas localmente.

### `schema.cypher`
Arquivo Cypher que define as tabelas de nós e tabelas de relações no Kuzu.

### SQLite
Banco relacional usado para armazenar a tabela `fontes`.

## API e interface

### FastAPI
Framework web em Python usado para expor endpoints de grafo e fontes.

### Cytoscape
Biblioteca de visualização de grafo usada no frontend.

### `NodeDetail`
Painel do frontend que mostra propriedades e relações de um nó selecionado.

### `SourceList`
Painel do frontend que mostra as fontes associadas a uma aresta selecionada.

### `Filters`
Controles do frontend usados para filtrar a visualização do grafo por confiança, tipo de nó e grau de vizinhança.

### Grau de vizinhança
Distância máxima em saltos a partir de um nó selecionado ao exibir nós e arestas conectados.

## Termos de extração e NLP

### NER
Named Entity Recognition. Aqui é usada para detectar entidades como pessoas, organizações, datas e valores monetários.

### spaCy
Biblioteca de NLP usada para NER, com `pt_core_news_lg` como modelo preferencial para português.

### Sumy
Biblioteca de sumarização usada para ranqueamento extrativo de frases relevantes.

### TextRank
Algoritmo de sumarização extrativa usado para ranquear frases importantes.

### Keyword boosting
Heurística que aumenta a importância de frases contendo termos relevantes do domínio político ou financeiro.
