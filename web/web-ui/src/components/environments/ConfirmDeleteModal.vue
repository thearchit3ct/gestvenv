<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
    <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white">
      <div class="mt-3">
        <!-- Header -->
        <div class="flex items-center justify-between pb-4 border-b border-gray-200">
          <div class="flex items-center space-x-3">
            <ExclamationTriangleIcon class="h-6 w-6 text-red-500" />
            <h3 class="text-lg font-medium text-gray-900">
              Confirmer la suppression
            </h3>
          </div>
          <button
            @click="$emit('cancel')"
            class="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon class="h-6 w-6" />
          </button>
        </div>

        <!-- Content -->
        <div class="mt-6">
          <div class="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
            <div class="flex">
              <div class="ml-3">
                <h3 class="text-sm font-medium text-red-800">
                  Attention : Cette action est irréversible
                </h3>
                <div class="mt-2 text-sm text-red-700">
                  <p>
                    Vous êtes sur le point de supprimer l'environnement 
                    <span class="font-semibold">{{ environmentName }}</span>.
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-1">
                    <li>Tous les packages installés seront perdus</li>
                    <li>Les fichiers de configuration seront supprimés</li>
                    <li>Cette action ne peut pas être annulée</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <!-- Confirmation input -->
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Pour confirmer, tapez le nom de l'environnement :
            </label>
            <input
              v-model="confirmationText"
              type="text"
              class="form-input"
              :placeholder="environmentName"
              @keyup.enter="handleConfirm"
            />
          </div>

          <!-- Force delete option -->
          <div class="flex items-center mb-4">
            <input
              id="force-delete"
              v-model="forceDelete"
              type="checkbox"
              class="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
            />
            <label for="force-delete" class="ml-2 block text-sm text-gray-700">
              Forcer la suppression même en cas d'erreur
            </label>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end space-x-3 pt-6 border-t border-gray-200">
          <button
            type="button"
            @click="$emit('cancel')"
            class="btn-outline"
            :disabled="loading"
          >
            Annuler
          </button>
          <button
            type="button"
            @click="handleConfirm"
            class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loading || !canConfirm"
          >
            <div v-if="loading" class="loading mr-2"></div>
            <TrashIcon v-else class="h-4 w-4 mr-2" />
            Supprimer définitivement
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { XMarkIcon, TrashIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

// Props
const props = defineProps<{
  environmentName: string
}>()

// Events
const emit = defineEmits<{
  confirm: [forceDelete: boolean]
  cancel: []
}>()

// State
const loading = ref(false)
const confirmationText = ref('')
const forceDelete = ref(false)

// Computed
const canConfirm = computed(() => {
  return confirmationText.value === props.environmentName
})

// Methods
function handleConfirm() {
  if (!canConfirm.value || loading.value) return
  
  loading.value = true
  emit('confirm', forceDelete.value)
}
</script>