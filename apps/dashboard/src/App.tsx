// Sources: https://react.dev/reference/react/useEffect
//          https://react.dev/reference/react/useState
import { useEffect, useState } from 'react'

type Workflow = {
  id: string; status: string; cloud: 'aws' | 'azure'; environment: string
  created_at: string; request_digest: string; plan_digest: string | null
}
type Request = {
  cloud: 'aws' | 'azure'; environment: string; requester: string
  application: { name: string; repository: string }
  infrastructure: { region: string; module: string }
  approval: { required: true; change_record: string | null }
}
type Detail = {
  workflow: Workflow; request: Request; events: { type: string; at: string }[]
  plan: { digest: string; sources: string[]; cloud: string; environment: string; application: string } | null
  report: {
    branch: string; pull_request: string; image_ref: string; ci_passed: boolean
    security_passed: boolean; supply_chain_passed: boolean
    deployment_status: string; deployment_revision: string
  } | null
}

const initialRequest: Request = {
  cloud: 'aws', environment: 'sandbox', requester: '',
  application: { name: 'sample-api', repository: 'https://github.com/example/sample-api' },
  infrastructure: { region: 'us-east-1', module: 'sandbox-api' },
  approval: { required: true, change_record: null },
}

async function api<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', ...options.headers },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = Array.isArray(error.detail)
      ? error.detail.map((item: { msg?: string }) => item.msg || 'Invalid field').join('; ')
      : error.detail
    throw new Error(detail || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

function formatDate(value: string) { return new Date(value).toLocaleString() }
function short(value: string | null) { return value ? `${value.slice(0, 10)}…` : 'Pending' }

export default function App() {
  const [token, setToken] = useState('')
  const [connected, setConnected] = useState(false)
  const [rows, setRows] = useState<Workflow[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [detail, setDetail] = useState<Detail | null>(null)
  const [request, setRequest] = useState<Request>(initialRequest)
  const [approval, setApproval] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<'overview' | 'new'>('overview')

  async function refresh() {
    const workflows = await api<Workflow[]>('/dashboard/workflows', token)
    setRows(workflows)
    if (selected) setDetail(await api<Detail>(`/dashboard/workflows/${selected}`, token))
  }

  useEffect(() => {
    if (!connected) return
    const timer = window.setInterval(() => { void refresh().catch(e => setError(String(e))) }, 5000)
    return () => window.clearInterval(timer)
    // Only restart polling after the selected workflow or connection changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connected, selected])

  async function connect() {
    try {
      setError('')
      const workflows = await api<Workflow[]>('/dashboard/workflows', token)
      setRows(workflows); setConnected(true)
      if (workflows.length) {
        setSelected(workflows[0].id)
        setDetail(await api<Detail>(`/dashboard/workflows/${workflows[0].id}`, token))
      }
    } catch (e) { setError(String(e)) }
  }

  async function choose(id: string) {
    setSelected(id); setError('')
    try { setDetail(await api<Detail>(`/dashboard/workflows/${id}`, token)) }
    catch (e) { setError(String(e)) }
  }

  async function submit() {
    setBusy(true); setError('')
    try {
      const created = await api<Workflow>('/dashboard/requests', token, {
        method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify(request),
      })
      setTab('overview')
      await refresh()
      await choose(created.id)
    } catch (e) { setError(String(e)) }
    finally { setBusy(false) }
  }

  async function approve() {
    if (!selected || !approval) return
    setBusy(true); setError('')
    try {
      await api(`/workflows/${selected}/approve`, token, {
        method: 'POST', body: JSON.stringify({ signed_approval: approval }),
      })
      setApproval('')
      await refresh()
    } catch (e) { setError(String(e)) }
    finally { setBusy(false) }
  }

  const completed = rows.filter(row => row.status === 'completed').length
  const awaiting = rows.filter(row => row.status === 'awaiting_approval').length

  if (!connected) return <main className="connect-shell">
    <div className="connect-card">
      <div className="brand-mark">D</div>
      <p className="eyebrow">Enterprise DevOps · Local workspace</p>
      <h1>Delivery Control Center</h1>
      <p>Review requests, plans and deployment evidence from one place.</p>
      <label htmlFor="token">Local dashboard token</label>
      <input id="token" type="password" value={token} onChange={e => setToken(e.target.value)} onKeyDown={e => e.key === 'Enter' && void connect()} />
      <button className="primary" onClick={() => void connect()} disabled={!token}>Open dashboard <span>→</span></button>
      {error && <p className="error" role="alert">{error}</p>}
      <p className="small muted">The token stays in this browser tab. Ask your local operator for the configured token.</p>
    </div>
  </main>

  return <div className="layout">
    <aside className="sidebar">
      <div className="logo"><div className="brand-mark">D</div><span>Delivery<br />Control Center</span></div>
      <nav aria-label="Main navigation">
        <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>◫ <span>Overview</span></button>
        <button className={tab === 'new' ? 'active' : ''} onClick={() => setTab('new')}>＋ <span>New request</span></button>
      </nav>
      <div className="side-footer"><span className="status-dot" /> Local mock environment<br /><small>Cloud changes are simulated</small></div>
    </aside>
    <main className="main">
      <header className="topbar"><div><p className="eyebrow">Workspace / {tab === 'overview' ? 'Overview' : 'New request'}</p><h1>{tab === 'overview' ? 'Delivery overview' : 'Submit a request'}</h1></div><button className="text-button" onClick={() => void refresh()}>Refresh ↻</button></header>
      {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')}>Dismiss</button></div>}
      {tab === 'new' ? <section className="panel form-panel">
        <div className="panel-heading"><div><p className="eyebrow">01 / Request details</p><h2>What are you building?</h2></div><span className="pill">Approval required</span></div>
        <div className="form-grid">
          <label>Requester email<input value={request.requester} onChange={e => setRequest({ ...request, requester: e.target.value })} placeholder="engineer@example.com" /></label>
          <label>Application name<input value={request.application.name} onChange={e => setRequest({ ...request, application: { ...request.application, name: e.target.value } })} /></label>
          <label>Repository URL<input value={request.application.repository} onChange={e => setRequest({ ...request, application: { ...request.application, repository: e.target.value } })} /></label>
          <label>Cloud<select value={request.cloud} onChange={e => setRequest({ ...request, cloud: e.target.value as Request['cloud'], infrastructure: { region: e.target.value === 'azure' ? 'eastus' : 'us-east-1', module: 'sandbox-api' } })}><option value="aws">AWS</option><option value="azure">Azure</option></select></label>
          <label>Environment<select value={request.environment} onChange={e => setRequest({ ...request, environment: e.target.value })}>{['sandbox', 'dev', 'staging', 'prod'].map(x => <option key={x}>{x}</option>)}</select></label>
          <label>Region<input value={request.infrastructure.region} onChange={e => setRequest({ ...request, infrastructure: { ...request.infrastructure, region: e.target.value } })} /></label>
          <label>Approved module<input value={request.infrastructure.module} onChange={e => setRequest({ ...request, infrastructure: { ...request.infrastructure, module: e.target.value } })} /></label>
          <label>Change record (optional)<input value={request.approval.change_record || ''} onChange={e => setRequest({ ...request, approval: { required: true, change_record: e.target.value || null } })} /></label>
        </div>
        <div className="form-actions"><button className="primary" disabled={busy || !request.requester} onClick={() => void submit()}>{busy ? 'Submitting…' : 'Submit request →'}</button></div>
      </section> : <>
        <section className="metrics" aria-label="Workspace summary">
          <div className="metric"><span>All requests</span><strong>{rows.length}</strong><small>Visible to this local requester</small></div>
          <div className="metric"><span>Awaiting approval</span><strong>{awaiting}</strong><small>Plan review required</small></div>
          <div className="metric"><span>Completed</span><strong>{completed}</strong><small>Simulated deployments</small></div>
        </section>
        <div className="content-grid">
          <section className="panel request-list"><div className="panel-heading"><div><p className="eyebrow">02 / Activity</p><h2>Requests</h2></div><button className="small-button" onClick={() => setTab('new')}>New +</button></div>
            {rows.length ? rows.map(row => <button key={row.id} className={`request-item ${selected === row.id ? 'selected' : ''}`} onClick={() => void choose(row.id)}><div><strong>{row.cloud.toUpperCase()} · {row.environment}</strong><span>{formatDate(row.created_at)}</span></div><span className={`badge ${row.status}`}>{row.status.replaceAll('_', ' ')}</span></button>) : <p className="empty">No requests yet. Start with a new request.</p>}
          </section>
          <div className="detail-stack">
            {detail ? <>
              <section className="panel"><div className="panel-heading"><div><p className="eyebrow">03 / Plan review</p><h2>{detail.request.application.name}</h2></div><span className={`badge ${detail.workflow.status}`}>{detail.workflow.status.replaceAll('_', ' ')}</span></div>
                <div className="details"><div><span>Cloud / region</span><strong>{detail.request.cloud.toUpperCase()} / {detail.request.infrastructure.region}</strong></div><div><span>Module</span><strong>{detail.request.infrastructure.module}</strong></div><div><span>Plan digest</span><code title={detail.plan?.digest || ''}>{short(detail.plan?.digest || null)}</code></div><div><span>Approval</span><strong>{detail.workflow.status === 'awaiting_approval' ? 'Waiting for signed approval' : detail.workflow.status}</strong></div></div>
                {detail.plan?.sources.length ? <div className="sources"><h3>Approved references</h3>{detail.plan.sources.map(source => <p key={source}>{source}</p>)}</div> : <p className="note">No approved knowledge references were attached to this plan.</p>}
                {detail.workflow.status === 'awaiting_approval' && <div className="approval-box"><label htmlFor="approval">Signed approval token</label><div><input id="approval" type="password" value={approval} onChange={e => setApproval(e.target.value)} placeholder="Paste a plan-bound token" /><button disabled={!approval || busy} onClick={() => void approve()}>Submit approval</button></div><small>Approval issuance is separate from this local dashboard.</small></div>}
              </section>
              <section className="panel"><div className="panel-heading"><div><p className="eyebrow">04 / Trace</p><h2>Agent activity</h2></div></div><div className="timeline">{detail.events.map((event, i) => <div key={i}><span className="timeline-dot" /><div><strong>{event.type.replaceAll('.', ' · ')}</strong><small>{formatDate(event.at)}</small></div></div>)}<div><span className="timeline-dot muted-dot" /><div><strong>Current phase: {detail.workflow.status.replaceAll('_', ' ')}</strong><small>Refreshes every 5 seconds</small></div></div></div></section>
              <section className="panel"><div className="panel-heading"><div><p className="eyebrow">05 / Operations</p><h2>Deployment & resources</h2></div></div>{detail.report ? <><div className="details"><div><span>Deployment</span><strong>{detail.report.deployment_status}</strong></div><div><span>Revision</span><code>{short(detail.report.deployment_revision)}</code></div><div><span>Image</span><code title={detail.report.image_ref}>{short(detail.report.image_ref)}</code></div><div><span>CI / security / supply chain</span><strong>{[detail.report.ci_passed, detail.report.security_passed, detail.report.supply_chain_passed].every(Boolean) ? 'Passed' : 'Needs attention'}</strong></div></div><p className="note">Simulated resource: {detail.request.infrastructure.module} in {detail.request.infrastructure.region}. Live cloud inventory is not connected.</p><a className="report-link" href={detail.report.pull_request} target="_blank" rel="noreferrer">View pull request ↗</a></> : <p className="empty">Deployment evidence and resource inventory appear after the mock workflow completes.</p>}</section>
            </> : <section className="panel empty-detail"><h2>Select a request</h2><p>Choose a request to review its plan and operational results.</p></section>}
          </div>
        </div>
      </>}
    </main>
  </div>
}
