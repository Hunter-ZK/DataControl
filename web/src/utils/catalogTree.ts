export interface CatalogEntry {
  code: string
  name: string
  parentCode?: string | null
  description?: string | null
}

export interface CatalogNode extends CatalogEntry {
  children: CatalogNode[]
  path: string[]
}

/** Materialize the server's real parentCode relationships; never infer levels from codes. */
export function buildCatalogTree(entries: CatalogEntry[]): CatalogNode[] {
  const nodes = new Map<string, CatalogNode>()
  for (const row of entries) {
    if (row.code && !nodes.has(row.code)) nodes.set(row.code, { ...row, children: [], path: [] })
  }
  const roots: CatalogNode[] = []
  for (const node of nodes.values()) {
    const parent = node.parentCode ? nodes.get(node.parentCode) : undefined
    // A corrupt self / cyclic parent chain cannot become a recursive UI branch.
    let cursor = parent
    const visited = new Set([node.code])
    let cycle = false
    while (cursor) {
      if (visited.has(cursor.code)) { cycle = true; break }
      visited.add(cursor.code)
      cursor = cursor.parentCode ? nodes.get(cursor.parentCode) : undefined
    }
    if (parent && !cycle) parent.children.push(node)
    else roots.push(node)
  }
  const walk = (node: CatalogNode, path: string[]) => {
    node.path = [...path, node.name]
    node.children.sort((a,b)=>a.name.localeCompare(b.name,'zh-CN'))
    for (const child of node.children) walk(child,node.path)
  }
  roots.sort((a,b)=>a.name.localeCompare(b.name,'zh-CN'))
  for (const root of roots) walk(root,[])
  return roots
}

export function flattenCatalogs(tree: CatalogNode[]): CatalogNode[] {
  return tree.flatMap(node => [node, ...flattenCatalogs(node.children)])
}
