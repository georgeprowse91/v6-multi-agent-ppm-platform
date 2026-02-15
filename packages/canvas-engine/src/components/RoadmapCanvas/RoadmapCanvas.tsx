import type { CanvasComponentProps } from '../../types/canvas';
import type { RoadmapContent } from '../../types/artifact';
import styles from './RoadmapCanvas.module.css';

export interface RoadmapCanvasProps extends CanvasComponentProps<RoadmapContent> {}

export function RoadmapCanvas({ artifact }: RoadmapCanvasProps) {
  return (
    <div className={styles.wrap}>
      {artifact.content.lanes.map((lane) => (
        <section key={lane} className={styles.lane}>
          <h4>{lane}</h4>
          <div className={styles.row}>
            {artifact.content.milestones.filter((m) => m.lane === lane).map((m) => (
              <article key={m.id} className={styles.milestone}>{m.title} ({m.startDate} → {m.endDate})</article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
