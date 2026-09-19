import { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { type ForceGraphMethods, type LinkObject, type NodeObject } from 'react-force-graph-2d'
import { kind, type Edge } from './api'

const COLOR = { document: '#3346d3', ticket: '#b45309', meeting: '#7c3aad', slack: '#0e7c66', entity: '#6b7686' }
const FONT = 'IBM Plex Sans, sans-serif'

type N = NodeObject<{ id: string }>
type L = LinkObject<{ id: string }, { label: string }>

export default function Graph({ edges, focus }: { edges: Edge[]; focus: string | null }) {
  const box = useRef<HTMLDivElement>(null)
  const fg = useRef<ForceGraphMethods<N, L>>(undefined)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width))
    if (box.current) ro.observe(box.current)
    return () => ro.disconnect()
  }, [])

  // force-graph mutates its input, so hand it fresh copies
  const data = useMemo(() => ({
    nodes: [...new Set(edges.flatMap(e => [e.source, e.target]))].map(id => ({ id })),
    links: edges.map(e => ({ ...e })),
  }), [edges])

  return (
    <div ref={box} className="graph">
      {edges.length === 0 ? (
        <p className="empty">No relationship path for this answer.</p>
      ) : width > 0 && (
        <ForceGraph2D<{ id: string }, { label: string }>
          ref={fg}
          graphData={data}
          width={width}
          height={340}
          cooldownTicks={80}
          onEngineStop={() => fg.current?.zoomToFit(300, 40)}
          linkColor={() => '#c3cad4'}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          nodeCanvasObject={(n: N, ctx, scale) => {
            const r = n.id === focus ? 7 : 5
            ctx.fillStyle = COLOR[kind(n.id)]
            ctx.beginPath()
            ctx.arc(n.x!, n.y!, r, 0, 2 * Math.PI)
            ctx.fill()
            ctx.font = `${n.id === focus ? 600 : 500} ${12 / scale}px ${FONT}`
            ctx.fillStyle = '#18202b'
            ctx.textAlign = 'center'
            ctx.fillText(n.id, n.x!, n.y! + r + 12 / scale)
          }}
          linkCanvasObjectMode={() => 'after'}
          linkCanvasObject={(l: L, ctx, scale) => {
            const s = l.source as N, t = l.target as N
            ctx.font = `${10 / scale}px ${FONT}`
            ctx.fillStyle = '#6b7686'
            ctx.textAlign = 'center'
            ctx.fillText(l.label, (s.x! + t.x!) / 2, (s.y! + t.y!) / 2 - 3 / scale)
          }}
        />
      )}
    </div>
  )
}
