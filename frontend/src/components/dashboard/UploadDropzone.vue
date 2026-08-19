<template>
  <div 
    @dragover.prevent="dragOver = true" 
    @dragleave.prevent="dragOver = false"
    @drop.prevent="onDrop"
    @click="$refs.fileInput?.click()"
    :class="[
      'relative w-full rounded-2xl p-6 flex flex-col justify-between cursor-pointer transition duration-200 shadow-sm overflow-hidden select-none border-2 min-h-[190px]',
      modelValue ? 'bg-studio-elevated text-studio-text border-studio-accent/30' : 'bg-studio-panel border-dashed border-studio-border hover:border-studio-accent/50 text-studio-textSecondary'
    ]"
  >
    <input 
      type="file" 
      ref="fileInput" 
      @change="onFileSelect" 
      class="hidden" 
      accept="application/pdf,image/*" 
    />

    <!-- Empty State: Upload Action Dropzone -->
    <div v-if="!modelValue" class="flex-1 flex flex-col items-center justify-center text-center p-4">
      <div class="p-3.5 bg-studio-secondary rounded-xl mb-3 text-studio-textSecondary border border-studio-border hover:text-studio-accent transition">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-studio-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <p class="text-xs font-bold text-studio-text">Drag or click to upload layout reference</p>
      <p class="text-[9px] text-studio-textMuted mt-1.5 uppercase tracking-wider font-semibold">PDF or Image file ≤ 10MB</p>
    </div>

    <!-- Active Document Layout Card -->
    <div v-else class="flex-1 flex flex-col justify-between">
      <div class="flex justify-between items-start">
        <div>
          <p class="text-[9px] text-studio-accent font-bold uppercase tracking-widest">Active Reference</p>
          <h4 class="text-sm font-black text-studio-text truncate max-w-[220px] mt-1">{{ modelValue.name }}</h4>
        </div>
        <button 
          @click.stop="$emit('update:modelValue', null)" 
          class="text-studio-textMuted hover:text-studio-text p-1 hover:bg-studio-secondary rounded-lg transition"
          title="Remove reference file"
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div class="mt-4 pt-3 border-t border-studio-border/60">
        <p class="text-xs font-mono text-studio-textMuted">SIZE: <span class="text-studio-text font-bold">{{ Math.round(modelValue.size / 1024) }} KB</span></p>
        <div class="flex justify-between items-center mt-2.5">
          <span class="flex items-center space-x-1.5 bg-studio-accent/10 px-2.5 py-0.5 rounded border border-studio-accent/20 text-[9px] font-black tracking-wider text-studio-accent uppercase">
            ● Ready
          </span>
          <span class="text-[10px] font-black font-mono text-studio-accent uppercase tracking-widest">VISA</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  modelValue: File | null
}>()

const emit = defineEmits(['update:modelValue'])
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const onDrop = (e: DragEvent) => {
  dragOver.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    emit('update:modelValue', e.dataTransfer.files[0])
  }
}

const onFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    emit('update:modelValue', target.files[0])
  }
}
</script>
