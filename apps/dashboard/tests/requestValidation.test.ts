import assert from 'node:assert/strict'
import { test } from 'node:test'
import { validateRequest, type RequestDraft } from '../src/requestValidation.ts'

const valid: RequestDraft = {
  cloud: 'aws', environment: 'sandbox', requester: 'engineer@example.com',
  cost_center: 'CC-123', description: 'Private network',
  application: { name: 'sample-api', repository: 'https://github.com/example/sample-api' },
  infrastructure: { region: 'us-east-1', module: 'sandbox-api' },
  approval: { required: true, change_record: null },
}

test('valid request has no field errors', () => {
  assert.deepEqual(validateRequest(valid), {})
})

test('missing target and cost center show field errors', () => {
  const errors = validateRequest({ ...valid, cloud: '', environment: '', cost_center: '',
    infrastructure: { region: '', module: '' } })
  assert.deepEqual(Object.keys(errors).sort(), ['cloud', 'cost_center', 'environment', 'module', 'region'])
})

test('HTML and oversized descriptions are rejected', () => {
  assert.match(validateRequest({ ...valid, description: '<script>alert(1)</script>' }).description || '', /plain text/)
  assert.match(validateRequest({ ...valid, description: 'x'.repeat(2001) }).description || '', /2,000/)
})

test('client bounds match the control-plane contract', () => {
  const errors = validateRequest({ ...valid, cost_center: 'X',
    infrastructure: { region: 'a', module: 'm'.repeat(129) },
    approval: { required: true, change_record: 'c'.repeat(129) } })
  assert.deepEqual(Object.keys(errors).sort(), ['change_record', 'cost_center', 'module', 'region'])
})
