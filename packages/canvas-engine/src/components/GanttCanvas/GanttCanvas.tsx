import type { CanvasComponentProps } from '../../types/canvas';
import type { GanttContent } from '../../types/artifact';
import styles from './GanttCanvas.module.css';

export interface GanttCanvasProps extends CanvasComponentProps<GanttContent> {}

export function GanttCanvas({ artifact, onChange, readOnly = false }: GanttCanvasProps) {
  const addTask = () => {
    if (readOnly) return;
    onChange?.({ tasks: [...artifact.content.tasks, { id: `task-${Date.now()}`, name: 'New task', startDate: new Date().toISOString().slice(0,10), endDate: new Date().toISOString().slice(0,10), dependencies: [] }] });
  };

  return (
    <div className={styles.wrap}>
      {!readOnly && <button onClick={addTask}>Add task</button>}
      {artifact.content.tasks.map((task) => (
        <div key={task.id} className={styles.row}>
          <input value={task.name} readOnly={readOnly} onChange={(e)=>onChange?.({tasks:artifact.content.tasks.map((t)=>t.id===task.id?{...t,name:e.target.value}:t)})} />
          <input type="date" value={task.startDate} readOnly={readOnly} onChange={(e)=>onChange?.({tasks:artifact.content.tasks.map((t)=>t.id===task.id?{...t,startDate:e.target.value}:t)})} />
          <input type="date" value={task.endDate} readOnly={readOnly} onChange={(e)=>onChange?.({tasks:artifact.content.tasks.map((t)=>t.id===task.id?{...t,endDate:e.target.value}:t)})} />
          <input type="date" value={task.baselineStart ?? ''} readOnly={readOnly} onChange={(e)=>onChange?.({tasks:artifact.content.tasks.map((t)=>t.id===task.id?{...t,baselineStart:e.target.value}:t)})} />
          <input type="date" value={task.baselineEnd ?? ''} readOnly={readOnly} onChange={(e)=>onChange?.({tasks:artifact.content.tasks.map((t)=>t.id===task.id?{...t,baselineEnd:e.target.value}:t)})} />
          <input value={task.dependencies.join(',')} readOnly={readOnly} onChange={(e)=>onChange?.({tasks:artifact.content.tasks.map((t)=>t.id===task.id?{...t,dependencies:e.target.value.split(',').map((v)=>v.trim()).filter(Boolean)}:t)})} />
        </div>
      ))}
    </div>
  );
}
