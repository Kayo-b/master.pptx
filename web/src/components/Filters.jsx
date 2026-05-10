const ALL_CONFIDENCES = ['confirmado', 'investigado', 'especulado'];
const ALL_NODE_TYPES = ['Pessoa', 'Organizacao', 'Orgao', 'Partido', 'Evento', 'InstrumentoFinanceiro', 'Bem'];
const CONFIDENCE_LABELS = {
  confirmado: 'Confirmado',
  investigado: 'Investigado',
  especulado: 'Especulado'
};
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
  confidences: 'Mostra o nível de certeza atribuído a cada aresta: confirmado, investigado ou especulado.',
  nodeTypes: 'Exibe apenas os tipos de entidade marcados nesta lista.',
  degree: 'Quando há um nó em foco, controla quantos saltos de distância aparecem no grafo.',
  edgeLabels: 'Mostra ou esconde os nomes curtos das arestas para reduzir poluição visual.'
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
          <h3>Confiança <span className="hint-badge" title={FILTER_HELP.confidences}>?</span></h3>
          {ALL_CONFIDENCES.map((value) => (
            <label key={value} className="checkbox-row">
              <input
                type="checkbox"
                checked={filters.confidences.has(value)}
                onChange={() =>
                  setFilters((current) => ({
                    ...current,
                    confidences: toggleInSet(current.confidences, value)
                  }))
                }
              />
              {CONFIDENCE_LABELS[value] || value}
            </label>
          ))}
        </div>
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
