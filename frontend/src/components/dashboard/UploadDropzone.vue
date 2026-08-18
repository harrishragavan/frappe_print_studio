<template>
  <div 
    @dragover.prevent="dragOver = true" 
    @dragleave.prevent="dragOver = false"
    @drop.prevent="onDrop"
    @click="$refs.fileInput?.click()"
    :class="[
      'relative w-full rounded-[20px] p-6 flex flex-col justify-between cursor-pointer transition duration-200 shadow-sm overflow-hidden select-none border min-h-[190px]',
      modelValue ? 'bg-studio-elevated text-studio-text border-studio-accent/30' : 'bg-studio-panel border-studio-border hover:border-studio-accent/40 text-studio-textSecondary'
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
      <div class="p-3 bg-studio-secondary rounded-full mb-3 text-studio-accent border border-studio-border">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      </div>
      <p class="text-xs font-bold text-studio-text">Drag or click to upload reference sample</p>
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
