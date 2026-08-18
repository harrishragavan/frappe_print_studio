<template>
  <div class="w-full h-full bg-studio-panel border-l border-studio-border flex flex-col select-none overflow-hidden">
    <!-- Header -->
    <div class="p-4 border-b border-studio-border flex justify-between items-center shrink-0">
      <h3 class="text-[10px] font-black text-studio-textSecondary uppercase tracking-widest">Inspector</h3>
      <span class="text-[9px] font-mono text-studio-accent uppercase font-bold">Properties</span>
    </div>

    <!-- Scrollable content -->
    <div class="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-5">
      <!-- Mode 1: Global Document Properties (No selection) -->
      <div v-if="!selectedRegion" class="space-y-4">
        <div class="space-y-1">
          <p class="text-[9px] text-studio-textMuted font-bold uppercase tracking-widest">Document Scope</p>
          <h4 class="text-sm font-black text-studio-text">Global Properties</h4>
        </div>
        
        <div class="h-[1px] bg-studio-border"></div>

        <div class="space-y-3 text-xs">
          <div class="flex justify-between items-center py-1">
            <span class="text-studio-textSecondary">Format Target</span>
            <span class="font-mono text-studio-text font-bold uppercase">{{ selectedJob?.target_doctype || 'Sales Invoice' }}</span>
          </div>
          <div class="flex justify-between items-center py-1">
            <span class="text-studio-textSecondary">Page Size</span>
            <span class="font-mono text-studio-text">A4 (Letter)</span>
          </div>
          <div class="flex justify-between items-center py-1">
            <span class="text-studio-textSecondary">Orientation</span>
            <span class="font-mono text-studio-text">Portrait</span>
          </div>
          <div class="flex justify-between items-center py-1">
            <span class="text-studio-textSecondary">Total Regions</span>
            <span class="font-mono text-studio-accent font-bold">{{ spatialRegions?.length || 0 }}</span>
          </div>
        </div>

        <div class="h-[1px] bg-studio-border"></div>

        <div class="space-y-2">
          <p class="text-[9px] text-studio-textMuted font-bold uppercase tracking-widest">Engine Metadata</p>
          <div class="p-3 bg-studio-bg rounded-xl border border-studio-border space-y-1.5">
            <div class="flex justify-between items-center text-[10px]">
              <span class="text-studio-textSecondary">Status:</span>
              <span class="text-studio-accent uppercase font-bold">Deployed</span>
            </div>
            <div class="flex justify-between items-center text-[10px]">
              <span class="text-studio-textSecondary">Mapping:</span>
              <span class="text-studio-text font-mono">100% matched</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Mode 2: Selected Region Properties -->
      <div v-else class="space-y-4">
        <div class="space-y-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-[8px] uppercase font-black px-1.5 py-0.5 rounded bg-studio-accent/15 text-studio-accent font-mono">
              {{ selectedRegion.region_type || 'REGION' }}
            </span>
          </div>
          <h4 class="text-xs font-black text-studio-text capitalize mt-1">{{ formatRegionName(selectedRegion) }}</h4>
        </div>

        <div class="h-[1px] bg-studio-border"></div>

        <!-- Coordinates Details (Bounding box details) -->
        <div class="space-y-2">
          <p class="text-[9px] text-studio-textMuted font-bold uppercase tracking-widest">Bounding Coordinates</p>
          <div class="grid grid-cols-2 gap-2 text-xs font-mono">
            <div class="bg-studio-bg border border-studio-border p-2 rounded-lg">
              <span class="text-[9px] text-studio-textMuted block">Min-X</span>
              <span class="text-studio-text font-bold">{{ selectedRegion.bbox?.[0]?.toFixed(1) || 0 }}px</span>
            </div>
            <div class="bg-studio-bg border border-studio-border p-2 rounded-lg">
              <span class="text-[9px] text-studio-textMuted block">Min-Y</span>
              <span class="text-studio-text font-bold">{{ selectedRegion.bbox?.[1]?.toFixed(1) || 0 }}px</span>
            </div>
            <div class="bg-studio-bg border border-studio-border p-2 rounded-lg">
              <span class="text-[9px] text-studio-textMuted block">Width</span>
              <span class="text-studio-text font-bold">{{ (selectedRegion.bbox?.[2] - selectedRegion.bbox?.[0])?.toFixed(1) || 0 }}px</span>
            </div>
            <div class="bg-studio-bg border border-studio-border p-2 rounded-lg">
              <span class="text-[9px] text-studio-textMuted block">Height</span>
              <span class="text-studio-text font-bold">{{ (selectedRegion.bbox?.[3] - selectedRegion.bbox?.[1])?.toFixed(1) || 0 }}px</span>
            </div>
          </div>
        </div>

        <!-- Extracted text snippet panel -->
        <div class="space-y-2">
          <p class="text-[9px] text-studio-textMuted font-bold uppercase tracking-widest">Extracted Text Content</p>
          <div class="p-3 bg-studio-bg border border-studio-border rounded-xl text-xs font-mono max-h-32 overflow-y-auto custom-scrollbar select-text text-studio-textSecondary leading-normal">
            {{ selectedRegion.text_snippet || 'No text content identified inside bounds.' }}
          </div>
        </div>

        <!-- Mapped DB Fields config -->
        <div class="space-y-2">
          <p class="text-[9px] text-studio-textMuted font-bold uppercase tracking-widest">Schema Field Mappings</p>
          
          <div class="p-3 bg-studio-bg border border-studio-border rounded-xl space-y-2">
            <div class="flex justify-between items-center text-[10px]">
              <span class="text-studio-textSecondary font-semibold">Mapped Field:</span>
              <span class="font-mono text-studio-accent font-bold">{{ getMappedField(selectedRegion.id) || 'Unassigned' }}</span>
            </div>
            
            <div class="flex justify-between items-center text-[10px] border-t border-studio-border/60 pt-2">
              <span class="text-studio-textSecondary font-semibold">Confidence Rate:</span>
              <span class="text-studio-accent font-black">98.5%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  spatialRegions: any[]
  selectedRegionId: string | null
  selectedJob: any
}>()

const selectedRegion = computed(() => {
  if (!props.selectedRegionId) return null
  return props.spatialRegions.find(r => r.id === props.selectedRegionId) || null
})

const formatRegionName = (region: any) => {
  if (region.region_type) {
    return region.region_type.replace('_', ' ')
  }
  return region.id
}

const getMappedField = (regionId: string) => {
  if (!props.selectedJob?.field_mappings) return ''
  const mapping = props.selectedJob.field_mappings.find((m: any) => m.region_id === regionId)
  return mapping ? mapping.frappe_field : ''
}
</script>
