<template>
  <div class="flex-1 flex flex-col min-h-0 bg-studio-bg relative overflow-hidden select-none">
    <!-- Toolbar -->
    <div class="h-10 px-4 bg-studio-panel border-b border-studio-border flex items-center justify-between shrink-0">
      <!-- Mode toggles -->
      <div class="flex space-x-1 bg-studio-bg rounded-lg p-0.5 border border-studio-border">
        <button 
          v-for="mode in ['normal', 'inspect', 'coordinates']" 
          :key="mode"
          @click="canvasMode = mode"
          :class="[
            'px-2.5 py-1 rounded text-[9px] uppercase tracking-wider font-bold transition',
            canvasMode === mode 
              ? 'bg-studio-elevated text-studio-accent border border-studio-border/60' 
              : 'text-studio-textSecondary hover:text-studio-text'
          ]"
        >
          {{ mode }}
        </button>
      </div>

      <!-- Zoom and controls -->
      <div class="flex items-center space-x-2.5 text-xs text-studio-textSecondary">
        <button 
          @click="zoomOut" 
          class="p-1 hover:bg-studio-secondary hover:text-studio-text rounded-md transition"
          title="Zoom Out"
        >
          <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M18 12H6" />
          </svg>
        </button>
        <span class="font-mono text-[9px] font-bold min-w-[32px] text-center">{{ Math.round(zoomScale * 100) }}%</span>
        <button 
          @click="zoomIn" 
          class="p-1 hover:bg-studio-secondary hover:text-studio-text rounded-md transition"
          title="Zoom In"
        >
          <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </button>
        <div class="h-3.5 w-[1px] bg-studio-border"></div>
        <button 
          @click="resetZoomPan" 
          class="p-1 hover:bg-studio-secondary hover:text-studio-text rounded-md transition"
          title="Fit to Screen"
        >
          <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Main Canvas Viewport Area -->
    <div 
      ref="viewport"
      @mousedown="startPan"
      @mousemove="doPan"
      @mouseup="endPan"
      @mouseleave="endPan"
      class="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing outline-none"
    >
      <!-- Tactile grid backing -->
      <div class="absolute inset-0 opacity-[0.4] drafting-board-grid pointer-events-none"></div>

      <!-- Transform wrapper (Warm Paper Sheet + Drafting Rulers) -->
      <div 
        :style="{
          transform: `translate(${panX}px, ${panY}px) scale(${zoomScale})`,
          transformOrigin: 'center center'
        }"
        class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[656px] h-[912px] bg-studio-panel shadow-2xl border border-studio-border z-10 transition-transform duration-100 ease-out select-none flex flex-col rounded-sm overflow-hidden"
      >
        <div class="w-full h-full relative flex">
          <!-- Top-Left Corner Block (0,0 point) -->
          <div class="absolute top-0 left-0 w-9 h-9 bg-studio-secondary border-r border-b border-studio-border flex items-center justify-center text-[7px] font-mono text-studio-textMuted select-none z-30 font-bold">
            mm
          </div>

          <!-- Horizontal Ruler (X axis) -->
          <div class="absolute top-0 left-9 right-0 h-9 bg-studio-secondary border-b border-studio-border flex items-center overflow-hidden z-20 select-none">
            <div class="flex w-full h-full relative">
              <div 
                v-for="tick in xTicks" 
                :key="tick.pos" 
                :style="{ left: `${tick.pos}px` }"
                class="absolute bottom-0 flex flex-col items-center h-full justify-end"
              >
                <div :class="['w-[1.2px] bg-studio-borderStrong/60', tick.major ? 'h-3.5' : 'h-1.5']"></div>
                <span v-if="tick.label" class="text-[6.5px] font-mono font-bold text-studio-textMuted absolute bottom-3.5 transform -translate-x-1/2 leading-none">
                  {{ tick.val }}
                </span>
              </div>
            </div>
          </div>

          <!-- Vertical Ruler (Y axis) -->
          <div class="absolute top-9 left-0 bottom-0 w-9 bg-studio-secondary border-r border-studio-border flex flex-col overflow-hidden z-20 select-none">
            <div class="flex-1 w-full relative">
              <div 
                v-for="tick in yTicks" 
                :key="tick.pos" 
                :style="{ top: `${tick.pos}px` }"
                class="absolute right-0 flex items-center w-full justify-end"
              >
                <span v-if="tick.label" class="text-[6.5px] font-mono font-bold text-studio-textMuted absolute right-3.5 transform -translate-y-1/2 leading-none">
                  {{ tick.val }}
                </span>
                <div :class="['h-[1.2px] bg-studio-borderStrong/60', tick.major ? 'w-3.5' : 'w-1.5']"></div>
              </div>
            </div>
          </div>

          <!-- The live template rendered inside an iframe (offset by 36px rulers) -->
          <div class="absolute top-9 left-9 right-0 bottom-0 bg-white overflow-hidden relative">
            <iframe 
              ref="iframeRef"
              class="w-full h-full border-none pointer-events-none bg-white"
              :srcdoc="iframeSrcDoc"
            ></iframe>

            <!-- Coordinate Outlines Overlays -->
            <div 
              v-if="canvasMode !== 'normal'" 
              class="absolute inset-0 bg-transparent pointer-events-auto"
            >
              <div 
                v-for="region in spatialRegions" 
                :key="region.id"
                :style="region.style"
                @click.stop="$emit('select-region', region.id)"
                @mouseenter="$emit('hover-region', region.id)"
                @mouseleave="$emit('hover-region', null)"
                :class="[
                  'absolute box-hover-transition cursor-pointer p-1 text-[8px] font-mono select-none overflow-visible flex flex-col justify-between',
                  activeRegionId === region.id 
                    ? 'marching-ants bg-studio-accent/5 text-studio-accent z-20' 
                    : hoverRegionId === region.id 
                    ? 'border-2 border-studio-accent/40 bg-studio-accent/5 text-studio-accent/80 z-10'
                    : 'border border-studio-borderStrong/30 bg-transparent text-studio-textMuted'
                ]"
              >
                <!-- Label Details shown in coordinate overlay mode -->
                <div v-if="canvasMode === 'coordinates' || activeRegionId === region.id" class="font-bold bg-studio-panel border border-studio-border px-1 py-0.5 rounded text-[7px] flex justify-between items-center w-full shadow-sm text-studio-text">
                  <span class="uppercase font-mono">{{ region.region_type || 'REGION' }}</span>
                  <span>{{ Math.round(region.confidence * 100) }}%</span>
                </div>
                
                <!-- Box coordinates indicator overlay -->
                <span v-if="canvasMode === 'coordinates'" class="text-[6.5px] font-semibold bg-studio-panel border border-studio-border px-1 rounded block self-start shadow-sm text-studio-textSecondary mt-0.5 font-mono">
                  X: {{ Math.round(region.bbox?.[0]) }} Y: {{ Math.round(region.bbox?.[1]) }}
                </span>

                <!-- Floating Contextual Tooling -->
                <div 
                  v-if="activeRegionId === region.id"
                  :class="[
                    'absolute left-0 right-0 h-9 z-30 flex justify-center pointer-events-auto',
                    parseFloat(region.style.top) < 10 ? 'top-full mt-2' : '-top-10'
                  ]"
                  @click.stop
                >
                  <div class="bg-studio-panel border border-studio-border text-studio-text rounded-lg px-2 py-1 text-[10px] font-bold shadow-lg flex items-center space-x-1 select-none pointer-events-auto shrink-0 whitespace-nowrap">
                    <span class="text-[8px] uppercase tracking-wider text-studio-accent font-mono font-black border border-studio-accent/30 rounded px-1">{{ region.region_type }}</span>
                    <button 
                      v-for="pill in getRegionPills(region.region_type)"
                      :key="pill"
                      @click.stop="applyFloatingPill(pill)"
                      class="px-2 py-0.5 hover:bg-studio-secondary rounded border border-studio-border text-studio-textSecondary hover:text-studio-text transition text-[9px]"
                    >
                      {{ pill }}
                    </button>
                    <div class="h-3 w-[1px] bg-studio-border"></div>
                    <button 
                      @click.stop="$emit('trigger-prompt', region.id)"
                      class="px-2 py-0.5 bg-studio-accent text-studio-bg font-black hover:bg-studio-accentHover rounded transition flex items-center space-x-1"
                    >
                      <span>Prompt</span>
                      <span class="text-[8px] font-normal opacity-85 font-mono">⌘K</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  spatialRegions: any[]
  activeRegionId: string | null
  hoverRegionId: string | null
  iframeSrcDoc: string
  docWidth: number
  docHeight: number
}>()

const emit = defineEmits(['select-region', 'hover-region', 'apply-pill', 'trigger-prompt'])

const canvasMode = ref('normal')
const zoomScale = ref(0.8)
const panX = ref(0)
const panY = ref(0)
const isPanning = ref(false)
const startX = ref(0)
const startY = ref(0)
const viewport = ref<HTMLElement | null>(null)

// Ticks computed coordinate map for A4 dimensions
const xTicks = computed(() => {
  const ticks = []
  for (let mm = 0; mm <= 210; mm += 10) {
    const pos = mm * (620 / 210)
    ticks.push({
      pos,
      major: mm % 20 === 0,
      label: mm % 20 === 0,
      val: mm
    })
  }
  return ticks
})

const yTicks = computed(() => {
  const ticks = []
  for (let mm = 0; mm <= 297; mm += 10) {
    const pos = mm * (876 / 297)
    ticks.push({
      pos,
      major: mm % 20 === 0,
      label: mm % 20 === 0,
      val: mm
    })
  }
  return ticks
})

const getRegionPills = (type: string) => {
  if (type === 'header') {
    return ['Align Left', 'Add Logo Spacing', 'Add Faint Border']
  } else if (type === 'table') {
    return ['Alternate Rows', 'Add Grid Borders', 'Align Columns']
  } else if (type === 'totals') {
    return ['Highlight Grand Total', 'Move Labels Right', 'Compact Margins']
  } else if (type === 'footer') {
    return ['Center Text', 'Add Signature Line', 'Add Page Numbers']
  }
  return ['Make Compact', 'Elegant Borders', 'Enlarge Text']
}

const applyFloatingPill = (pillText: string) => {
  const customPrompts: Record<string, string> = {
    'Align Left': 'Align header left',
    'Add Logo Spacing': 'Increase logo spacing',
    'Add Faint Border': 'Add faint border below header',
    'Alternate Rows': 'Add striped background to rows',
    'Add Grid Borders': 'Add border to table grid',
    'Align Columns': 'Align table columns properly',
    'Highlight Grand Total': 'Highlight grand total text in vermilion',
    'Move Labels Right': 'Move total label to right',
    'Compact Margins': 'Compact totals margins',
    'Center Text': 'Center footer text',
    'Add Signature Line': 'Add a signed-by signature line at the bottom',
    'Add Page Numbers': 'Add page numbers inside footer',
    'Make Compact': 'Make layout more compact',
    'Elegant Borders': 'Add elegant page border',
    'Enlarge Text': 'Enlarge body text slightly'
  }
  emit('apply-pill', customPrompts[pillText] || pillText)
}

const zoomIn = () => {
  if (zoomScale.value < 2.0) {
    zoomScale.value = parseFloat((zoomScale.value + 0.1).toFixed(1))
  }
}

const zoomOut = () => {
  if (zoomScale.value > 0.4) {
    zoomScale.value = parseFloat((zoomScale.value - 0.1).toFixed(1))
  }
}

const resetZoomPan = () => {
  zoomScale.value = 0.8
  panX.value = 0
  panY.value = 0
}

const startPan = (e: MouseEvent) => {
  isPanning.value = true
  startX.value = e.clientX - panX.value
  startY.value = e.clientY - panY.value
}

const doPan = (e: MouseEvent) => {
  if (!isPanning.value) return
  panX.value = e.clientX - startX.value
  panY.value = e.clientY - startY.value
}

const endPan = () => {
  isPanning.value = false
}
</script>
