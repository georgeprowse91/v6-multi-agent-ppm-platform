/**
 * SpreadsheetCanvas - Simple grid/spreadsheet editor
 *
 * A basic spreadsheet component for tabular data.
 * Formula support will be added in a future iteration.
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import type { CanvasComponentProps } from '../../types/canvas';
import type { SpreadsheetContent, SpreadsheetCell } from '../../types/artifact';
import styles from './SpreadsheetCanvas.module.css';

export interface SpreadsheetCanvasProps extends CanvasComponentProps<SpreadsheetContent> {}

interface CellPosition {
  row: number;
  col: number;
}

type FormulaType = 'SUM' | 'AVERAGE';

interface ParsedFormula {
  type: FormulaType;
  startRow: number;
  startCol: number;
  endRow: number;
  endCol: number;
}

const formulaRegex = /^(sum|average)\s*\(\s*([a-z]+)(\d+)\s*(?::\s*([a-z]+)(\d+))?\s*\)$/i;

const columnLabelToIndex = (label: string): number => {
  return label
    .toUpperCase()
    .split('')
    .reduce((acc, char) => acc * 26 + (char.charCodeAt(0) - 64), 0) - 1;
};

const parseFormula = (formula: string): ParsedFormula | null => {
  const match = formulaRegex.exec(formula.trim());
  if (!match) return null;
  const [, type, startCol, startRow, endCol, endRow] = match;
  const startColumnIndex = columnLabelToIndex(startCol);
  const endColumnIndex = columnLabelToIndex(endCol ?? startCol);
  const startRowIndex = Number(startRow) - 1;
  const endRowIndex = Number(endRow ?? startRow) - 1;

  if (
    Number.isNaN(startRowIndex) ||
    Number.isNaN(endRowIndex) ||
    startColumnIndex < 0 ||
    endColumnIndex < 0
  ) {
    return null;
  }

  return {
    type: type.toUpperCase() as FormulaType,
    startRow: Math.min(startRowIndex, endRowIndex),
    startCol: Math.min(startColumnIndex, endColumnIndex),
    endRow: Math.max(startRowIndex, endRowIndex),
    endCol: Math.max(startColumnIndex, endColumnIndex),
  };
};

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
  const [editingColumn, setEditingColumn] = useState<number | null>(null);
  const [columnEditValue, setColumnEditValue] = useState('');
  const [viewMode, setViewMode] = useState<'table' | 'pivot'>('table');
  const [pivotGroupBy, setPivotGroupBy] = useState<string>('phase');
  const inputRef = useRef<HTMLInputElement>(null);
  const columnInputRef = useRef<HTMLInputElement>(null);

  const selectedRow = selectedCell?.row ?? null;
  const selectedColumn = selectedCell?.col ?? null;
  const columnLabels = useMemo(
    () => columns.map((col, idx) => col || String.fromCharCode(65 + idx)),
    [columns]
  );

  const pivotOptions = useMemo(() => {
    const labels = columns.map(label => label.toLowerCase());
    const options: { label: string; value: string; index: number }[] = [];
    labels.forEach((label, index) => {
      if (label.includes('phase')) {
        options.push({ label: columns[index], value: 'phase', index });
      }
      if (label.includes('resource') || label.includes('owner')) {
        options.push({ label: columns[index], value: 'resource', index });
      }
    });
    return options;
  }, [columns]);

  const costColumnIndex = useMemo(() => {
    const index = columns.findIndex(label => label.toLowerCase().includes('cost'));
    return index === -1 ? null : index;
  }, [columns]);

  useEffect(() => {
    if (pivotOptions.length === 0) return;
    const hasCurrent = pivotOptions.some(option => option.value === pivotGroupBy);
    if (!hasCurrent) {
      setPivotGroupBy(pivotOptions[0].value);
    }
  }, [pivotOptions, pivotGroupBy]);

  // Focus input when editing
  useEffect(() => {
    if (editingCell && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingCell]);

  useEffect(() => {
    if (editingColumn !== null && columnInputRef.current) {
      columnInputRef.current.focus();
      columnInputRef.current.select();
    }
  }, [editingColumn]);

  const getCellValue = (cell: SpreadsheetCell): string => {
    if (cell.value === null || cell.value === undefined) return '';
    return String(cell.value);
  };

  const resolveCellValue = useCallback(
    (
      rowIdx: number,
      colIdx: number,
      visited: Set<string> = new Set()
    ): number | string | boolean | null => {
      const cell = rows[rowIdx]?.[colIdx];
      if (!cell) return null;
      if (!cell.formula) return cell.value;
      const key = `${rowIdx}:${colIdx}`;
      if (visited.has(key)) return '#CYCLE!';
      const parsed = parseFormula(cell.formula);
      if (!parsed) return '#ERROR';
      visited.add(key);

      const values: number[] = [];
      for (let r = parsed.startRow; r <= parsed.endRow; r += 1) {
        for (let c = parsed.startCol; c <= parsed.endCol; c += 1) {
          const val = resolveCellValue(r, c, new Set(visited));
          if (typeof val === 'number') {
            values.push(val);
          }
        }
      }

      if (values.length === 0) return 0;
      const total = values.reduce((sum, val) => sum + val, 0);
      return parsed.type === 'AVERAGE' ? total / values.length : total;
    },
    [rows]
  );

  const getDisplayValue = useCallback(
    (rowIdx: number, colIdx: number): string => {
      const cell = rows[rowIdx]?.[colIdx];
      if (!cell) return '';
      if (cell.formula) {
        const resolved = resolveCellValue(rowIdx, colIdx);
        return resolved === null || resolved === undefined ? '' : String(resolved);
      }
      return getCellValue(cell);
    },
    [rows, resolveCellValue]
  );

  const handleCellClick = useCallback(
    (row: number, col: number) => {
      setSelectedCell({ row, col });
      if (!readOnly) {
        const cell = rows[row]?.[col];
        if (cell?.formula) {
          setEditValue(`=${cell.formula}`);
        } else {
          setEditValue(getCellValue(cell || { value: null }));
        }
      }
    },
    [rows, readOnly]
  );

  const handleRowHeaderClick = useCallback((row: number) => {
    setSelectedCell({ row, col: 0 });
  }, []);

  const handleColumnHeaderClick = useCallback((col: number) => {
    setSelectedCell({ row: 0, col });
  }, []);

  const handleCellDoubleClick = useCallback(
    (row: number, col: number) => {
      if (readOnly) return;
      setEditingCell({ row, col });
      const cell = rows[row]?.[col];
      if (cell?.formula) {
        setEditValue(`=${cell.formula}`);
      } else {
        setEditValue(getCellValue(cell || { value: null }));
      }
    },
    [rows, readOnly]
  );

  const handleCellChange = useCallback(
    (row: number, col: number, value: string) => {
      if (!onChange) return;

      const trimmed = value.trim();
      let parsedValue: string | number | boolean | null = trimmed;
      let formula: string | undefined;
      if (trimmed.startsWith('=')) {
        formula = trimmed.slice(1);
        parsedValue = null;
      } else if (trimmed === '') {
        parsedValue = null;
      } else if (trimmed.toLowerCase() === 'true') {
        parsedValue = true;
      } else if (trimmed.toLowerCase() === 'false') {
        parsedValue = false;
      } else if (!isNaN(Number(trimmed)) && trimmed !== '') {
        parsedValue = Number(trimmed);
      }

      const newRows = rows.map((r, rowIdx) =>
        rowIdx === row
          ? r.map((c, colIdx) =>
              colIdx === col
                ? {
                    ...c,
                    value: parsedValue,
                    formula,
                  }
                : c
            )
          : r
      );

      onChange({ ...artifact.content, rows: newRows });
    },
    [rows, onChange, artifact.content]
  );

  const handleColumnRename = useCallback(() => {
    if (editingColumn === null || !onChange || readOnly) {
      setEditingColumn(null);
      return;
    }
    const trimmed = columnEditValue.trim();
    const updated = columns.map((col, idx) =>
      idx === editingColumn ? trimmed || col : col
    );
    onChange({ ...artifact.content, columns: updated });
    setEditingColumn(null);
  }, [editingColumn, columnEditValue, onChange, readOnly, columns, artifact.content]);

  const handleColumnDoubleClick = useCallback(
    (col: number) => {
      if (readOnly) return;
      setEditingColumn(col);
      setColumnEditValue(columns[col] || '');
    },
    [columns, readOnly]
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
            if (cell?.formula) {
              setEditValue(`=${cell.formula}`);
            } else {
              setEditValue(getCellValue(cell || { value: null }));
            }
          }
          break;

        case 'Escape':
          setEditingCell(null);
          setEditingColumn(null);
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

  const handleDeleteRow = useCallback(() => {
    if (!onChange || readOnly || selectedRow === null) return;
    const newRows = rows.filter((_, idx) => idx !== selectedRow);
    onChange({ ...artifact.content, rows: newRows });
    setSelectedCell(null);
  }, [onChange, readOnly, selectedRow, rows, artifact.content]);

  const handleDeleteColumn = useCallback(() => {
    if (!onChange || readOnly || selectedColumn === null) return;
    const newColumns = columns.filter((_, idx) => idx !== selectedColumn);
    const newRows = rows.map((row) => row.filter((_, idx) => idx !== selectedColumn));
    onChange({ ...artifact.content, columns: newColumns, rows: newRows });
    setSelectedCell(null);
  }, [onChange, readOnly, selectedColumn, columns, rows, artifact.content]);

  const pivotData = useMemo(() => {
    if (costColumnIndex === null || pivotOptions.length === 0) return null;
    const groupOption = pivotOptions.find(option => option.value === pivotGroupBy) ?? pivotOptions[0];
    if (!groupOption) return null;
    const totals = new Map<string, number>();
    rows.forEach((row, rowIdx) => {
      const groupCell = row[groupOption.index];
      const costCell = row[costColumnIndex];
      if (!groupCell || !costCell) return;
      const groupValue = String(groupCell.value ?? '').trim();
      if (!groupValue) return;
      const resolved = resolveCellValue(rowIdx, costColumnIndex);
      const resolvedCost = typeof resolved === 'number' ? resolved : Number(costCell.value);
      if (!Number.isFinite(resolvedCost)) return;
      totals.set(groupValue, (totals.get(groupValue) ?? 0) + resolvedCost);
    });
    return {
      groupLabel: groupOption.label,
      rows: Array.from(totals.entries()).map(([group, total]) => ({
        group,
        total,
      })),
    };
  }, [rows, costColumnIndex, pivotOptions, pivotGroupBy, resolveCellValue]);

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
            <button
              className={styles.toolbarButton}
              onClick={handleDeleteRow}
              title="Delete selected row"
              disabled={selectedRow === null}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Delete Row
            </button>
            <button
              className={styles.toolbarButton}
              onClick={handleDeleteColumn}
              title="Delete selected column"
              disabled={selectedColumn === null}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Delete Column
            </button>
          </>
        )}
        <div className={styles.viewToggle}>
          <button
            className={`${styles.toolbarButton} ${viewMode === 'table' ? styles.activeButton : ''}`}
            onClick={() => setViewMode('table')}
            type="button"
          >
            Table
          </button>
          <button
            className={`${styles.toolbarButton} ${viewMode === 'pivot' ? styles.activeButton : ''}`}
            onClick={() => setViewMode('pivot')}
            type="button"
          >
            Pivot
          </button>
        </div>
        {viewMode === 'pivot' && pivotOptions.length > 0 && (
          <label className={styles.pivotControl}>
            Group by
            <select
              value={pivotGroupBy}
              onChange={event => setPivotGroupBy(event.target.value)}
            >
              {pivotOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        )}
        <span className={styles.info}>
          {rows.length} rows x {columns.length} columns
        </span>
      </div>

      {viewMode === 'table' ? (
        <div className={styles.tableWrapper} onKeyDown={handleKeyDown} tabIndex={0}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.rowHeader}>#</th>
                {columnLabels.map((col, idx) => (
                  <th
                    key={idx}
                    className={`${styles.colHeader} ${selectedColumn === idx ? styles.selectedHeader : ''}`}
                    onClick={() => handleColumnHeaderClick(idx)}
                    onDoubleClick={() => handleColumnDoubleClick(idx)}
                  >
                    {editingColumn === idx ? (
                      <input
                        ref={columnInputRef}
                        type="text"
                        className={styles.columnInput}
                        value={columnEditValue}
                        onChange={(e) => setColumnEditValue(e.target.value)}
                        onBlur={handleColumnRename}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            handleColumnRename();
                          }
                        }}
                      />
                    ) : (
                      <span>{col}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  <td
                    className={`${styles.rowHeader} ${
                      selectedRow === rowIdx ? styles.selectedHeader : ''
                    }`}
                    onClick={() => handleRowHeaderClick(rowIdx)}
                  >
                    {rowIdx + 1}
                  </td>
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
                            {cell.formula ? getDisplayValue(rowIdx, colIdx) : getCellValue(cell)}
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
      ) : (
        <div className={styles.pivotWrapper}>
          {pivotData ? (
            <table className={styles.pivotTable}>
              <thead>
                <tr>
                  <th>{pivotData.groupLabel}</th>
                  <th>Total Cost</th>
                </tr>
              </thead>
              <tbody>
                {pivotData.rows.map(row => (
                  <tr key={row.group}>
                    <td>{row.group}</td>
                    <td>{row.total.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className={styles.pivotEmptyState}>
              <p>Pivot view requires columns named Phase or Resource and Cost.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
