/**
 * WizardContainer — multi-step project onboarding wizard (T034).
 * FR-043: auto-save on each step via PATCH /api/v1/wizard/sessions/{id}/step.
 * FR-043: resume prompt shown if an active session exists on mount.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../services/api';
import { WizardStep } from './WizardStep';
import type { WizardQuestion } from './WizardStep';

// Wizard questions loaded from backend
async function fetchWizardQuestions(): Promise<WizardQuestion[]> {
  const res = await apiClient.get<WizardQuestion[]>('/api/v1/wizard/questions');
  return res.data;
}

interface WizardSessionState {
  id: string;
  stepIndex: number;
  answersJson: Record<string, unknown>;
  projectContextJson: Record<string, unknown>;
  isComplete: boolean;
}

async function fetchActiveSession(): Promise<WizardSessionState | null> {
  const res = await apiClient.get<WizardSessionState | null>('/api/v1/wizard/sessions/active');
  return res.data;
}

async function createSession(): Promise<WizardSessionState> {
  const res = await apiClient.post<WizardSessionState>('/api/v1/wizard/sessions');
  return res.data;
}

async function patchStep(sessionId: string, stepIndex: number, answersJson: Record<string, unknown>): Promise<void> {
  await apiClient.patch(`/api/v1/wizard/sessions/${sessionId}/step`, { step_index: stepIndex, answers_json: answersJson });
}

async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/api/v1/wizard/sessions/${sessionId}`);
}

export function WizardContainer() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [questions, setQuestions] = useState<WizardQuestion[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [resumePrompt, setResumePrompt] = useState<WizardSessionState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load questions + check for existing session on mount
  useEffect(() => {
    let cancelled = false;
    fetchWizardQuestions()
      .then((qs) => { if (!cancelled) setQuestions(qs); })
      .catch(() => { /* questions will remain empty */ });

    fetchActiveSession()
      .then((session) => {
        if (!cancelled && session && !session.isComplete) {
          setResumePrompt(session);
        }
      })
      .catch(() => { /* no active session */ });

    return () => { cancelled = true; };
  }, []);

  const startNew = useCallback(async () => {
    if (resumePrompt) {
      await deleteSession(resumePrompt.id).catch(() => undefined);
      setResumePrompt(null);
    }
    const session = await createSession();
    setSessionId(session.id);
    setCurrentStep(0);
    setAnswers({});
  }, [resumePrompt]);

  const resumeExisting = useCallback(() => {
    if (!resumePrompt) return;
    setSessionId(resumePrompt.id);
    setCurrentStep(resumePrompt.stepIndex);
    setAnswers(resumePrompt.answersJson);
    setResumePrompt(null);
  }, [resumePrompt]);

  // Auto-save on every answer change (FR-043)
  const handleChange = useCallback(async (key: string, value: unknown) => {
    const updated = { ...answers, [key]: value };
    setAnswers(updated);
    if (!sessionId) return;
    setSaving(true);
    try {
      await patchStep(sessionId, currentStep, updated);
    } finally {
      setSaving(false);
    }
  }, [answers, sessionId, currentStep]);

  const canAdvance = useCallback(() => {
    const q = visibleQuestions[currentStep];
    if (!q) return true;
    if (!q.required) return true;
    const v = answers[q.key];
    if (v === undefined || v === null || v === '') return false;
    if (Array.isArray(v) && v.length === 0) return false;
    return true;
  }, [answers, currentStep]);  // visibleQuestions computed below

  // Filter out depends_on questions when their condition is not met
  const visibleQuestions = questions.filter((q) => {
    if (!q.depends_on) return true;
    const dep = answers[q.depends_on.key];
    if (!dep) return false;
    if (Array.isArray(dep)) return !dep.includes(q.depends_on.not_value);
    return dep !== q.depends_on.not_value;
  });

  const totalSteps = visibleQuestions.length;

  const handleNext = async () => {
    if (!canAdvance()) return;
    if (!sessionId) {
      const session = await createSession();
      setSessionId(session.id);
    }
    if (currentStep < totalSteps - 1) {
      setCurrentStep((s) => s + 1);
    } else {
      await handleSubmit();
    }
  };

  const handleBack = () => setCurrentStep((s) => Math.max(0, s - 1));

  const handleSubmit = async () => {
    if (!sessionId) return;
    setSubmitting(true);
    setError(null);
    try {
      // Create project from wizard answers
      const res = await apiClient.post<{ id: string }>('/api/v1/wizard/complete', {
        session_id: sessionId,
        answers_json: answers,
      });
      navigate(`/projects/${res.data.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('wizard.error.submit_failed'));
    } finally {
      setSubmitting(false);
    }
  };

  // ── Resume Prompt ────────────────────────────────────────────────────────
  if (resumePrompt && !sessionId) {
    return (
      <div className="wizard-resume">
        <h2>{t('wizard.resume.title')}</h2>
        <p>{t('wizard.resume.description')}</p>
        <div className="wizard-resume__actions">
          <button className="btn btn--primary" onClick={resumeExisting}>{t('wizard.resume.continue')}</button>
          <button className="btn btn--secondary" onClick={startNew}>{t('wizard.resume.start_over')}</button>
        </div>
      </div>
    );
  }

  // ── Initial state before session created ─────────────────────────────────
  if (!sessionId) {
    return (
      <div className="wizard-start">
        <h2>{t('wizard.start.title')}</h2>
        <p>{t('wizard.start.description')}</p>
        <button className="btn btn--primary" onClick={startNew}>{t('wizard.start.begin')}</button>
      </div>
    );
  }

  const currentQuestion = visibleQuestions[currentStep];

  return (
    <div className="wizard">
      {/* Progress bar */}
      <div className="wizard__progress">
        <div
          className="wizard__progress-bar"
          style={{ width: `${((currentStep + 1) / totalSteps) * 100}%` }}
          role="progressbar"
          aria-valuenow={currentStep + 1}
          aria-valuemin={1}
          aria-valuemax={totalSteps}
        />
      </div>
      <div className="wizard__step-counter">
        {t('wizard.step_of', { current: currentStep + 1, total: totalSteps })}
      </div>

      {/* Current step */}
      {currentQuestion && (
        <WizardStep
          question={currentQuestion}
          value={(answers[currentQuestion.key] as string | string[] | number | null) ?? null}
          onChange={handleChange}
        />
      )}

      {saving && <span className="wizard__saving">{t('wizard.auto_saving')}</span>}
      {error && <div className="wizard__error" role="alert">{error}</div>}

      {/* Navigation */}
      <div className="wizard__nav">
        {currentStep > 0 && (
          <button className="btn btn--secondary" onClick={handleBack}>{t('wizard.back')}</button>
        )}
        <button
          className="btn btn--primary"
          onClick={handleNext}
          disabled={!canAdvance() || submitting}
        >
          {currentStep === totalSteps - 1 ? t('wizard.finish') : t('wizard.next')}
        </button>
      </div>
    </div>
  );
}
