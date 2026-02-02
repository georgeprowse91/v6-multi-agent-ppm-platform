import { useCallback, useEffect, useMemo, useState } from 'react';
import { hasPermission } from '@/auth/permissions';
import { useAppStore } from '@/store';
import styles from './MethodologyEditor.module.css';

const API_BASE = '/v1';

type MethodologyActivity = {
  id: string;
  name: string;
  description: string;
  prerequisites: string[];
  category?: string;
  recommended_canvas_tab?: string;
};

type MethodologyStage = {
  id: string;
  name: string;
  exit_criteria: string[];
  activities: MethodologyActivity[];
};

type MethodologyGateCriteria = {
  id: string;
  description: string;
  evidence?: string | null;
  check?: string | null;
};

type MethodologyGate = {
  id: string;
  name: string;
  stage: string;
  criteria: MethodologyGateCriteria[];
};

type MethodologyEditorPayload = {
  methodology_id: string;
  stages: MethodologyStage[];
  gates: MethodologyGate[];
};

const canvasTabs = ['document', 'tree', 'timeline', 'spreadsheet', 'dashboard'];

const createActivity = (): MethodologyActivity => ({
  id: '',
  name: '',
  description: '',
  prerequisites: [],
  category: 'methodology',
  recommended_canvas_tab: 'document',
});

const createStage = (): MethodologyStage => ({
  id: '',
  name: '',
  exit_criteria: [],
  activities: [],
});

const createGate = (): MethodologyGate => ({
  id: '',
  name: '',
  stage: '',
  criteria: [],
});

const createGateCriteria = (): MethodologyGateCriteria => ({
  id: '',
  description: '',
  evidence: '',
  check: '',
});

export function MethodologyEditor() {
  const { session } = useAppStore();
  const [methodologyId] = useState('hybrid');
  const [payload, setPayload] = useState<MethodologyEditorPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const canEdit = hasPermission(session.user?.permissions, 'methodology.edit');

  const activityIds = useMemo(() => {
    if (!payload) {
      return [];
    }
    return payload.stages.flatMap((stage) => stage.activities.map((activity) => activity.id));
  }, [payload]);

  const fetchEditor = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/methodology/editor?methodology_id=${methodologyId}`
      );
      if (!response.ok) {
        throw new Error(`Failed to load methodology editor: ${response.statusText}`);
      }
      const data = (await response.json()) as MethodologyEditorPayload;
      setPayload(data);
    } catch (fetchError) {
      const message = fetchError instanceof Error
        ? fetchError.message
        : 'Failed to load methodology editor.';
      setError(message);
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [methodologyId]);

  useEffect(() => {
    fetchEditor();
  }, [fetchEditor]);

  const updateStage = (index: number, updater: (stage: MethodologyStage) => MethodologyStage) => {
    setPayload((current) => {
      if (!current) {
        return current;
      }
      const stages = current.stages.map((stage, stageIndex) =>
        stageIndex === index ? updater(stage) : stage
      );
      return { ...current, stages };
    });
  };

  const updateActivity = (
    stageIndex: number,
    activityIndex: number,
    updater: (activity: MethodologyActivity) => MethodologyActivity
  ) => {
    updateStage(stageIndex, (stage) => {
      const activities = stage.activities.map((activity, index) =>
        index === activityIndex ? updater(activity) : activity
      );
      return { ...stage, activities };
    });
  };

  const moveStage = (index: number, direction: number) => {
    setPayload((current) => {
      if (!current) {
        return current;
      }
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= current.stages.length) {
        return current;
      }
      const stages = [...current.stages];
      [stages[index], stages[targetIndex]] = [stages[targetIndex], stages[index]];
      return { ...current, stages };
    });
  };

  const moveActivity = (stageIndex: number, activityIndex: number, direction: number) => {
    updateStage(stageIndex, (stage) => {
      const targetIndex = activityIndex + direction;
      if (targetIndex < 0 || targetIndex >= stage.activities.length) {
        return stage;
      }
      const activities = [...stage.activities];
      [activities[activityIndex], activities[targetIndex]] =
        [activities[targetIndex], activities[activityIndex]];
      return { ...stage, activities };
    });
  };

  const validatePayload = (current: MethodologyEditorPayload) => {
    const errors: string[] = [];
    current.stages.forEach((stage, stageIndex) => {
      if (!stage.id.trim()) {
        errors.push(`Stage ${stageIndex + 1}: ID is required.`);
      }
      if (!stage.name.trim()) {
        errors.push(`Stage ${stageIndex + 1}: name is required.`);
      }
      stage.activities.forEach((activity, activityIndex) => {
        if (!activity.id.trim()) {
          errors.push(`Stage ${stageIndex + 1} Activity ${activityIndex + 1}: ID is required.`);
        }
        if (!activity.name.trim()) {
          errors.push(`Stage ${stageIndex + 1} Activity ${activityIndex + 1}: name is required.`);
        }
        if (!activity.description.trim()) {
          errors.push(
            `Stage ${stageIndex + 1} Activity ${activityIndex + 1}: description is required.`
          );
        }
      });
    });

    const ids = new Set(activityIds.filter((id) => id.trim()));
    current.stages.forEach((stage) => {
      stage.activities.forEach((activity) => {
        activity.prerequisites.forEach((prereq) => {
          if (prereq.trim() && !ids.has(prereq.trim())) {
            errors.push(`Prerequisite ${prereq} referenced by ${activity.id} does not exist.`);
          }
        });
      });
    });

    current.gates.forEach((gate, gateIndex) => {
      if (!gate.id.trim()) {
        errors.push(`Gate ${gateIndex + 1}: ID is required.`);
      }
      if (!gate.name.trim()) {
        errors.push(`Gate ${gateIndex + 1}: name is required.`);
      }
      if (!gate.stage.trim()) {
        errors.push(`Gate ${gateIndex + 1}: stage is required.`);
      }
      gate.criteria.forEach((criterion, criterionIndex) => {
        if (!criterion.id.trim()) {
          errors.push(`Gate ${gateIndex + 1} Criterion ${criterionIndex + 1}: ID is required.`);
        }
        if (!criterion.description.trim()) {
          errors.push(
            `Gate ${gateIndex + 1} Criterion ${criterionIndex + 1}: description is required.`
          );
        }
      });
    });

    return errors;
  };

  const handleSave = async () => {
    if (!canEdit) {
      setError('You do not have permission to edit methodology settings.');
      return;
    }
    if (!payload) {
      return;
    }
    const errors = validatePayload(payload);
    setValidationErrors(errors);
    setSuccessMessage(null);
    if (errors.length) {
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/methodology/editor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Failed to save methodology: ${response.statusText}`);
      }
      const data = (await response.json()) as MethodologyEditorPayload;
      setPayload(data);
      setSuccessMessage('Methodology updated successfully.');
    } catch (saveError) {
      const message = saveError instanceof Error
        ? saveError.message
        : 'Failed to save methodology.';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <p>Loading methodology editor…</p>
      </div>
    );
  }

  if (!payload) {
    return (
      <div className={styles.container}>
        <p>{error ?? 'Methodology editor data unavailable.'}</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Methodology Editor</h1>
        <p>
          Manage stages, activities, prerequisites, exit criteria, and gate criteria for{' '}
          <span className={styles.inlineCode}>{payload.methodology_id}</span>.
        </p>
        {!canEdit && (
          <div className={`${styles.alert} ${styles.alertError}`}>
            You do not have permission to edit methodology settings.
          </div>
        )}
        {error && <div className={`${styles.alert} ${styles.alertError}`}>{error}</div>}
        {successMessage && (
          <div className={`${styles.alert} ${styles.alertSuccess}`}>{successMessage}</div>
        )}
        {validationErrors.length > 0 && (
          <div className={`${styles.alert} ${styles.alertError}`}>
            <strong>Validation issues:</strong>
            <ul>
              {validationErrors.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>Stages &amp; Activities</h2>
          <button
            type="button"
            className={styles.buttonPrimary}
            onClick={() =>
              setPayload((current) =>
                current
                  ? {
                      ...current,
                      stages: [...current.stages, createStage()],
                    }
                  : current
              )
            }
            disabled={!canEdit}
          >
            Add stage
          </button>
        </div>

        {payload.stages.map((stage, stageIndex) => (
          <div key={`${stage.id}-${stageIndex}`} className={styles.stageCard}>
            <div className={styles.stageHeader}>
              <label className={styles.field}>
                Stage ID
                <input
                  value={stage.id}
                  onChange={(event) =>
                    updateStage(stageIndex, (current) => ({
                      ...current,
                      id: event.target.value,
                    }))
                  }
                />
              </label>
              <label className={styles.field}>
                Stage name
                <input
                  value={stage.name}
                  onChange={(event) =>
                    updateStage(stageIndex, (current) => ({
                      ...current,
                      name: event.target.value,
                    }))
                  }
                />
              </label>
              <div className={styles.actionsRow}>
                <button
                  type="button"
                  onClick={() => moveStage(stageIndex, -1)}
                  disabled={!canEdit}
                >
                  Move up
                </button>
                <button
                  type="button"
                  onClick={() => moveStage(stageIndex, 1)}
                  disabled={!canEdit}
                >
                  Move down
                </button>
                <button
                  type="button"
                  className={styles.buttonGhost}
                  onClick={() =>
                    setPayload((current) => {
                      if (!current) {
                        return current;
                      }
                      const stages = current.stages.filter((_, idx) => idx !== stageIndex);
                      return { ...current, stages };
                    })
                  }
                  disabled={!canEdit}
                >
                  Remove stage
                </button>
              </div>
            </div>

            <div className={styles.listGroup}>
              <h3>Exit criteria</h3>
              {stage.exit_criteria.map((criteria, criteriaIndex) => (
                <div key={`${criteria}-${criteriaIndex}`} className={styles.listItem}>
                  <input
                    value={criteria}
                    onChange={(event) =>
                      updateStage(stageIndex, (current) => {
                        const exit_criteria = [...current.exit_criteria];
                        exit_criteria[criteriaIndex] = event.target.value;
                        return { ...current, exit_criteria };
                      })
                    }
                  />
                  <button
                    type="button"
                    onClick={() =>
                      updateStage(stageIndex, (current) => ({
                        ...current,
                        exit_criteria: current.exit_criteria.filter(
                          (_, idx) => idx !== criteriaIndex
                        ),
                      }))
                    }
                    disabled={!canEdit}
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                className={styles.buttonGhost}
                onClick={() =>
                  updateStage(stageIndex, (current) => ({
                    ...current,
                    exit_criteria: [...current.exit_criteria, ''],
                  }))
                }
                disabled={!canEdit}
              >
                Add exit criterion
              </button>
            </div>

            <div className={styles.listGroup}>
              <div className={styles.sectionHeader}>
                <h3>Activities</h3>
                <button
                  type="button"
                  className={styles.buttonGhost}
                  onClick={() =>
                    updateStage(stageIndex, (current) => ({
                      ...current,
                      activities: [...current.activities, createActivity()],
                    }))
                  }
                  disabled={!canEdit}
                >
                  Add activity
                </button>
              </div>

              {stage.activities.map((activity, activityIndex) => (
                <div key={`${activity.id}-${activityIndex}`} className={styles.activityCard}>
                  <div className={styles.actionsRow}>
                    <button
                      type="button"
                      onClick={() => moveActivity(stageIndex, activityIndex, -1)}
                      disabled={!canEdit}
                    >
                      Move up
                    </button>
                    <button
                      type="button"
                      onClick={() => moveActivity(stageIndex, activityIndex, 1)}
                      disabled={!canEdit}
                    >
                      Move down
                    </button>
                    <button
                      type="button"
                      className={styles.buttonGhost}
                      onClick={() =>
                        updateStage(stageIndex, (current) => ({
                          ...current,
                          activities: current.activities.filter(
                            (_, idx) => idx !== activityIndex
                          ),
                        }))
                      }
                      disabled={!canEdit}
                    >
                      Remove activity
                    </button>
                  </div>

                  <div className={styles.stageHeader}>
                    <label className={styles.field}>
                      Activity ID
                      <input
                        value={activity.id}
                        onChange={(event) =>
                          updateActivity(stageIndex, activityIndex, (current) => ({
                            ...current,
                            id: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <label className={styles.field}>
                      Activity name
                      <input
                        value={activity.name}
                        onChange={(event) =>
                          updateActivity(stageIndex, activityIndex, (current) => ({
                            ...current,
                            name: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <label className={styles.field}>
                      Canvas tab
                      <select
                        value={activity.recommended_canvas_tab}
                        onChange={(event) =>
                          updateActivity(stageIndex, activityIndex, (current) => ({
                            ...current,
                            recommended_canvas_tab: event.target.value,
                          }))
                        }
                        disabled={!canEdit}
                      >
                        {canvasTabs.map((tab) => (
                          <option key={tab} value={tab}>
                            {tab}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className={styles.field}>
                      Category
                      <select
                        value={activity.category}
                        onChange={(event) =>
                          updateActivity(stageIndex, activityIndex, (current) => ({
                            ...current,
                            category: event.target.value,
                          }))
                        }
                        disabled={!canEdit}
                      >
                        <option value="methodology">methodology</option>
                        <option value="monitoring">monitoring</option>
                      </select>
                    </label>
                  </div>

                  <label className={styles.field}>
                    Activity description
                    <textarea
                      value={activity.description}
                      onChange={(event) =>
                        updateActivity(stageIndex, activityIndex, (current) => ({
                          ...current,
                          description: event.target.value,
                        }))
                      }
                    />
                  </label>

                  <div className={styles.listGroup}>
                    <h4>Prerequisites</h4>
                    {activity.prerequisites.map((prereq, prereqIndex) => (
                      <div key={`${prereq}-${prereqIndex}`} className={styles.listItem}>
                        <input
                          value={prereq}
                          onChange={(event) =>
                            updateActivity(stageIndex, activityIndex, (current) => {
                              const prerequisites = [...current.prerequisites];
                              prerequisites[prereqIndex] = event.target.value;
                              return { ...current, prerequisites };
                            })
                          }
                        />
                        <button
                          type="button"
                          onClick={() =>
                            updateActivity(stageIndex, activityIndex, (current) => ({
                              ...current,
                              prerequisites: current.prerequisites.filter(
                                (_, idx) => idx !== prereqIndex
                              ),
                            }))
                          }
                          disabled={!canEdit}
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      className={styles.buttonGhost}
                      onClick={() =>
                        updateActivity(stageIndex, activityIndex, (current) => ({
                          ...current,
                          prerequisites: [...current.prerequisites, ''],
                        }))
                      }
                      disabled={!canEdit}
                    >
                      Add prerequisite
                    </button>
                    <p>
                      Current activity IDs: {activityIds.length === 0 ? 'None' : activityIds.join(', ')}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>Gate Criteria</h2>
          <button
            type="button"
            className={styles.buttonPrimary}
            onClick={() =>
              setPayload((current) =>
                current
                  ? {
                      ...current,
                      gates: [...current.gates, createGate()],
                    }
                  : current
              )
            }
            disabled={!canEdit}
          >
            Add gate
          </button>
        </div>

        {payload.gates.map((gate, gateIndex) => (
          <div key={`${gate.id}-${gateIndex}`} className={styles.stageCard}>
            <div className={styles.stageHeader}>
              <label className={styles.field}>
                Gate ID
                <input
                  value={gate.id}
                  onChange={(event) =>
                    setPayload((current) => {
                      if (!current) {
                        return current;
                      }
                      const gates = current.gates.map((entry, index) =>
                        index === gateIndex ? { ...entry, id: event.target.value } : entry
                      );
                      return { ...current, gates };
                    })
                  }
                />
              </label>
              <label className={styles.field}>
                Gate name
                <input
                  value={gate.name}
                  onChange={(event) =>
                    setPayload((current) => {
                      if (!current) {
                        return current;
                      }
                      const gates = current.gates.map((entry, index) =>
                        index === gateIndex ? { ...entry, name: event.target.value } : entry
                      );
                      return { ...current, gates };
                    })
                  }
                />
              </label>
              <label className={styles.field}>
                Stage
                <input
                  value={gate.stage}
                  onChange={(event) =>
                    setPayload((current) => {
                      if (!current) {
                        return current;
                      }
                      const gates = current.gates.map((entry, index) =>
                        index === gateIndex ? { ...entry, stage: event.target.value } : entry
                      );
                      return { ...current, gates };
                    })
                  }
                />
              </label>
              <div className={styles.actionsRow}>
                <button
                  type="button"
                  className={styles.buttonGhost}
                  onClick={() =>
                    setPayload((current) => {
                      if (!current) {
                        return current;
                      }
                      const gates = current.gates.filter((_, index) => index !== gateIndex);
                      return { ...current, gates };
                    })
                  }
                  disabled={!canEdit}
                >
                  Remove gate
                </button>
              </div>
            </div>

            <div className={styles.listGroup}>
              <div className={styles.sectionHeader}>
                <h3>Criteria</h3>
                <button
                  type="button"
                  className={styles.buttonGhost}
                  onClick={() =>
                    setPayload((current) => {
                      if (!current) {
                        return current;
                      }
                      const gates = current.gates.map((entry, index) => {
                        if (index !== gateIndex) {
                          return entry;
                        }
                        return {
                          ...entry,
                          criteria: [...entry.criteria, createGateCriteria()],
                        };
                      });
                      return { ...current, gates };
                    })
                  }
                  disabled={!canEdit}
                >
                  Add criterion
                </button>
              </div>

              {gate.criteria.map((criterion, criterionIndex) => (
                <div
                  key={`${criterion.id}-${criterionIndex}`}
                  className={styles.activityCard}
                >
                  <div className={styles.stageHeader}>
                    <label className={styles.field}>
                      Criterion ID
                      <input
                        value={criterion.id}
                        onChange={(event) =>
                          setPayload((current) => {
                            if (!current) {
                              return current;
                            }
                            const gates = current.gates.map((entry, index) => {
                              if (index !== gateIndex) {
                                return entry;
                              }
                              const criteria = entry.criteria.map((item, itemIndex) =>
                                itemIndex === criterionIndex
                                  ? { ...item, id: event.target.value }
                                  : item
                              );
                              return { ...entry, criteria };
                            });
                            return { ...current, gates };
                          })
                        }
                      />
                    </label>
                    <label className={styles.field}>
                      Description
                      <input
                        value={criterion.description}
                        onChange={(event) =>
                          setPayload((current) => {
                            if (!current) {
                              return current;
                            }
                            const gates = current.gates.map((entry, index) => {
                              if (index !== gateIndex) {
                                return entry;
                              }
                              const criteria = entry.criteria.map((item, itemIndex) =>
                                itemIndex === criterionIndex
                                  ? { ...item, description: event.target.value }
                                  : item
                              );
                              return { ...entry, criteria };
                            });
                            return { ...current, gates };
                          })
                        }
                      />
                    </label>
                  </div>

                  <label className={styles.field}>
                    Evidence
                    <textarea
                      value={criterion.evidence ?? ''}
                      onChange={(event) =>
                        setPayload((current) => {
                          if (!current) {
                            return current;
                          }
                          const gates = current.gates.map((entry, index) => {
                            if (index !== gateIndex) {
                              return entry;
                            }
                            const criteria = entry.criteria.map((item, itemIndex) =>
                              itemIndex === criterionIndex
                                ? { ...item, evidence: event.target.value }
                                : item
                            );
                            return { ...entry, criteria };
                          });
                          return { ...current, gates };
                        })
                      }
                    />
                  </label>

                  <label className={styles.field}>
                    Check
                    <textarea
                      value={criterion.check ?? ''}
                      onChange={(event) =>
                        setPayload((current) => {
                          if (!current) {
                            return current;
                          }
                          const gates = current.gates.map((entry, index) => {
                            if (index !== gateIndex) {
                              return entry;
                            }
                            const criteria = entry.criteria.map((item, itemIndex) =>
                              itemIndex === criterionIndex
                                ? { ...item, check: event.target.value }
                                : item
                            );
                            return { ...entry, criteria };
                          });
                          return { ...current, gates };
                        })
                      }
                    />
                  </label>

                  <button
                    type="button"
                    className={styles.buttonGhost}
                    onClick={() =>
                      setPayload((current) => {
                        if (!current) {
                          return current;
                        }
                        const gates = current.gates.map((entry, index) => {
                          if (index !== gateIndex) {
                            return entry;
                          }
                          const criteria = entry.criteria.filter(
                            (_, idx) => idx !== criterionIndex
                          );
                          return { ...entry, criteria };
                        });
                        return { ...current, gates };
                      })
                    }
                    disabled={!canEdit}
                  >
                    Remove criterion
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      <div className={styles.actionsRow}>
        <button
          type="button"
          className={styles.buttonPrimary}
          onClick={handleSave}
          disabled={saving || !canEdit}
        >
          {saving ? 'Saving…' : 'Save methodology'}
        </button>
      </div>
    </div>
  );
}
