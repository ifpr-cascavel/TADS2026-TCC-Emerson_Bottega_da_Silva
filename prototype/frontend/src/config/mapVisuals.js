// Single source of truth for the styling of every element drawn on the map.
// Both the map layers (MapView) and the legend (MapLegend) read from here, so
// the two can never drift out of sync (DRY).

export const MAP_VISUALS = {
  boundaryPoint: {
    id: 'boundaryPoint',
    label: 'Pontos de delimitação',
    color: '#2563eb', // blue
  },
  boundaryArea: {
    id: 'boundaryArea',
    label: 'Área delimitada',
    color: '#2563eb',
    fillColor: '#bfdbfe',
  },
  triangleEdge: {
    id: 'triangleEdge',
    label: 'Triângulos (malha de Delaunay)',
    color: '#dc2626', // red
  },
  voronoiEdge: {
    id: 'voronoiEdge',
    label: 'Arestas de Voronoi',
    color: '#059669', // green
    tooltip:
      'Linhas que dividem o mapa em regiões. Cada região reúne os locais mais ' +
      'próximos de um mesmo ponto da malha; por isso ajudam a visualizar qual ' +
      'ponto vizinho está mais perto em cada parte do terreno.',
  },
  sensorCandidate: {
    id: 'sensorCandidate',
    label: 'Pontos sugeridos para sensores',
    color: '#f59e0b', // amber
    // Describes the internal mesh junctions used as suggested sensor locations.
    tooltip:
      'Pontos sugeridos para sensores: junções internas da malha, onde três ou ' +
      'mais triângulos se encontram. Pontos sobre a borda delimitada pelo usuário ' +
      'não são sugeridos. O protótipo não define um raio de cobertura físico; ' +
      'cada ponto representa um local de monitoramento sugerido.',
  },
  sensorInfluence: {
    id: 'sensorInfluence',
    label: 'Área de influência do sensor',
    color: '#ffffff',
    fillColor: '#f59e0b',
    tooltip:
      'Área aproximada que um sensor consegue monitorar conforme o alcance ' +
      'informado em metros. Regiões sobrepostas podem ser monitoradas por mais ' +
      'de um sensor.',
  },
};

// Qualitative palette used to color triangles by partition. Colors are chosen
// to stay distinguishable next to one another; the palette cycles when the
// partition count exceeds its length.
export const PARTITION_PALETTE = [
  '#2563eb', '#dc2626', '#059669', '#d946ef', '#f59e0b',
  '#0891b2', '#7c3aed', '#65a30d', '#db2777', '#ea580c',
  '#0d9488', '#4f46e5',
];

export const getPartitionColor = (partitionIndex) =>
  PARTITION_PALETTE[partitionIndex % PARTITION_PALETTE.length];
