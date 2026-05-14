const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Erro ao consultar ${path}`);
  }
  return response.json();
}

export function fetchGraph() {
  return request('/graph');
}

export function fetchNode(nodeId) {
  return request(`/graph/node/${nodeId}`);
}

export function fetchNeighbors(nodeId, grau = 1) {
  return request(`/graph/node/${nodeId}/neighbors?grau=${grau}`);
}

export function resolveMediaUrl(url) {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  if (url.startsWith('/')) {
    return `${API_BASE_URL}${url}`;
  }
  return url;
}
