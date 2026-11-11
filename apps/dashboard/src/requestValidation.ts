// The browser form mirrors apps.api.contracts.RequestCreate; the API remains authoritative.
// Sources: https://react.dev/reference/react-dom/components/input
//          https://developer.mozilla.org/en-US/docs/Web/HTML/Guides/Constraint_validation
export type RequestDraft = {
  cloud: '' | 'aws' | 'azure'; environment: string; requester: string
  cost_center: string; description: string
  application: { name: string; repository: string }
  infrastructure: { region: string; module: string }
  approval: { required: true; change_record: string | null }
}

export type FieldErrors = Partial<Record<
  'requester' | 'cost_center' | 'description' | 'application' | 'repository' | 'cloud' | 'environment' | 'region' | 'module' | 'change_record', string
>>

export function validateRequest(request: RequestDraft): FieldErrors {
  const errors: FieldErrors = {}
  if (!request.cloud) errors.cloud = 'Choose a cloud.'
  if (!request.environment) errors.environment = 'Choose an environment.'
  if (!request.requester.trim()) errors.requester = 'Requester email is required.'
  else if (request.requester.length > 128 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(request.requester)) errors.requester = 'Enter a valid email address.'
  if (!request.cost_center.trim()) errors.cost_center = 'Cost center is required.'
  else if (request.cost_center.length < 2) errors.cost_center = 'Use at least 2 characters.'
  else if (request.cost_center.length > 64) errors.cost_center = 'Use 64 characters or fewer.'
  if (!request.application.name.trim()) errors.application = 'Application name is required.'
  else if (!/^[a-z][a-z0-9-]*[a-z0-9]$/.test(request.application.name) || request.application.name.length > 63) errors.application = 'Use 2–63 lowercase letters, numbers or hyphens.'
  if (!request.application.repository.trim()) errors.repository = 'Repository URL is required.'
  else if (request.application.repository.length > 256 || !/^https:\/\//.test(request.application.repository)) errors.repository = 'Enter an HTTPS repository URL.'
  if (!request.infrastructure.region.trim()) errors.region = 'Region is required.'
  else if (request.infrastructure.region.length < 2 || request.infrastructure.region.length > 64) errors.region = 'Use 2–64 characters.'
  if (!request.infrastructure.module.trim()) errors.module = 'Approved module is required.'
  else if (request.infrastructure.module.length > 128) errors.module = 'Use 128 characters or fewer.'
  if ((request.approval.change_record?.length || 0) > 128) errors.change_record = 'Use 128 characters or fewer.'
  if (request.description.length > 2000) errors.description = 'Use 2,000 characters or fewer.'
  else if (/[<>]/.test(request.description)) errors.description = 'Use plain text without HTML.'
  return errors
}
