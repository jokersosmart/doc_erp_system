/**
 * ProjectDashboardPage — role-specific project dashboard (T036).
 * PM view: document skeleton list with lifecycle + lock badges (FR-012).
 * Data source: GET /api/v1/projects/{id}/documents
 */
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../services/api';

export type LifecycleState = 'DRAFT' | 'REVIEW' | 'APPROVED' | 'OBSOLETE';
export type LockState = 'UNLOCKED' | 'LOCKED' | 'PENDING_QRA';

export interface DocumentSummary {
  id: string;
  title: string;
  partition: string;
  lifecycle_state: LifecycleState;
  lock_state: LockState;
  is_safety_critical: boolean;
  owner_name: string | null;
  updated_at: string;
}

interface ProjectInfo {
  id: string;
  name: string;
  bu_node_id: string;
  aspice_level: number | null;
  asil_level: string | null;
  cal_level: string | null;
  standards: string[];
}

// ── Badge helpers ─────────────────────────────────────────────────────────────

function LifecycleBadge({ state }: { state: LifecycleState }) {
  const colours: Record<LifecycleState, string> = {
    DRAFT: '#6b7280',
    REVIEW: '#d97706',
    APPROVED: '#16a34a',
    OBSOLETE: '#9ca3af',
  };
  return (
    <span
      className="badge"
      style={{ backgroundColor: colours[state], color: '#fff', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}
    >
      {state}
    </span>
  );
}

function LockBadge({ state }: { state: LockState }) {
  const meta: Record<LockState, { label: string; color: string }> = {
    UNLOCKED: { label: '🔓 UNLOCKED', color: '#16a34a' },
    LOCKED: { label: '🔒 LOCKED', color: '#dc2626' },
    PENDING_QRA: { label: '⏳ PENDING QRA', color: '#d97706' },
  };
  const { label, color } = meta[state];
  return (
    <span className="badge" style={{ color, fontWeight: 600, fontSize: 12 }}>
      {label}
    </span>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ProjectDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { t } = useTranslation();

  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setLoading(true);

    Promise.all([
      apiClient.get<ProjectInfo>(`/api/v1/projects/${projectId}`),
      apiClient.get<DocumentSummary[]>(`/api/v1/projects/${projectId}/documents`),
    ])
      .then(([pRes, dRes]) => {
        if (cancelled) return;
        setProject(pRes.data);
        setDocuments(dRes.data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : t('dashboard.error.load_failed'));
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [projectId, t]);

  if (loading) return <div className="loading">{t('common.loading')}</div>;
  if (error) return <div className="error" role="alert">{error}</div>;
  if (!project) return null;

  // Group documents by partition
  const byPartition: Record<string, DocumentSummary[]> = {};
  for (const doc of documents) {
    (byPartition[doc.partition] ??= []).push(doc);
  }
  const partitionOrder = ['SYS', 'HW', 'SWE', 'SAFETY', 'SECURITY', 'VCT'];
  const sortedPartitions = Object.keys(byPartition).sort(
    (a, b) => (partitionOrder.indexOf(a) < 0 ? 99 : partitionOrder.indexOf(a)) - (partitionOrder.indexOf(b) < 0 ? 99 : partitionOrder.indexOf(b))
  );

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard__header">
        <h1 className="dashboard__title">{project.name}</h1>
        <div className="dashboard__meta">
          {project.aspice_level !== null && <span>ASPICE L{project.aspice_level}</span>}
          {project.asil_level && <span>{project.asil_level}</span>}
          {project.cal_level && <span>{project.cal_level}</span>}
          {project.standards.map((s) => <span key={s} className="tag">{s}</span>)}
        </div>
      </header>

      {/* Empty state */}
      {documents.length === 0 && (
        <div className="dashboard__empty">
          <p>{t('dashboard.empty.description')}</p>
          <Link to={`/projects/${projectId}/wizard`} className="btn btn--primary">
            {t('dashboard.empty.run_wizard')}
          </Link>
        </div>
      )}

      {/* Document skeleton list grouped by partition */}
      {sortedPartitions.map((partition) => (
        <section key={partition} className="dashboard__partition">
          <h2 className="dashboard__partition-title">{partition}</h2>
          <table className="doc-table">
            <thead>
              <tr>
                <th>{t('dashboard.table.title')}</th>
                <th>{t('dashboard.table.lifecycle')}</th>
                <th>{t('dashboard.table.lock')}</th>
                <th>{t('dashboard.table.safety_critical')}</th>
                <th>{t('dashboard.table.owner')}</th>
                <th>{t('dashboard.table.updated')}</th>
              </tr>
            </thead>
            <tbody>
              {byPartition[partition].map((doc) => (
                <tr key={doc.id}>
                  <td>
                    <Link to={`/documents/${doc.id}`}>{doc.title}</Link>
                  </td>
                  <td><LifecycleBadge state={doc.lifecycle_state} /></td>
                  <td><LockBadge state={doc.lock_state} /></td>
                  <td>{doc.is_safety_critical ? '⚠️' : '—'}</td>
                  <td>{doc.owner_name ?? '—'}</td>
                  <td>{new Date(doc.updated_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}
