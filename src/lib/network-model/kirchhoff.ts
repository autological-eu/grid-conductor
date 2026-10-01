/** Fundamental AC cycles; controllable links are deliberately outside this graph.
 * A spanning forest plus one row per chord provides a complete independent basis.
 */
export function kirchhoffCycles(
  edges: { id: string; a: string; b: string }[],
  branches: { edge_id: string; reactance: number }[],
): [string, number][][] {
  const byId = new Map(edges.map((e) => [e.id, e]));
  const tree = new Map<string, { to: string; edge: string; sign: number }[]>();
  const weights = new Map(branches.map((b) => [b.edge_id, b.reactance]));
  const cycles: [string, number][][] = [];
  for (const branch of branches) {
    const edge = byId.get(branch.edge_id)!;
    // Find the return path b -> a using only the existing spanning forest.
    const queue: { node: string; path: [string, number][] }[] = [{ node: edge.b, path: [] }];
    const visited = new Set([edge.b]);
    let path: [string, number][] | undefined;
    for (let i = 0; i < queue.length; i++) {
      const entry = queue[i]!;
      if (entry.node === edge.a) {
        path = entry.path;
        break;
      }
      for (const next of tree.get(entry.node) ?? []) {
        if (visited.has(next.to)) continue;
        visited.add(next.to);
        queue.push({ node: next.to, path: [...entry.path, [next.edge, next.sign]] });
      }
    }
    if (path) {
      const row: [string, number][] = [
        [edge.id, branch.reactance],
        ...path.map(([id, sign]): [string, number] => [id, sign * weights.get(id)!]),
      ];
      const scale = Math.max(...row.map(([, value]) => Math.abs(value)));
      cycles.push(row.map(([id, value]) => [id, value / scale]));
    } else {
      tree.set(edge.a, [...(tree.get(edge.a) ?? []), { to: edge.b, edge: edge.id, sign: 1 }]);
      tree.set(edge.b, [...(tree.get(edge.b) ?? []), { to: edge.a, edge: edge.id, sign: -1 }]);
    }
  }
  return cycles;
}
