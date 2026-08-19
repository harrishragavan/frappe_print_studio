<template>
  <div class="flex-1 flex flex-col lg:flex-row min-h-0 bg-studio-bg select-none">
    <!-- Code Editor Section (Left Pane) -->
    <div class="flex-1 flex flex-col min-h-[400px] lg:h-full border-r border-studio-border">
      <!-- Tabs header -->
      <div class="h-10 px-2 bg-studio-panel border-b border-studio-border flex justify-between items-center shrink-0">
        <div class="flex space-x-1">
          <button 
            @click="activeCodeTab = 'html'"
            :class="[
              'px-3.5 py-1 rounded-md text-[10px] font-black uppercase tracking-wider transition',
              activeCodeTab === 'html' 
                ? 'bg-studio-bg text-studio-accent border border-studio-border' 
                : 'text-studio-textSecondary hover:text-studio-text'
            ]"
          >
            HTML / Jinja
          </button>
          <button 
            @click="activeCodeTab = 'css'"
            :class="[
              'px-3.5 py-1 rounded-md text-[10px] font-black uppercase tracking-wider transition',
              activeCodeTab === 'css' 
                ? 'bg-studio-bg text-studio-accent border border-studio-border' 
                : 'text-studio-textSecondary hover:text-studio-text'
            ]"
          >
            CSS Style
          </button>
        </div>
        <span class="text-[9px] font-mono text-studio-textMuted uppercase font-semibold pr-2">Editor</span>
      </div>

      <!-- Editor Content -->
      <div class="flex-1 min-h-0 bg-studio-bg p-4 relative flex flex-col">
        <!-- Jinja/HTML source -->
        <textarea 
          v-if="activeCodeTab === 'html'"
          :value="generatedJinja"
          @input="$emit('update:generatedJinja', ($event.target as HTMLTextAreaElement).value)"
          class="flex-1 w-full bg-[#1A1D20] text-[#E0E2E4] border-[#2A2E33] rounded-xl p-4 font-mono text-xs focus:outline-none focus:border-studio-accent/70 focus:ring-1 focus:ring-studio-accent/30 leading-relaxed resize-none custom-scrollbar"
        ></textarea>

        <!-- CSS style source -->
        <textarea 
          v-if="activeCodeTab === 'css'"
          :value="generatedCss"
          @input="$emit('update:generatedCss', ($event.target as HTMLTextAreaElement).value)"
          class="flex-1 w-full bg-[#1A1D20] text-[#E0E2E4] border-[#2A2E33] rounded-xl p-4 font-mono text-xs focus:outline-none focus:border-studio-accent/70 focus:ring-1 focus:ring-studio-accent/30 leading-relaxed resize-none custom-scrollbar"
        ></textarea>

        <!-- Validation warnings indicator footer -->
        <div class="mt-3.5 bg-studio-panel border border-studio-border rounded-xl p-3 flex items-center justify-between">
          <div class="flex items-center space-x-2 text-xs">
            <span class="w-1.5 h-1.5 rounded-full bg-studio-accent"></span>
            <span class="text-studio-textSecondary font-semibold">Validations:</span>
            <span class="text-[10px] uppercase font-bold text-studio-accent">All systems ready</span>
          </div>
          <span class="text-[9px] font-mono text-studio-textMuted uppercase">Frappe compiler v2</span>
        </div>
      </div>
    </div>

    <!-- Live Preview Section (Right Pane) -->
    <div class="flex-1 flex flex-col min-h-[400px] lg:h-full relative p-4 bg-transparent">
      <!-- Tactile grid backing -->
      <div class="absolute inset-0 opacity-[0.3] drafting-board-grid pointer-events-none"></div>

      <div class="text-[9px] uppercase tracking-widest text-studio-textMuted font-bold mb-2 pb-1 border-b border-studio-border flex justify-between shrink-0 z-10">
        <span>Template Render Preview</span>
        <span>A4 Portrait</span>
      </div>
      <div class="flex-1 bg-white rounded-xl border border-studio-border overflow-hidden shadow-2xl relative z-10">
        <iframe 
          class="w-full h-full border-none bg-white"
          :srcdoc="iframeSrcDoc"
        ></iframe>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  generatedJinja: string
  generatedCss: string
  iframeSrcDoc: string
}>()

defineEmits(['update:generatedJinja', 'update:generatedCss'])

const activeCodeTab = ref<'html' | 'css'>('html')
</script>
