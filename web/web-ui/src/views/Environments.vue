<template>
  <div class="space-y-6">
    <!-- Header avec filtres et actions -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Environnements</h1>
        <p class="mt-2 text-gray-600">
          Gérez vos environnements virtuels Python
        </p>
      </div>
      
      <div class="flex items-center space-x-3">
        <button
          @click="refreshEnvironments"
          class="btn-outline"
          :disabled="loading"
        >
          <ArrowPathIcon class="h-4 w-4 mr-2" :class="{ 'animate-spin': loading }" />
          Actualiser
        </button>
        <button
          @click="showCreateModal = true"
          class="btn-primary"
        >
          <PlusIcon class="h-4 w-4 mr-2" />
          Créer un environnement
        </button>
      </div>
    </div>

    <!-- Filtres et recherche -->
    <div class="card">
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <!-- Recherche -->
          <div class="md:col-span-2">
            <label class="form-label">Rechercher</label>
            <div class="relative">
              <MagnifyingGlassIcon class="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                v-model="searchQuery"
                type="text"
                class="form-input pl-10"
                placeholder="Nom ou chemin d'environnement..."
              />
            </div>
          </div>

          <!-- Filtre backend -->
          <div>
            <label class="form-label">Backend</label>
            <select v-model="selectedBackend" class="form-input">
              <option value="">Tous les backends</option>
              <option value="pip">pip</option>
              <option value="uv">uv</option>
              <option value="poetry">poetry</option>
              <option value="pdm">pdm</option>
            </select>
          </div>

          <!-- Filtre statut -->
          <div>
            <label class="form-label">Statut</label>
            <select v-model="selectedStatus" class="form-input">
              <option value="">Tous les statuts</option>
              <option value="healthy">Sain</option>
              <option value="warning">Attention</option>
              <option value="error">Erreur</option>
              <option value="creating">En création</option>
            </select>
          </div>
        </div>

        <!-- Tri -->
        <div class="mt-4 flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-600">Trier par :</span>
            <select v-model="sortField" class="form-input w-auto">
              <option value="name">Nom</option>
              <option value="created">Date de création</option>
              <option value="used">Dernière utilisation</option>
              <option value="size">Taille</option>
            </select>
            <button
              @click="toggleSortDirection"
              class="btn-outline btn-sm"
            >
              <ChevronUpIcon v-if="sortDirection === 'asc'" class="h-4 w-4" />
              <ChevronDownIcon v-else class="h-4 w-4" />
            </button>
          </div>

          <div class="flex items-center space-x-2">
            <span class="text-sm text-gray-600">
              {{ filteredEnvironments.length }} environnement(s)
            </span>
            <button
              v-if="hasFilters"
              @click="clearFilters"
              class="text-sm text-primary-600 hover:text-primary-500"
            >
              Effacer les filtres
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Liste des environnements -->
    <div v-if="loading && environments.length === 0" class="flex justify-center py-12">
      <div class="loading"></div>
    </div>

    <div v-else-if="filteredEnvironments.length === 0" class="card">
      <div class="card-body text-center py-12">
        <ServerIcon class="mx-auto h-16 w-16 text-gray-400" />
        <h3 class="mt-4 text-lg font-medium text-gray-900">
          {{ hasFilters ? 'Aucun résultat' : 'Aucun environnement' }}
        </h3>
        <p class="mt-2 text-gray-600">
          {{ hasFilters 
            ? 'Aucun environnement ne correspond à vos critères de recherche.' 
            : 'Commencez par créer votre premier environnement virtuel.'
          }}
        </p>
        <div class="mt-6">
          <button
            v-if="hasFilters"
            @click="clearFilters"
            class="btn-outline mr-3"
          >
            Effacer les filtres
          </button>
          <button
            @click="showCreateModal = true"
            class="btn-primary"
          >
            <PlusIcon class="h-4 w-4 mr-2" />
            Créer un environnement
          </button>
        </div>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
      <EnvironmentCard
        v-for="environment in filteredEnvironments"
        :key="environment.name"
        :environment="environment"
        @activate="activateEnvironment"
        @delete="deleteEnvironment"
        @sync="syncEnvironment"
      />
    </div>

    <!-- Modal de création -->
    <CreateEnvironmentModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="onEnvironmentCreated"
    />

    <!-- Modal de confirmation de suppression -->
    <ConfirmDeleteModal
      v-if="environmentToDelete"
      :environment-name="environmentToDelete"
      @confirm="confirmDelete"
      @cancel="environmentToDelete = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  PlusIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  ServerIcon
} from '@heroicons/vue/24/outline'

// Components
import EnvironmentCard from '@/components/environments/EnvironmentCard.vue'
import CreateEnvironmentModal from '@/components/environments/CreateEnvironmentModal.vue'
import ConfirmDeleteModal from '@/components/environments/ConfirmDeleteModal.vue'

// Stores
import { useEnvironmentsStore } from '@/stores/environments'

// State
const showCreateModal = ref(false)
const environmentToDelete = ref<string | null>(null)
const searchQuery = ref('')
const selectedBackend = ref('')
const selectedStatus = ref('')
const sortField = ref('name')
const sortDirection = ref<'asc' | 'desc'>('asc')

// Store
const environmentsStore = useEnvironmentsStore()

// Computed
const environments = computed(() => environmentsStore.environments)
const loading = computed(() => environmentsStore.loading)
const error = computed(() => environmentsStore.error)

const filteredEnvironments = computed(() => {
  let result = [...environments.value]

  // Filtre de recherche
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(env => 
      env.name.toLowerCase().includes(query) ||
      env.path.toLowerCase().includes(query)
    )
  }

  // Filtre backend
  if (selectedBackend.value) {
    result = result.filter(env => env.backend === selectedBackend.value)
  }

  // Filtre statut
  if (selectedStatus.value) {
    result = result.filter(env => env.status === selectedStatus.value)
  }

  // Tri
  result.sort((a, b) => {
    let aVal: any, bVal: any
    
    switch (sortField.value) {
      case 'created':
        aVal = new Date(a.created_at).getTime()
        bVal = new Date(b.created_at).getTime()
        break
      case 'used':
        aVal = a.last_used ? new Date(a.last_used).getTime() : 0
        bVal = b.last_used ? new Date(b.last_used).getTime() : 0
        break
      case 'size':
        aVal = a.size_mb
        bVal = b.size_mb
        break
      default: // name
        aVal = a.name.toLowerCase()
        bVal = b.name.toLowerCase()
    }

    if (sortDirection.value === 'desc') {
      return aVal < bVal ? 1 : aVal > bVal ? -1 : 0
    } else {
      return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
    }
  })

  return result
})

const hasFilters = computed(() => {
  return searchQuery.value || selectedBackend.value || selectedStatus.value
})

// Methods
async function refreshEnvironments() {
  await environmentsStore.fetchEnvironments()
}

function toggleSortDirection() {
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
}

function clearFilters() {
  searchQuery.value = ''
  selectedBackend.value = ''
  selectedStatus.value = ''
}

async function activateEnvironment(name: string) {
  try {
    await environmentsStore.activateEnvironment(name)
  } catch (error) {
    console.error('Failed to activate environment:', error)
  }
}

function deleteEnvironment(name: string) {
  environmentToDelete.value = name
}

async function confirmDelete(force = false) {
  if (!environmentToDelete.value) return
  
  try {
    await environmentsStore.deleteEnvironment(environmentToDelete.value, force)
    environmentToDelete.value = null
  } catch (error) {
    console.error('Failed to delete environment:', error)
  }
}

async function syncEnvironment(name: string) {
  try {
    await environmentsStore.syncEnvironment(name)
  } catch (error) {
    console.error('Failed to sync environment:', error)
  }
}

function onEnvironmentCreated() {
  showCreateModal.value = false
  refreshEnvironments()
}

// Watchers pour les filtres
watch([searchQuery, selectedBackend, selectedStatus], () => {
  environmentsStore.setFilters({
    search: searchQuery.value,
    backend: selectedBackend.value as any,
    status: selectedStatus.value as any
  })
})

watch([sortField, sortDirection], () => {
  environmentsStore.setSort({
    field: sortField.value as any,
    direction: sortDirection.value
  })
})

// Lifecycle
onMounted(() => {
  environmentsStore.initialize()
})
</script>