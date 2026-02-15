import type { CanvasComponentProps } from '../../types/canvas';
import type { FinancialContent } from '../../types/artifact';
import styles from './FinancialCanvas.module.css';

export interface FinancialCanvasProps extends CanvasComponentProps<FinancialContent> {}

export function FinancialCanvas({ artifact, onChange, readOnly = false }: FinancialCanvasProps) {
  const total = artifact.content.lineItems.reduce((sum, item) => sum + item.forecast, 0);
  return (
    <div className={styles.wrap}>
      <label>
        Version
        <select value={artifact.content.version} disabled={readOnly} onChange={(e)=>onChange?.({ ...artifact.content, version: e.target.value })}>
          <option value="v1">v1</option>
          <option value="v2">v2</option>
          <option value="v3">v3</option>
        </select>
      </label>
      <table className={styles.table}>
        <thead><tr><th>Category</th><th>Budget</th><th>Actual</th><th>Forecast</th></tr></thead>
        <tbody>
          {artifact.content.lineItems.map((item) => (
            <tr key={item.id}>
              <td>{item.category}</td><td>{item.budget}</td><td>{item.actual}</td><td>{item.forecast}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <strong>Total Forecast: {total}</strong>
    </div>
  );
}
