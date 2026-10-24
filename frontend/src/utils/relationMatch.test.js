import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildRelationMatchDimensionInsight,
  formatRelationMatchTendency,
  isOwnRelationMatchShare,
} from './relationMatch.js'

test('formatRelationMatchTendency maps compare directions', () => {
  assert.equal(formatRelationMatchTendency('a'), 'A 方更高')
  assert.equal(formatRelationMatchTendency('b'), 'B 方更高')
  assert.equal(formatRelationMatchTendency('equal'), '双方持平')
})

test('buildRelationMatchDimensionInsight mentions shared gap and tendency', () => {
  const text = buildRelationMatchDimensionInsight({
    label: '主导',
    shared: 7,
    gap: 2,
    tendency: 'a',
  })

  assert.match(text, /共同值为 7\/10/)
  assert.match(text, /差值为 2\/10/)
  assert.match(text, /A 方更高/)
})

test('isOwnRelationMatchShare only matches the visitor own share code', () => {
  const myData = { has_profile: true, profile: { share_code: '030926' } }
  assert.equal(isOwnRelationMatchShare(myData, '030926'), true)
  assert.equal(isOwnRelationMatchShare(myData, '119305'), false)
  assert.equal(isOwnRelationMatchShare(myData, ''), false)
  assert.equal(isOwnRelationMatchShare({ has_profile: false, profile: null }, '030926'), false)
  assert.equal(isOwnRelationMatchShare(null, '030926'), false)
})
