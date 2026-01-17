<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
    <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
      <div class="mt-3">
        <!-- Header -->
        <div class="flex items-center justify-between pb-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">
            Créer un nouvel environnement
          </h3>
          <button
            @click="$emit('close')"
            class="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon class="h-6 w-6" />
          </button>
        </div>

        <!-- Formulaire -->
        <form @submit.prevent="createEnvironment" class="mt-6 space-y-6">
          <!-- Nom de l'environnement -->
          <div>
            <label class="form-label">Nom de l'environnement *</label>
            <input
              v-model="form.name"
              type="text"
              class="form-input"
              placeholder="mon-environnement"
              required
            />
            <p class="mt-1 text-sm text-gray-500">
              Nom unique pour identifier l'environnement
            </p>
          </div>

          <!-- Version Python -->
          <div>
            <label class="form-label">Version Python</label>
            <select v-model="form.python_version" class="form-input">
              <option value="">Détecter automatiquement</option>
              <option value="3.12">Python 3.12</option>
              <option value="3.11">Python 3.11</option>
              <option value="3.10">Python 3.10</option>
              <option value="3.9">Python 3.9</option>
              <option value="3.8">Python 3.8</option>
            </select>
          </div>

          <!-- Backend -->
          <div>
            <label class="form-label">Backend</label>
            <select v-model="form.backend" class="form-input">
              <option value="auto">Détection automatique</option>
              <option value="uv">uv (Recommandé - Ultra rapide)</option>
              <option value="pdm">PDM (Standards modernes)</option>
              <option value="poetry">Poetry (Populaire)</option>
              <option value="pip">pip (Compatible universel)</option>
            </select>
          </div>

          <!-- Template -->
          <div>
            <div class="flex items-center space-x-3 mb-3">
              <input
                id="use-template"
                v-model="form.useTemplate"
                type="checkbox"
                class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <label for="use-template" class="form-label mb-0">
                Utiliser un template
              </label>
            </div>

            <div v-if="form.useTemplate" class="space-y-4 pl-7">
              <select v-model="form.template" class="form-input">
                <option value="">Sélectionner un template</option>
                <option value="basic">Basic - Projet Python minimal</option>
                <option value="cli">CLI - Outil en ligne de commande</option>
                <option value="web">Web - Application web générique</option>
                <option value="fastapi">FastAPI - API REST moderne</option>
                <option value="django">Django - Application web complète</option>
                <option value="data-science">Data Science - Analyse ML</option>
              </select>

              <!-- Options template -->
              <div v-if="form.template" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="form-label">Auteur</label>
                  <input
                    v-model="form.templateData.author"
                    type="text"
                    class="form-input"
                    placeholder="Votre nom"
                  />
                </div>
                <div>
                  <label class="form-label">Email</label>
                  <input
                    v-model="form.templateData.email"
                    type="email"
                    class="form-input"
                    placeholder="votre@email.com"
                  />
                </div>
                <div>
                  <label class="form-label">Version initiale</label>
                  <input
                    v-model="form.templateData.version"
                    type="text"
                    class="form-input"
                    placeholder="0.1.0"
                  />
                </div>
                <div>
                  <label class="form-label">Répertoire de sortie</label>
                  <input
                    v-model="form.templateData.output"
                    type="text"
                    class="form-input"
                    placeholder="Chemin personnalisé (optionnel)"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Packages initiaux -->
          <div v-if="!form.useTemplate">
            <label class="form-label">Packages initiaux (optionnel)</label>
            <input
              v-model="packagesInput"
              type="text"
              class="form-input"
              placeholder="requests, flask, numpy (séparés par des virgules)"
            />
            <p class="mt-1 text-sm text-gray-500">
              Packages à installer après la création de l'environnement
            </p>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-end space-x-3 pt-6 border-t border-gray-200">
            <button
              type="button"
              @click="$emit('close')"
              class="btn-outline"
              :disabled="loading"
            >
              Annuler
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="loading || !form.name"
            >
              <div v-if="loading" class="loading mr-2"></div>
              <PlusIcon v-else class="h-4 w-4 mr-2" />
              Créer l'environnement
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { XMarkIcon, PlusIcon } from '@heroicons/vue/24/outline'
import type { EnvironmentCreate } from '@/types'
import { useEnvironmentsStore } from '@/stores/environments'

// Events
const emit = defineEmits<{
  close: []
  created: [environment: any]
}>()

// State
const loading = ref(false)
const packagesInput = ref('')

const form = ref({
  name: '',
  python_version: '',
  backend: 'auto' as any,
  useTemplate: false,
  template: '',
  templateData: {
    author: '',
    email: '',
    version: '0.1.0',
    output: ''
  }
})

// Store
const environmentsStore = useEnvironmentsStore()

// Computed
const packages = computed(() => {
  if (!packagesInput.value) return []
  return packagesInput.value
    .split(',')
    .map(pkg => pkg.trim())
    .filter(pkg => pkg.length > 0)
})

// Methods
async function createEnvironment() {
  loading.value = true

  try {
    const environmentData: EnvironmentCreate = {
      name: form.value.name,
      python_version: form.value.python_version || undefined,
      backend: form.value.backend,
      packages: form.value.useTemplate ? undefined : packages.value
    }

    // Si template est utilisé, utiliser l'API de création depuis template
    if (form.value.useTemplate && form.value.template) {
      const { api } = await import('@/services/api')
      await api.createFromTemplate({
        template_name: form.value.template,
        project_name: form.value.name,
        author: form.value.templateData.author || undefined,
        email: form.value.templateData.email || undefined,
        version: form.value.templateData.version,
        python_version: form.value.python_version || undefined,
        backend: form.value.backend,
        output_path: form.value.templateData.output || undefined
      })
    } else {
      // Création normale
      await environmentsStore.createEnvironment(environmentData)
    }

    emit('created', environmentData)
  } catch (error) {
    console.error('Failed to create environment:', error)
    // L'erreur sera affichée par le store
  } finally {
    loading.value = false
  }
}
</script>