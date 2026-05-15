const ALL_NODE_TYPES = ['Pessoa', 'Organizacao', 'Orgao', 'Partido', 'Evento', 'InstrumentoFinanceiro', 'Bem'];
const NODE_TYPE_LABELS = {
  Pessoa: 'Pessoa',
  Organizacao: 'Organização',
  Orgao: 'Órgão',
  Partido: 'Partido',
  Evento: 'Evento',
  InstrumentoFinanceiro: 'Instrumento financeiro',
  Bem: 'Bem'
};
const FILTER_HELP = {
  nodeTypes: 'Exibe apenas os tipos de entidade marcados nesta lista.',
  degree: 'Controla quantos saltos de distância aparecem no grafo. Sem nó em foco, usa o core Master/Vorcaro como referência.',
  edgeLabels: 'Mostra ou esconde os nomes curtos das arestas para reduzir poluição visual.',
  masterCore: 'Esconde grupos soltos e mantém apenas nós e arestas conectados, em qualquer grau, ao núcleo Master/Vorcaro.'
};

function toggleInSet(set, value) {
  const next = new Set(set);
  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }
  return next;
}

export default function Filters({ filters, setFilters }) {
  return (
    <details className="panel collapsible-panel" open>
      <summary className="panel-summary">
        <span>Filtros</span>
      </summary>
      <div className="panel-body">
        <div className="filter-group">
          <h3>Tipo de nó <span className="hint-badge" title={FILTER_HELP.nodeTypes}>?</span></h3>
          {ALL_NODE_TYPES.map((value) => (
            <label key={value} className="checkbox-row">
              <input
                type="checkbox"
                checked={filters.nodeTypes.has(value)}
                onChange={() =>
                  setFilters((current) => ({
                    ...current,
                    nodeTypes: toggleInSet(current.nodeTypes, value)
                  }))
                }
              />
              {NODE_TYPE_LABELS[value] || value}
            </label>
          ))}
        </div>
        <div className="filter-group">
          <h3>Core do caso <span className="hint-badge" title={FILTER_HELP.masterCore}>?</span></h3>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={filters.hideDisconnectedFromCore}
              onChange={() =>
                setFilters((current) => ({
                  ...current,
                  hideDisconnectedFromCore: !current.hideDisconnectedFromCore
                }))
              }
            />
            Esconder grupos fora do core Master/Vorcaro
          </label>
        </div>
        <div className="filter-group">
          <h3>Grau <span className="hint-badge" title={FILTER_HELP.degree}>?</span></h3>
          <input
            type="range"
            min="1"
            max="4"
            value={filters.degree}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                degree: Number(event.target.value)
              }))
            }
          />
          <span>{filters.degree}</span>
        </div>
        <div className="filter-group">
          <h3>Rótulos das arestas <span className="hint-badge" title={FILTER_HELP.edgeLabels}>?</span></h3>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={filters.showEdgeLabels}
              onChange={() =>
                setFilters((current) => ({
                  ...current,
                  showEdgeLabels: !current.showEdgeLabels
                }))
              }
            />
            Mostrar nomes curtos das arestas
          </label>
        </div>
      </div>
    </details>
  );
}
