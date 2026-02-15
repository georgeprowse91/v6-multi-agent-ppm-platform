import type { CanvasComponentProps } from '../../types/canvas';
import type { GridContent } from '../../types/artifact';
import styles from './GridCanvas.module.css';

export interface GridCanvasProps extends CanvasComponentProps<GridContent> {}

export function GridCanvas({ artifact, onChange, readOnly = false }: GridCanvasProps) {
  const addRow = () => {
    if (readOnly) return;
    const row: Record<string, string | number> = {};
    artifact.content.columns.forEach((column) => { row[column.key] = column.type === 'number' ? 0 : ''; });
    onChange?.({ ...artifact.content, rows: [...artifact.content.rows, row] });
  };

  return (
    <div className={styles.wrap}>
      {!readOnly && <button onClick={addRow}>Add row</button>}
      <table className={styles.table}>
        <thead><tr>{artifact.content.columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead>
        <tbody>
          {artifact.content.rows.map((row, i) => (
            <tr key={i}>
              {artifact.content.columns.map((column) => (
                <td key={column.key}>
                  <input
                    aria-label={`${column.key}-${i}`}
                    value={String(row[column.key] ?? '')}
                    readOnly={readOnly}
                    onChange={(event) => {
                      const value = column.type === 'number' ? Number(event.target.value) : event.target.value;
                      const rows = artifact.content.rows.map((candidate, idx) => idx === i ? { ...candidate, [column.key]: value } : candidate);
                      onChange?.({ ...artifact.content, rows });
                    }}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
