/**
 * SpreadsheetCanvas - Simple grid/spreadsheet editor
 *
 * A basic spreadsheet component for tabular data.
 * Formula support will be added in a future iteration.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type { CanvasComponentProps } from '../../types/canvas';
import type { SpreadsheetContent, SpreadsheetCell } from '../../types/artifact';
import styles from './SpreadsheetCanvas.module.css';

export interface SpreadsheetCanvasProps extends CanvasComponentProps<SpreadsheetContent> {}

interface CellPosition {
  row: number;
  col: number;
}

export function SpreadsheetCanvas({
  artifact,
  readOnly = false,
  onChange,
  className,
}: SpreadsheetCanvasProps) {
  const { columns, rows } = artifact.content;
  const [selectedCell, setSelectedCell] = useState<CellPosition | null>(null);
  const [editingCell, setEditingCell] = useState<CellPosition | null>(null);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when editing
  useEffect(() => {
    if (editingCell && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingCell]);

  const getCellValue = (cell: SpreadsheetCell): string => {
    if (cell.value === null || cell.value === undefined) return '';
    return String(cell.value);
  };

  const handleCellClick = useCallback(
    (row: number, col: number) => {
      setSelectedCell({ row, col });
      if (!readOnly) {
        const cell = rows[row]?.[col];
        setEditValue(getCellValue(cell || { value: null }));
      }
    },
    [rows, readOnly]
  );

  const handleCellDoubleClick = useCallback(
    (row: number, col: number) => {
      if (readOnly) return;
      setEditingCell({ row, col });
      const cell = rows[row]?.[col];
      setEditValue(getCellValue(cell || { value: null }));
    },
    [rows, readOnly]
  );

  const handleCellChange = useCallback(
    (row: number, col: number, value: string) => {
      if (!onChange) return;

      // Parse value (simple type detection)
      let parsedValue: string | number | boolean | null = value;
      if (value === '') {
        parsedValue = null;
      } else if (value.toLowerCase() === 'true') {
        parsedValue = true;
      } else if (value.toLowerCase() === 'false') {
        parsedValue = false;
      } else if (!isNaN(Number(value)) && value.trim() !== '') {
        parsedValue = Number(value);
      }

      const newRows = rows.map((r, rowIdx) =>
        rowIdx === row
          ? r.map((c, colIdx) =>
              colIdx === col ? { ...c, value: parsedValue } : c
            )
          : r
      );

      onChange({ ...artifact.content, rows: newRows });
    },
    [rows, onChange, artifact.content]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!selectedCell) return;

      const { row, col } = selectedCell;

      switch (e.key) {
        case 'Enter':
          if (editingCell) {
            handleCellChange(row, col, editValue);
            setEditingCell(null);
            // Move to next row
            if (row < rows.length - 1) {
              setSelectedCell({ row: row + 1, col });
            }
          } else if (!readOnly) {
            setEditingCell({ row, col });
            const cell = rows[row]?.[col];
            setEditValue(getCellValue(cell || { value: null }));
          }
          break;

        case 'Escape':
          setEditingCell(null);
          break;

        case 'Tab':
          e.preventDefault();
          if (editingCell) {
            handleCellChange(row, col, editValue);
            setEditingCell(null);
          }
          // Move to next column or wrap
          if (col < columns.length - 1) {
            setSelectedCell({ row, col: col + 1 });
          } else if (row < rows.length - 1) {
            setSelectedCell({ row: row + 1, col: 0 });
          }
          break;

        case 'ArrowUp':
          if (!editingCell && row > 0) {
            e.preventDefault();
            setSelectedCell({ row: row - 1, col });
          }
          break;

        case 'ArrowDown':
          if (!editingCell && row < rows.length - 1) {
            e.preventDefault();
            setSelectedCell({ row: row + 1, col });
          }
          break;

        case 'ArrowLeft':
          if (!editingCell && col > 0) {
            e.preventDefault();
            setSelectedCell({ row, col: col - 1 });
          }
          break;

        case 'ArrowRight':
          if (!editingCell && col < columns.length - 1) {
            e.preventDefault();
            setSelectedCell({ row, col: col + 1 });
          }
          break;

        default:
          // Start editing on any printable character
          if (!editingCell && !readOnly && e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
            setEditingCell({ row, col });
            setEditValue(e.key);
          }
      }
    },
    [selectedCell, editingCell, editValue, rows, columns.length, readOnly, handleCellChange]
  );

  const handleAddRow = useCallback(() => {
    if (!onChange || readOnly) return;
    const newRow: SpreadsheetCell[] = columns.map(() => ({ value: null }));
    onChange({
      ...artifact.content,
      rows: [...rows, newRow],
    });
  }, [onChange, readOnly, columns, rows, artifact.content]);

  const handleAddColumn = useCallback(() => {
    if (!onChange || readOnly) return;
    const newColName = String.fromCharCode(65 + columns.length); // A, B, C...
    onChange({
      ...artifact.content,
      columns: [...columns, newColName],
      rows: rows.map(row => [...row, { value: null }]),
    });
  }, [onChange, readOnly, columns, rows, artifact.content]);

  return (
    <div className={`${styles.container} ${className ?? ''}`}>
      <div className={styles.toolbar}>
        {!readOnly && (
          <>
            <button
              className={styles.toolbarButton}
              onClick={handleAddRow}
              title="Add row"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Add Row
            </button>
            <button
              className={styles.toolbarButton}
              onClick={handleAddColumn}
              title="Add column"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Add Column
            </button>
          </>
        )}
        <span className={styles.info}>
          {rows.length} rows x {columns.length} columns
        </span>
      </div>

      <div className={styles.tableWrapper} onKeyDown={handleKeyDown} tabIndex={0}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.rowHeader}>#</th>
              {columns.map((col, idx) => (
                <th key={idx} className={styles.colHeader}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                <td className={styles.rowHeader}>{rowIdx + 1}</td>
                {row.map((cell, colIdx) => {
                  const isSelected =
                    selectedCell?.row === rowIdx && selectedCell?.col === colIdx;
                  const isEditing =
                    editingCell?.row === rowIdx && editingCell?.col === colIdx;

                  return (
                    <td
                      key={colIdx}
                      className={`${styles.cell} ${isSelected ? styles.selected : ''}`}
                      onClick={() => handleCellClick(rowIdx, colIdx)}
                      onDoubleClick={() => handleCellDoubleClick(rowIdx, colIdx)}
                    >
                      {isEditing ? (
                        <input
                          ref={inputRef}
                          type="text"
                          className={styles.cellInput}
                          value={editValue}
                          onChange={e => setEditValue(e.target.value)}
                          onBlur={() => {
                            handleCellChange(rowIdx, colIdx, editValue);
                            setEditingCell(null);
                          }}
                        />
                      ) : (
                        <span className={styles.cellValue}>
                          {getCellValue(cell)}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
