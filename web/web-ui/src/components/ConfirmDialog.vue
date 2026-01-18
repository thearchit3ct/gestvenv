<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div
        v-if="visible"
        class="confirm-dialog-overlay"
        @click.self="handleCancel"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="descriptionId"
      >
        <div class="confirm-dialog" :class="[variant]" ref="dialogRef">
          <div class="dialog-icon" v-if="showIcon">
            <component :is="iconComponent" />
          </div>

          <h2 :id="titleId" class="dialog-title">{{ title }}</h2>

          <p :id="descriptionId" class="dialog-message">{{ message }}</p>

          <div v-if="details" class="dialog-details">
            <slot name="details">{{ details }}</slot>
          </div>

          <div v-if="showInput" class="dialog-input">
            <label :for="inputId">{{ inputLabel }}</label>
            <input
              :id="inputId"
              v-model="inputValue"
              :type="inputType"
              :placeholder="inputPlaceholder"
              ref="inputRef"
              @keydown.enter="handleConfirm"
            />
            <span v-if="inputHint" class="input-hint">{{ inputHint }}</span>
          </div>

          <div class="dialog-actions">
            <button
              @click="handleCancel"
              class="btn btn-cancel"
              :disabled="loading"
            >
              {{ cancelText }}
            </button>
            <button
              @click="handleConfirm"
              class="btn btn-confirm"
              :class="[`btn-${variant}`]"
              :disabled="loading || (showInput && !isInputValid)"
              ref="confirmBtnRef"
            >
              <span v-if="loading" class="spinner"></span>
              <span>{{ confirmText }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, h } from 'vue'

type DialogVariant = 'danger' | 'warning' | 'info'

interface Props {
  visible: boolean
  title: string
  message: string
  details?: string
  confirmText?: string
  cancelText?: string
  variant?: DialogVariant
  loading?: boolean
  showIcon?: boolean
  showInput?: boolean
  inputLabel?: string
  inputType?: string
  inputPlaceholder?: string
  inputHint?: string
  inputValidation?: (value: string) => boolean
}

const props = withDefaults(defineProps<Props>(), {
  confirmText: 'Confirmer',
  cancelText: 'Annuler',
  variant: 'danger',
  loading: false,
  showIcon: true,
  showInput: false,
  inputLabel: '',
  inputType: 'text',
  inputPlaceholder: '',
  inputHint: '',
  inputValidation: () => true
})

const emit = defineEmits<{
  (e: 'confirm', inputValue?: string): void
  (e: 'cancel'): void
  (e: 'update:visible', value: boolean): void
}>()

const dialogRef = ref<HTMLElement>()
const inputRef = ref<HTMLInputElement>()
const confirmBtnRef = ref<HTMLButtonElement>()
const inputValue = ref('')

const titleId = computed(() => `dialog-title-${Math.random().toString(36).substr(2, 9)}`)
const descriptionId = computed(() => `dialog-desc-${Math.random().toString(36).substr(2, 9)}`)
const inputId = computed(() => `dialog-input-${Math.random().toString(36).substr(2, 9)}`)

const isInputValid = computed(() => {
  if (!props.showInput) return true
  return inputValue.value.trim() !== '' && props.inputValidation(inputValue.value)
})

const iconComponent = computed(() => {
  const icons = {
    danger: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('circle', { cx: '12', cy: '12', r: '10' }),
      h('line', { x1: '15', y1: '9', x2: '9', y2: '15' }),
      h('line', { x1: '9', y1: '9', x2: '15', y2: '15' })
    ]),
    warning: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z' }),
      h('line', { x1: '12', y1: '9', x2: '12', y2: '13' }),
      h('line', { x1: '12', y1: '17', x2: '12.01', y2: '17' })
    ]),
    info: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('circle', { cx: '12', cy: '12', r: '10' }),
      h('line', { x1: '12', y1: '16', x2: '12', y2: '12' }),
      h('line', { x1: '12', y1: '8', x2: '12.01', y2: '8' })
    ])
  }
  return icons[props.variant]
})

function handleConfirm() {
  if (props.loading || (props.showInput && !isInputValid.value)) return
  emit('confirm', props.showInput ? inputValue.value : undefined)
}

function handleCancel() {
  if (props.loading) return
  inputValue.value = ''
  emit('cancel')
  emit('update:visible', false)
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.key === 'Escape' && !props.loading) {
    handleCancel()
  }
}

watch(() => props.visible, async (visible) => {
  if (visible) {
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', handleKeyDown)
    await nextTick()
    if (props.showInput && inputRef.value) {
      inputRef.value.focus()
    } else if (confirmBtnRef.value) {
      confirmBtnRef.value.focus()
    }
  } else {
    document.body.style.overflow = ''
    document.removeEventListener('keydown', handleKeyDown)
    inputValue.value = ''
  }
})
</script>

<style scoped>
.confirm-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.confirm-dialog {
  width: 90%;
  max-width: 420px;
  padding: 24px;
  background: var(--bg-primary, #fff);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  text-align: center;
}

.dialog-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  border-radius: 50%;
}

.dialog-icon svg {
  width: 28px;
  height: 28px;
}

.danger .dialog-icon {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.warning .dialog-icon {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.info .dialog-icon {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.dialog-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #333);
}

.dialog-message {
  margin: 0 0 16px;
  font-size: 14px;
  color: var(--text-secondary, #666);
  line-height: 1.5;
}

.dialog-details {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary, #666);
  text-align: left;
}

.dialog-input {
  margin-bottom: 20px;
  text-align: left;
}

.dialog-input label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #333);
}

.dialog-input input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.dialog-input input:focus {
  outline: none;
  border-color: var(--primary-color, #4a90d9);
  box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.1);
}

.input-hint {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-secondary, #666);
}

.dialog-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn {
  flex: 1;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  background: var(--bg-secondary, #f0f0f0);
  color: var(--text-primary, #333);
}

.btn-cancel:hover:not(:disabled) {
  background: var(--bg-hover, #e0e0e0);
}

.btn-confirm {
  color: white;
}

.btn-danger {
  background: #ef4444;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}

.btn-warning {
  background: #f59e0b;
}

.btn-warning:hover:not(:disabled) {
  background: #d97706;
}

.btn-info {
  background: #3b82f6;
}

.btn-info:hover:not(:disabled) {
  background: #2563eb;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Animations */
.dialog-enter-active,
.dialog-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-enter-active .confirm-dialog,
.dialog-leave-active .confirm-dialog {
  transition: transform 0.2s ease;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .confirm-dialog,
.dialog-leave-to .confirm-dialog {
  transform: scale(0.95) translateY(-10px);
}

/* Dark mode */
:global(.dark-mode) .confirm-dialog {
  background: var(--bg-primary-dark, #1f2937);
}

:global(.dark-mode) .dialog-title {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .dialog-message {
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .dialog-details {
  background: var(--bg-secondary-dark, #374151);
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .dialog-input label {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .dialog-input input {
  background: var(--bg-secondary-dark, #374151);
  border-color: var(--border-color-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .btn-cancel {
  background: var(--bg-secondary-dark, #374151);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .btn-cancel:hover:not(:disabled) {
  background: var(--bg-hover-dark, #4b5563);
}
</style>
