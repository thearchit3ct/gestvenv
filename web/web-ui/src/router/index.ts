import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// Import des vues
const Dashboard = () => import('@/views/Dashboard.vue')
const Environments = () => import('@/views/Environments.vue')
const EnvironmentDetails = () => import('@/views/EnvironmentDetails.vue')
const Packages = () => import('@/views/Packages.vue')
const Cache = () => import('@/views/Cache.vue')
const System = () => import('@/views/System.vue')
const Templates = () => import('@/views/Templates.vue')
const Operations = () => import('@/views/Operations.vue')
const Settings = () => import('@/views/Settings.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: {
      title: 'Tableau de bord'
    }
  },
  {
    path: '/environments',
    name: 'Environments',
    component: Environments,
    meta: {
      title: 'Environnements'
    }
  },
  {
    path: '/environments/:name',
    name: 'EnvironmentDetails',
    component: EnvironmentDetails,
    props: true,
    meta: {
      title: 'Détails environnement'
    }
  },
  {
    path: '/packages',
    name: 'Packages',
    component: Packages,
    meta: {
      title: 'Packages'
    }
  },
  {
    path: '/cache',
    name: 'Cache',
    component: Cache,
    meta: {
      title: 'Cache'
    }
  },
  {
    path: '/system',
    name: 'System',
    component: System,
    meta: {
      title: 'Système'
    }
  },
  {
    path: '/templates',
    name: 'Templates',
    component: Templates,
    meta: {
      title: 'Templates'
    }
  },
  {
    path: '/operations',
    name: 'Operations',
    component: Operations,
    meta: {
      title: 'Opérations'
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    meta: {
      title: 'Paramètres'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach((to, from, next) => {
  // Mettre à jour le titre de la page
  if (to.meta?.title) {
    document.title = `${to.meta.title} - GestVenv`
  } else {
    document.title = 'GestVenv'
  }
  
  next()
})

export default router