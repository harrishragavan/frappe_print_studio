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
      <!-- Subtle dot grid backing -->
      <div class="absolute inset-0 opacity-[0.03] bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:20px_20px] pointer-events-none"></div>

      <!-- Transform wrapper (Warm Paper Sheet) -->
      <div 
        :style="{
          transform: `translate(${panX}px, ${panY}px) scale(${zoomScale})`,
          transformOrigin: 'center center'
        }"
        class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[620px] aspect-[1/1.414] bg-studio-paper shadow-2xl border border-studio-borderStrong/15 transition-transform duration-100 ease-out select-none flex flex-col rounded-sm overflow-hidden"
      >
        <!-- The live template rendered inside an iframe -->
        <div class="flex-1 w-full h-full relative">
          <iframe 
            ref="iframeRef"
            class="w-full h-full border-none pointer-events-none"
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
                'absolute border box-hover-transition cursor-pointer p-1 text-[8px] font-mono select-none overflow-hidden flex flex-col justify-between',
                activeRegionId === region.id 
                  ? 'border-studio-accent bg-studio-accent/10 text-studio-accent z-20' 
                  : hoverRegionId === region.id 
                  ? 'border-studio-accent/40 bg-studio-accent/5 text-studio-accent/80 z-10'
                  : 'border-studio-borderStrong/40 bg-transparent text-studio-textMuted'
              ]"
            >
              <!-- Label Details shown in coordinate overlay mode -->
              <div v-if="canvasMode === 'coordinates' || activeRegionId === region.id" class="font-bold bg-studio-bg/90 border border-studio-border/50 px-1 py-0.5 rounded text-[7px] flex justify-between items-center w-full">
                <span class="uppercase">{{ region.region_type || 'REGION' }}</span>
                <span>{{ Math.round(region.confidence * 100) }}%</span>
              </div>
              
              <!-- Box coordinates indicator overlay -->
              <span v-if="canvasMode === 'coordinates'" class="text-[6.5px] font-semibold bg-studio-panel/90 border border-studio-border/30 px-1 rounded block self-start">
                X: {{ Math.round(region.bbox?.[0]) }} Y: {{ Math.round(region.bbox?.[1]) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{
  spatialRegions: any[]
  activeRegionId: string | null
  hoverRegionId: string | null
  iframeSrcDoc: string
  docWidth: number
  docHeight: number
}>()

defineEmits(['select-region', 'hover-region'])

const canvasMode = ref('normal')
const zoomScale = ref(0.8)
const panX = ref(0)
const panY = ref(0)
const isPanning = ref(false)
const startX = ref(0)
const startY = ref(0)
const viewport = ref<HTMLElement | null>(null)

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
