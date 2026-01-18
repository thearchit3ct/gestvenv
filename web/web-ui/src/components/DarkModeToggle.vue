<template>
  <button
    @click="toggleDarkMode"
    class="dark-mode-toggle"
    :class="{ 'dark': isDark }"
    :aria-label="isDark ? 'Activer le mode clair' : 'Activer le mode sombre'"
    :title="isDark ? 'Mode clair' : 'Mode sombre'"
  >
    <transition name="fade" mode="out-in">
      <svg v-if="isDark" key="moon" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
      </svg>
      <svg v-else key="sun" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="5"></circle>
        <line x1="12" y1="1" x2="12" y2="3"></line>
        <line x1="12" y1="21" x2="12" y2="23"></line>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
        <line x1="1" y1="12" x2="3" y2="12"></line>
        <line x1="21" y1="12" x2="23" y2="12"></line>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
      </svg>
    </transition>
  </button>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

const isDark = ref(false)

const STORAGE_KEY = 'gestvenv-dark-mode'

function detectSystemPreference(): boolean {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
}

function loadSavedPreference(): boolean | null {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved !== null) {
    return saved === 'true'
  }
  return null
}

function savPreference(dark: boolean) {
  localStorage.setItem(STORAGE_KEY, String(dark))
}

function applyDarkMode(dark: boolean) {
  if (dark) {
    document.documentElement.classList.add('dark')
    document.body.classList.add('dark-mode')
  } else {
    document.documentElement.classList.remove('dark')
    document.body.classList.remove('dark-mode')
  }
}

function toggleDarkMode() {
  isDark.value = !isDark.value
  savPreference(isDark.value)
  applyDarkMode(isDark.value)
}

onMounted(() => {
  const saved = loadSavedPreference()
  isDark.value = saved !== null ? saved : detectSystemPreference()
  applyDarkMode(isDark.value)

  // Écouter les changements de préférence système
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', (e) => {
    if (loadSavedPreference() === null) {
      isDark.value = e.matches
      applyDarkMode(isDark.value)
    }
  })
})

watch(isDark, (newValue) => {
  applyDarkMode(newValue)
})
</script>

<style scoped>
.dark-mode-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: var(--bg-secondary, #f0f0f0);
  color: var(--text-primary, #333);
  cursor: pointer;
  transition: all 0.3s ease;
}

.dark-mode-toggle:hover {
  background: var(--bg-hover, #e0e0e0);
  transform: scale(1.05);
}

.dark-mode-toggle:focus {
  outline: 2px solid var(--primary-color, #4a90d9);
  outline-offset: 2px;
}

.dark-mode-toggle.dark {
  background: var(--bg-secondary-dark, #374151);
  color: var(--text-primary-dark, #f9fafb);
}

.dark-mode-toggle.dark:hover {
  background: var(--bg-hover-dark, #4b5563);
}

.icon {
  width: 20px;
  height: 20px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
