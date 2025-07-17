import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// Styles
import './style.css'

// Créer l'application Vue
const app = createApp(App)

// Configuration Pinia
const pinia = createPinia()

// Plugins
app.use(pinia)
app.use(router)

// Monter l'application
app.mount('#app')