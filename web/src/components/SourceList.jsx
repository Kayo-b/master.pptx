import { describeEdge } from '../graphLabels.js';

const CONFIDENCE_LABELS = {
  confirmado: 'Confirmado',
  investigado: 'Investigado',
  especulado: 'Especulado'
};

export default function SourceList({ edge, nodesById }) {
  return (
    <details className="panel collapsible-panel" open>
      <summary className="panel-summary">
        <span>Aresta selecionada</span>
      </summary>
      <div className="panel-body">
        {!edge ? (
          <p>Selecione uma aresta.</p>
        ) : (
          <>
            <p><strong>{describeEdge(edge, nodesById)}</strong></p>
            <p>Confiança: {CONFIDENCE_LABELS[edge.confianca] || edge.confianca}</p>
            <h3>Fontes</h3>
            <ul className="relation-list relation-list--scroll">
              {(edge.fontes || []).map((source) => (
                <li key={source.id}>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.titulo || source.url}
                  </a>
                </li>
              ))}
              {!edge.fontes?.length ? <li>Nenhuma fonte resolvida pela API.</li> : null}
            </ul>
          </>
        )}
      </div>
    </details>
  );
}
