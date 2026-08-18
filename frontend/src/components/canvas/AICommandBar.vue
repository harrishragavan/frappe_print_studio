<template>
  <div class="bg-studio-panel border-t border-studio-border p-4 space-y-3 shrink-0 select-none">
    <!-- Suggestions Tags -->
    <div class="flex flex-wrap gap-2 items-center">
      <span class="text-[9px] uppercase tracking-widest text-studio-textMuted font-bold shrink-0">Suggestions:</span>
      <button 
        v-for="s in currentSuggestions" 
        :key="s" 
        @click="$emit('select-suggestion', s)"
        class="bg-studio-bg hover:bg-studio-elevated text-studio-textSecondary hover:text-studio-text border border-studio-border rounded-lg px-2.5 py-1 text-[10px] font-semibold transition select-none shadow-sm"
      >
        {{ s }}
      </button>
    </div>

    <!-- Active Attachments list -->
    <div v-if="chatAttachments.length > 0" class="flex flex-wrap gap-2 pt-1 border-t border-studio-border/60">
      <div 
        v-for="(attachment, idx) in chatAttachments" 
        :key="idx"
        class="flex items-center space-x-1.5 bg-studio-bg border border-studio-border rounded-lg px-2.5 py-1 text-[10px] select-none shadow-sm"
      >
        <svg class="w-3.5 h-3.5 text-studio-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
        </svg>
        <span class="truncate max-w-[130px] font-bold text-studio-textSecondary">{{ attachment.name }}</span>
        <button 
          @click="$emit('remove-attachment', idx)" 
          class="text-studio-textMuted hover:text-rose-500 transition ml-1"
        >
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Main Command Bar Input Row -->
    <div class="flex items-center space-x-2 bg-studio-bg border border-studio-border rounded-xl p-1.5 focus-within:border-studio-accent/60 focus-within:ring-1 focus-within:ring-studio-accent/40 transition">
      <!-- Hidden file input for references -->
      <input 
        type="file" 
        ref="attachmentInput" 
        class="hidden" 
        accept="application/pdf, image/*"
        @change="onAttachmentSelect" 
      />

      <button 
        @click="attachmentInput?.click()"
        :disabled="isRefining || isUploadingAttachment"
        class="p-2 bg-studio-panel border border-studio-border hover:bg-studio-elevated text-studio-textSecondary hover:text-studio-text rounded-lg transition disabled:opacity-50 shrink-0 shadow-sm"
        title="Attach Reference (PDF/Image)"
      >
        <svg v-if="isUploadingAttachment" class="animate-spin h-4 w-4 text-studio-accent" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
        </svg>
      </button>

      <button 
        @click="$emit('open-site-files')"
        :disabled="isRefining || isUploadingAttachment"
        class="p-2 bg-studio-panel border border-studio-border hover:bg-studio-elevated text-studio-textSecondary hover:text-studio-text rounded-lg transition disabled:opacity-50 shrink-0 shadow-sm"
        title="Browse Site Files"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      </button>

      <input 
        type="text" 
        :value="modelValue"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        @keyup.enter="$emit('refine')"
        :disabled="isRefining"
        placeholder="⌘K Ask Print Studio to refine layout..."
        class="flex-1 bg-transparent border-none py-1.5 px-2.5 text-studio-text text-xs focus:outline-none focus:ring-0 placeholder-studio-textMuted"
      />
      
      <button 
        @click="$emit('refine')"
        :disabled="isRefining || isUploadingAttachment || (!modelValue.trim() && chatAttachments.length === 0)"
        class="px-4 py-2 bg-studio-accent hover:bg-studio-accentHover disabled:bg-studio-border disabled:text-studio-textMuted text-studio-bg font-black uppercase tracking-wider text-[10px] rounded-lg transition flex items-center space-x-1.5 shadow-sm shrink-0"
      >
        <svg v-if="isRefining" class="animate-spin h-3.5 w-3.5 text-studio-bg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>{{ isRefining ? 'Refining...' : 'Refine' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  modelValue: string
  chatAttachments: any[]
  isUploadingAttachment: boolean
  isRefining: boolean
  selectedRegionId: string | null
  spatialRegions: any[]
}>()

const emit = defineEmits([
  'update:modelValue',
  'select-suggestion',
  'remove-attachment',
  'upload-attachment',
  'open-site-files',
  'refine'
])

const attachmentInput = ref<HTMLInputElement | null>(null)

// Context-aware suggestions depending on selection
const currentSuggestions = computed(() => {
  if (props.selectedRegionId) {
    const region = props.spatialRegions.find(r => r.id === props.selectedRegionId)
    if (region && region.region_type === 'header') {
      return ['Align header left', 'Increase logo spacing', 'Add header background']
    } else if (region && region.region_type === 'table') {
      return ['Enlarge table font', 'Add border to table grid', 'Remove item rates']
    } else if (region && region.region_type === 'totals') {
      return ['Highlight grand total text', 'Move total label to right', 'Compact totals margins']
    }
  }
  return [
    'Add elegant page border',
    'Make layout more compact',
    'Enlarge invoice totals text',
    'Add a signed-by signature line'
  ]
})

const onAttachmentSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    emit('upload-attachment', target.files[0])
    target.value = ''
  }
}
</script>
