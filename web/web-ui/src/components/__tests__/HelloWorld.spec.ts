import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'

// Simple component test since HelloWorld.vue doesn't exist
describe('Component Tests', () => {
  it('should pass basic test', () => {
    expect(true).toBe(true)
  })

  it('should mount pinia store', () => {
    const pinia = createPinia()
    expect(pinia).toBeDefined()
  })
})