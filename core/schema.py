from __future__ import annotations

from dataclasses import dataclass


CONFIDENCE_VALUES = ("confirmado", "investigado", "especulado")
SOURCE_TYPES = ("artigo", "documento_oficial", "relatorio", "transcript", "cpi")


@dataclass(frozen=True)
class NodeSchema:
    fields: tuple[str, ...]
    required: tuple[str, ...]
    enum_fields: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class RelationSchema:
    source_type: str
    target_type: str
    fields: tuple[str, ...]


NODE_ID_PREFIXES = {
    "Pessoa": "pessoa",
    "Organizacao": "org",
    "Orgao": "orgao",
    "Partido": "partido",
    "Evento": "evento",
    "InstrumentoFinanceiro": "instrumento",
    "Bem": "bem",
}


NODE_SCHEMAS: dict[str, NodeSchema] = {
    "Pessoa": NodeSchema(
        fields=("id", "nome", "apelido", "cargo_atual", "descricao"),
        required=("nome",),
        enum_fields={},
    ),
    "Organizacao": NodeSchema(
        fields=("id", "nome", "tipo", "cnpj", "descricao"),
        required=("nome",),
        enum_fields={
            "tipo": ("banco", "empresa", "escritorio_advocacia", "fundo", "corretora", "ong"),
        },
    ),
    "Orgao": NodeSchema(
        fields=("id", "nome", "sigla", "tipo", "descricao"),
        required=("nome",),
        enum_fields={
            "tipo": ("regulador", "judiciario", "policial", "ministerio", "legislativo"),
        },
    ),
    "Partido": NodeSchema(
        fields=("id", "nome", "sigla"),
        required=("nome",),
        enum_fields={},
    ),
    "Evento": NodeSchema(
        fields=("id", "nome", "tipo", "data_inicio", "data_fim", "descricao"),
        required=("nome",),
        enum_fields={
            "tipo": ("operacao_policial", "cpi", "julgamento", "delacao", "reuniao", "contrato"),
        },
    ),
    "InstrumentoFinanceiro": NodeSchema(
        fields=("id", "tipo", "valor", "descricao", "status"),
        required=("tipo",),
        enum_fields={
            "tipo": ("CDB", "carteira_credito", "precatorio", "titulo", "fundo"),
            "status": ("ativo", "liquidado", "investigado", "falso"),
        },
    ),
    "Bem": NodeSchema(
        fields=("id", "tipo", "descricao", "valor_estimado", "localizacao"),
        required=("tipo",),
        enum_fields={
            "tipo": ("imovel", "aeronave", "veiculo", "resort", "empresa_offshore"),
        },
    ),
}


RELATION_SCHEMAS: dict[str, RelationSchema] = {
    "CONTROLA": RelationSchema("Pessoa", "Organizacao", ("desde", "fonte_ids", "confianca")),
    "TRABALHOU_EM": RelationSchema("Pessoa", "Organizacao", ("cargo", "desde", "ate", "fonte_ids", "confianca")),
    "RECEBEU_DE": RelationSchema("Pessoa", "Organizacao", ("valor", "data", "descricao", "fonte_ids", "confianca")),
    "CONTRATOU": RelationSchema("Pessoa", "Organizacao", ("valor", "descricao", "data", "fonte_ids", "confianca")),
    "PRESSIONOU": RelationSchema("Pessoa", "Orgao", ("meio", "data", "descricao", "fonte_ids", "confianca")),
    "INVESTIGADO_POR": RelationSchema("Pessoa", "Orgao", ("data", "fonte_ids", "confianca")),
    "FILIADO_A": RelationSchema("Pessoa", "Partido", ("desde", "ate", "fonte_ids", "confianca")),
    "INVESTIGADO_EM": RelationSchema("Pessoa", "Evento", ("papel", "fonte_ids", "confianca")),
    "PARTICIPOU_DE": RelationSchema("Pessoa", "Evento", ("papel", "fonte_ids", "confianca")),
    "NEGOCIOU": RelationSchema("Pessoa", "Evento", ("papel", "resultado", "fonte_ids", "confianca")),
    "ASSOCIADO_A": RelationSchema("Pessoa", "Pessoa", ("tipo", "descricao", "fonte_ids", "confianca")),
    "POSSUI": RelationSchema("Pessoa", "Bem", ("desde", "fonte_ids", "confianca")),
    "TRANSFERIU_PARA": RelationSchema("Organizacao", "Organizacao", ("valor", "data", "fonte_ids", "confianca")),
    "VENDEU_ATIVOS_A": RelationSchema("Organizacao", "Organizacao", ("valor", "tipo_ativo", "data", "fonte_ids", "confianca")),
    "TENTOU_COMPRAR": RelationSchema("Organizacao", "Organizacao", ("data", "resultado", "fonte_ids", "confianca")),
    "EMITIU": RelationSchema("Organizacao", "InstrumentoFinanceiro", ("data", "lastro", "fonte_ids", "confianca")),
    "ENVOLVIDA_EM": RelationSchema("Organizacao", "Evento", ("papel", "fonte_ids", "confianca")),
    "FISCALIZOU": RelationSchema("Orgao", "Organizacao", ("resultado", "data", "fonte_ids", "confianca")),
    "LIQUIDOU": RelationSchema("Orgao", "Organizacao", ("data", "motivo", "fonte_ids", "confianca")),
    "CITADO_EM": RelationSchema("Partido", "Evento", ("contexto", "fonte_ids", "confianca")),
}
