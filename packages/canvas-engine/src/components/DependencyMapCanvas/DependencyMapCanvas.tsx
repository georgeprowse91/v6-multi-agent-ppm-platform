import type { CanvasComponentProps } from '../../types/canvas';
import type { DependencyMapContent } from '../../types/artifact';
import styles from './DependencyMapCanvas.module.css';

export interface DependencyMapCanvasProps extends CanvasComponentProps<DependencyMapContent> {}

export function DependencyMapCanvas({ artifact }: DependencyMapCanvasProps) {
  return (
    <div className={styles.wrap}>
      <ul>{artifact.content.nodes.map((node)=><li key={node.id}>{node.label}</li>)}</ul>
      <svg width="500" height="180" className={styles.graph}>
        {artifact.content.links.map((link, i) => {
          const s = artifact.content.nodes.findIndex((n)=>n.id===link.source);
          const t = artifact.content.nodes.findIndex((n)=>n.id===link.target);
          return <line key={i} x1={30+s*120} y1={40} x2={30+t*120} y2={120} stroke="#64748b" />;
        })}
        {artifact.content.nodes.map((node, i) => <circle key={node.id} cx={30+i*120} cy={40 + (i%2)*80} r={16} fill="#0ea5e9" />)}
      </svg>
    </div>
  );
}
