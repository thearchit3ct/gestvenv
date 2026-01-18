<template>
  <li
    class="dependency-node"
    :class="{ 'has-children': hasChildren, 'expanded': isExpanded, 'highlighted': isHighlighted }"
    role="treeitem"
    :aria-expanded="hasChildren ? isExpanded : undefined"
    :aria-level="level + 1"
  >
    <div class="node-content" @click="handleClick" @keydown.enter="handleClick" tabindex="0">
      <button
        v-if="hasChildren"
        class="expand-btn"
        @click.stop="toggle"
        :aria-label="isExpanded ? 'Réduire' : 'Développer'"
      >
        <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
      <span v-else class="no-children-spacer"></span>

      <span class="package-icon" :class="iconClass">📦</span>

      <span class="package-name" :class="{ 'dev': dependency.is_dev }">
        {{ dependency.name }}
      </span>

      <span class="package-version">
        {{ dependency.version }}
        <span v-if="dependency.required_version && dependency.required_version !== dependency.version" class="required-version">
          (requis: {{ dependency.required_version }})
        </span>
      </span>

      <span v-if="dependency.license" class="package-license">
        {{ dependency.license }}
      </span>

      <span v-if="dependency.is_dev" class="dev-badge">DEV</span>
    </div>

    <transition name="slide">
      <ul v-if="hasChildren && isExpanded && shouldShowChildren" class="children" role="group">
        <DependencyNode
          v-for="child in dependency.dependencies"
          :key="child.name"
          :dependency="child"
          :level="level + 1"
          :max-level="maxLevel"
          :search-query="searchQuery"
          :expanded-nodes="expandedNodes"
          @toggle="$emit('toggle', $event)"
          @select="$emit('select', $event)"
        />
      </ul>
    </transition>
  </li>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Dependency {
  name: string
  version: string
  required_version?: string
  dependencies?: Dependency[]
  is_dev?: boolean
  license?: string
}

interface Props {
  dependency: Dependency
  level: number
  maxLevel: number
  searchQuery: string
  expandedNodes: Set<string>
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'toggle', name: string): void
  (e: 'select', dep: Dependency): void
}>()

const hasChildren = computed(() => {
  return props.dependency.dependencies && props.dependency.dependencies.length > 0
})

const isExpanded = computed(() => {
  return props.expandedNodes.has(props.dependency.name)
})

const shouldShowChildren = computed(() => {
  if (props.maxLevel === 0) return true
  return props.level < props.maxLevel
})

const isHighlighted = computed(() => {
  if (!props.searchQuery) return false
  return props.dependency.name.toLowerCase().includes(props.searchQuery.toLowerCase())
})

const iconClass = computed(() => {
  if (props.dependency.is_dev) return 'dev'
  if (props.level === 0) return 'root'
  return ''
})

function toggle() {
  emit('toggle', props.dependency.name)
}

function handleClick() {
  emit('select', props.dependency)
}
</script>

<style scoped>
.dependency-node {
  margin: 2px 0;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.node-content:hover {
  background: var(--bg-hover, rgba(0, 0, 0, 0.05));
}

.node-content:focus {
  outline: 2px solid var(--primary-color, #4a90d9);
  outline-offset: 1px;
}

.highlighted .node-content {
  background: var(--highlight-bg, rgba(74, 144, 217, 0.15));
}

.expand-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-secondary, #666);
  transition: transform 0.2s ease;
}

.expand-btn:hover {
  color: var(--text-primary, #333);
}

.expanded > .node-content .expand-btn {
  transform: rotate(90deg);
}

.chevron {
  width: 16px;
  height: 16px;
}

.no-children-spacer {
  width: 20px;
}

.package-icon {
  font-size: 14px;
}

.package-icon.root {
  filter: hue-rotate(45deg);
}

.package-icon.dev {
  filter: grayscale(0.5);
}

.package-name {
  font-weight: 500;
  color: var(--text-primary, #333);
}

.package-name.dev {
  color: var(--text-secondary, #666);
}

.package-version {
  color: var(--text-secondary, #666);
  font-size: 13px;
}

.required-version {
  color: var(--warning-color, #f59e0b);
  font-size: 12px;
}

.package-license {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--bg-secondary, #f0f0f0);
  border-radius: 4px;
  color: var(--text-secondary, #666);
}

.dev-badge {
  font-size: 10px;
  padding: 2px 6px;
  background: var(--info-color, #3b82f6);
  color: white;
  border-radius: 4px;
  font-weight: 600;
}

.children {
  list-style: none;
  padding-left: 24px;
  margin: 0;
  border-left: 1px dashed var(--border-color, #e0e0e0);
  margin-left: 10px;
}

/* Animations */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
}

.slide-enter-to,
.slide-leave-from {
  opacity: 1;
  max-height: 1000px;
}

/* Dark mode */
:global(.dark-mode) .node-content:hover {
  background: var(--bg-hover-dark, rgba(255, 255, 255, 0.05));
}

:global(.dark-mode) .package-name {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .package-version,
:global(.dark-mode) .package-license {
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .package-license {
  background: var(--bg-secondary-dark, #374151);
}

:global(.dark-mode) .children {
  border-color: var(--border-color-dark, #4b5563);
}
</style>
