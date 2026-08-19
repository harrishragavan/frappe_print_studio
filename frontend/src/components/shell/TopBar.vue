<template>
  <header class="h-14 px-4 bg-studio-panel border-b border-studio-border flex items-center justify-between shrink-0 select-none">
    <!-- Left Section: Logo & Breadcrumbs -->
    <div class="flex items-center space-x-4">
      <div 
        @click="$emit('go-home')" 
        class="flex items-center space-x-2 cursor-pointer hover:opacity-85 transition group"
      >
        <span class="text-studio-accent font-black tracking-widest text-sm group-hover:scale-105 transition-transform duration-150">◈</span>
        <h1 class="text-xs font-black text-studio-text uppercase tracking-widest">PRINT STUDIO</h1>
      </div>
      
      <div class="h-4 w-[1px] bg-studio-border"></div>
      
      <!-- Context breadcrumb & Save state -->
      <div class="flex items-center space-x-2 text-xs">
        <span 
          v-if="selectedJobName"
          class="text-studio-textSecondary font-medium"
        >
          {{ selectedJob?.target_doctype || 'Print Format' }}
          <span class="text-studio-textMuted font-normal mx-1">/</span>
          <span class="text-studio-textMuted font-mono truncate max-w-[120px] inline-block align-bottom">{{ selectedJob?.name }}</span>
        </span>
        <span v-else class="text-studio-textSecondary font-medium">Studio Home</span>
        
        <span class="flex items-center space-x-1.5 ml-2 bg-studio-elevated px-2 py-0.5 rounded border border-studio-border text-[9px] font-bold tracking-wider">
          <span class="w-1.5 h-1.5 rounded-full bg-studio-accent animate-pulse"></span>
          <span class="text-studio-accent uppercase font-bold">Ready</span>
        </span>
      </div>
    </div>

    <!-- Center Section: View Mode Toggles (Visible when a job is active) -->
    <div class="flex items-center bg-studio-bg rounded-lg p-0.5 border border-studio-border">
      <button
        v-if="selectedJobName"
        @click="$emit('set-view-mode', 'design')"
        :class="[
          'px-3.5 py-1.5 rounded-md text-[10px] font-black uppercase tracking-wider transition select-none',
          activeViewMode === 'design' 
            ? 'bg-studio-elevated text-studio-accent shadow-sm border border-studio-border' 
            : 'text-studio-textSecondary hover:text-studio-text border border-transparent'
        ]"
      >
        Design
      </button>
      <button
        v-if="selectedJobName"
        @click="$emit('set-view-mode', 'code')"
        :class="[
          'px-3.5 py-1.5 rounded-md text-[10px] font-black uppercase tracking-wider transition select-none',
          activeViewMode === 'code' 
            ? 'bg-studio-elevated text-studio-accent shadow-sm border border-studio-border' 
            : 'text-studio-textSecondary hover:text-studio-text border border-transparent'
        ]"
      >
        Code
      </button>
      <span v-else class="px-4 py-1 text-[10px] text-studio-textMuted uppercase tracking-wider font-bold">Workbench</span>
    </div>

    <!-- Right Section: Actions -->
    <div class="flex items-center space-x-2.5">
      <div v-if="selectedJobName" class="flex items-center space-x-1 border-r border-studio-border pr-2.5">
        <button 
          @click="$emit('undo')"
          class="p-1.5 text-studio-textSecondary hover:text-studio-text hover:bg-studio-elevated rounded-lg transition"
          title="Undo (Ctrl+Z)"
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
          </svg>
        </button>
        <button 
          @click="$emit('redo')"
          class="p-1.5 text-studio-textSecondary hover:text-studio-text hover:bg-studio-elevated rounded-lg transition"
          title="Redo (Ctrl+Shift+Z)"
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11.934 12.8a1 1 0 000-1.6l-5.334-4A1 1 0 005 8v8a1 1 0 001.6.8l5.334-4z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.934 12.8a1 1 0 000-1.6l-5.334-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.334-4z" />
          </svg>
        </button>
      </div>

      <button 
        v-if="selectedJobName"
        @click="$emit('trigger-spotlight')"
        class="flex items-center space-x-1.5 bg-studio-elevated hover:bg-studio-secondary text-studio-textSecondary hover:text-studio-text border border-studio-border rounded-lg px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider select-none shadow-sm transition"
        title="Open Command Palette (Cmd+K)"
      >
        <svg class="h-3 w-3 text-studio-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <span>Search</span>
        <span class="text-[8px] opacity-70 bg-studio-secondary px-1 py-0.2 rounded border border-studio-border font-mono">⌘K</span>
      </button>

      <button 
        @click="$emit('toggle-settings')"
        class="flex items-center space-x-1.5 bg-studio-elevated hover:bg-studio-secondary text-studio-textSecondary hover:text-studio-text border border-studio-border rounded-lg px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider select-none shadow-sm transition"
      >
        <span>Engine</span>
      </button>

      <button
        v-if="selectedJobName"
        @click="$emit('deploy')"
        :disabled="isDeploying"
        class="bg-studio-accent hover:bg-studio-accentHover disabled:bg-studio-border disabled:text-studio-textMuted text-studio-bg font-black uppercase tracking-wider text-[10px] px-4 py-1.5 rounded-lg transition shadow-sm flex items-center space-x-1"
      >
        <span v-if="isDeploying" class="animate-spin rounded-full h-3 w-3 border-2 border-studio-bg border-t-transparent"></span>
        <span>{{ isDeploying ? 'Deploying...' : 'Deploy' }}</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  selectedJobName: string | null
  selectedJob: any
  activeViewMode: 'design' | 'code'
  isSubmitting: boolean
  isDeploying: boolean
  bootUser: string
}>()

defineEmits(['go-home', 'toggle-settings', 'set-view-mode', 'deploy', 'undo', 'redo', 'trigger-spotlight'])
</script>
