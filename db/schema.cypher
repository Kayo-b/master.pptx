CREATE NODE TABLE Pessoa (
  id STRING,
  nome STRING,
  apelido STRING,
  cargo_atual STRING,
  descricao STRING,
  PRIMARY KEY(id)
);

CREATE NODE TABLE Organizacao (
  id STRING,
  nome STRING,
  tipo STRING,
  cnpj STRING,
  descricao STRING,
  PRIMARY KEY(id)
);

CREATE NODE TABLE Orgao (
  id STRING,
  nome STRING,
  sigla STRING,
  tipo STRING,
  descricao STRING,
  PRIMARY KEY(id)
);

CREATE NODE TABLE Partido (
  id STRING,
  nome STRING,
  sigla STRING,
  PRIMARY KEY(id)
);

CREATE NODE TABLE Evento (
  id STRING,
  nome STRING,
  tipo STRING,
  data_inicio STRING,
  data_fim STRING,
  descricao STRING,
  PRIMARY KEY(id)
);

CREATE NODE TABLE InstrumentoFinanceiro (
  id STRING,
  tipo STRING,
  valor STRING,
  descricao STRING,
  status STRING,
  PRIMARY KEY(id)
);

CREATE NODE TABLE Bem (
  id STRING,
  tipo STRING,
  descricao STRING,
  valor_estimado STRING,
  localizacao STRING,
  PRIMARY KEY(id)
);

CREATE REL TABLE CONTROLA (FROM Pessoa TO Organizacao, desde STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE TRABALHOU_EM (FROM Pessoa TO Organizacao, cargo STRING, desde STRING, ate STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE RECEBEU_DE (FROM Pessoa TO Organizacao, valor STRING, data STRING, descricao STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE CONTRATOU (FROM Pessoa TO Organizacao, valor STRING, descricao STRING, data STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE PRESSIONOU (FROM Pessoa TO Orgao, meio STRING, data STRING, descricao STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE INVESTIGADO_POR (FROM Pessoa TO Orgao, data STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE FILIADO_A (FROM Pessoa TO Partido, desde STRING, ate STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE INVESTIGADO_EM (FROM Pessoa TO Evento, papel STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE PARTICIPOU_DE (FROM Pessoa TO Evento, papel STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE NEGOCIOU (FROM Pessoa TO Evento, papel STRING, resultado STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE ASSOCIADO_A (FROM Pessoa TO Pessoa, tipo STRING, descricao STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE POSSUI (FROM Pessoa TO Bem, desde STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE TRANSFERIU_PARA (FROM Organizacao TO Organizacao, valor STRING, data STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE VENDEU_ATIVOS_A (FROM Organizacao TO Organizacao, valor STRING, tipo_ativo STRING, data STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE TENTOU_COMPRAR (FROM Organizacao TO Organizacao, data STRING, resultado STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE EMITIU (FROM Organizacao TO InstrumentoFinanceiro, data STRING, lastro STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE ENVOLVIDA_EM (FROM Organizacao TO Evento, papel STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE FISCALIZOU (FROM Orgao TO Organizacao, resultado STRING, data STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE LIQUIDOU (FROM Orgao TO Organizacao, data STRING, motivo STRING, fonte_ids STRING, confianca STRING);
CREATE REL TABLE CITADO_EM (FROM Partido TO Evento, contexto STRING, fonte_ids STRING, confianca STRING);
