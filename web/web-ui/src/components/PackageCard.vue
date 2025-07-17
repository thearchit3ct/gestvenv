<template>
  <Card>
    <CardHeader class="pb-3">
      <div class="flex items-start justify-between">
        <div class="space-y-1">
          <CardTitle class="text-base">{{ package.name }}</CardTitle>
          <p v-if="package.description" class="text-sm text-muted-foreground line-clamp-2">
            {{ package.description }}
          </p>
        </div>
        <Badge
          :variant="package.status === 'installed' ? 'default' : 
                   package.status === 'outdated' ? 'secondary' : 'outline'"
        >
          {{ statusText }}
        </Badge>
      </div>
    </CardHeader>
    <CardContent>
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
          <Button
            v-if="package.status === 'outdated'"
            size="sm"
            variant="outline"
            @click="$emit('update', { package: package.name, environment })"
            class="flex-1"
          >
            <Download :size="14" class="mr-1" />
            Mettre à jour
          </Button>
          <Button
            v-if="package.status === 'installed' || package.status === 'outdated'"
            size="sm"
            variant="outline"
            @click="$emit('uninstall', { package: package.name, environment })"
            class="flex-1"
          >
            <Trash2 :size="14" class="mr-1" />
            Désinstaller
          </Button>
          <Button
            v-if="!package.status || package.status === 'missing'"
            size="sm"
            @click="$emit('install', { package: package.name, environment })"
            class="flex-1"
          >
            <Plus :size="14" class="mr-1" />
            Installer
          </Button>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Download, Trash2, Plus } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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