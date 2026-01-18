<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="shortcuts-modal" @click.self="close" role="dialog" aria-modal="true" aria-labelledby="shortcuts-title">
        <div class="shortcuts-content" ref="contentRef">
          <div class="shortcuts-header">
            <h2 id="shortcuts-title">Raccourcis clavier</h2>
            <button @click="close" class="close-btn" aria-label="Fermer">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          <div class="shortcuts-body">
            <div v-for="group in shortcutGroups" :key="group.name" class="shortcut-group">
              <h3 class="group-title">{{ group.name }}</h3>
              <div class="shortcut-list">
                <div v-for="shortcut in group.shortcuts" :key="shortcut.keys" class="shortcut-item">
                  <span class="shortcut-description">{{ shortcut.description }}</span>
                  <span class="shortcut-keys">
                    <kbd v-for="(key, index) in parseKeys(shortcut.keys)" :key="index" class="key">
                      {{ key }}
                    </kbd>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="shortcuts-footer">
            <span class="hint">Appuyez sur <kbd class="key">?</kbd> pour afficher ce menu</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'

interface Shortcut {
  keys: string
  description: string
  action: () => void
}

interface ShortcutGroup {
  name: string
  shortcuts: Shortcut[]
}

interface Props {
  visible?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  visible: false
})

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'close'): void
}>()

const router = useRouter()
const contentRef = ref<HTMLElement>()

const shortcutGroups: ShortcutGroup[] = [
  {
    name: 'Navigation',
    shortcuts: [
      { keys: 'g h', description: 'Aller au Dashboard', action: () => router.push('/') },
      { keys: 'g e', description: 'Aller aux Environnements', action: () => router.push('/environments') },
      { keys: 'g p', description: 'Aller aux Packages', action: () => router.push('/packages') },
      { keys: 'g t', description: 'Aller aux Templates', action: () => router.push('/templates') },
      { keys: 'g c', description: 'Aller au Cache', action: () => router.push('/cache') },
      { keys: 'g s', description: 'Aller aux Paramètres', action: () => router.push('/settings') }
    ]
  },
  {
    name: 'Actions',
    shortcuts: [
      { keys: 'n', description: 'Nouvel environnement', action: () => emit('close') },
      { keys: 'r', description: 'Rafraîchir', action: () => window.location.reload() },
      { keys: '/', description: 'Rechercher', action: focusSearch },
      { keys: 'Escape', description: 'Fermer le modal', action: close }
    ]
  },
  {
    name: 'Général',
    shortcuts: [
      { keys: '?', description: 'Afficher l\'aide', action: () => emit('update:visible', true) },
      { keys: 'Ctrl+k', description: 'Palette de commandes', action: openCommandPalette },
      { keys: 'Ctrl+Shift+d', description: 'Mode sombre', action: toggleDarkMode }
    ]
  }
]

let keySequence = ''
let sequenceTimeout: ReturnType<typeof setTimeout> | null = null

function handleKeyDown(event: KeyboardEvent) {
  // Ignorer si on est dans un input
  const target = event.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
    if (event.key === 'Escape') {
      (target as HTMLInputElement).blur()
    }
    return
  }

  // Gérer ? pour ouvrir l'aide
  if (event.key === '?' && !event.ctrlKey && !event.metaKey) {
    event.preventDefault()
    emit('update:visible', !props.visible)
    return
  }

  // Gérer Escape pour fermer
  if (event.key === 'Escape' && props.visible) {
    close()
    return
  }

  // Construire la séquence de touches
  if (sequenceTimeout) {
    clearTimeout(sequenceTimeout)
  }

  const key = getKeyString(event)
  keySequence += (keySequence ? ' ' : '') + key

  // Chercher un raccourci correspondant
  for (const group of shortcutGroups) {
    for (const shortcut of group.shortcuts) {
      if (shortcut.keys === keySequence) {
        event.preventDefault()
        shortcut.action()
        keySequence = ''
        return
      }
    }
  }

  // Reset après 1 seconde
  sequenceTimeout = setTimeout(() => {
    keySequence = ''
  }, 1000)
}

function getKeyString(event: KeyboardEvent): string {
  let key = ''

  if (event.ctrlKey || event.metaKey) key += 'Ctrl+'
  if (event.shiftKey) key += 'Shift+'
  if (event.altKey) key += 'Alt+'

  // Normaliser la touche
  switch (event.key) {
    case ' ':
      key += 'Space'
      break
    case 'ArrowUp':
      key += '↑'
      break
    case 'ArrowDown':
      key += '↓'
      break
    case 'ArrowLeft':
      key += '←'
      break
    case 'ArrowRight':
      key += '→'
      break
    default:
      key += event.key.length === 1 ? event.key.toLowerCase() : event.key
  }

  return key
}

function parseKeys(keys: string): string[] {
  return keys.split(/(?<!Ctrl|Shift|Alt)\+| /).filter(Boolean).map(key => {
    // Afficher les symboles pour les modificateurs
    switch (key) {
      case 'Ctrl': return navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'
      case 'Shift': return '⇧'
      case 'Alt': return navigator.platform.includes('Mac') ? '⌥' : 'Alt'
      case 'Escape': return 'Esc'
      default: return key.charAt(0).toUpperCase() + key.slice(1)
    }
  })
}

function close() {
  emit('update:visible', false)
  emit('close')
}

function focusSearch() {
  const searchInput = document.querySelector('input[type="search"], input[placeholder*="Rechercher"]') as HTMLInputElement
  if (searchInput) {
    searchInput.focus()
  }
}

function openCommandPalette() {
  // À implémenter avec une palette de commandes
  console.log('Command palette opened')
}

function toggleDarkMode() {
  document.documentElement.classList.toggle('dark')
  document.body.classList.toggle('dark-mode')
}

watch(() => props.visible, (visible) => {
  if (visible) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
  if (sequenceTimeout) {
    clearTimeout(sequenceTimeout)
  }
})
</script>

<style scoped>
.shortcuts-modal {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.shortcuts-content {
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  background: var(--bg-primary, #fff);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.shortcuts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.shortcuts-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #333);
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: var(--bg-secondary, #f0f0f0);
  cursor: pointer;
  color: var(--text-secondary, #666);
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: var(--bg-hover, #e0e0e0);
  color: var(--text-primary, #333);
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

.shortcuts-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.shortcut-group {
  margin-bottom: 24px;
}

.shortcut-group:last-child {
  margin-bottom: 0;
}

.group-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary, #666);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shortcut-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--bg-secondary, #f8f9fa);
  border-radius: 8px;
}

.shortcut-description {
  color: var(--text-primary, #333);
  font-size: 14px;
}

.shortcut-keys {
  display: flex;
  gap: 4px;
}

.key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #d0d0d0);
  border-radius: 6px;
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary, #333);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.shortcuts-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color, #e0e0e0);
  text-align: center;
}

.hint {
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.hint .key {
  margin: 0 4px;
  vertical-align: middle;
}

/* Animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-active .shortcuts-content,
.modal-leave-active .shortcuts-content {
  transition: transform 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .shortcuts-content,
.modal-leave-to .shortcuts-content {
  transform: scale(0.95);
}

/* Dark mode */
:global(.dark-mode) .shortcuts-content {
  background: var(--bg-primary-dark, #1f2937);
}

:global(.dark-mode) .shortcuts-header {
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .shortcuts-header h2 {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .close-btn {
  background: var(--bg-secondary-dark, #374151);
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .close-btn:hover {
  background: var(--bg-hover-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .group-title {
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .shortcut-item {
  background: var(--bg-secondary-dark, #374151);
}

:global(.dark-mode) .shortcut-description {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .key {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .shortcuts-footer {
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .hint {
  color: var(--text-secondary-dark, #9ca3af);
}
</style>
