import { useEffect, useMemo, useState } from 'react';
import Graph from './components/Graph.jsx';
import Filters from './components/Filters.jsx';
import Legend from './components/Legend.jsx';
import NodeDetail from './components/NodeDetail.jsx';
import SourceList from './components/SourceList.jsx';
import { fetchGraph, fetchNode } from './api.js';
import { describeEdge, edgeKey, edgeShortLabel, nodeLabel, normalizeForSearch } from './graphLabels.js';

const ALL_NODE_TYPES = ['Pessoa', 'Organizacao', 'Orgao', 'Partido', 'Evento', 'InstrumentoFinanceiro', 'Bem'];
const CORE_TERMS = ['master', 'vorcaro'];
const GRAPH_POSITIONS_STORAGE_KEY = 'master-graph-positions';
const NODE_ALIAS_MAP = {
  pessoa_henrique: 'pessoa_henrique_vorcaro',
  pessoa_vorcaro: 'pessoa_henrique_vorcaro',
  pessoa_familia_vorcaro: 'pessoa_henrique_vorcaro'
};
const NODE_IMAGE_OVERRIDES = {
  evento_cpi_do_crime_organizado: '/assets/images/cpi_do_crime_organizado-8e855c0cbc.jpg',
  evento_ligacao_de_flavio_bolsonaro_e_vorcaro_abre_crise_na_campanha_bolsonarista_balde_de_agua_fria: '/assets/images/flavio_bolsonaro_admitiu_ter_pedido_recursos_a_daniel_vorcaro_para_financiar_filme_sobre_jair_bolsonaro-e4346e322e.jpg',
  org_agencia_mithi: '/assets/images/agencia_mithi-5dc63de95f.png',
  org_financeira_brk: 'https://media.licdn.com/dms/image/v2/C4E0BAQGq9dkhZzKAdg/company-logo_200_200/company-logo_200_200/0/1631372732090/brickell_logo?e=2147483647&v=beta&t=srHcD-4KUgzsKSYOvRrmOpCv8_EOR-AYXu-OTQq1GcU'
  ,org_ligga_telecom: '/assets/images/ligga_telecom-1012500196.png',
  orgao_banco_central_do_brasil: '/assets/images/banco_central_do_brasil-24414cab39.png',
  orgao_supremo_tribunal_federal: '/assets/images/supremo_tribunal_federal-74513af570.jpg',
  pessoa_acm_neto: '/assets/images/acm_neto-0dbeb77cac.jpg',
  pessoa_alexandre_de_moraes: '/assets/images/alexandre_de_moraes-8136e01e83.jpg',
  pessoa_andreia_sadi: '/assets/images/andreia_sadi-cc0cf12d9e.jpg',
  pessoa_anthony_garotinho: '/assets/images/anthony_garotinho-1c1b15df2c.jpg',
  pessoa_chico_vigilante: '/assets/images/chico_vigilante-c497c8a282.jpg',
  pessoa_guido_mantega: '/assets/images/guido_mantega-bbfcba1437.jpg',
  pessoa_henrique_vorcaro: '/assets/images/henrique_vorcaro-e8bd51cfdc.jpg',
  pessoa_ibaneis_rocha: '/assets/images/ibaneis_rocha-5b1a857b86.jpg',
  pessoa_jair_bolsonaro: '/assets/images/jair_bolsonaro-04740743f4.jpg',
  pessoa_lula_da_silva: '/assets/images/lula_da_silva-686169bde8.jpg',
  pessoa_michel_temer: '/assets/images/michel_temer-ca397a053b.jpg',
  pessoa_ricardo_lewandowski: '/assets/images/ricardo_lewandowski-2d925e8b4c.jpg'
};

function isValidPosition(position) {
  return (
    position &&
    typeof position === 'object' &&
    Number.isFinite(position.x) &&
    Number.isFinite(position.y)
  );
}

function readStoredPositions() {
  if (typeof window === 'undefined') {
    return {};
  }
  try {
    const parsed = JSON.parse(window.localStorage.getItem(GRAPH_POSITIONS_STORAGE_KEY) || '{}');
    if (!parsed || typeof parsed !== 'object') {
      return {};
    }
    return Object.fromEntries(
      Object.entries(parsed).filter(([, position]) => isValidPosition(position))
    );
  } catch {
    return {};
  }
}

function remapNodeId(nodeId) {
  return NODE_ALIAS_MAP[nodeId] || nodeId;
}

function sanitizeNode(node) {
  if (!node) {
    return node;
  }
  const nextId = remapNodeId(node.id);
  const nextNode = nextId === node.id ? { ...node } : { ...node, id: nextId, nome: 'Henrique Vorcaro' };
  const imageOverride = NODE_IMAGE_OVERRIDES[nextNode.id];
  if (imageOverride) {
    nextNode.imagem_url = imageOverride;
  }
  return nextNode;
}

function sanitizeGraph(rawGraph) {
  const nodesById = new Map();
  rawGraph.nodes.forEach((node) => {
    const nextNode = sanitizeNode(node);
    const nextId = nextNode.id;
    if (!nodesById.has(nextId)) {
      nodesById.set(nextId, nextNode);
      return;
    }
    const current = nodesById.get(nextId);
    if (!current.imagem_url && nextNode.imagem_url) {
      current.imagem_url = nextNode.imagem_url;
    }
    if ((!current.descricao || current.descricao === current.nome) && nextNode.descricao) {
      current.descricao = nextNode.descricao;
    }
  });

  const edgesByKey = new Map();
  rawGraph.edges.forEach((edge) => {
    const nextEdge = {
      ...edge,
      origem_id: remapNodeId(edge.origem_id),
      destino_id: remapNodeId(edge.destino_id)
    };
    if (nextEdge.origem_id === nextEdge.destino_id) {
      return;
    }
    const key = edgeKey(nextEdge);
    if (!edgesByKey.has(key)) {
      edgesByKey.set(key, nextEdge);
    }
  });

  return {
    nodes: Array.from(nodesById.values()),
    edges: Array.from(edgesByKey.values())
  };
}

function neighborhood(graph, nodeId, degree) {
  return neighborhoodFromSeeds(graph, [nodeId], degree);
}

function neighborhoodFromSeeds(graph, seedIds, degree) {
  const validSeeds = seedIds.filter(Boolean);
  if (!validSeeds.length) {
    return graph;
  }
  const adjacency = new Map();
  graph.edges.forEach((edge) => {
    if (!adjacency.has(edge.origem_id)) adjacency.set(edge.origem_id, new Set());
    if (!adjacency.has(edge.destino_id)) adjacency.set(edge.destino_id, new Set());
    adjacency.get(edge.origem_id).add(edge.destino_id);
    adjacency.get(edge.destino_id).add(edge.origem_id);
  });
  const visited = new Set(validSeeds);
  const queue = validSeeds.map((id) => ({ id, depth: 0 }));
  while (queue.length) {
    const current = queue.shift();
    if (current.depth >= degree) continue;
    (adjacency.get(current.id) || []).forEach((neighbor) => {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push({ id: neighbor, depth: current.depth + 1 });
      }
    });
  }
  return {
    nodes: graph.nodes.filter((node) => visited.has(node.id)),
    edges: graph.edges.filter((edge) => visited.has(edge.origem_id) && visited.has(edge.destino_id))
  };
}

function coreSeedIds(graph) {
  return graph.nodes
    .filter((node) => {
      const searchable = normalizeForSearch(`${node.id} ${nodeLabel(node)}`);
      return CORE_TERMS.some((term) => searchable.includes(term));
    })
    .map((node) => node.id);
}

function connectedToCore(graph) {
  const seeds = coreSeedIds(graph);
  if (!seeds.length) {
    return { nodes: [], edges: [] };
  }
  const adjacency = new Map();
  graph.edges.forEach((edge) => {
    if (!adjacency.has(edge.origem_id)) adjacency.set(edge.origem_id, new Set());
    if (!adjacency.has(edge.destino_id)) adjacency.set(edge.destino_id, new Set());
    adjacency.get(edge.origem_id).add(edge.destino_id);
    adjacency.get(edge.destino_id).add(edge.origem_id);
  });
  const visited = new Set(seeds);
  const queue = [...seeds];
  while (queue.length) {
    const current = queue.shift();
    (adjacency.get(current) || []).forEach((neighbor) => {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push(neighbor);
      }
    });
  }
  return {
    nodes: graph.nodes.filter((node) => visited.has(node.id)),
    edges: graph.edges.filter((edge) => visited.has(edge.origem_id) && visited.has(edge.destino_id))
  };
}

function buildIndirectEdges(graph, nodesById) {
  const directAssociations = new Set(
    graph.edges
      .filter((edge) => {
        const originType = nodesById.get(edge.origem_id)?.tipo_no;
        const destinationType = nodesById.get(edge.destino_id)?.tipo_no;
        return originType === 'Pessoa' && destinationType === 'Pessoa';
      })
      .map((edge) => [edge.origem_id, edge.destino_id].sort().join('::'))
  );
  const derived = new Map();
  const controlEdges = graph.edges.filter((edge) => edge.tipo_relacao === 'CONTROLA');

  controlEdges.forEach((controlEdge) => {
    const controller = nodesById.get(controlEdge.origem_id);
    const organization = nodesById.get(controlEdge.destino_id);
    if (controller?.tipo_no !== 'Pessoa' || organization?.tipo_no !== 'Organizacao') {
      return;
    }

    graph.edges.forEach((supportEdge) => {
      if (supportEdge === controlEdge || supportEdge.tipo_relacao === 'CONTROLA') return;

      let relatedPersonId = null;
      if (
        supportEdge.destino_id === organization.id &&
        nodesById.get(supportEdge.origem_id)?.tipo_no === 'Pessoa'
      ) {
        relatedPersonId = supportEdge.origem_id;
      } else if (
        supportEdge.origem_id === organization.id &&
        nodesById.get(supportEdge.destino_id)?.tipo_no === 'Pessoa'
      ) {
        relatedPersonId = supportEdge.destino_id;
      }

      if (!relatedPersonId || relatedPersonId === controller.id) return;

      const pairIds = [controller.id, relatedPersonId].sort();
      const pairKey = pairIds.join('::');
      if (directAssociations.has(pairKey)) return;

      const current = derived.get(pairKey) || {
        tipo_relacao: 'ASSOCIADO_INDIRETAMENTE',
        origem_id: pairIds[0],
        destino_id: pairIds[1],
        confianca: 'investigado',
        fonte_ids: new Set(),
        fontes: new Map(),
        intermediarios: new Set(),
        suportes: new Set()
      };

      current.intermediarios.add(nodeLabel(organization));
      current.suportes.add(edgeShortLabel(supportEdge));

      [controlEdge, supportEdge].forEach((edge) => {
        (edge.fonte_ids || []).forEach((sourceId) => current.fonte_ids.add(sourceId));
        (edge.fontes || []).forEach((source) => current.fontes.set(source.id, source));
      });

      if (controlEdge.confianca === 'confirmado' && supportEdge.confianca === 'confirmado') {
        current.confianca = 'confirmado';
      }

      derived.set(pairKey, current);
    });
  });

  return Array.from(derived.values()).map((edge) => {
    const intermediarios = Array.from(edge.intermediarios);
    const suportes = Array.from(edge.suportes).filter(Boolean);
    const resumoOrg =
      intermediarios.length > 2
        ? `${intermediarios.slice(0, 2).join(', ')} e mais ${intermediarios.length - 2}`
        : intermediarios.join(', ');
    const resumoSuporte = suportes.length ? `; suporte: ${suportes.join(', ')}` : '';
    return {
      tipo_relacao: edge.tipo_relacao,
      origem_id: edge.origem_id,
      destino_id: edge.destino_id,
      confianca: edge.confianca,
      fonte_ids: Array.from(edge.fonte_ids),
      fontes: Array.from(edge.fontes.values()),
      descricao: resumoOrg
        ? `Ligação indireta via organização controlada: ${resumoOrg}${resumoSuporte}.`
        : 'Ligação indireta por organização controlada.',
      derivada: true,
      intermediarios
    };
  });
}

export default function App() {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [nodeDetail, setNodeDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [graphPositions, setGraphPositions] = useState(() => readStoredPositions());
  const [filters, setFilters] = useState({
    nodeTypes: new Set(ALL_NODE_TYPES),
    degree: 1,
    showEdgeLabels: true,
    hideDisconnectedFromCore: false
  });

  useEffect(() => {
    fetchGraph()
      .then((nextGraph) => setGraph(sanitizeGraph(nextGraph)))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    window.localStorage.setItem(GRAPH_POSITIONS_STORAGE_KEY, JSON.stringify(graphPositions));
  }, [graphPositions]);

  useEffect(() => {
    if (!selectedNode) {
      setNodeDetail(null);
      return;
    }
    fetchNode(selectedNode.id)
      .then((nextNode) => setNodeDetail(sanitizeNode(nextNode)))
      .catch((err) => setError(err.message));
  }, [selectedNode]);

  const filteredGraph = useMemo(() => {
    const visibleNodes = graph.nodes.filter((node) => filters.nodeTypes.has(node.tipo_no));
    const visibleNodeIds = new Set(visibleNodes.map((node) => node.id));
    const visibleEdges = graph.edges.filter(
      (edge) =>
        visibleNodeIds.has(edge.origem_id) &&
        visibleNodeIds.has(edge.destino_id)
    );
    return {
      nodes: visibleNodes,
      edges: visibleEdges
    };
  }, [filters, graph]);
  const nodesById = useMemo(
    () => new Map(graph.nodes.map((node) => [node.id, node])),
    [graph.nodes]
  );
  const indirectRelations = useMemo(() => buildIndirectEdges(filteredGraph, nodesById), [filteredGraph, nodesById]);

  const displayGraph = useMemo(() => {
    const graphWithIndirect = {
      nodes: filteredGraph.nodes,
      edges: [...filteredGraph.edges, ...indirectRelations]
    };
    const graphInScope = filters.hideDisconnectedFromCore ? connectedToCore(graphWithIndirect) : graphWithIndirect;
    if (selectedNode) {
      return neighborhood(graphInScope, selectedNode.id, filters.degree);
    }
    const coreSeeds = coreSeedIds(graphInScope);
    if (!coreSeeds.length) {
      return graphInScope;
    }
    return neighborhoodFromSeeds(graphInScope, coreSeeds, filters.degree);
  }, [filteredGraph, filters.degree, filters.hideDisconnectedFromCore, indirectRelations, selectedNode]);
  const visibleNodeIds = useMemo(() => new Set(displayGraph.nodes.map((node) => node.id)), [displayGraph.nodes]);
  const visibleEdgeKeys = useMemo(() => new Set(displayGraph.edges.map((edge) => edgeKey(edge))), [displayGraph.edges]);
  const normalizedSearch = useMemo(() => normalizeForSearch(searchQuery.trim()), [searchQuery]);
  const searchMatches = useMemo(() => {
    if (!normalizedSearch) {
      return { nodeIds: new Set(), edgeKeys: new Set(), nodes: 0, edges: 0 };
    }
    const matchedNodeIds = new Set(
      displayGraph.nodes
        .filter((node) => normalizeForSearch(nodeLabel(node)).includes(normalizedSearch))
        .map((node) => node.id)
    );
    const matchedEdgeKeys = new Set(
      displayGraph.edges
        .filter((edge) => {
          const edgeText = normalizeForSearch(describeEdge(edge, nodesById));
          return (
            edgeText.includes(normalizedSearch) ||
            matchedNodeIds.has(edge.origem_id) ||
            matchedNodeIds.has(edge.destino_id)
          );
        })
        .map((edge) => edgeKey(edge))
    );
    return {
      nodeIds: matchedNodeIds,
      edgeKeys: matchedEdgeKeys,
      nodes: matchedNodeIds.size,
      edges: matchedEdgeKeys.size
    };
  }, [displayGraph.edges, displayGraph.nodes, nodesById, normalizedSearch]);
  const activeNode = selectedNode ? nodesById.get(selectedNode.id) || selectedNode : null;
  const activeEdgeLabel = useMemo(() => {
    if (!selectedEdge) return null;
    const origin = nodeLabel(nodesById.get(selectedEdge.origem_id)) || selectedEdge.origem_id;
    const destination = nodeLabel(nodesById.get(selectedEdge.destino_id)) || selectedEdge.destino_id;
    return `${origin} -> ${selectedEdge.tipo_relacao} -> ${destination}`;
  }, [nodesById, selectedEdge]);
  const displayedNodeDetail = useMemo(() => {
    if (!nodeDetail) return null;
    const derivedRelations = indirectRelations.filter(
      (edge) => edge.origem_id === nodeDetail.id || edge.destino_id === nodeDetail.id
    );
    return {
      ...nodeDetail,
      relacoes: [...(nodeDetail.relacoes || []), ...derivedRelations]
    };
  }, [indirectRelations, nodeDetail]);

  useEffect(() => {
    if (selectedNode && !visibleNodeIds.has(selectedNode.id)) {
      setSelectedNode(null);
      setNodeDetail(null);
    }
  }, [selectedNode, visibleNodeIds]);

  useEffect(() => {
    if (selectedEdge && !visibleEdgeKeys.has(edgeKey(selectedEdge))) {
      setSelectedEdge(null);
    }
  }, [selectedEdge, visibleEdgeKeys]);

  function clearGraphFocus() {
    setSelectedNode(null);
    setSelectedEdge(null);
  }

  function rememberGraphPositions(nextPositions) {
    setGraphPositions((current) => ({ ...current, ...nextPositions }));
  }

  if (loading) {
    return <main className="layout"><section className="panel">Carregando...</section></main>;
  }

  if (error) {
    return <main className="layout"><section className="panel">Erro: {error}</section></main>;
  }

  return (
    <main className="layout">
      <aside className="sidebar">
        <div className="sidebar__scroll">
          <NodeDetail
            node={displayedNodeDetail}
            nodesById={nodesById}
            selectedEdgeKey={selectedEdge ? edgeKey(selectedEdge) : null}
            onSelectRelation={setSelectedEdge}
          />
          <SourceList edge={selectedEdge} nodesById={nodesById} />
          <Filters filters={filters} setFilters={setFilters} />
        </div>
      </aside>
      <section className="content">
        <section className="graph-panel">
          <div className="graph-toolbar">
            <div className="graph-toolbar__main">
              <div className="graph-toolbar__status">
                <span className="graph-pill graph-pill--primary">
                  {activeNode ? `Foco em: ${nodeLabel(activeNode)}` : 'Visão geral do grafo'}
                </span>
                <span className="graph-pill">
                  {activeNode ? `Grau ${filters.degree}` : `Grau ${filters.degree} a partir do core`}
                </span>
                {selectedEdge ? (
                  <span className="graph-pill">{activeEdgeLabel}</span>
                ) : null}
                <span className="graph-pill">
                  {displayGraph.nodes.length} nós / {displayGraph.edges.length} arestas
                </span>
                {filters.hideDisconnectedFromCore ? (
                  <span className="graph-pill">Apenas componente conectado ao core Master/Vorcaro</span>
                ) : null}
                <span className="graph-pill">Shift + arrastar: selecionar e mover vários nós</span>
                {normalizedSearch ? (
                  <span className="graph-pill">
                    Busca: {searchMatches.nodes} nós / {searchMatches.edges} arestas
                  </span>
                ) : null}
              </div>
            </div>
            {(activeNode || selectedEdge) ? (
              <button type="button" className="ghost-button" onClick={clearGraphFocus}>
                Voltar à visão geral
              </button>
            ) : null}
          </div>
          <div className="graph-canvas">
            <div className="graph-overlay graph-overlay--left">
              <div className="graph-search">
                <input
                  type="search"
                  className="graph-search__input"
                  placeholder="Buscar nomes no grafo"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
                {searchQuery ? (
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => setSearchQuery('')}
                  >
                    Limpar
                  </button>
                ) : null}
              </div>
            </div>
            <div className="graph-overlay graph-overlay--right">
              <Legend />
            </div>
            <Graph
              graph={displayGraph}
              onSelectNode={(node) => {
                setSelectedNode(node);
                setSelectedEdge(null);
              }}
              onSelectEdge={(edge) => {
                setSelectedEdge(edge);
                setSelectedNode(null);
              }}
              onClearSelection={clearGraphFocus}
              highlightedNodeIds={searchMatches.nodeIds}
              highlightedEdgeKeys={searchMatches.edgeKeys}
              hasSearch={Boolean(normalizedSearch)}
              positions={graphPositions}
              onPositionsChange={rememberGraphPositions}
              showEdgeLabels={filters.showEdgeLabels}
            />
          </div>
        </section>
      </section>
    </main>
  );
}
