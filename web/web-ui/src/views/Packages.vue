<template>
  <div class="container mx-auto p-6">
    <div class="mb-6">
      <h1 class="text-3xl font-bold">Packages</h1>
      <p class="text-muted-foreground mt-2">Recherchez et gérez les packages dans tous vos environnements</p>
    </div>

    <!-- Search Section -->
    <div class="card mb-6">
      <div class="card-header">
        <h2 class="text-xl font-semibold">Recherche de packages</h2>
      </div>
      <div class="card-body">
        <div class="flex space-x-4">
          <div class="flex-1 relative">
            <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Rechercher des packages... (ex: requests, numpy)"
              class="form-input pl-9 w-full"
              @keydown.enter="searchPackages"
            />
          </div>
          <select v-model="selectedEnvironment" class="form-select w-[200px]">
            <option value="all">Tous les environnements</option>
            <option v-for="env in environments" :key="env.name" :value="env.name">
              {{ env.name }}
            </option>
          </select>
          <button class="btn btn-primary" @click="searchPackages" :disabled="isSearching">
            <Search :size="16" class="mr-2" />
            Rechercher
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="card">
        <div class="card-body p-6">
          <div class="space-y-3">
            <div class="skeleton h-4 w-1/3"></div>
            <div class="skeleton h-4 w-1/2"></div>
            <div class="skeleton h-4 w-2/3"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Results Section -->
    <div v-else-if="searchResults.length > 0" class="space-y-4">
      <div class="flex items-center justify-between mb-4">
        <p class="text-sm text-gray-500">
          {{ searchResults.length }} package(s) trouvé(s)
        </p>
        <div class="flex items-center space-x-2">
          <label for="group-by-env" class="form-label">Grouper par environnement</label>
          <input
            type="checkbox"
            id="group-by-env"
            v-model="groupByEnvironment"
            class="mr-2"
          />
        </div>
      </div>

      <!-- Grouped View -->
      <div v-if="groupByEnvironment" class="space-y-6">
        <div v-for="(group, envName) in groupedResults" :key="envName">
          <h3 class="text-lg font-semibold mb-3 flex items-center space-x-2">
            <Folder :size="20" />
            <span>{{ envName }}</span>
            <span class="badge badge-secondary">{{ group.length }} packages</span>
          </h3>
          <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <PackageCard
              v-for="pkg in group"
              :key="`${envName}-${pkg.name}`"
              :package="pkg"
              :environment="envName"
              @install="installPackage"
              @uninstall="uninstallPackage"
              @update="updatePackage"
            />
          </div>
        </div>
      </div>

      <!-- Flat View -->
      <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <PackageCard
          v-for="(pkg, index) in searchResults"
          :key="`${pkg.environment}-${pkg.name}-${index}`"
          :package="pkg"
          :environment="pkg.environment"
          @install="installPackage"
          @uninstall="uninstallPackage"
          @update="updatePackage"
        />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="card">
      <div class="card-body text-center py-12">
        <Package :size="48" class="mx-auto text-gray-400 mb-4" />
        <h3 class="text-lg font-medium mb-2">Commencez votre recherche</h3>
        <p class="text-gray-500">
          Recherchez des packages installés dans vos environnements virtuels
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useEnvironmentsStore } from '@/stores/environments'
import { usePackagesStore } from '@/stores/packages'
import { Search, Package as PackageIcon, Folder } from 'lucide-vue-next'
import type { Package } from '@/types'
import PackageCard from '@/components/PackageCard.vue'

// Simple toast notification function
const showToast = (options: { title: string; description?: string; variant?: string }) => {
  console.log(`[${options.variant || 'info'}] ${options.title}: ${options.description || ''}`)
}

const environmentsStore = useEnvironmentsStore()
const packagesStore = usePackagesStore()

const searchQuery = ref('')
const selectedEnvironment = ref('all')
const groupByEnvironment = ref(true)
const isLoading = ref(false)
const isSearching = ref(false)
const searchResults = ref<any[]>([])
const environments = ref<any[]>([])

// Computed
const groupedResults = computed(() => {
  const groups: Record<string, any[]> = {}

  searchResults.value.forEach(pkg => {
    if (!groups[pkg.environment]) {
      groups[pkg.environment] = []
    }
    groups[pkg.environment].push(pkg)
  })

  return groups
})

// Methods
const loadEnvironments = async () => {
  try {
    await environmentsStore.fetchEnvironments()
    environments.value = environmentsStore.environments
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: 'Impossible de charger les environnements',
      variant: 'destructive'
    })
  }
}

const searchPackages = async () => {
  if (!searchQuery.value.trim()) return

  isSearching.value = true
  searchResults.value = []

  try {
    if (selectedEnvironment.value === 'all') {
      // Search in all environments
      const results = []
      for (const env of environments.value) {
        const envDetails = await environmentsStore.fetchEnvironmentDetails(env.name)
        if (!envDetails) continue
        const packages = envDetails.packages || []

        const filtered = packages.filter((pkg: Package) =>
          pkg.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
          pkg.description?.toLowerCase().includes(searchQuery.value.toLowerCase())
        )

        results.push(...filtered.map((pkg: Package) => ({
          ...pkg,
          environment: env.name
        })))
      }
      searchResults.value = results
    } else {
      // Search in specific environment
      const envDetails = await environmentsStore.fetchEnvironmentDetails(selectedEnvironment.value)
      if (!envDetails) {
        searchResults.value = []
        return
      }
      const packages = envDetails.packages || []

      const filtered = packages.filter((pkg: Package) =>
        pkg.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
        pkg.description?.toLowerCase().includes(searchQuery.value.toLowerCase())
      )

      searchResults.value = filtered.map((pkg: Package) => ({
        ...pkg,
        environment: selectedEnvironment.value
      }))
    }
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: 'Erreur lors de la recherche des packages',
      variant: 'destructive'
    })
  } finally {
    isSearching.value = false
  }
}

const installPackage = async ({ package: packageName, environment }: { package: string; environment: string }) => {
  try {
    await packagesStore.installPackage(environment, {
      name: packageName
    })

    showToast({
      title: 'Succès',
      description: `Package ${packageName} installé dans ${environment}`
    })

    // Refresh search results
    await searchPackages()
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: `Impossible d'installer ${packageName}`,
      variant: 'destructive'
    })
  }
}

const uninstallPackage = async ({ package: packageName, environment }: any) => {
  try {
    await packagesStore.uninstallPackage(environment, packageName)

    showToast({
      title: 'Succès',
      description: `Package ${packageName} désinstallé de ${environment}`
    })

    // Refresh search results
    await searchPackages()
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: `Impossible de désinstaller ${packageName}`,
      variant: 'destructive'
    })
  }
}

const updatePackage = async ({ package: packageName, environment }: any) => {
  try {
    await packagesStore.updatePackages(environment, [packageName])

    showToast({
      title: 'Succès',
      description: `Package ${packageName} mis à jour dans ${environment}`
    })

    // Refresh search results
    await searchPackages()
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: `Impossible de mettre à jour ${packageName}`,
      variant: 'destructive'
    })
  }
}

// Lifecycle
onMounted(() => {
  loadEnvironments()
})
</script>
