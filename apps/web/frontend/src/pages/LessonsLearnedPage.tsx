import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMethodologyStore } from '@/store/methodology';
import { useRequestState } from '@/hooks/useRequestState';
import { getErrorMessage } from '@/services/apiClient';
import {
  createLesson,
  deleteLesson,
  fetchLessonRecommendations,
  fetchLessons,
  updateLesson,
  type LessonRecord,
} from '@/services/knowledgeApi';
import styles from './LessonsLearnedPage.module.css';

const parseList = (value: string): string[] =>
  value
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);

export function LessonsLearnedPage() {
  const { projectMethodology } = useMethodologyStore();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('project') || projectMethodology.projectId;
  const stages = projectMethodology.methodology.stages;

  const [query, setQuery] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [topicFilter, setTopicFilter] = useState('');
  const [lessons, setLessons] = useState<LessonRecord[]>([]);
  const [recommendations, setRecommendations] = useState<LessonRecord[]>([]);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [formTitle, setFormTitle] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formTags, setFormTags] = useState('');
  const [formTopics, setFormTopics] = useState('');
  const [formStageId, setFormStageId] = useState<string | null>(null);
  const [editingLessonId, setEditingLessonId] = useState<string | null>(null);

  const lessonsRequest = useRequestState();
  const recommendationsRequest = useRequestState();
  const { start: startLessons, succeed: succeedLessons, fail: failLessons } = lessonsRequest;
  const { start: startRecommendations, succeed: succeedRecommendations, fail: failRecommendations, reset: resetRecommendations } = recommendationsRequest;

  const loadLessons = useCallback(async () => {
    startLessons();
    try {
      const results = await fetchLessons(
        projectId,
        query.trim() || undefined,
        parseList(tagFilter),
        parseList(topicFilter)
      );
      setLessons(results);
      succeedLessons();
    } catch (error) {
      setLessons([]);
      failLessons(getErrorMessage(error, 'Failed to load lessons.'));
    }
  }, [failLessons, projectId, query, startLessons, succeedLessons, tagFilter, topicFilter]);

  const loadRecommendations = useCallback(async () => {
    const tags = parseList(tagFilter);
    const topics = parseList(topicFilter);
    if (!tags.length && !topics.length) {
      resetRecommendations();
      setRecommendations([]);
      return;
    }

    startRecommendations();
    try {
      const results = await fetchLessonRecommendations({
        projectId,
        tags,
        topics,
        limit: 5,
      });
      setRecommendations(results);
      succeedRecommendations();
    } catch (error) {
      setRecommendations([]);
      failRecommendations(
        getErrorMessage(error, 'Failed to load lesson recommendations.')
      );
    }
  }, [failRecommendations, projectId, resetRecommendations, startRecommendations, succeedRecommendations, tagFilter, topicFilter]);

  useEffect(() => {
    const params = new URLSearchParams(searchParams);
    const stageId = params.get('stageId');
    const stageName = params.get('stageName');
    if (stageId) {
      setFormStageId(stageId);
      if (stageName && !formTitle) {
        setFormTitle(`Lessons learned - ${stageName}`);
      }
    }
  }, [formTitle, searchParams]);

  useEffect(() => {
    loadLessons();
    loadRecommendations();
  }, [loadLessons, loadRecommendations]);

  const selectedStage = useMemo(
    () => stages.find((stage) => stage.id === formStageId),
    [formStageId, stages]
  );

  const resetForm = () => {
    setFormTitle('');
    setFormDescription('');
    setFormTags('');
    setFormTopics('');
    setFormStageId(null);
    setEditingLessonId(null);
  };

  const handleSubmit = async () => {
    if (!formTitle.trim() || !formDescription.trim()) return;

    const payload = {
      projectId,
      stageId: formStageId,
      stageName: selectedStage?.name ?? null,
      title: formTitle.trim(),
      description: formDescription.trim(),
      tags: parseList(formTags),
      topics: parseList(formTopics),
    };

    setIsSaving(true);
    setFeedbackMessage(null);
    try {
      if (editingLessonId) {
        await updateLesson(editingLessonId, payload);
        setFeedbackMessage('Lesson updated successfully.');
      } else {
        await createLesson(payload);
        setFeedbackMessage('Lesson saved successfully.');
      }
      resetForm();
      await loadLessons();
      await loadRecommendations();
    } catch (error) {
      setFeedbackMessage(getErrorMessage(error, 'Failed to save lesson.'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleEdit = (lesson: LessonRecord) => {
    setEditingLessonId(lesson.lessonId);
    setFormTitle(lesson.title);
    setFormDescription(lesson.description);
    setFormTags(lesson.tags.join(', '));
    setFormTopics(lesson.topics.join(', '));
    setFormStageId(lesson.stageId ?? null);
  };

  const handleDelete = async (lessonId: string) => {
    setFeedbackMessage(null);
    try {
      await deleteLesson(lessonId);
      setFeedbackMessage('Lesson deleted.');
      await loadLessons();
      await loadRecommendations();
    } catch (error) {
      setFeedbackMessage(getErrorMessage(error, 'Failed to delete lesson.'));
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Lessons Learned</h1>
          <p>
            Capture and reuse project learnings for <strong>{projectMethodology.projectName}</strong>.
          </p>
        </div>
        <div className={styles.filters}>
          <input
            className={styles.filterInput}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search lessons"
          />
          <input
            className={styles.filterInput}
            value={tagFilter}
            onChange={(event) => setTagFilter(event.target.value)}
            placeholder="Tags (comma separated)"
          />
          <input
            className={styles.filterInput}
            value={topicFilter}
            onChange={(event) => setTopicFilter(event.target.value)}
            placeholder="Topics (comma separated)"
          />
          <button className={styles.primaryButton} onClick={loadLessons}>
            Filter
          </button>
        </div>
      </header>

      {feedbackMessage && <div className={styles.feedbackBanner}>{feedbackMessage}</div>}

      <div className={styles.layout}>
        <section className={styles.formSection}>
          <h2>{editingLessonId ? 'Edit Lesson' : 'Capture Lesson'}</h2>
          <div className={styles.formGroup}>
            <label>
              Stage
              <select value={formStageId ?? ''} onChange={(event) => setFormStageId(event.target.value || null)}>
                <option value="">Select stage</option>
                {stages.map((stage) => (
                  <option key={stage.id} value={stage.id}>
                    {stage.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Title
              <input value={formTitle} onChange={(event) => setFormTitle(event.target.value)} placeholder="Lesson title" />
            </label>
            <label>
              Description
              <textarea
                value={formDescription}
                onChange={(event) => setFormDescription(event.target.value)}
                placeholder="Describe what happened and the recommendation"
                rows={4}
              />
            </label>
            <label>
              Tags
              <input value={formTags} onChange={(event) => setFormTags(event.target.value)} placeholder="e.g. scheduling, vendor" />
            </label>
            <label>
              Topics
              <input value={formTopics} onChange={(event) => setFormTopics(event.target.value)} placeholder="e.g. scope, communications" />
            </label>
          </div>
          <div className={styles.formActions}>
            <button className={styles.primaryButton} onClick={handleSubmit} disabled={isSaving}>
              {editingLessonId ? 'Update Lesson' : 'Save Lesson'}
            </button>
            <button className={styles.secondaryButton} onClick={resetForm}>
              Clear
            </button>
          </div>
        </section>

        <section className={styles.listSection}>
          <div className={styles.sectionHeader}>
            <h2>Lesson Library</h2>
            <button className={styles.secondaryButton} onClick={loadLessons}>
              Refresh
            </button>
          </div>
          {lessonsRequest.isLoading && <div className={styles.emptyState}>Loading lessons...</div>}
          {lessonsRequest.isError && (
            <div className={styles.errorState}>
              <span>{lessonsRequest.error}</span>
              <button onClick={loadLessons}>Retry</button>
            </div>
          )}
          {!lessonsRequest.isLoading && !lessonsRequest.isError && lessons.length === 0 && (
            <div className={styles.emptyState}>No lessons captured yet.</div>
          )}
          {!lessonsRequest.isLoading && !lessonsRequest.isError && lessons.length > 0 && (
            <ul className={styles.lessonList}>
              {lessons.map((lesson) => (
                <li key={lesson.lessonId} className={styles.lessonCard}>
                  <div className={styles.lessonHeader}>
                    <div>
                      <h3>{lesson.title}</h3>
                      <p className={styles.lessonMeta}>
                        {lesson.stageName ?? 'General'} · {new Date(lesson.updatedAt).toLocaleDateString()}
                      </p>
                    </div>
                    <div className={styles.lessonActions}>
                      <button className={styles.secondaryButton} onClick={() => handleEdit(lesson)}>
                        Edit
                      </button>
                      <button className={styles.dangerButton} onClick={() => handleDelete(lesson.lessonId)}>
                        Delete
                      </button>
                    </div>
                  </div>
                  <p className={styles.lessonDescription}>{lesson.description}</p>
                  <div className={styles.chipRow}>
                    {lesson.tags.map((tag) => (
                      <span key={`tag-${lesson.lessonId}-${tag}`} className={styles.chip}>
                        #{tag}
                      </span>
                    ))}
                    {lesson.topics.map((topic) => (
                      <span key={`topic-${lesson.lessonId}-${topic}`} className={styles.chipAlt}>
                        {topic}
                      </span>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className={styles.recommendationSection}>
          <h2>Recommended Lessons</h2>
          {recommendationsRequest.isLoading && <div className={styles.emptyState}>Loading recommendations...</div>}
          {recommendationsRequest.isError && (
            <div className={styles.errorState}>
              <span>{recommendationsRequest.error}</span>
              <button onClick={loadRecommendations}>Retry</button>
            </div>
          )}
          {recommendationsRequest.status === 'idle' && (
            <div className={styles.emptyState}>Add tags/topics to see recommended lessons.</div>
          )}
          {!recommendationsRequest.isLoading && !recommendationsRequest.isError && recommendationsRequest.status !== 'idle' && recommendations.length === 0 && (
            <div className={styles.emptyState}>No recommendations matched your current filters.</div>
          )}
          {!recommendationsRequest.isLoading && !recommendationsRequest.isError && recommendations.length > 0 && (
            <ul className={styles.recommendationList}>
              {recommendations.map((lesson) => (
                <li key={`rec-${lesson.lessonId}`} className={styles.recommendationCard}>
                  <h3>{lesson.title}</h3>
                  <p className={styles.lessonMeta}>
                    {lesson.stageName ?? 'General'} · {lesson.tags.concat(lesson.topics).slice(0, 4).join(', ')}
                  </p>
                  <p className={styles.lessonDescription}>{lesson.description}</p>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  );
}
