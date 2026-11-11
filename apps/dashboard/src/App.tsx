// Sources: https://react.dev/reference/react/useEffect
//          https://react.dev/reference/react/useState
import { useEffect, useRef, useState } from 'react'
import { validateRequest, type FieldErrors, type RequestDraft } from './requestValidation'

type Workflow = {
  id: string; status: string; cloud: 'aws' | 'azure'; environment: string
  created_at: string; request_digest: string; plan_digest: string | null
}
type Detail = {
  workflow: Workflow; request: RequestDraft; events: { type: string; at: string }[]
  plan: { digest: string; sources: string[]; cloud: string; environment: string; application: string } | null
  report: {
    branch: string; pull_request: string; image_ref: string; ci_passed: boolean
    security_passed: boolean; supply_chain_passed: boolean
    deployment_status: string; deployment_revision: string
  } | null
}

const initialRequest: RequestDraft = {
  cloud: '', environment: '', requester: '', cost_center: '', description: '',
  application: { name: '', repository: '' },
  infrastructure: { region: '', module: '' },
  approval: { required: true, change_record: null },
}

const DRAFT_KEY = 'multicloud-request-draft-v1'
const SUBMISSION_KEY = 'multicloud-request-submission-v1'

function loadDraft(): RequestDraft {
  try {
    const stored = JSON.parse(sessionStorage.getItem(DRAFT_KEY) || 'null')
    if (stored && typeof stored === 'object') return { ...initialRequest, ...stored }
  } catch { /* Storage can be disabled in a browser profile. */ }
  return initialRequest
}

class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message) }
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
    throw new ApiError(detail || `Request failed (${response.status})`, response.status)
  }
  return response.json() as Promise<T>
}

function formatDate(value: string) { return new Date(value).toLocaleString() }
function short(value: string | null) { return value ? `${value.slice(0, 10)}…` : 'Pending' }
function statusLabel(status: string) {
  return status === 'received' || status === 'queued' ? 'Pending plan' : status.replaceAll('_', ' ')
}

export default function App() {
  const [token, setToken] = useState('')
  const [connected, setConnected] = useState(false)
  const [rows, setRows] = useState<Workflow[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [detail, setDetail] = useState<Detail | null>(null)
  const [request, setRequest] = useState<RequestDraft>(loadDraft)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [approval, setApproval] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<'overview' | 'new'>('overview')
  const submissionKey = useRef<string | null>(null)

  useEffect(() => {
    try { sessionStorage.setItem(DRAFT_KEY, JSON.stringify(request)) } catch { /* Draft stays in memory. */ }
  }, [request])

  useEffect(() => {
    if (Object.keys(fieldErrors).length) setFieldErrors(validateRequest(request))
    // Recheck visible errors as the user edits the draft.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request])

  function showError(cause: unknown) {
    if (cause instanceof ApiError && cause.status === 403 && cause.message === 'dashboard access denied') {
      setConnected(false); setToken('')
      setError('Session expired. Enter a new dashboard token; your request draft is saved in this tab.')
    } else if (cause instanceof ApiError && cause.status === 404) {
      setError('Access denied or request not found.')
    } else if ((cause instanceof ApiError && cause.status >= 500) || cause instanceof TypeError) {
      setError('Control plane is unavailable. Your draft is saved in this tab; retry when service returns.')
    } else setError(String(cause))
  }

  async function refresh() {
    const workflows = await api<Workflow[]>('/dashboard/workflows', token)
    setRows(workflows)
    if (selected) {
      const current = await api<Detail>(`/dashboard/workflows/${selected}`, token)
      setDetail(current)
      if (current.workflow.status !== 'awaiting_approval') setApproval('')
    }
  }

  useEffect(() => {
    if (!connected) return
    let stopped = false
    let timer: number
    const poll = async () => {
      if (!document.hidden) {
        try { await refresh() } catch (cause) { showError(cause) }
      }
      if (!stopped) timer = window.setTimeout(() => { void poll() }, 2000)
    }
    timer = window.setTimeout(() => { void poll() }, 2000)
    return () => { stopped = true; window.clearTimeout(timer) }
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
    } catch (e) { showError(e) }
  }

  async function choose(id: string) {
    setSelected(id); setError(''); setApproval('')
    try { setDetail(await api<Detail>(`/dashboard/workflows/${id}`, token)) }
    catch (e) { showError(e) }
  }

  async function submit() {
    const errors = validateRequest(request)
    setFieldErrors(errors)
    if (Object.keys(errors).length) return
    setBusy(true); setError('')
    try {
      if (!submissionKey.current) {
        try { submissionKey.current = sessionStorage.getItem(SUBMISSION_KEY) } catch { /* Storage is optional. */ }
        submissionKey.current ||= crypto.randomUUID()
        try { sessionStorage.setItem(SUBMISSION_KEY, submissionKey.current) } catch { /* Retry within this tab still uses the ref. */ }
      }
      const created = await api<Workflow>('/dashboard/requests', token, {
        method: 'POST', headers: { 'Idempotency-Key': submissionKey.current },
        body: JSON.stringify(request),
      })
      submissionKey.current = null
      try { sessionStorage.removeItem(SUBMISSION_KEY); sessionStorage.removeItem(DRAFT_KEY) } catch { /* Storage is optional. */ }
      setRequest(initialRequest)
      setTab('overview')
      await refresh()
      await choose(created.id)
    } catch (e) { showError(e) }
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
    } catch (e) { showError(e) }
    finally { setBusy(false) }
  }

  async function generateLocalApproval() {
    if (!selected) return
    setBusy(true); setError('')
    try {
      const result = await api<{ signed_approval: string }>(
        `/dashboard/workflows/${selected}/local-mock-approval`, token, { method: 'POST' },
      )
      setApproval(result.signed_approval)
    } catch (e) { showError(e) }
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
      {tab === 'new' ? <form className="panel form-panel" noValidate onSubmit={e => { e.preventDefault(); void submit() }}>
        <div className="panel-heading"><div><p className="eyebrow">01 / Request details</p><h2>What are you building?</h2></div><span className="pill">Approval required</span></div>
        <div className="form-grid">
          <label>Requester email<input type="email" required value={request.requester} aria-invalid={!!fieldErrors.requester} onChange={e => setRequest({ ...request, requester: e.target.value })} placeholder="engineer@example.com" />{fieldErrors.requester && <small className="field-error" role="alert">{fieldErrors.requester}</small>}</label>
          <label>Cost center<input required value={request.cost_center} aria-invalid={!!fieldErrors.cost_center} onChange={e => setRequest({ ...request, cost_center: e.target.value })} />{fieldErrors.cost_center && <small className="field-error" role="alert">{fieldErrors.cost_center}</small>}</label>
          <label>Application name<input required value={request.application.name} aria-invalid={!!fieldErrors.application} onChange={e => setRequest({ ...request, application: { ...request.application, name: e.target.value } })} />{fieldErrors.application && <small className="field-error" role="alert">{fieldErrors.application}</small>}</label>
          <label>Repository URL<input type="url" required value={request.application.repository} aria-invalid={!!fieldErrors.repository} onChange={e => setRequest({ ...request, application: { ...request.application, repository: e.target.value } })} />{fieldErrors.repository && <small className="field-error" role="alert">{fieldErrors.repository}</small>}</label>
          <label>Cloud<select required value={request.cloud} aria-invalid={!!fieldErrors.cloud} onChange={e => setRequest({ ...request, cloud: e.target.value as RequestDraft['cloud'], infrastructure: { region: e.target.value === 'azure' ? 'eastus' : 'us-east-1', module: 'sandbox-api' } })}><option value="">Choose cloud</option><option value="aws">AWS</option><option value="azure">Azure</option></select>{fieldErrors.cloud && <small className="field-error" role="alert">{fieldErrors.cloud}</small>}</label>
          <label>Environment<select required value={request.environment} aria-invalid={!!fieldErrors.environment} onChange={e => setRequest({ ...request, environment: e.target.value })}><option value="">Choose environment</option>{['sandbox', 'dev', 'staging', 'prod'].map(x => <option key={x}>{x}</option>)}</select>{fieldErrors.environment && <small className="field-error" role="alert">{fieldErrors.environment}</small>}</label>
          <label>Region<input required value={request.infrastructure.region} aria-invalid={!!fieldErrors.region} onChange={e => setRequest({ ...request, infrastructure: { ...request.infrastructure, region: e.target.value } })} />{fieldErrors.region && <small className="field-error" role="alert">{fieldErrors.region}</small>}</label>
          <label>Approved module<input required value={request.infrastructure.module} aria-invalid={!!fieldErrors.module} onChange={e => setRequest({ ...request, infrastructure: { ...request.infrastructure, module: e.target.value } })} />{fieldErrors.module && <small className="field-error" role="alert">{fieldErrors.module}</small>}</label>
          <label className="wide-field">Request details (optional)<textarea value={request.description} aria-invalid={!!fieldErrors.description} onChange={e => setRequest({ ...request, description: e.target.value })} maxLength={2001} rows={4} placeholder="Describe the application and requested infrastructure in plain text." />{fieldErrors.description && <small className="field-error" role="alert">{fieldErrors.description}</small>}<small>{request.description.length}/2,000 characters</small></label>
          <label>Change record (optional)<input value={request.approval.change_record || ''} aria-invalid={!!fieldErrors.change_record} onChange={e => setRequest({ ...request, approval: { required: true, change_record: e.target.value || null } })} />{fieldErrors.change_record && <small className="field-error" role="alert">{fieldErrors.change_record}</small>}</label>
        </div>
        <div className="form-actions"><button className="primary" type="submit" disabled={busy}>{busy ? 'Submitting…' : 'Submit request →'}</button></div>
      </form> : <>
        <section className="metrics" aria-label="Workspace summary">
          <div className="metric"><span>All requests</span><strong>{rows.length}</strong><small>Visible to this local requester</small></div>
          <div className="metric"><span>Awaiting approval</span><strong>{awaiting}</strong><small>Plan review required</small></div>
          <div className="metric"><span>Completed</span><strong>{completed}</strong><small>Simulated deployments</small></div>
        </section>
        <div className="content-grid">
          <section className="panel request-list"><div className="panel-heading"><div><p className="eyebrow">02 / Activity</p><h2>Requests</h2></div><button className="small-button" onClick={() => setTab('new')}>New +</button></div>
            {rows.length ? rows.map(row => <button key={row.id} className={`request-item ${selected === row.id ? 'selected' : ''}`} onClick={() => void choose(row.id)}><div><strong>{row.cloud.toUpperCase()} · {row.environment}</strong><span>{formatDate(row.created_at)}</span></div><span className={`badge ${row.status}`}>{statusLabel(row.status)}</span></button>) : <p className="empty">No requests yet. Start with a new request.</p>}
          </section>
          <div className="detail-stack">
            {detail ? <>
              <section className="panel"><div className="panel-heading"><div><p className="eyebrow">03 / Plan review</p><h2>{detail.request.application.name}</h2></div><span className={`badge ${detail.workflow.status}`} aria-live="polite">{statusLabel(detail.workflow.status)}</span></div>
                <div className="details"><div><span>Request ID</span><code>{detail.workflow.id}</code></div><div><span>Cloud / region</span><strong>{detail.request.cloud.toUpperCase()} / {detail.request.infrastructure.region}</strong></div><div><span>Module</span><strong>{detail.request.infrastructure.module}</strong></div><div><span>Plan digest</span><code title={detail.plan?.digest || ''}>{short(detail.plan?.digest || null)}</code></div><div><span>Approval</span><strong>{detail.workflow.status === 'awaiting_approval' ? 'Waiting for signed approval' : statusLabel(detail.workflow.status)}</strong></div></div>
                {detail.plan && <p className="note">Terraform diff, cost estimate and risk score are not supplied by the local mock planner.</p>}
                {detail.plan?.sources.length ? <div className="sources"><h3>Approved references</h3>{detail.plan.sources.map(source => <p key={source}>{source}</p>)}</div> : <p className="note">No approved knowledge references were attached to this plan.</p>}
                {detail.workflow.status === 'awaiting_approval' && <div className="approval-box">
                  <p className="approval-context">Local mock only · This token simulates a separate reviewer. It is not an enterprise approval.</p>
                  <button type="button" disabled={busy} onClick={() => void generateLocalApproval()}>Show local mock token</button>
                  <label htmlFor="approval">Signed approval token</label>
                  <div><input id="approval" type="text" value={approval} onChange={e => setApproval(e.target.value)} placeholder="Generate a local token or paste one" autoComplete="off" spellCheck={false} /><button type="button" disabled={!approval || busy} onClick={() => void approve()}>Submit approval</button></div>
                  <small>Review the plan digest above before submitting. A generated token expires after 10 minutes.</small>
                </div>}
              </section>
              <section className="panel"><div className="panel-heading"><div><p className="eyebrow">04 / Trace</p><h2>Agent activity</h2></div></div><div className="timeline">{detail.events.map((event, i) => <div key={i}><span className="timeline-dot" /><div><strong>{event.type.replaceAll('.', ' · ')}</strong><small>{formatDate(event.at)}</small></div></div>)}<div><span className="timeline-dot muted-dot" /><div><strong>Current phase: {statusLabel(detail.workflow.status)}</strong><small>Checks for updates every 2 seconds</small></div></div></div></section>
              <section className="panel"><div className="panel-heading"><div><p className="eyebrow">05 / Operations</p><h2>Deployment & resources</h2></div></div>{detail.report ? <><div className="details"><div><span>Deployment</span><strong>{detail.report.deployment_status}</strong></div><div><span>Revision</span><code>{short(detail.report.deployment_revision)}</code></div><div><span>Image</span><code title={detail.report.image_ref}>{short(detail.report.image_ref)}</code></div><div><span>CI / security / supply chain</span><strong>{[detail.report.ci_passed, detail.report.security_passed, detail.report.supply_chain_passed].every(Boolean) ? 'Passed' : 'Needs attention'}</strong></div></div><p className="note">Simulated resource: {detail.request.infrastructure.module} in {detail.request.infrastructure.region}. Live cloud inventory is not connected.</p><a className="report-link" href={detail.report.pull_request} target="_blank" rel="noreferrer">View pull request ↗</a></> : <p className="empty">Deployment evidence and resource inventory appear after the mock workflow completes.</p>}</section>
            </> : <section className="panel empty-detail"><h2>Select a request</h2><p>Choose a request to review its plan and operational results.</p></section>}
          </div>
        </div>
      </>}
    </main>
  </div>
}
