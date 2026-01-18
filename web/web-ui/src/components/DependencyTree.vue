<template>
  <div class="dependency-tree" role="tree" :aria-label="ariaLabel">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>Chargement des dépendances...</span>
    </div>

    <div v-else-if="error" class="error-state">
      <span class="error-icon">⚠️</span>
      <span>{{ error }}</span>
      <button @click="$emit('retry')" class="retry-btn">Réessayer</button>
    </div>

    <div v-else-if="!dependencies.length" class="empty-state">
      <span>Aucune dépendance trouvée</span>
    </div>

    <template v-else>
      <div class="tree-controls">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Rechercher un package..."
          class="search-input"
          aria-label="Rechercher dans les dépendances"
        />
        <div class="level-filter">
          <label>Niveau max:</label>
          <select v-model="maxLevel" aria-label="Niveau de profondeur">
            <option :value="0">Tous</option>
            <option :value="1">1</option>
            <option :value="2">2</option>
            <option :value="3">3</option>
            <option :value="4">4</option>
          </select>
        </div>
        <button @click="expandAll" class="control-btn" title="Tout développer">
          <span>+</span>
        </button>
        <button @click="collapseAll" class="control-btn" title="Tout réduire">
          <span>−</span>
        </button>
      </div>

      <ul class="tree-root" role="group">
        <DependencyNode
          v-for="dep in filteredDependencies"
          :key="dep.name"
          :dependency="dep"
          :level="0"
          :max-level="maxLevel"
          :search-query="searchQuery"
          :expanded-nodes="expandedNodes"
          @toggle="toggleNode"
          @select="selectNode"
        />
      </ul>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import DependencyNode from './DependencyNode.vue'

export interface Dependency {
  name: string
  version: string
  required_version?: string
  dependencies?: Dependency[]
  is_dev?: boolean
  license?: string
}

interface Props {
  dependencies: Dependency[]
  loading?: boolean
  error?: string
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: '',
  ariaLabel: 'Arbre des dépendances'
})

const emit = defineEmits<{
  (e: 'select', dep: Dependency): void
  (e: 'retry'): void
}>()

const searchQuery = ref('')
const maxLevel = ref(0)
const expandedNodes = ref<Set<string>>(new Set())

const filteredDependencies = computed(() => {
  if (!searchQuery.value) {
    return props.dependencies
  }

  const query = searchQuery.value.toLowerCase()
  return filterDependencies(props.dependencies, query)
})

function filterDependencies(deps: Dependency[], query: string): Dependency[] {
  return deps.filter(dep => {
    const matches = dep.name.toLowerCase().includes(query)
    const childMatches = dep.dependencies?.some(child =>
      child.name.toLowerCase().includes(query) ||
      filterDependencies(child.dependencies || [], query).length > 0
    )
    return matches || childMatches
  }).map(dep => ({
    ...dep,
    dependencies: dep.dependencies ? filterDependencies(dep.dependencies, query) : []
  }))
}

function toggleNode(name: string) {
  if (expandedNodes.value.has(name)) {
    expandedNodes.value.delete(name)
  } else {
    expandedNodes.value.add(name)
  }
  expandedNodes.value = new Set(expandedNodes.value)
}

function selectNode(dep: Dependency) {
  emit('select', dep)
}

function expandAll() {
  const allNodes = collectAllNodes(props.dependencies)
  expandedNodes.value = new Set(allNodes)
}

function collapseAll() {
  expandedNodes.value = new Set()
}

function collectAllNodes(deps: Dependency[], result: string[] = []): string[] {
  for (const dep of deps) {
    result.push(dep.name)
    if (dep.dependencies) {
      collectAllNodes(dep.dependencies, result)
    }
  }
  return result
}

watch(() => props.dependencies, () => {
  // Développer le premier niveau par défaut
  if (props.dependencies.length) {
    const firstLevel = props.dependencies.map(d => d.name)
    expandedNodes.value = new Set(firstLevel)
  }
}, { immediate: true })
</script>

<style scoped>
.dependency-tree {
  font-family: var(--font-mono, monospace);
  font-size: 14px;
  padding: 16px;
  background: var(--bg-primary, #fff);
  border-radius: 8px;
  border: 1px solid var(--border-color, #e0e0e0);
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: var(--text-secondary, #666);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--primary-color, #4a90d9);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  color: var(--error-color, #dc3545);
}

.retry-btn {
  padding: 8px 16px;
  background: var(--primary-color, #4a90d9);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.retry-btn:hover {
  opacity: 0.9;
}

.tree-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.search-input {
  flex: 1;
  min-width: 200px;
  padding: 8px 12px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 4px;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-color, #4a90d9);
}

.level-filter {
  display: flex;
  align-items: center;
  gap: 8px;
}

.level-filter select {
  padding: 6px 12px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 4px;
}

.control-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 4px;
  background: var(--bg-secondary, #f5f5f5);
  cursor: pointer;
  font-size: 18px;
  font-weight: bold;
}

.control-btn:hover {
  background: var(--bg-hover, #e8e8e8);
}

.tree-root {
  list-style: none;
  padding: 0;
  margin: 0;
}

/* Dark mode */
:global(.dark-mode) .dependency-tree {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .search-input,
:global(.dark-mode) .level-filter select {
  background: var(--bg-secondary-dark, #374151);
  border-color: var(--border-color-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .control-btn {
  background: var(--bg-secondary-dark, #374151);
  border-color: var(--border-color-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}
</style>
