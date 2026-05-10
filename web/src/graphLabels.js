export const NODE_COLORS = {
  Pessoa: '#60a5fa',
  Organizacao: '#f59e0b',
  Orgao: '#c084fc',
  Partido: '#34d399',
  Evento: '#fb7185',
  InstrumentoFinanceiro: '#facc15',
  Bem: '#94a3b8'
};

const EDGE_SHORT_LABELS = {
  CONTROLA: 'controla',
  TRABALHOU_EM: 'trabalhou',
  RECEBEU_DE: 'recebeu',
  CONTRATOU: 'contratou',
  PRESSIONOU: 'pressionou',
  INVESTIGADO_POR: 'invest. por',
  FILIADO_A: 'filiado',
  INVESTIGADO_EM: 'invest. em',
  PARTICIPOU_DE: 'participou',
  NEGOCIOU: 'negociou',
  ASSOCIADO_A: 'associado',
  ASSOCIADO_INDIRETAMENTE: 'indireta',
  POSSUI: 'possui',
  TRANSFERIU_PARA: 'transferiu',
  VENDEU_ATIVOS_A: 'vendeu',
  TENTOU_COMPRAR: 'tentou',
  EMITIU: 'emitiu',
  ENVOLVIDA_EM: 'envolvida',
  FISCALIZOU: 'fiscalizou',
  LIQUIDOU: 'liquidou',
  CITADO_EM: 'citado'
};

const EDGE_COLORS = {
  CONTROLA: '#38bdf8',
  TRABALHOU_EM: '#38bdf8',
  FILIADO_A: '#38bdf8',
  ASSOCIADO_A: '#38bdf8',
  ASSOCIADO_INDIRETAMENTE: '#64748b',
  POSSUI: '#38bdf8',
  RECEBEU_DE: '#f59e0b',
  CONTRATOU: '#f59e0b',
  TRANSFERIU_PARA: '#f59e0b',
  VENDEU_ATIVOS_A: '#f59e0b',
  TENTOU_COMPRAR: '#f59e0b',
  NEGOCIOU: '#f59e0b',
  EMITIU: '#f59e0b',
  INVESTIGADO_POR: '#f43f5e',
  INVESTIGADO_EM: '#f43f5e',
  ENVOLVIDA_EM: '#f43f5e',
  FISCALIZOU: '#f43f5e',
  LIQUIDOU: '#f43f5e',
  PRESSIONOU: '#f43f5e',
  PARTICIPOU_DE: '#a78bfa',
  CITADO_EM: '#a78bfa'
};

export const EDGE_CONFIDENCE_STYLES = {
  confirmado: 'solid',
  investigado: 'dashed',
  especulado: 'dotted'
};

export const EDGE_CONFIDENCE_LABELS = {
  confirmado: 'Linha contínua = confirmado',
  investigado: 'Linha tracejada = investigado',
  especulado: 'Linha pontilhada = especulado'
};

const RELATION_PHRASES = {
  CONTROLA: {
    outgoing: 'Controla',
    incoming: 'É controlado por'
  },
  TRABALHOU_EM: {
    outgoing: 'Trabalhou em',
    incoming: 'Teve atuação de'
  },
  RECEBEU_DE: {
    outgoing: 'Recebeu de',
    incoming: 'Pagou a'
  },
  CONTRATOU: {
    outgoing: 'Contratou',
    incoming: 'Foi contratado por'
  },
  PRESSIONOU: {
    outgoing: 'Pressionou',
    incoming: 'Sofreu pressão de'
  },
  INVESTIGADO_POR: {
    outgoing: 'Foi investigado por',
    incoming: 'Investigou'
  },
  FILIADO_A: {
    outgoing: 'Foi filiado a',
    incoming: 'Teve filiação de'
  },
  INVESTIGADO_EM: {
    outgoing: 'Foi investigado em',
    incoming: 'Teve como investigado'
  },
  PARTICIPOU_DE: {
    outgoing: 'Participou de',
    incoming: 'Contou com a participação de'
  },
  NEGOCIOU: {
    outgoing: 'Negociou em',
    incoming: 'Foi palco de negociação de'
  },
  ASSOCIADO_A: {
    outgoing: 'Foi associado a',
    incoming: 'Foi associado a'
  },
  ASSOCIADO_INDIRETAMENTE: {
    outgoing: 'Tem ligação indireta com',
    incoming: 'Tem ligação indireta com'
  },
  POSSUI: {
    outgoing: 'Possui',
    incoming: 'Pertence a'
  },
  TRANSFERIU_PARA: {
    outgoing: 'Transferiu para',
    incoming: 'Recebeu transferência de'
  },
  VENDEU_ATIVOS_A: {
    outgoing: 'Vendeu ativos para',
    incoming: 'Comprou ativos de'
  },
  TENTOU_COMPRAR: {
    outgoing: 'Tentou comprar',
    incoming: 'Recebeu tentativa de compra de'
  },
  EMITIU: {
    outgoing: 'Emitiu',
    incoming: 'Foi emitido por'
  },
  ENVOLVIDA_EM: {
    outgoing: 'Esteve envolvida em',
    incoming: 'Envolveu'
  },
  FISCALIZOU: {
    outgoing: 'Fiscalizou',
    incoming: 'Foi fiscalizado por'
  },
  LIQUIDOU: {
    outgoing: 'Liquidou',
    incoming: 'Foi liquidado por'
  },
  CITADO_EM: {
    outgoing: 'Foi citado em',
    incoming: 'Citou'
  }
};

function appendContext(edge, description) {
  const extras = [];
  if (edge.cargo) extras.push(`cargo: ${edge.cargo}`);
  if (edge.papel) extras.push(`papel: ${edge.papel}`);
  if (edge.resultado) extras.push(`resultado: ${edge.resultado}`);
  if (edge.motivo) extras.push(`motivo: ${edge.motivo}`);
  if (edge.descricao) extras.push(edge.descricao);
  return extras.length ? `${description} — ${extras.join(' · ')}` : description;
}

export function edgeKey(edge) {
  return `${edge.tipo_relacao}:${edge.origem_id}:${edge.destino_id}:${edge.confianca}`;
}

export function normalizeForSearch(value) {
  return (value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

export function nodeLabel(node) {
  if (!node) return 'entidade desconhecida';
  return node.nome || node.descricao || node.sigla || node.tipo || node.id;
}

export function edgeShortLabel(edge) {
  const relationType = typeof edge === 'string' ? edge : edge?.tipo_relacao;
  return EDGE_SHORT_LABELS[relationType] || relationType?.toLowerCase() || '';
}

export function edgeColor(edge) {
  const relationType = typeof edge === 'string' ? edge : edge?.tipo_relacao;
  return EDGE_COLORS[relationType] || '#94a3b8';
}

export function edgeArrowShape(edge) {
  const relationType = typeof edge === 'string' ? edge : edge?.tipo_relacao;
  return relationType === 'ASSOCIADO_A' || relationType === 'ASSOCIADO_INDIRETAMENTE' ? 'none' : 'triangle';
}

export function describeRelation(edge, selectedNodeId, nodesById) {
  const isSource = edge.origem_id === selectedNodeId;
  const otherNodeId = isSource ? edge.destino_id : edge.origem_id;
  const otherNode = nodesById.get(otherNodeId);
  const phrases = RELATION_PHRASES[edge.tipo_relacao] || {};
  const verb = isSource
    ? (phrases.outgoing || edge.tipo_relacao)
    : (phrases.incoming || edge.tipo_relacao);
  return appendContext(edge, `${verb} ${nodeLabel(otherNode)}`);
}

export function describeEdge(edge, nodesById) {
  const source = nodeLabel(nodesById.get(edge.origem_id));
  const target = nodeLabel(nodesById.get(edge.destino_id));
  const phrase = RELATION_PHRASES[edge.tipo_relacao]?.outgoing || edge.tipo_relacao;
  return appendContext(edge, `${source} — ${phrase} ${target}`);
}
