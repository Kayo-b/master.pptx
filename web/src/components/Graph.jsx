import { useMemo } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import { EDGE_CONFIDENCE_STYLES, NODE_COLORS, edgeArrowShape, edgeColor, edgeKey, edgeShortLabel } from '../graphLabels.js';

function toElements(graph, highlightedNodeIds, highlightedEdgeKeys, hasSearch, positions) {
  const nodes = graph.nodes.map((node) => ({
    position: positions[node.id],
    classes: highlightedNodeIds.has(node.id)
      ? 'search-match-node'
      : hasSearch ? 'search-dim-node' : '',
    data: {
      id: node.id,
      label: node.nome || node.descricao || node.id,
      tipo: node.tipo_no,
      color: NODE_COLORS[node.tipo_no] || '#34495E'
    }
  }));
  const edges = graph.edges.map((edge) => ({
    classes: highlightedEdgeKeys.has(edgeKey(edge))
      ? 'search-match-edge'
      : hasSearch ? 'search-dim-edge' : '',
    data: {
      id: edgeKey(edge),
      source: edge.origem_id,
      target: edge.destino_id,
      labelShort: edgeShortLabel(edge),
      tipo: edge.tipo_relacao,
      confianca: edge.confianca,
      lineStyle: EDGE_CONFIDENCE_STYLES[edge.confianca] || 'solid',
      lineColor: edgeColor(edge),
      arrowShape: edgeArrowShape(edge),
      raw: edge
    }
  }));
  return [...nodes, ...edges];
}

export default function Graph({
  graph,
  onSelectNode,
  onSelectEdge,
  onClearSelection,
  highlightedNodeIds,
  highlightedEdgeKeys,
  hasSearch,
  positions,
  onPositionsChange,
  showEdgeLabels
}) {
  const hasCompletePositions = graph.nodes.every((node) => positions[node.id]);
  const elements = useMemo(
    () => toElements(graph, highlightedNodeIds, highlightedEdgeKeys, hasSearch, positions),
    [graph, highlightedEdgeKeys, highlightedNodeIds, hasSearch, positions]
  );
  const graphKey = useMemo(() => {
    const nodeIds = graph.nodes.map((node) => node.id).sort().join('|');
    const edgeIds = graph.edges
      .map((edge) => edgeKey(edge))
      .sort()
      .join('|');
    return `${nodeIds}__${edgeIds}__${hasCompletePositions ? 'preset' : 'cose'}`;
  }, [graph, hasCompletePositions]);
  const layout = useMemo(() => ({
    name: hasCompletePositions ? 'preset' : 'cose',
    animate: false,
    fit: true,
    padding: 48,
    randomize: !hasCompletePositions,
    componentSpacing: 160,
    nodeRepulsion: 200000,
    nodeOverlap: 24,
    idealEdgeLength: 140,
    edgeElasticity: 120,
    gravity: 0.2,
    numIter: 1500,
    initialTemp: 1200,
    coolingFactor: 0.96,
    minTemp: 1
  }), [hasCompletePositions]);

  return (
    <CytoscapeComponent
      key={graphKey}
      elements={elements}
      layout={layout}
      style={{ width: '100%', height: '100%', background: '#05060a' }}
      stylesheet={[
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'background-color': 'data(color)',
            color: '#e5eef9',
            width: 24,
            height: 24,
            'font-size': 9,
            'text-wrap': 'wrap',
            'text-max-width': 120,
            'text-margin-y': -16,
            'text-outline-width': 1,
            'text-outline-color': '#05060a'
          }
        },
        {
          selector: 'node.search-match-node',
          style: {
            'border-width': 4,
            'border-color': '#f59e0b',
            'overlay-opacity': 0,
            width: 30,
            height: 30,
            'font-size': 10,
            'z-index': 20
          }
        },
        {
          selector: 'node.search-dim-node',
          style: {
            opacity: 0.3
          }
        },
        {
          selector: 'edge',
          style: {
            label: showEdgeLabels ? 'data(labelShort)' : '',
            'curve-style': 'bezier',
            'line-style': 'data(lineStyle)',
            'line-color': 'data(lineColor)',
            'target-arrow-color': 'data(lineColor)',
            'target-arrow-shape': 'data(arrowShape)',
            color: '#94a3b8',
            'font-size': 7,
            width: 2,
            'text-background-opacity': 0,
            opacity: 0.8
          }
        },
        {
          selector: 'edge.search-match-edge',
          style: {
            width: 5,
            'line-color': '#f59e0b',
            'target-arrow-color': '#f59e0b',
            color: '#92400e',
            'font-size': 8,
            opacity: 1,
            'z-index': 15
          }
        },
        {
          selector: 'edge.search-dim-edge',
          style: {
            opacity: 0.15
          }
        }
      ]}
      cy={(cy) => {
        cy.off('tap');
        cy.on('tap', (event) => {
          if (event.target === cy) {
            onClearSelection();
          }
        });
        cy.off('layoutstop');
        cy.on('layoutstop', () => {
          const nextPositions = {};
          cy.nodes().forEach((node) => {
            nextPositions[node.id()] = node.position();
          });
          onPositionsChange(nextPositions);
        });
        cy.off('dragfree');
        cy.on('dragfree', 'node', () => {
          const nextPositions = {};
          cy.nodes().forEach((node) => {
            nextPositions[node.id()] = node.position();
          });
          onPositionsChange(nextPositions);
        });
        cy.off('tap', 'node');
        cy.on('tap', 'node', (event) => {
          onSelectNode(event.target.data());
        });
        cy.off('tap', 'edge');
        cy.on('tap', 'edge', (event) => {
          const data = event.target.data();
          onSelectEdge({ ...data.raw, id: data.id });
        });
      }}
    />
  );
}
