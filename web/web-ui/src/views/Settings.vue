<template>
  <div class="container mx-auto p-6">
    <div class="mb-6">
      <h1 class="text-3xl font-bold">Paramètres</h1>
      <p class="text-gray-500 mt-2">Configuration de l'application GestVenv</p>
    </div>

    <!-- Settings Tabs -->
    <div class="space-y-4">
      <div class="border-b border-gray-200">
        <nav class="-mb-px flex space-x-4" aria-label="Tabs">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            @click="activeTab = tab.value"
            :class="[
              activeTab === tab.value
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'group inline-flex items-center px-1 py-2 border-b-2 font-medium text-sm'
            ]"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <!-- General Settings -->
      <div v-if="activeTab === 'general'" class="space-y-4">
        <div class="card">
          <div class="card-header">
            <h2 class="text-xl font-semibold">Paramètres généraux</h2>
            <p class="text-sm text-gray-500 mt-1">
              Configurez les préférences générales de l'application
            </p>
          </div>
          <div class="card-body space-y-6">
            <!-- Default Python Version -->
            <div class="space-y-2">
              <label for="default-python" class="form-label">Version Python par défaut</label>
              <select
                id="default-python"
                v-model="settings.default_python_version"
                class="form-input"
              >
                <option value="3.8">Python 3.8</option>
                <option value="3.9">Python 3.9</option>
                <option value="3.10">Python 3.10</option>
                <option value="3.11">Python 3.11</option>
                <option value="3.12">Python 3.12</option>
                <option value="system">Version système</option>
              </select>
            </div>

            <!-- Default Backend -->
            <div class="space-y-2">
              <label for="default-backend" class="form-label">Backend par défaut</label>
              <select
                id="default-backend"
                v-model="settings.default_backend"
                class="form-input"
              >
                <option value="auto">Auto-détection</option>
                <option value="pip">pip</option>
                <option value="uv">uv</option>
                <option value="poetry">Poetry</option>
                <option value="pdm">PDM</option>
              </select>
            </div>

            <!-- Environments Path -->
            <div class="space-y-2">
              <label for="envs-path" class="form-label">Répertoire des environnements</label>
              <input
                id="envs-path"
                v-model="settings.environments_path"
                placeholder="~/.gestvenv/envs"
                class="form-input"
              />
              <p class="text-sm text-gray-500">
                Chemin où les environnements virtuels sont stockés
              </p>
            </div>

            <!-- Auto Activate -->
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <label class="form-label">Activation automatique</label>
                <p class="text-sm text-gray-500">
                  Active automatiquement l'environnement lors de la navigation
                </p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="settings.auto_activate" class="sr-only peer">
                <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>

            <!-- Check Updates -->
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <label class="form-label">Vérifier les mises à jour</label>
                <p class="text-sm text-gray-500">
                  Vérifie automatiquement les mises à jour de packages
                </p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="settings.check_updates" class="sr-only peer">
                <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Backend Settings -->
      <div v-if="activeTab === 'backends'" class="space-y-4">
        <div class="card">
          <div class="card-header">
            <h2 class="text-xl font-semibold">Configuration des backends</h2>
            <p class="text-sm text-gray-500 mt-1">
              Configurez les paramètres spécifiques à chaque backend
            </p>
          </div>
          <div class="card-body space-y-6">
            <!-- pip Settings -->
            <div class="space-y-4">
              <h4 class="font-medium flex items-center">
                <Package :size="16" class="mr-2" />
                pip
              </h4>
              <div class="ml-6 space-y-4">
                <div class="space-y-2">
                  <label for="pip-index" class="form-label">URL de l'index</label>
                  <input
                    id="pip-index"
                    v-model="settings.backends.pip.index_url"
                    placeholder="https://pypi.org/simple"
                    class="form-input"
                  />
                </div>
                <div class="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="pip-use-pep517"
                    v-model="settings.backends.pip.use_pep517"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label for="pip-use-pep517" class="text-sm font-medium text-gray-700">
                    Utiliser PEP 517
                  </label>
                </div>
                <div class="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="pip-no-deps"
                    v-model="settings.backends.pip.no_deps"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label for="pip-no-deps" class="text-sm font-medium text-gray-700">
                    Ne pas installer les dépendances
                  </label>
                </div>
              </div>
            </div>

            <hr class="border-gray-200" />

            <!-- uv Settings -->
            <div class="space-y-4">
              <h4 class="font-medium flex items-center">
                <Zap :size="16" class="mr-2" />
                uv
              </h4>
              <div class="ml-6 space-y-4">
                <div class="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="uv-system-python"
                    v-model="settings.backends.uv.system_python"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label for="uv-system-python" class="text-sm font-medium text-gray-700">
                    Utiliser Python système
                  </label>
                </div>
                <div class="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="uv-preview"
                    v-model="settings.backends.uv.preview"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label for="uv-preview" class="text-sm font-medium text-gray-700">
                    Activer les fonctionnalités preview
                  </label>
                </div>
              </div>
            </div>

            <hr class="border-gray-200" />

            <!-- Poetry Settings -->
            <div class="space-y-4">
              <h4 class="font-medium flex items-center">
                <BookOpen :size="16" class="mr-2" />
                Poetry
              </h4>
              <div class="ml-6 space-y-4">
                <div class="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="poetry-virtualenvs-in-project"
                    v-model="settings.backends.poetry.virtualenvs_in_project"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label for="poetry-virtualenvs-in-project" class="text-sm font-medium text-gray-700">
                    Créer les virtualenvs dans le projet
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Cache Settings -->
      <div v-if="activeTab === 'cache'" class="space-y-4">
        <div class="card">
          <div class="card-header">
            <h2 class="text-xl font-semibold">Configuration du cache</h2>
            <p class="text-sm text-gray-500 mt-1">
              Gérez les paramètres du cache de packages
            </p>
          </div>
          <div class="card-body space-y-6">
            <!-- Cache Enabled -->
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <label class="form-label">Activer le cache</label>
                <p class="text-sm text-gray-500">
                  Stocke les packages téléchargés pour une utilisation hors ligne
                </p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="settings.cache.enabled" class="sr-only peer">
                <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>

            <!-- Cache Directory -->
            <div class="space-y-2">
              <label for="cache-dir" class="form-label">Répertoire du cache</label>
              <input
                id="cache-dir"
                v-model="settings.cache.directory"
                placeholder="~/.gestvenv/cache"
                class="form-input"
              />
            </div>

            <!-- Max Cache Size -->
            <div class="space-y-2">
              <label for="cache-size" class="form-label">Taille maximale du cache (GB)</label>
              <div class="flex items-center space-x-4">
                <input
                  type="range"
                  id="cache-size"
                  v-model="settings.cache.max_size_gb"
                  :max="100"
                  :step="1"
                  class="flex-1"
                />
                <span class="w-12 text-right font-mono text-sm">
                  {{ settings.cache.max_size_gb }}GB
                </span>
              </div>
            </div>

            <!-- Cache TTL -->
            <div class="space-y-2">
              <label for="cache-ttl" class="form-label">Durée de vie du cache (jours)</label>
              <input
                id="cache-ttl"
                v-model.number="settings.cache.ttl_days"
                type="number"
                min="1"
                max="365"
                class="form-input"
              />
              <p class="text-sm text-gray-500">
                Les packages plus anciens seront automatiquement supprimés
              </p>
            </div>

            <!-- Auto Clean -->
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <label class="form-label">Nettoyage automatique</label>
                <p class="text-sm text-gray-500">
                  Nettoie automatiquement le cache lorsqu'il dépasse la taille maximale
                </p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="settings.cache.auto_clean" class="sr-only peer">
                <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Advanced Settings -->
      <div v-if="activeTab === 'advanced'" class="space-y-4">
        <div class="card">
          <div class="card-header">
            <h2 class="text-xl font-semibold">Paramètres avancés</h2>
            <p class="text-sm text-gray-500 mt-1">
              Options avancées pour les utilisateurs expérimentés
            </p>
          </div>
          <div class="card-body space-y-6">
            <!-- Parallel Operations -->
            <div class="space-y-2">
              <label for="parallel-ops" class="form-label">Opérations parallèles maximales</label>
              <input
                id="parallel-ops"
                v-model.number="settings.advanced.max_parallel_operations"
                type="number"
                min="1"
                max="10"
                class="form-input"
              />
              <p class="text-sm text-gray-500">
                Nombre maximum d'opérations pouvant s'exécuter en parallèle
              </p>
            </div>

            <!-- Log Level -->
            <div class="space-y-2">
              <label for="log-level" class="form-label">Niveau de log</label>
              <select
                id="log-level"
                v-model="settings.advanced.log_level"
                class="form-input"
              >
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
              </select>
            </div>

            <!-- Timeout -->
            <div class="space-y-2">
              <label for="timeout" class="form-label">Timeout des opérations (secondes)</label>
              <input
                id="timeout"
                v-model.number="settings.advanced.operation_timeout"
                type="number"
                min="30"
                max="3600"
                class="form-input"
              />
            </div>

            <!-- Experimental Features -->
            <div class="space-y-4">
              <h4 class="font-medium flex items-center">
                <FlaskConical :size="16" class="mr-2" />
                Fonctionnalités expérimentales
              </h4>
              <div class="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div class="flex items-start">
                  <AlertTriangle :size="16" class="mr-2 text-yellow-600 mt-0.5" />
                  <div>
                    <h4 class="text-sm font-medium text-yellow-900">Attention</h4>
                    <p class="text-sm text-yellow-700 mt-1">
                      Ces fonctionnalités sont expérimentales et peuvent être instables
                    </p>
                  </div>
                </div>
              </div>
              <div class="space-y-2">
                <div class="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="exp-fast-deps"
                    v-model="settings.advanced.experimental.fast_deps_resolution"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label for="exp-fast-deps" class="text-sm font-medium text-gray-700">
                    Résolution rapide des dépendances
                  </label>
                </div>
                <div class="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="exp-smart-cache"
                    v-model="settings.advanced.experimental.smart_cache"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label for="exp-smart-cache" class="text-sm font-medium text-gray-700">
                    Cache intelligent avec prédiction
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Reset Settings -->
        <div class="card">
          <div class="card-header">
            <h2 class="text-xl font-semibold">Réinitialiser les paramètres</h2>
            <p class="text-sm text-gray-500 mt-1">
              Restaurer tous les paramètres à leurs valeurs par défaut
            </p>
          </div>
          <div class="card-body">
            <button class="btn btn-danger" @click="showResetDialog = true">
              <RotateCcw :size="16" class="mr-2" />
              Réinitialiser tout
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Save Button -->
    <div class="fixed bottom-6 right-6">
      <button
        class="btn btn-primary btn-lg shadow-lg"
        @click="saveSettings"
        :disabled="!hasChanges || isSaving"
      >
        <Loader2 v-if="isSaving" :size="16" class="mr-2 animate-spin" />
        <Save v-else :size="16" class="mr-2" />
        {{ isSaving ? 'Enregistrement...' : 'Enregistrer' }}
      </button>
    </div>

    <!-- Reset Confirmation Dialog -->
    <div v-if="showResetDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div class="mb-4">
          <h3 class="text-lg font-semibold">Réinitialiser les paramètres</h3>
          <p class="text-sm text-gray-500 mt-1">
            Êtes-vous sûr de vouloir réinitialiser tous les paramètres à leurs valeurs par défaut ?
            Cette action ne peut pas être annulée.
          </p>
        </div>
        <div class="flex justify-end space-x-2">
          <button class="btn btn-outline" @click="showResetDialog = false">
            Annuler
          </button>
          <button class="btn btn-danger" @click="resetSettings">
            Réinitialiser
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
// Toast functionality will be implemented locally
import {
  Package,
  Zap,
  BookOpen,
  Save,
  RotateCcw,
  FlaskConical,
  AlertTriangle,
  Loader2
} from 'lucide-vue-next'
// Using custom CSS classes from style.css

// Simple toast notification function
const showToast = (options: { title: string; description?: string; variant?: string }) => {
  // For now, using console.log - can be replaced with a proper notification system
  console.log(`[${options.variant || 'info'}] ${options.title}: ${options.description || ''}`)
}

// State
const activeTab = ref('general')
const isSaving = ref(false)
const showResetDialog = ref(false)
const originalSettings = ref<any>(null)

// Tabs configuration
const tabs = [
  { value: 'general', label: 'Général' },
  { value: 'backends', label: 'Backends' },
  { value: 'cache', label: 'Cache' },
  { value: 'advanced', label: 'Avancé' }
]

// Settings model
const settings = ref({
  default_python_version: '3.11',
  default_backend: 'auto',
  environments_path: '~/.gestvenv/envs',
  auto_activate: true,
  check_updates: true,
  
  backends: {
    pip: {
      index_url: 'https://pypi.org/simple',
      use_pep517: true,
      no_deps: false
    },
    uv: {
      system_python: false,
      preview: false
    },
    poetry: {
      virtualenvs_in_project: true
    },
    pdm: {}
  },
  
  cache: {
    enabled: true,
    directory: '~/.gestvenv/cache',
    max_size_gb: 10,
    ttl_days: 30,
    auto_clean: true
  },
  
  advanced: {
    max_parallel_operations: 3,
    log_level: 'INFO',
    operation_timeout: 300,
    experimental: {
      fast_deps_resolution: false,
      smart_cache: false
    }
  }
})

// Computed
const hasChanges = computed(() => {
  return JSON.stringify(settings.value) !== JSON.stringify(originalSettings.value)
})

// Methods
const loadSettings = async () => {
  try {
    // In a real app, this would load from an API
    // For now, we'll use localStorage
    const savedSettings = localStorage.getItem('gestvenv_settings')
    if (savedSettings) {
      settings.value = JSON.parse(savedSettings)
    }
    originalSettings.value = JSON.parse(JSON.stringify(settings.value))
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: 'Impossible de charger les paramètres',
      variant: 'destructive'
    })
  }
}

const saveSettings = async () => {
  isSaving.value = true
  
  try {
    // In a real app, this would save to an API
    // For now, we'll use localStorage
    localStorage.setItem('gestvenv_settings', JSON.stringify(settings.value))
    originalSettings.value = JSON.parse(JSON.stringify(settings.value))
    
    showToast({
      title: 'Succès',
      description: 'Paramètres enregistrés'
    })
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: 'Impossible d\'enregistrer les paramètres',
      variant: 'destructive'
    })
  } finally {
    isSaving.value = false
  }
}

const resetSettings = async () => {
  try {
    // Reset to default values
    localStorage.removeItem('gestvenv_settings')
    await loadSettings()
    showResetDialog.value = false
    
    showToast({
      title: 'Succès',
      description: 'Paramètres réinitialisés'
    })
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: 'Impossible de réinitialiser les paramètres',
      variant: 'destructive'
    })
  }
}

// Lifecycle
onMounted(() => {
  loadSettings()
})
</script>