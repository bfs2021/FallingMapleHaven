import test from 'node:test'
import assert from 'node:assert/strict'

import { findAdminPluginByType } from './adminPlugins.js'

test('findAdminPluginByType reads the wrapped admin plugin payload', () => {
  const response = {
    code: 0,
    message: 'success',
    data: {
      total: 1,
      page: 1,
      page_size: 20,
      results: [
        { id: 3, type: 'relation_match', is_active: false },
      ],
    },
  }

  assert.deepEqual(findAdminPluginByType(response, 'relation_match'), response.data.results[0])
})
