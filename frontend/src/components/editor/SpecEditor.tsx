/**
 * SpecEditor — Markdown editor with AI consultant integration (T045).
 * FR-007: AI consultant trigger button always visible.
 * FR-033b: Shows AI_OFFLINE banner when LLM unavailable.
 * FR-015b: 409 conflict → ConflictMergeModal.
 */
import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../services/api';
import { AISidePanel } from './AISidePanel';
import type { Suggestion } from './AISidePanel';
import { ConflictMergeModal } from './ConflictMergeModal';

interface SpecEditorProps {
  documentId: string;
  initialContent: string;
  currentVersion: number;
  specItemId?: string;
  onSaved?: (newVersion: number) => void;
}

export function SpecEditor({ documentId, initialContent, currentVersion, specItemId, onSaved }: SpecEditorProps) {
  const { t } = useTranslation();
  const [content, setContent] = useState(initialContent);
  const [version, setVersion] = useState(currentVersion);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [aiOffline, setAiOffline] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState<{ yourVersion: number; dbVersion: number } | null>(null);

  // Invoke AI consultant (FR-007)
  const handleConsult = useCallback(async () => {
    setLoadingAI(true);
    try {
      const res = await apiClient.post<Suggestion[]>('/api/v1/ai/consult', {
        document_id: documentId,
        spec_item_id: specItemId ?? null,
      });
      const data = res.data;
      setSuggestions(data);
      setAiOffline(data.length > 0 && data[0].ai_offline_mode);
    } finally {
      setLoadingAI(false);
    }
  }, [documentId, specItemId]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const res = await apiClient.patch<{ current_version: number }>(`/api/v1/documents/${documentId}`, {
        content_markdown: content,
        current_version: version,
      });
      const newVer = res.data.current_version;
      setVersion(newVer);
      onSaved?.(newVer);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number; data?: { detail?: { your_version?: number; db_version?: number } } } })?.response?.status;
      if (status === 409) {
        const detail = (err as { response?: { data?: { detail?: { your_version?: number; db_version?: number } } } })?.response?.data?.detail;
        setConflict({ yourVersion: detail?.your_version ?? version, dbVersion: detail?.db_version ?? version });
      } else {
        throw err;
      }
    } finally {
      setSaving(false);
    }
  }, [content, documentId, version, onSaved]);

  const handleAccepted = (suggestionId: string, acceptedContent: string) => {
    setContent((prev) => `${prev}\n\n${acceptedContent}`);
    setSuggestions((prev) => prev.filter((s) => s.id !== suggestionId));
  };

  const handleRejected = (suggestionId: string) => {
    setSuggestions((prev) => prev.filter((s) => s.id !== suggestionId));
  };

  const handleConflictResolve = async (resolvedContent: string) => {
    // After manual resolution fetch latest version and save
    const res = await apiClient.get<{ current_version: number }>(`/api/v1/documents/${documentId}`);
    const latestVersion = res.data.current_version;
    setVersion(latestVersion);
    setContent(resolvedContent);
    setConflict(null);
    onSaved?.(latestVersion);
  };

  return (
    <div className="spec-editor">
      <div className="spec-editor__toolbar">
        <button
          className="btn btn--primary btn--sm"
          onClick={handleConsult}
          disabled={loadingAI}
        >
          {loadingAI ? t('editor.ai_loading') : t('editor.ai_consult')}
        </button>
        <button className="btn btn--secondary btn--sm" onClick={handleSave} disabled={saving}>
          {saving ? t('common.saving') : t('editor.save')}
        </button>
      </div>

      {aiOffline && (
        <div className="spec-editor__offline-banner" role="alert">
          ⚠️ {t('editor.ai_offline_banner')}
        </div>
      )}

      <div className="spec-editor__body">
        <textarea
          className="spec-editor__textarea"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          spellCheck={false}
          aria-label={t('editor.content_label')}
        />
        {suggestions.length > 0 && (
          <AISidePanel
            suggestions={suggestions}
            aiOfflineMode={aiOffline}
            onAccepted={handleAccepted}
            onRejected={handleRejected}
          />
        )}
      </div>

      {conflict && (
        <ConflictMergeModal
          yourContent={content}
          yourVersion={conflict.yourVersion}
          dbVersion={conflict.dbVersion}
          documentId={documentId}
          onResolved={handleConflictResolve}
          onCancel={() => setConflict(null)}
        />
      )}
    </div>
  );
}
