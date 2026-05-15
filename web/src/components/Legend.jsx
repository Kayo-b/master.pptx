import { NODE_COLORS, edgeColor } from '../graphLabels.js';

const NODE_LEGEND = [
  ['Pessoa', NODE_COLORS.Pessoa],
  ['Organização', NODE_COLORS.Organizacao],
  ['Órgão', NODE_COLORS.Orgao],
  ['Partido', NODE_COLORS.Partido],
  ['Evento', NODE_COLORS.Evento],
  ['Instrumento', NODE_COLORS.InstrumentoFinanceiro],
  ['Bem', NODE_COLORS.Bem]
];

const EDGE_LEGEND = [
  ['Institucional', edgeColor('CONTROLA')],
  ['Financeira', edgeColor('RECEBEU_DE')],
  ['Investigação', edgeColor('INVESTIGADO_EM')],
  ['Contexto/Citação', edgeColor('PARTICIPOU_DE')],
  ['Indireta', edgeColor('ASSOCIADO_INDIRETAMENTE')]
];

export default function Legend() {
  return (
    <details className="panel collapsible-panel" open>
      <summary className="panel-summary">
        <span>Legenda</span>
      </summary>
      <div className="panel-body">
        <div className="filter-group">
          <h3>Cores dos nós</h3>
          <ul className="legend-list">
            {NODE_LEGEND.map(([label, color]) => (
              <li key={label} className="legend-row">
                <span className="legend-swatch" style={{ backgroundColor: color }} />
                <span>{label}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="filter-group">
          <h3>Cores das arestas</h3>
          <ul className="legend-list">
            {EDGE_LEGEND.map(([label, color]) => (
              <li key={label} className="legend-row">
                <span className="legend-line" style={{ backgroundColor: color }} />
                <span>{label}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  );
}
