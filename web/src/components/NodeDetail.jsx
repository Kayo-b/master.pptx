import { describeRelation, edgeKey } from '../graphLabels.js';
import { resolveMediaUrl } from '../api.js';

const CONFIDENCE_LABELS = {
  confirmado: 'Confirmado',
  investigado: 'Investigado',
  especulado: 'Especulado'
};

export default function NodeDetail({ node, nodesById, selectedEdgeKey, onSelectRelation }) {
  return (
    <details className="panel collapsible-panel" open>
      <summary className="panel-summary">
        <span>Nó selecionado</span>
      </summary>
      <div className="panel-body">
        {!node ? (
          <p>Selecione um nó no grafo.</p>
        ) : (
          <>
            {node.imagem_url ? (
              <img
                src={resolveMediaUrl(node.imagem_url)}
                alt={node.nome || node.id}
                className="node-detail-image"
              />
            ) : null}
            <p><strong>{node.nome || node.id}</strong></p>
            <p>Tipo: {node.tipo_no}</p>
            {node.descricao ? <p>{node.descricao}</p> : null}
            <h3>Relações</h3>
            <ul className="relation-list">
              {node.relacoes?.map((relation) => (
                <li key={edgeKey(relation)}>
                  <button
                    type="button"
                    className={`relation-item${selectedEdgeKey === edgeKey(relation) ? ' relation-item--active' : ''}`}
                    onClick={() => onSelectRelation(relation)}
                  >
                    <span>{describeRelation(relation, node.id, nodesById)}</span>
                    <small>{CONFIDENCE_LABELS[relation.confianca] || relation.confianca}</small>
                  </button>
                </li>
              ))}
              {!node.relacoes?.length ? <li>Nenhuma relação encontrada.</li> : null}
            </ul>
          </>
        )}
      </div>
    </details>
  );
}
