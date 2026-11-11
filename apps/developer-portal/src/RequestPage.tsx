// Source: https://backstage.io/docs/next/plugins/call-existing-api/
import { discoveryApiRef, fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { useCallback, useEffect, useState } from 'react';

type Workflow = { id: string; status: string; cloud: string; environment: string; plan_digest?: string };
type Detail = {
  workflow: Workflow;
  plan?: { digest: string; sources: string[] } | null;
  report?: { deployment_status: string; image_ref: string } | null;
};

export function RequestPage() {
  const discovery = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [rows, setRows] = useState<Workflow[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const base = await discovery.getBaseUrl('multicloud-delivery');
      const response = await fetchApi.fetch(`${base}/workflows`);
      if (!response.ok) throw new Error(`Request list failed (${response.status})`);
      setRows(await response.json() as Workflow[]);
      setError('');
    } catch (cause) {
      setError(String(cause));
    } finally {
      setLoading(false);
    }
  }, [discovery, fetchApi]);

  useEffect(() => { void load(); }, [load]);

  async function select(id: string) {
    try {
      const base = await discovery.getBaseUrl('multicloud-delivery');
      const response = await fetchApi.fetch(`${base}/workflows/${encodeURIComponent(id)}`);
      if (!response.ok) throw new Error(`Request detail failed (${response.status})`);
      setDetail(await response.json() as Detail);
      setError('');
    } catch (cause) { setError(String(cause)); }
  }

  return <main style={{ padding: 24 }}>
    <h1>Multi-cloud delivery requests</h1>
    <p>Review workflow state, plan sources and deployment evidence.</p>
    {error && <p role="alert">{error}</p>}
    {loading ? <p>Loading requests…</p> : <ul>{rows.map(row =>
      <li key={row.id}><button onClick={() => void select(row.id)}>
        {row.cloud.toUpperCase()} · {row.environment} · {row.status}
      </button></li>
    )}</ul>}
    {detail && <section aria-label="Selected request">
      <h2>Workflow {detail.workflow.id}</h2>
      <p>Status: {detail.workflow.status}</p>
      <p>Plan digest: {detail.plan?.digest ?? 'Pending'}</p>
      <h3>Approved references</h3>
      <ul>{(detail.plan?.sources ?? []).map(source => <li key={source}>{source}</li>)}</ul>
      <p>Deployment: {detail.report?.deployment_status ?? 'Pending'}</p>
      <p>Image: {detail.report?.image_ref ?? 'Pending'}</p>
    </section>}
  </main>;
}
