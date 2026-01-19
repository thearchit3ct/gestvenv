<template>
  <div class="card hover:shadow-lg transition-shadow duration-200">
    <div class="card-body">
      <!-- Header avec nom et statut -->
      <div class="flex items-start justify-between mb-4">
        <div class="flex-1 min-w-0">
          <h3 class="text-lg font-semibold text-gray-900 truncate">
            {{ environment.name }}
          </h3>
          <p class="text-sm text-gray-500 truncate">
            {{ environment.path }}
          </p>
        </div>
        
        <!-- Statut -->
        <div class="flex items-center ml-3">
          <div
            class="w-3 h-3 rounded-full mr-2"
            :class="getStatusColor(environment.status)"
          ></div>
          <span class="badge" :class="getStatusBadgeClass(environment.status)">
            {{ getStatusText(environment.status) }}
          </span>
        </div>
      </div>

      <!-- Informations techniques -->
      <div class="space-y-2 mb-4">
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-600">Python</span>
          <span class="font-medium text-gray-900">
            {{ environment.python_version || 'N/A' }}
          </span>
        </div>
        
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-600">Backend</span>
          <span class="font-medium text-gray-900 capitalize">
            {{ environment.backend }}
          </span>
        </div>
        
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-600">Packages</span>
          <span class="font-medium text-gray-900">
            {{ environment.package_count }}
          </span>
        </div>
        
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-600">Taille</span>
          <span class="font-medium text-gray-900">
            {{ formatSize(environment.size_mb) }}
          </span>
        </div>
      </div>

      <!-- Méta-informations -->
      <div class="flex items-center justify-between text-xs text-gray-500 mb-4 pt-3 border-t border-gray-100">
        <span>
          Créé {{ formatDate(environment.created_at) }}
        </span>
        <span v-if="environment.last_used">
          Utilisé {{ formatDate(environment.last_used) }}
        </span>
      </div>

      <!-- Badge actif -->
      <div v-if="environment.active" class="mb-4">
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <div class="w-2 h-2 bg-green-400 rounded-full mr-1.5"></div>
          Environnement actif
        </span>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-between space-x-2">
        <div class="flex space-x-2">
          <!-- Activation/Désactivation -->
          <button
            v-if="!environment.active"
            @click="$emit('activate', environment.name)"
            class="btn-primary btn-sm"
            :disabled="environment.status !== 'healthy'"
          >
            <PlayIcon class="h-3 w-3 mr-1" />
            Activer
          </button>
          
          <!-- Synchronisation -->
          <button
            @click="$emit('sync', environment.name)"
            class="btn-outline btn-sm"
            :disabled="environment.status === 'creating'"
            title="Synchroniser avec pyproject.toml"
          >
            <ArrowPathIcon class="h-3 w-3" />
          </button>
        </div>

        <div class="flex space-x-2">
          <!-- Voir les détails -->
          <router-link
            :to="`/environments/${environment.name}`"
            class="btn-outline btn-sm"
          >
            <EyeIcon class="h-3 w-3 mr-1" />
            Détails
          </router-link>
          
          <!-- Menu actions -->
          <div class="relative" ref="menuRef">
            <button
              @click="showMenu = !showMenu"
              class="btn-outline btn-sm p-1"
            >
              <EllipsisHorizontalIcon class="h-4 w-4" />
            </button>
            
            <!-- Menu déroulant -->
            <div
              v-if="showMenu"
              class="absolute right-0 mt-1 w-48 bg-white rounded-md shadow-lg border border-gray-200 z-10"
            >
              <div class="py-1">
                <button
                  @click="openTerminal"
                  class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <CommandLineIcon class="h-4 w-4 inline mr-2" />
                  Ouvrir terminal
                </button>
                
                <router-link
                  :to="`/environments/${environment.name}`"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  @click="showMenu = false"
                >
                  <FolderOpenIcon class="h-4 w-4 inline mr-2" />
                  Gérer packages
                </router-link>
                
                <button
                  @click="exportEnvironment"
                  class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <ArrowDownTrayIcon class="h-4 w-4 inline mr-2" />
                  Exporter
                </button>
                
                <div class="border-t border-gray-100"></div>
                
                <button
                  @click="deleteEnvironment"
                  class="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <TrashIcon class="h-4 w-4 inline mr-2" />
                  Supprimer
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  PlayIcon,
  ArrowPathIcon,
  EyeIcon,
  EllipsisHorizontalIcon,
  CommandLineIcon,
  FolderOpenIcon,
  ArrowDownTrayIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import type { Environment } from '@/types'

// Props
interface Props {
  environment: Environment
}

const props = defineProps<Props>()

// Events
const emit = defineEmits<{
  activate: [name: string]
  sync: [name: string]
  delete: [name: string]
}>()

// State
const showMenu = ref(false)
const menuRef = ref<HTMLElement>()

// Methods
function getStatusColor(status: string) {
  switch (status) {
    case 'healthy': return 'bg-green-400'
    case 'warning': return 'bg-yellow-400'
    case 'error': return 'bg-red-400'
    case 'creating': return 'bg-blue-400'
    default: return 'bg-gray-400'
  }
}

function getStatusBadgeClass(status: string) {
  switch (status) {
    case 'healthy': return 'badge-success'
    case 'warning': return 'badge-warning'
    case 'error': return 'badge-danger'
    case 'creating': return 'badge-primary'
    default: return 'badge-gray'
  }
}

function getStatusText(status: string) {
  switch (status) {
    case 'healthy': return 'Sain'
    case 'warning': return 'Attention'
    case 'error': return 'Erreur'
    case 'creating': return 'Création'
    default: return 'Inconnu'
  }
}

function formatSize(sizeMb: number) {
  if (sizeMb < 1024) {
    return `${sizeMb.toFixed(1)} MB`
  }
  return `${(sizeMb / 1024).toFixed(1)} GB`
}

function formatDate(dateString: string) {
  try {
    return formatDistanceToNow(new Date(dateString), { 
      addSuffix: true, 
      locale: fr 
    })
  } catch {
    return 'Date invalide'
  }
}

function openTerminal() {
  // TODO: Implémenter l'ouverture du terminal
  console.log('Opening terminal for environment:', props.environment.name)
  showMenu.value = false
}

function exportEnvironment() {
  // TODO: Implémenter l'export d'environnement
  console.log('Exporting environment:', props.environment.name)
  showMenu.value = false
}

function deleteEnvironment() {
  emit('delete', props.environment.name)
  showMenu.value = false
}

// Click outside handler
function handleClickOutside(event: Event) {
  if (menuRef.value && !menuRef.value.contains(event.target as Node)) {
    showMenu.value = false
  }
}

// Lifecycle
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>