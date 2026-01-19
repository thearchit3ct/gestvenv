<template>
  <div class="card">
    <div class="card-header pb-3">
      <div class="flex items-start justify-between">
        <div class="space-y-1">
          <h3 class="text-base font-semibold">{{ package.name }}</h3>
          <p v-if="package.description" class="text-sm text-muted-foreground line-clamp-2">
            {{ package.description }}
          </p>
        </div>
        <span
          :class="[
            'badge',
            package.status === 'installed' ? 'badge-primary' :
            package.status === 'outdated' ? 'badge-warning' : 'badge-secondary'
          ]"
        >
          {{ statusText }}
        </span>
      </div>
    </div>
    <div class="card-body">
      <div class="space-y-3">
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div>
            <p class="text-muted-foreground">Version installée</p>
            <p class="font-mono">{{ package.installed_version || 'N/A' }}</p>
          </div>
          <div>
            <p class="text-muted-foreground">Dernière version</p>
            <p class="font-mono">{{ package.latest_version || 'N/A' }}</p>
          </div>
        </div>

        <div class="text-sm">
          <p class="text-muted-foreground">Environnement</p>
          <p class="font-medium">{{ environment }}</p>
        </div>

        <div class="flex space-x-2">
          <button
            v-if="package.status === 'outdated'"
            class="btn btn-sm btn-outline flex-1"
            @click="$emit('update', { package: package.name, environment })"
          >
            <Download :size="14" class="mr-1" />
            Mettre à jour
          </button>
          <button
            v-if="package.status === 'installed' || package.status === 'outdated'"
            class="btn btn-sm btn-outline flex-1"
            @click="$emit('uninstall', { package: package.name, environment })"
          >
            <Trash2 :size="14" class="mr-1" />
            Désinstaller
          </button>
          <button
            v-if="!package.status || package.status === 'missing'"
            class="btn btn-sm btn-primary flex-1"
            @click="$emit('install', { package: package.name, environment })"
          >
            <Plus :size="14" class="mr-1" />
            Installer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Download, Trash2, Plus } from 'lucide-vue-next'

interface Props {
  package: {
    name: string
    description?: string
    status?: string
    installed_version?: string
    latest_version?: string
  }
  environment: string
}

const props = defineProps<Props>()

defineEmits<{
  install: [payload: { package: string; environment: string }]
  uninstall: [payload: { package: string; environment: string }]
  update: [payload: { package: string; environment: string }]
}>()

const statusText = computed(() => {
  switch (props.package.status) {
    case 'installed': return 'Installé'
    case 'outdated': return 'Obsolète'
    case 'missing': return 'Non installé'
    default: return 'Inconnu'
  }
})
</script>
