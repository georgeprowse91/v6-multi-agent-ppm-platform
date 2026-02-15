import type { DragEvent } from 'react';
import type { CanvasComponentProps } from '../../types/canvas';
import type { BoardCard, BoardColumn, BoardContent } from '../../types/artifact';
import styles from './BoardCanvas.module.css';

export interface BoardCanvasProps extends CanvasComponentProps<BoardContent> {}

export function BoardCanvas({ artifact, onChange, readOnly = false }: BoardCanvasProps) {
  const onDragStart = (event: DragEvent<HTMLElement>, card: BoardCard, sourceColumnId: string) => {
    event.dataTransfer.setData('application/json', JSON.stringify({ card, sourceColumnId }));
  };

  const onDrop = (event: DragEvent<HTMLElement>, targetColumnId: string) => {
    if (readOnly) return;
    const raw = event.dataTransfer.getData('application/json');
    if (!raw) return;
    const { card, sourceColumnId } = JSON.parse(raw) as { card: BoardCard; sourceColumnId: string };
    const columns = artifact.content.columns.map((column): BoardColumn => ({
      ...column,
      cards:
        column.id === sourceColumnId
          ? column.cards.filter((candidate) => candidate.id !== card.id)
          : column.id === targetColumnId
            ? [...column.cards, card]
            : column.cards,
    }));
    onChange?.({ columns });
  };

  const addCard = (columnId: string) => {
    if (readOnly) return;
    const card: BoardCard = { id: `card-${Date.now()}`, title: 'New card' };
    onChange?.({
      columns: artifact.content.columns.map((column) =>
        column.id === columnId ? { ...column, cards: [...column.cards, card] } : column
      ),
    });
  };

  return (
    <div className={styles.board}>
      {artifact.content.columns.map((column) => (
        <section
          key={column.id}
          className={styles.column}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => onDrop(event, column.id)}
        >
          <header className={styles.header}>{column.title}</header>
          <div className={styles.cards}>
            {column.cards.map((card) => (
              <article
                key={card.id}
                className={styles.card}
                draggable={!readOnly}
                onDragStart={(event) => onDragStart(event, card, column.id)}
              >
                <input
                  value={card.title}
                  readOnly={readOnly}
                  onChange={(event) => {
                    const nextColumns = artifact.content.columns.map((candidate) =>
                      candidate.id === column.id
                        ? {
                            ...candidate,
                            cards: candidate.cards.map((c) =>
                              c.id === card.id ? { ...c, title: event.target.value } : c
                            ),
                          }
                        : candidate
                    );
                    onChange?.({ columns: nextColumns });
                  }}
                />
              </article>
            ))}
          </div>
          {!readOnly && <button onClick={() => addCard(column.id)}>Add card</button>}
        </section>
      ))}
    </div>
  );
}
