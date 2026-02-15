import type { CanvasComponentProps } from '../../types/canvas';
import type { BacklogContent } from '../../types/artifact';
import styles from './BacklogCanvas.module.css';

export interface BacklogCanvasProps extends CanvasComponentProps<BacklogContent> {}

export function BacklogCanvas({ artifact, onChange, readOnly = false }: BacklogCanvasProps) {
  const addItem = (parentId: string | null = null) => {
    if (readOnly) return;
    onChange?.({
      items: [...artifact.content.items, { id: `item-${Date.now()}`, title: 'New item', parentId, rank: artifact.content.items.length + 1, estimate: 1 }],
    });
  };

  return (
    <div className={styles.wrap}>
      {!readOnly && <button onClick={() => addItem(null)}>Add backlog item</button>}
      <table className={styles.table}>
        <thead><tr><th>Title</th><th>Parent</th><th>Rank</th><th>Estimate</th></tr></thead>
        <tbody>
          {artifact.content.items.map((item) => (
            <tr key={item.id}>
              <td><input value={item.title} readOnly={readOnly} onChange={(e)=>onChange?.({items:artifact.content.items.map((candidate)=>candidate.id===item.id?{...candidate,title:e.target.value}:candidate)})} /></td>
              <td>{item.parentId ?? '—'}</td>
              <td><input type="number" value={item.rank} readOnly={readOnly} onChange={(e)=>onChange?.({items:artifact.content.items.map((candidate)=>candidate.id===item.id?{...candidate,rank:Number(e.target.value)}:candidate)})} /></td>
              <td><input type="number" value={item.estimate} readOnly={readOnly} onChange={(e)=>onChange?.({items:artifact.content.items.map((candidate)=>candidate.id===item.id?{...candidate,estimate:Number(e.target.value)}:candidate)})} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
