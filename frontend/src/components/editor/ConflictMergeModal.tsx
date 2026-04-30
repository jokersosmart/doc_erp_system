/**
 * ConflictMergeModal — three-way diff on 409 optimistic lock conflict (T047).
 * FR-015b: No auto-merge. Human must manually resolve.
 * Shows: My changes | Base (server) | Submit resolved.
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../services/api';

interface ConflictMergeModalProps {
  yourContent: string;
  yourVersion: number;
  dbVersion: number;
  documentId: string;
  onResolved: (resolvedContent: string) => Promise<void>;
  onCancel: () => void;
}

export function ConflictMergeModal({ yourContent, yourVersion, dbVersion, documentId, onResolved, onCancel }: ConflictMergeModalProps) {
  const { t } = useTranslation();
  const [serverContent, setServerContent] = useState<string>('');
  const [resolved, setResolved] = useState(yourContent);
  const [submitting, setSubmitting] = useState(false);

  // Load current server version for diff display
  useEffect(() => {
    apiClient.get<{ content_markdown?: string }>(`/api/v1/documents/${documentId}`)
      .then((res) => setServerContent(res.data.content_markdown ?? ''))
      .catch(() => setServerContent('(unable to load server version)'));
  }, [documentId]);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onResolved(resolved);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="conflict-title">
      <div className="modal conflict-modal">
        <h2 id="conflict-title" className="modal__title">{t('conflict.title')}</h2>
        <p className="modal__subtitle">
          {t('conflict.description', { yourVersion, dbVersion })}
        </p>

        <div className="conflict-modal__columns">
          {/* My changes */}
          <section className="conflict-modal__col">
            <h3>{t('conflict.my_changes')}</h3>
            <pre className="conflict-modal__diff conflict-modal__diff--yours">{yourContent}</pre>
          </section>

          {/* Server version */}
          <section className="conflict-modal__col">
            <h3>{t('conflict.server_version')}</h3>
            <pre className="conflict-modal__diff conflict-modal__diff--server">{serverContent}</pre>
          </section>
        </div>

        {/* Resolved content editor */}
        <section className="conflict-modal__resolve">
          <h3>{t('conflict.resolved_content')}</h3>
          <p className="conflict-modal__hint">{t('conflict.no_auto_merge')}</p>
          <textarea
            className="conflict-modal__textarea"
            value={resolved}
            onChange={(e) => setResolved(e.target.value)}
            aria-label={t('conflict.resolved_content')}
          />
        </section>

        <div className="modal__actions">
          <button className="btn btn--secondary" onClick={onCancel} disabled={submitting}>
            {t('common.cancel')}
          </button>
          <button className="btn btn--primary" onClick={handleSubmit} disabled={submitting}>
            {submitting ? t('common.saving') : t('conflict.submit_resolved')}
          </button>
        </div>
      </div>
    </div>
  );
}
