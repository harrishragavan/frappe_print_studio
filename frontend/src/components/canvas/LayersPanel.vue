<template>
  <div class="w-full h-full bg-studio-panel border-r border-studio-border flex flex-col select-none">
    <!-- Header -->
    <div class="p-4 border-b border-studio-border flex justify-between items-center shrink-0">
      <h3 class="text-[10px] font-black text-studio-textSecondary uppercase tracking-widest">Layers</h3>
      <span class="text-[9px] font-mono text-studio-textMuted uppercase font-semibold">Workspace</span>
    </div>

    <!-- Tree list -->
    <div class="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
      <div class="space-y-1">
        <!-- Root node -->
        <div class="flex items-center space-x-1.5 py-1 px-1.5 text-xs text-studio-text font-black uppercase tracking-wider">
          <svg class="h-3.5 w-3.5 text-studio-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Document</span>
        </div>

        <!-- Dynamic Layer Nodes from regions -->
        <div class="pl-4 space-y-0.5">
          <div 
            v-for="region in spatialRegions" 
            :key="region.id"
            @click="$emit('select-region', region.id)"
            @mouseenter="$emit('hover-region', region.id)"
            @mouseleave="$emit('hover-region', null)"
            :class="[
              'flex items-center justify-between py-2 px-2.5 rounded-lg text-xs font-semibold cursor-pointer transition select-none group border',
              activeRegionId === region.id 
                ? 'bg-studio-accent/5 text-studio-accent border-studio-accent/25 shadow-sm' 
                : hoverRegionId === region.id 
                ? 'bg-studio-secondary text-studio-text border-studio-border' 
                : 'text-studio-textSecondary hover:bg-studio-secondary/60 border-transparent'
            ]"
          >
            <div class="flex items-center space-x-2.5 truncate">
              <!-- Type Icon -->
              <span class="text-[8px] uppercase font-black px-1.5 py-0.5 rounded bg-studio-bg border border-studio-border text-studio-textMuted group-hover:text-studio-textSecondary transition font-mono shrink-0">
                {{ region.region_type ? region.region_type.substring(0, 4) : 'REG' }}
              </span>
              <span class="truncate capitalize text-studio-textSecondary group-hover:text-studio-text transition">{{ formatRegionName(region) }}</span>
            </div>
            
            <svg 
              v-if="activeRegionId === region.id" 
              class="h-3.5 w-3.5 text-studio-accent shrink-0" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor" 
              stroke-width="2.5"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  spatialRegions: any[]
  activeRegionId: string | null
  hoverRegionId: string | null
}>()

defineEmits(['select-region', 'hover-region'])

const formatRegionName = (region: any) => {
  if (region.region_type) {
    return region.region_type.replace('_', ' ')
  }
  return region.id
}
</script>
