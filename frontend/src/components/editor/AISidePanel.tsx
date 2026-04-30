/**
 * AISidePanel — list of AI suggestion cards (T046).
 * FR-007: Accept/Reject UI. No auto-insertion. Accepted suggestions appear in editor.
 */
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../services/api';

export interface Suggestion {
  id: string;
  suggested_content: string;
  clause_reference: string | null;
  severity: 'error' | 'warning' | 'info';
  type: string;
  gap: string | null;
  ai_offline_mode: boolean;
}

interface AISidePanelProps {
  suggestions: Suggestion[];
  aiOfflineMode: boolean;
  onAccepted: (suggestionId: string, content: string) => void;
  onRejected: (suggestionId: string) => void;
}

export function AISidePanel({ suggestions, aiOfflineMode, onAccepted, onRejected }: AISidePanelProps) {
  const { t } = useTranslation();

  const accept = async (s: Suggestion) => {
    await apiClient.post(`/api/v1/ai/suggestions/${s.id}/accept`);
    onAccepted(s.id, s.suggested_content);
  };

  const reject = async (s: Suggestion) => {
    await apiClient.post(`/api/v1/ai/suggestions/${s.id}/reject`);
    onRejected(s.id);
  };

  const severityColour = (sev: Suggestion['severity']) => {
    if (sev === 'error') return '#dc2626';
    if (sev === 'warning') return '#d97706';
    return '#6b7280';
  };

  return (
    <aside className="ai-panel">
      <h3 className="ai-panel__title">{t('ai_panel.title')}</h3>

      {aiOfflineMode && (
        <div className="ai-panel__offline-banner" role="alert">
          ⚠️ {t('ai_panel.offline_mode')}
        </div>
      )}

      {suggestions.length === 0 && (
        <p className="ai-panel__empty">{t('ai_panel.no_suggestions')}</p>
      )}

      <ul className="ai-panel__list">
        {suggestions.map((s) => (
          <li key={s.id} className="ai-card" style={{ borderLeftColor: severityColour(s.severity) }}>
            {s.gap && <p className="ai-card__gap"><strong>{t('ai_panel.gap')}:</strong> {s.gap}</p>}
            {s.clause_reference && (
              <p className="ai-card__clause">
                <strong>{t('ai_panel.clause')}:</strong>{' '}
                <code>{s.clause_reference}</code>
              </p>
            )}
            <pre className="ai-card__content">{s.suggested_content}</pre>
            <div className="ai-card__actions">
              <button
                className="btn btn--success btn--sm"
                onClick={() => accept(s)}
                aria-label={t('ai_panel.accept')}
              >
                {t('ai_panel.accept')}
              </button>
              <button
                className="btn btn--danger btn--sm"
                onClick={() => reject(s)}
                aria-label={t('ai_panel.reject')}
              >
                {t('ai_panel.reject')}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
