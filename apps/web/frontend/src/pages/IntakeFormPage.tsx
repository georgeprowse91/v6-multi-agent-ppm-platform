import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store';
import styles from './IntakeFormPage.module.css';

const API_BASE = '/v1';

const steps = [
  { id: 'sponsor', label: 'Sponsor details' },
  { id: 'business', label: 'Business case' },
  { id: 'success', label: 'Success criteria' },
  { id: 'attachments', label: 'Attachments' },
];

interface IntakeFormState {
  sponsorName: string;
  sponsorEmail: string;
  sponsorDepartment: string;
  sponsorTitle: string;
  reviewers: string;
  businessSummary: string;
  businessJustification: string;
  expectedBenefits: string;
  estimatedBudget: string;
  successMetrics: string;
  targetDate: string;
  riskNotes: string;
  attachmentSummary: string;
  attachmentLinks: string;
}

const initialFormState: IntakeFormState = {
  sponsorName: '',
  sponsorEmail: '',
  sponsorDepartment: '',
  sponsorTitle: '',
  reviewers: '',
  businessSummary: '',
  businessJustification: '',
  expectedBenefits: '',
  estimatedBudget: '',
  successMetrics: '',
  targetDate: '',
  riskNotes: '',
  attachmentSummary: '',
  attachmentLinks: '',
};

export function IntakeFormPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { featureFlags } = useAppStore();
  const [stepIndex, setStepIndex] = useState(0);
  const [formState, setFormState] = useState<IntakeFormState>(initialFormState);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadClassification, setUploadClassification] = useState('internal');
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);

  useEffect(() => {
    setStepIndex(0);
    setFormState(initialFormState);
    setErrors({});
    setSubmitting(false);
    setSubmitError(null);
    setUploadFile(null);
    setUploadClassification('internal');
    setExtracting(false);
    setExtractError(null);
  }, [location.key, location.state]);

  const currentStep = steps[stepIndex];
  const multimodalEnabled = featureFlags.multimodal_intake === true;

  const reviewersList = useMemo(
    () =>
      formState.reviewers
        .split(',')
        .map((reviewer) => reviewer.trim())
        .filter(Boolean),
    [formState.reviewers]
  );

  const updateField = (field: keyof IntakeFormState, value: string) => {
    setFormState((prev) => ({ ...prev, [field]: value }));
  };

  const applyExtraction = (payload: {
    demand?: Record<string, string>;
    project?: Record<string, string>;
    document_id?: string | null;
  }) => {
    setFormState((prev) => {
      const demand = payload.demand ?? {};
      const project = payload.project ?? {};
      return {
        ...prev,
        sponsorName:
          prev.sponsorName || demand.requester || project.owner || prev.sponsorName,
        sponsorDepartment:
          prev.sponsorDepartment || demand.business_unit || prev.sponsorDepartment,
        businessSummary:
          prev.businessSummary || demand.description || project.name || prev.businessSummary,
        businessJustification:
          prev.businessJustification ||
          demand.business_objective ||
          prev.businessJustification,
        targetDate: prev.targetDate || project.end_date || prev.targetDate,
        attachmentSummary:
          prev.attachmentSummary ||
          (payload.document_id ? `Extracted from document ${payload.document_id}` : '') ||
          prev.attachmentSummary,
      };
    });
  };

  const handleExtract = async () => {
    if (!uploadFile) {
      setExtractError('Select a document to extract fields.');
      return;
    }
    setExtracting(true);
    setExtractError(null);
    try {
      const uploadForm = new FormData();
      uploadForm.append('file', uploadFile);
      uploadForm.append('classification', uploadClassification);
      const uploadResponse = await fetch(`${API_BASE}/api/intake/uploads`, {
        method: 'POST',
        body: uploadForm,
      });
      if (!uploadResponse.ok) {
        throw new Error('Unable to upload the intake document.');
      }
      const uploadPayload = await uploadResponse.json();
      const extractForm = new FormData();
      extractForm.append('file', uploadFile);
      if (uploadPayload.document_id) {
        extractForm.append('document_id', uploadPayload.document_id);
      }
      extractForm.append('target', 'both');
      const extractResponse = await fetch(`${API_BASE}/api/intake/extract`, {
        method: 'POST',
        body: extractForm,
      });
      if (!extractResponse.ok) {
        throw new Error('Unable to extract fields from the document.');
      }
      const extractPayload = await extractResponse.json();
      applyExtraction(extractPayload);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Extraction failed to complete.';
      setExtractError(message);
    } finally {
      setExtracting(false);
    }
  };

  const validateStep = (index: number) => {
    const nextErrors: Record<string, string> = {};
    if (index === 0) {
      if (!formState.sponsorName.trim()) {
        nextErrors.sponsorName = 'Sponsor name is required.';
      }
      if (!formState.sponsorEmail.trim()) {
        nextErrors.sponsorEmail = 'Sponsor email is required.';
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formState.sponsorEmail)) {
        nextErrors.sponsorEmail = 'Enter a valid email address.';
      }
      if (!formState.sponsorDepartment.trim()) {
        nextErrors.sponsorDepartment = 'Department is required.';
      }
    }
    if (index === 1) {
      if (!formState.businessSummary.trim()) {
        nextErrors.businessSummary = 'Provide a concise business summary.';
      }
      if (!formState.businessJustification.trim()) {
        nextErrors.businessJustification = 'Justification is required.';
      }
      if (!formState.expectedBenefits.trim()) {
        nextErrors.expectedBenefits = 'Expected benefits are required.';
      }
    }
    if (index === 2) {
      if (!formState.successMetrics.trim()) {
        nextErrors.successMetrics = 'Define success metrics.';
      }
    }
    if (index === 3) {
      if (!formState.attachmentSummary.trim()) {
        nextErrors.attachmentSummary = 'Summarize the supporting materials.';
      }
    }
    return nextErrors;
  };

  const handleNext = () => {
    const nextErrors = validateStep(stepIndex);
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      return;
    }
    setErrors({});
    setStepIndex((prev) => Math.min(prev + 1, steps.length - 1));
  };

  const handleBack = () => {
    setErrors({});
    setStepIndex((prev) => Math.max(prev - 1, 0));
  };

  const handleSubmit = async () => {
    const nextErrors = validateStep(stepIndex);
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const response = await fetch(`${API_BASE}/api/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sponsor: {
            name: formState.sponsorName.trim(),
            email: formState.sponsorEmail.trim(),
            department: formState.sponsorDepartment.trim(),
            title: formState.sponsorTitle.trim() || undefined,
          },
          business_case: {
            summary: formState.businessSummary.trim(),
            justification: formState.businessJustification.trim(),
            expected_benefits: formState.expectedBenefits.trim(),
            estimated_budget: formState.estimatedBudget.trim() || undefined,
          },
          success_criteria: {
            metrics: formState.successMetrics.trim(),
            target_date: formState.targetDate.trim() || undefined,
            risks: formState.riskNotes.trim() || undefined,
          },
          attachments: {
            summary: formState.attachmentSummary.trim(),
            links: formState.attachmentLinks
              .split(',')
              .map((link) => link.trim())
              .filter(Boolean),
          },
          reviewers: reviewersList,
        }),
      });
      if (!response.ok) {
        throw new Error('Unable to submit the intake request.');
      }
      const data = await response.json();
      navigate(`/intake/status/${data.request_id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Submission failed.';
      setSubmitError(message);
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Portfolio intake request</h1>
          <p>
            Capture the sponsor details, business case, and success criteria so reviewers
            can evaluate the portfolio request quickly.
          </p>
        </div>
        <div className={styles.stepIndicator}>
          Step {stepIndex + 1} of {steps.length}
        </div>
      </header>

      <div className={styles.content}>
        <aside className={styles.stepList}>
          <h2>Form steps</h2>
          <ol>
            {steps.map((step, index) => (
              <li
                key={step.id}
                className={index === stepIndex ? styles.activeStep : undefined}
              >
                <span>{step.label}</span>
              </li>
            ))}
          </ol>
        </aside>

        <section className={styles.formSection}>
          <h2>{currentStep.label}</h2>

          {multimodalEnabled && currentStep.id === 'attachments' && (
            <section className={styles.intakeAssist}>
              <div className={styles.intakeAssistHeader}>
                <div>
                  <h3>Prefill from a supporting document</h3>
                  <p>
                    Upload a PDF, Word doc, or notes to extract demand and project fields
                    into this intake form.
                  </p>
                </div>
                <span className={styles.intakeAssistBadge}>Multimodal intake</span>
              </div>
              <div className={styles.intakeAssistGrid}>
                <label className={styles.field}>
                  Document file
                  <input
                    type="file"
                    onChange={(event) =>
                      setUploadFile(event.target.files ? event.target.files[0] : null)
                    }
                  />
                </label>
                <label className={styles.field}>
                  Classification
                  <select
                    value={uploadClassification}
                    onChange={(event) => setUploadClassification(event.target.value)}
                  >
                    <option value="public">Public</option>
                    <option value="internal">Internal</option>
                    <option value="confidential">Confidential</option>
                    <option value="restricted">Restricted</option>
                  </select>
                </label>
              </div>
              <div className={styles.intakeAssistActions}>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={handleExtract}
                  disabled={extracting || !uploadFile}
                >
                  {extracting ? 'Extracting…' : 'Extract fields'}
                </button>
                {extractError && (
                  <span className={styles.intakeAssistError}>{extractError}</span>
                )}
              </div>
            </section>
          )}

          {currentStep.id === 'sponsor' && (
            <div className={styles.formGrid}>
              <label className={styles.field}>
                Sponsor name
                <input
                  type="text"
                  value={formState.sponsorName}
                  onChange={(event) => updateField('sponsorName', event.target.value)}
                />
                {errors.sponsorName && <span className={styles.error}>{errors.sponsorName}</span>}
              </label>
              <label className={styles.field}>
                Sponsor email
                <input
                  type="email"
                  value={formState.sponsorEmail}
                  onChange={(event) => updateField('sponsorEmail', event.target.value)}
                />
                {errors.sponsorEmail && (
                  <span className={styles.error}>{errors.sponsorEmail}</span>
                )}
              </label>
              <label className={styles.field}>
                Department
                <input
                  type="text"
                  value={formState.sponsorDepartment}
                  onChange={(event) =>
                    updateField('sponsorDepartment', event.target.value)
                  }
                />
                {errors.sponsorDepartment && (
                  <span className={styles.error}>{errors.sponsorDepartment}</span>
                )}
              </label>
              <label className={styles.field}>
                Title (optional)
                <input
                  type="text"
                  value={formState.sponsorTitle}
                  onChange={(event) => updateField('sponsorTitle', event.target.value)}
                />
              </label>
              <label className={styles.fieldFull}>
                Designated reviewers (comma separated)
                <input
                  type="text"
                  value={formState.reviewers}
                  onChange={(event) => updateField('reviewers', event.target.value)}
                  placeholder="e.g., d.hudson, pm-reviewer"
                />
              </label>
            </div>
          )}

          {currentStep.id === 'business' && (
            <div className={styles.formGrid}>
              <label className={styles.fieldFull}>
                Business case summary
                <textarea
                  value={formState.businessSummary}
                  onChange={(event) => updateField('businessSummary', event.target.value)}
                  rows={3}
                />
                {errors.businessSummary && (
                  <span className={styles.error}>{errors.businessSummary}</span>
                )}
              </label>
              <label className={styles.fieldFull}>
                Strategic justification
                <textarea
                  value={formState.businessJustification}
                  onChange={(event) =>
                    updateField('businessJustification', event.target.value)
                  }
                  rows={3}
                />
                {errors.businessJustification && (
                  <span className={styles.error}>{errors.businessJustification}</span>
                )}
              </label>
              <label className={styles.fieldFull}>
                Expected benefits
                <textarea
                  value={formState.expectedBenefits}
                  onChange={(event) => updateField('expectedBenefits', event.target.value)}
                  rows={3}
                />
                {errors.expectedBenefits && (
                  <span className={styles.error}>{errors.expectedBenefits}</span>
                )}
              </label>
              <label className={styles.field}>
                Estimated budget (optional)
                <input
                  type="text"
                  value={formState.estimatedBudget}
                  onChange={(event) => updateField('estimatedBudget', event.target.value)}
                />
              </label>
            </div>
          )}

          {currentStep.id === 'success' && (
            <div className={styles.formGrid}>
              <label className={styles.fieldFull}>
                Success metrics
                <textarea
                  value={formState.successMetrics}
                  onChange={(event) => updateField('successMetrics', event.target.value)}
                  rows={3}
                />
                {errors.successMetrics && (
                  <span className={styles.error}>{errors.successMetrics}</span>
                )}
              </label>
              <label className={styles.field}>
                Target decision date (optional)
                <input
                  type="text"
                  value={formState.targetDate}
                  onChange={(event) => updateField('targetDate', event.target.value)}
                  placeholder="e.g., 2024-11-30"
                />
              </label>
              <label className={styles.fieldFull}>
                Risks or dependencies (optional)
                <textarea
                  value={formState.riskNotes}
                  onChange={(event) => updateField('riskNotes', event.target.value)}
                  rows={3}
                />
              </label>
            </div>
          )}

          {currentStep.id === 'attachments' && (
            <div className={styles.formGrid}>
              <label className={styles.fieldFull}>
                Attachment summary
                <textarea
                  value={formState.attachmentSummary}
                  onChange={(event) => updateField('attachmentSummary', event.target.value)}
                  rows={3}
                />
                {errors.attachmentSummary && (
                  <span className={styles.error}>{errors.attachmentSummary}</span>
                )}
              </label>
              <label className={styles.fieldFull}>
                Supporting links (optional)
                <input
                  type="text"
                  value={formState.attachmentLinks}
                  onChange={(event) => updateField('attachmentLinks', event.target.value)}
                  placeholder="Comma-separated URLs or document locations"
                />
              </label>
            </div>
          )}

          {submitError && <div className={styles.submitError}>{submitError}</div>}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={handleBack}
              disabled={stepIndex === 0}
            >
              Back
            </button>
            {stepIndex < steps.length - 1 && (
              <button type="button" className={styles.primaryButton} onClick={handleNext}>
                Continue
              </button>
            )}
            {stepIndex === steps.length - 1 && (
              <button
                type="button"
                className={styles.primaryButton}
                onClick={handleSubmit}
                disabled={submitting}
              >
                {submitting ? 'Submitting...' : 'Submit for approval'}
              </button>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default IntakeFormPage;
