<template>
  <div class="container mx-auto p-6">
    <div class="mb-6">
      <h1 class="text-3xl font-bold">Templates</h1>
      <p class="text-muted-foreground mt-2">Modèles de projets pour créer rapidement des environnements</p>
    </div>

    <!-- Template Categories -->
    <div class="mb-6">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="category in categories"
          :key="category"
          class="btn btn-sm"
          :class="selectedCategory === category ? 'btn-primary' : 'btn-outline'"
          @click="selectedCategory = category"
        >
          {{ category }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div v-for="i in 6" :key="i" class="card">
        <div class="card-body p-6">
          <div class="space-y-3">
            <div class="h-6 w-3/4 bg-gray-200 rounded animate-pulse" />
            <div class="h-4 w-full bg-gray-200 rounded animate-pulse" />
            <div class="h-4 w-full bg-gray-200 rounded animate-pulse" />
            <div class="h-10 w-full bg-gray-200 rounded animate-pulse" />
          </div>
        </div>
      </div>
    </div>

    <!-- Templates Grid -->
    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="template in filteredTemplates"
        :key="template.name"
        class="card hover:shadow-lg transition-shadow"
      >
        <div class="card-header">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="text-lg font-semibold">{{ template.name }}</h3>
              <span class="badge badge-secondary mt-1">{{ template.category }}</span>
            </div>
            <component :is="getTemplateIcon(template.category)" :size="24" class="text-gray-500" />
          </div>
        </div>
        <div class="card-body">
          <p class="text-sm text-muted-foreground mb-4">
            {{ template.description }}
          </p>
          
          <!-- Dependencies Preview -->
          <div class="mb-4">
            <p class="text-sm font-medium mb-2">Dépendances principales :</p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="dep in template.dependencies.slice(0, 3)"
                :key="dep"
                class="badge badge-outline text-xs"
              >
                {{ dep }}
              </span>
              <span
                v-if="template.dependencies.length > 3"
                class="badge badge-outline text-xs"
              >
                +{{ template.dependencies.length - 3 }} autres
              </span>
            </div>
          </div>

          <!-- Files Preview -->
          <div class="mb-4">
            <p class="text-sm font-medium mb-2">Fichiers créés :</p>
            <p class="text-xs text-muted-foreground">
              {{ template.files.length }} fichier(s)
            </p>
          </div>

          <button
            class="btn btn-primary w-full"
            @click="selectTemplate(template)"
          >
            <Rocket :size="16" class="mr-2" />
            Utiliser ce template
          </button>
        </div>
      </div>
    </div>

    <!-- Create Project Dialog -->
    <div v-if="showCreateDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
        <div class="mb-4">
          <h3 class="text-lg font-semibold">Créer un projet depuis le template</h3>
          <p class="text-sm text-gray-500 mt-1">
            Configurez votre nouveau projet basé sur le template "{{ selectedTemplate?.name }}"
          </p>
        </div>
        
        <div class="space-y-4 max-h-[60vh] overflow-y-auto">
          <!-- Basic Info -->
          <div class="space-y-4">
            <div>
              <label for="project-name" class="form-label">Nom du projet *</label>
              <input
                id="project-name"
                v-model="projectConfig.project_name"
                placeholder="mon-projet"
                @input="validateProjectName"
                class="form-input"
              />
              <p v-if="projectNameError" class="text-sm text-red-500 mt-1">
                {{ projectNameError }}
              </p>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label for="author" class="form-label">Auteur</label>
                <input
                  id="author"
                  v-model="projectConfig.author"
                  placeholder="Votre nom"
                  class="form-input"
                />
              </div>
              
              <div>
                <label for="email" class="form-label">Email</label>
                <input
                  id="email"
                  v-model="projectConfig.email"
                  placeholder="email@example.com"
                  type="email"
                  class="form-input"
                />
              </div>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label for="version" class="form-label">Version</label>
                <input
                  id="version"
                  v-model="projectConfig.version"
                  placeholder="0.1.0"
                  class="form-input"
                />
              </div>
              
              <div>
                <label for="python-version" class="form-label">Version Python</label>
                <select
                  id="python-version"
                  v-model="projectConfig.python_version"
                  class="form-input"
                >
                  <option value="3.8">Python 3.8</option>
                  <option value="3.9">Python 3.9</option>
                  <option value="3.10">Python 3.10</option>
                  <option value="3.11">Python 3.11</option>
                  <option value="3.12">Python 3.12</option>
                </select>
              </div>
            </div>
            
            <div>
              <label for="backend" class="form-label">Backend</label>
              <select
                id="backend"
                v-model="projectConfig.backend"
                class="form-input"
              >
                <option value="auto">Auto-détection</option>
                <option value="pip">pip</option>
                <option value="uv">uv</option>
                <option value="poetry">Poetry</option>
                <option value="pdm">PDM</option>
              </select>
            </div>
            
            <div>
              <label for="output-path" class="form-label">Chemin de sortie</label>
              <input
                id="output-path"
                v-model="projectConfig.output_path"
                placeholder="Chemin optionnel (par défaut: répertoire courant)"
                class="form-input"
              />
            </div>
          </div>
          
          <!-- Template Variables -->
          <div v-if="selectedTemplate?.variables?.length > 0">
            <hr class="border-gray-200 my-4" />
            <h4 class="font-medium mb-3">Variables du template</h4>
            <div class="space-y-3">
              <div
                v-for="variable in selectedTemplate.variables"
                :key="variable"
              >
                <label :for="`var-${variable}`" class="form-label">
                  {{ formatVariableName(variable) }}
                </label>
                <input
                  :id="`var-${variable}`"
                  v-model="projectConfig.variables[variable]"
                  :placeholder="`Valeur pour ${variable}`"
                  class="form-input"
                />
              </div>
            </div>
          </div>
        </div>
        
        <div class="flex justify-end space-x-2 mt-6">
          <button class="btn btn-outline" @click="showCreateDialog = false">
            Annuler
          </button>
          <button
            class="btn btn-primary"
            @click="createProject"
            :disabled="!isFormValid || isCreating"
          >
            <Loader2 v-if="isCreating" :size="16" class="mr-2 animate-spin" />
            Créer le projet
          </button>
        </div>
      </div>
    </div>

    <!-- Success/Error Messages -->
    <div v-if="successMessage" class="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
      <div class="flex items-start">
        <CheckCircle2 :size="16" class="mr-2 text-green-600 mt-0.5" />
        <div>
          <h4 class="text-sm font-medium text-green-900">Succès</h4>
          <p class="text-sm text-green-700 mt-1">{{ successMessage }}</p>
        </div>
      </div>
    </div>

    <div v-if="error" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
      <div class="flex items-start">
        <AlertCircle :size="16" class="mr-2 text-red-600 mt-0.5" />
        <div>
          <h4 class="text-sm font-medium text-red-900">Erreur</h4>
          <p class="text-sm text-red-700 mt-1">{{ error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
// Toast functionality will be implemented locally
import { api } from '@/services/api'
import {
  Rocket,
  Globe,
  Server,
  Smartphone,
  Database,
  Microscope,
  Gamepad2,
  Code2,
  AlertCircle,
  CheckCircle2,
  Loader2
} from 'lucide-vue-next'
// Using custom CSS classes from style.css

const router = useRouter()
// Simple toast notification function
const showToast = (options: { title: string; description?: string; variant?: string }) => {
  // For now, using console.log - can be replaced with a proper notification system
  console.log(`[${options.variant || 'info'}] ${options.title}: ${options.description || ''}`)
}

// State
const templates = ref<any[]>([])
const isLoading = ref(false)
const isCreating = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Filter state
const selectedCategory = ref('Tous')
const categories = ref(['Tous'])

// Dialog state
const showCreateDialog = ref(false)
const selectedTemplate = ref<any>(null)
const projectConfig = ref({
  template_name: '',
  project_name: '',
  author: '',
  email: '',
  version: '0.1.0',
  python_version: '',
  backend: 'auto',
  output_path: '',
  variables: {} as Record<string, string>
})

// Validation
const projectNameError = ref('')

// Computed
const filteredTemplates = computed(() => {
  if (selectedCategory.value === 'Tous') {
    return templates.value
  }
  return templates.value.filter(t => t.category === selectedCategory.value)
})

const isFormValid = computed(() => {
  return projectConfig.value.project_name.trim() && 
         !projectNameError.value &&
         projectConfig.value.template_name
})

// Icons mapping
const categoryIcons: Record<string, any> = {
  'Web': Globe,
  'API': Server,
  'Mobile': Smartphone,
  'Data': Database,
  'Science': Microscope,
  'Game': Gamepad2,
  'CLI': Code2
}

// Methods
const getTemplateIcon = (category: string) => {
  return categoryIcons[category] || Code2
}

const formatVariableName = (variable: string) => {
  return variable
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const validateProjectName = () => {
  const name = projectConfig.value.project_name
  if (!name) {
    projectNameError.value = ''
    return
  }
  
  if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(name)) {
    projectNameError.value = 'Le nom doit commencer par une lettre et contenir uniquement des lettres, chiffres, tirets et underscores'
  } else if (name.length < 3) {
    projectNameError.value = 'Le nom doit contenir au moins 3 caractères'
  } else {
    projectNameError.value = ''
  }
}

const loadTemplates = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await api.getTemplates()
    templates.value = response
    
    // Extract unique categories
    const uniqueCategories = new Set(response.map((t: any) => t.category))
    categories.value = ['Tous', ...Array.from(uniqueCategories)]
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors du chargement des templates'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isLoading.value = false
  }
}

const selectTemplate = (template: any) => {
  selectedTemplate.value = template
  projectConfig.value.template_name = template.name
  
  // Initialize variables
  projectConfig.value.variables = {}
  if (template.variables) {
    template.variables.forEach((variable: string) => {
      projectConfig.value.variables[variable] = ''
    })
  }
  
  showCreateDialog.value = true
}

const createProject = async () => {
  if (!isFormValid.value) return
  
  isCreating.value = true
  error.value = null
  
  try {
    await api.createFromTemplate(projectConfig.value)
    
    showCreateDialog.value = false
    
    showToast({
      title: 'Succès',
      description: 'Projet créé avec succès'
    })
    
    // Navigate to environments page after a short delay
    setTimeout(() => {
      router.push('/environments')
    }, 1500)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de la création du projet'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isCreating.value = false
  }
}

// Reset form when dialog closes
watch(showCreateDialog, (newValue) => {
  if (!newValue) {
    selectedTemplate.value = null
    projectConfig.value = {
      template_name: '',
      project_name: '',
      author: '',
      email: '',
      version: '0.1.0',
      python_version: '',
      backend: 'auto',
      output_path: '',
      variables: {}
    }
    projectNameError.value = ''
  }
})

// Lifecycle
onMounted(() => {
  loadTemplates()
})

// Clear messages after timeout
watch([error, successMessage], () => {
  if (error.value || successMessage.value) {
    setTimeout(() => {
      error.value = null
      successMessage.value = null
    }, 5000)
  }
})
</script>