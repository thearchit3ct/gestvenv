<template>
  <div id="app" class="h-full bg-gray-50">
    <!-- Navigation latérale -->
    <div class="fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0" :class="{ '-translate-x-full': !sidebarOpen }">
      <div class="flex h-full flex-col">
        <!-- Logo et titre -->
        <div class="flex h-16 items-center justify-between px-6 border-b border-gray-200">
          <div class="flex items-center">
            <div class="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span class="text-white font-bold text-lg">G</span>
            </div>
            <h1 class="ml-3 text-xl font-bold text-gray-900">GestVenv</h1>
          </div>
          <button
            @click="toggleSidebar"
            class="lg:hidden text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon class="h-6 w-6" />
          </button>
        </div>

        <!-- Navigation -->
        <nav class="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
          <router-link
            v-for="item in navigation"
            :key="item.name"
            :to="item.path"
            class="group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200"
            :class="[
              $route.path === item.path
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
            ]"
            @click="closeSidebarOnMobile"
          >
            <component :is="item.icon" class="mr-3 h-5 w-5 flex-shrink-0" />
            {{ item.name }}
            <span
              v-if="item.badge"
              class="ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600"
            >
              {{ item.badge }}
            </span>
          </router-link>
        </nav>

        <!-- Statut WebSocket -->
        <div class="px-6 py-4 border-t border-gray-200">
          <div class="flex items-center text-sm">
            <div
              class="h-2 w-2 rounded-full mr-2"
              :class="[
                wsConnected ? 'bg-green-400' : wsReconnecting ? 'bg-yellow-400' : 'bg-red-400'
              ]"
            ></div>
            <span class="text-gray-600">
              {{ wsConnected ? 'Connecté' : wsReconnecting ? 'Reconnexion...' : 'Déconnecté' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Overlay pour mobile -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
      @click="closeSidebar"
    ></div>

    <!-- Contenu principal -->
    <div class="lg:pl-64">
      <!-- Header -->
      <header class="bg-white shadow-sm border-b border-gray-200">
        <div class="flex h-16 items-center justify-between px-6">
          <div class="flex items-center">
            <!-- Bouton menu mobile -->
            <button
              @click="toggleSidebar"
              class="lg:hidden text-gray-400 hover:text-gray-600 mr-4"
            >
              <Bars3Icon class="h-6 w-6" />
            </button>
            
            <!-- Titre de page -->
            <h2 class="text-lg font-semibold text-gray-900">
              {{ currentPageTitle }}
            </h2>
          </div>

          <!-- Actions header -->
          <div class="flex items-center space-x-4">
            <!-- Indicateur opérations en cours -->
            <div v-if="runningOperations.length > 0" class="flex items-center text-sm text-gray-600">
              <div class="loading mr-2"></div>
              {{ runningOperations.length }} opération(s) en cours
            </div>

            <!-- Notifications -->
            <button class="text-gray-400 hover:text-gray-600 relative">
              <BellIcon class="h-6 w-6" />
              <span v-if="runningOperations.length > 0" class="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full"></span>
            </button>

            <!-- Menu utilisateur -->
            <div class="relative">
              <button class="flex items-center text-sm text-gray-600 hover:text-gray-900">
                <UserCircleIcon class="h-8 w-8" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <!-- Contenu de la page -->
      <main class="flex-1 p-6">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <!-- Toast notifications -->
    <div class="fixed bottom-4 right-4 z-50 space-y-2">
      <transition-group name="slide-up">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          class="bg-white rounded-lg shadow-lg border border-gray-200 p-4 max-w-sm"
        >
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <component
                :is="getNotificationIcon(notification.type)"
                class="h-5 w-5"
                :class="getNotificationIconClass(notification.type)"
              />
            </div>
            <div class="ml-3 flex-1">
              <p class="text-sm font-medium text-gray-900">
                {{ notification.title }}
              </p>
              <p class="mt-1 text-sm text-gray-600">
                {{ notification.message }}
              </p>
            </div>
            <button
              @click="dismissNotification(notification.id)"
              class="ml-4 flex-shrink-0 text-gray-400 hover:text-gray-600"
            >
              <XMarkIcon class="h-4 w-4" />
            </button>
          </div>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Bars3Icon,
  XMarkIcon,
  HomeIcon,
  ServerIcon,
  CubeIcon,
  CircleStackIcon,
  ComputerDesktopIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  CogIcon,
  BellIcon,
  UserCircleIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  InformationCircleIcon
} from '@heroicons/vue/24/outline'

// Stores
import { useSystemStore } from '@/stores/system'

// Navigation items
interface NavItem {
  name: string
  path: string
  icon: typeof HomeIcon
  badge?: string | number
}

const navigation: NavItem[] = [
  { name: 'Tableau de bord', path: '/', icon: HomeIcon },
  { name: 'Environnements', path: '/environments', icon: ServerIcon },
  { name: 'Packages', path: '/packages', icon: CubeIcon },
  { name: 'Cache', path: '/cache', icon: CircleStackIcon },
  { name: 'Système', path: '/system', icon: ComputerDesktopIcon },
  { name: 'Templates', path: '/templates', icon: DocumentTextIcon },
  { name: 'Opérations', path: '/operations', icon: ClipboardDocumentListIcon },
  { name: 'Paramètres', path: '/settings', icon: CogIcon }
]

// State
const sidebarOpen = ref(false)
const notifications = ref<Array<{
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  title: string
  message: string
}>>([])

// Stores
const systemStore = useSystemStore()
const route = useRoute()

// Computed
const currentPageTitle = computed(() => {
  return route.meta?.title as string || 'GestVenv'
})

const runningOperations = computed(() => systemStore.runningOperations)
const wsConnected = computed(() => systemStore.wsConnected)
const wsReconnecting = computed(() => systemStore.wsReconnecting)

// Methods
function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function closeSidebar() {
  sidebarOpen.value = false
}

function closeSidebarOnMobile() {
  if (window.innerWidth < 1024) {
    sidebarOpen.value = false
  }
}

function addNotification(type: 'success' | 'warning' | 'error' | 'info', title: string, message: string) {
  const id = Date.now().toString()
  notifications.value.push({ id, type, title, message })
  
  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    dismissNotification(id)
  }, 5000)
}

function dismissNotification(id: string) {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index > -1) {
    notifications.value.splice(index, 1)
  }
}

function getNotificationIcon(type: string) {
  switch (type) {
    case 'success': return CheckCircleIcon
    case 'warning': return ExclamationTriangleIcon
    case 'error': return XCircleIcon
    default: return InformationCircleIcon
  }
}

function getNotificationIconClass(type: string) {
  switch (type) {
    case 'success': return 'text-green-400'
    case 'warning': return 'text-yellow-400'
    case 'error': return 'text-red-400'
    default: return 'text-blue-400'
  }
}

// Lifecycle
onMounted(async () => {
  // Initialiser les stores
  await systemStore.initialize()
  
  // Écouter les événements WebSocket pour les notifications
  const { websocket } = await import('@/services/websocket')
  
  websocket.onEnvironmentCreated((data) => {
    addNotification('success', 'Environnement créé', `L'environnement "${data.environment_name}" a été créé avec succès`)
  })
  
  websocket.onEnvironmentDeleted((data) => {
    addNotification('info', 'Environnement supprimé', `L'environnement "${data.environment_name}" a été supprimé`)
  })
  
  websocket.onPackageInstalled((data) => {
    addNotification('success', 'Package installé', `Le package "${data.package_name}" a été installé dans "${data.environment_name}"`)
  })
  
  websocket.onOperationCompleted((data) => {
    addNotification('success', 'Opération terminée', `L'opération a été terminée avec succès`)
  })
})

onUnmounted(() => {
  const { websocket } = require('@/services/websocket')
  websocket.disconnect()
})
</script>