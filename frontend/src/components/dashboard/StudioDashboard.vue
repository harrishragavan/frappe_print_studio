<template>
  <div class="flex-1 flex flex-col lg:flex-row p-6 md:p-8 gap-6 md:gap-8 overflow-y-auto no-scrollbar bg-studio-bg select-none">
    <!-- LEFT PANEL: Create / Import Tools -->
    <div class="flex-1 flex flex-col space-y-6 max-w-2xl">
      <div class="space-y-1.5">
        <h2 class="text-lg font-black text-studio-text tracking-wider uppercase">Create a print format</h2>
        <p class="text-xs text-studio-textSecondary font-semibold">Convert a scanned document, PDF, or image into a production-ready template.</p>
      </div>

      <!-- Blueprint Scanner (when submitting) -->
      <div v-if="isSubmitting" class="flex-1 bg-studio-panel border border-studio-border rounded-3xl p-6 relative flex flex-col items-center justify-center overflow-hidden min-h-[350px] shadow-sm">
        <!-- Blueprint cutting mat backing -->
        <div class="absolute inset-0 opacity-[0.05] bg-[linear-gradient(#2A2B2A_1px,transparent_1px),linear-gradient(90deg,#2A2B2A_1px,transparent_1px)] [background-size:16px_16px]"></div>
        
        <!-- The Blueprint Document Card -->
        <div class="relative w-[220px] aspect-[1/1.414] bg-studio-secondary/40 border-2 border-dashed border-studio-accent/40 rounded-lg overflow-hidden flex flex-col items-center justify-center p-4 shadow-xl z-10">
          <!-- File Symbol -->
          <svg class="h-14 w-14 text-studio-accent/40 animate-pulse mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <span class="text-[9px] font-mono text-studio-accent/70 uppercase tracking-widest font-black">SCANNING BLUEPRINT</span>
          <span class="text-[8px] font-mono text-studio-textMuted mt-1">{{ targetDocType }}</span>

          <!-- The Laser Scanning Beam -->
          <div class="absolute left-0 right-0 h-0.5 bg-studio-accent/80 shadow-[0_0_8px_#F0533A] animate-scan-beam"></div>

          <!-- Random blueprint grid highlight outlines flashing -->
          <div class="absolute inset-0 pointer-events-none">
            <div class="absolute border border-studio-accent/30 w-16 h-8 top-12 left-4 animate-flash-region"></div>
            <div class="absolute border border-studio-accent/30 w-24 h-12 top-28 right-6 animate-flash-region-delayed"></div>
            <div class="absolute border border-studio-accent/30 w-12 h-6 bottom-8 left-8 animate-flash-region-more-delayed"></div>
          </div>
        </div>
        
        <div class="mt-6 text-center z-10">
          <p class="text-xs font-mono text-studio-textMuted uppercase tracking-widest font-bold">ANALYZING SPECIFICATION</p>
          <p class="text-[10px] text-studio-accent font-black uppercase mt-1 animate-pulse">{{ pipelineSteps[activeStepIndex] }}</p>
        </div>
      </div>

      <!-- Standard dropzone & parameters setup (when NOT submitting) -->
      <template v-else>
        <!-- Dropzone Component -->
        <UploadDropzone 
          :model-value="selectedFile"
          @update:model-value="$emit('update:selectedFile', $event)"
        />

        <!-- Searchable DocType Selector -->
        <div class="space-y-2">
          <label class="block text-[10px] font-bold uppercase tracking-wider text-studio-textSecondary">Target DocType</label>
          <div class="relative">
            <input 
              type="text" 
              v-model="docTypeSearch"
              placeholder="Search Target DocType (e.g. Sales Invoice, Purchase Order...)"
              class="w-full bg-studio-panel border border-studio-border rounded-xl py-3 px-4 text-studio-text text-xs focus:outline-none focus:border-studio-accent focus:ring-1 focus:ring-studio-accent"
            />
            <!-- Filter Dropdown results -->
            <div 
              v-if="docTypeSearch && filteredDocTypes.length > 0"
              class="absolute z-10 w-full mt-1.5 bg-studio-panel border border-studio-border rounded-xl shadow-lg max-h-48 overflow-y-auto custom-scrollbar"
            >
              <div 
                v-for="option in filteredDocTypes"
                :key="option"
                @click="selectDocType(option)"
                class="px-4 py-2.5 hover:bg-studio-elevated text-xs font-semibold text-studio-textSecondary hover:text-studio-text cursor-pointer transition flex items-center justify-between"
              >
                <span>{{ option }}</span>
                <span class="text-[9px] uppercase tracking-wider text-studio-textMuted font-mono">Frappe Schema</span>
              </div>
            </div>
          </div>
          
          <!-- Active Target Pill badge -->
          <div class="flex items-center space-x-2.5 bg-studio-panel border border-studio-border rounded-xl p-3">
            <span class="text-[9px] text-studio-textMuted uppercase font-bold tracking-wider">Active Target:</span>
            <span class="text-xs font-bold text-studio-accent">{{ targetDocType }}</span>
          </div>
        </div>

        <!-- Action Panel: Edit Existing Print Format -->
        <div class="bg-studio-panel rounded-2xl p-5 border border-studio-border space-y-4">
          <div class="border-b border-studio-border pb-2.5">
            <h4 class="text-xs font-black text-studio-text uppercase tracking-widest">Edit Existing Print Format</h4>
            <p class="text-[10px] text-studio-textMuted font-semibold mt-1">Refine and overwrite layouts loaded directly from your site database.</p>
          </div>

          <div class="flex flex-col sm:flex-row gap-3">
            <select 
              :value="selectedPrintFormatName"
              @change="$emit('update:selectedPrintFormatName', ($event.target as HTMLSelectElement).value)"
              class="flex-1 bg-studio-bg border border-studio-border rounded-xl py-2 px-3 text-studio-text text-xs focus:outline-none focus:border-studio-accent"
            >
              <option value="">-- Choose format --</option>
              <option 
                v-for="pf in printFormatsList" 
                :key="pf.name" 
                :value="pf.name"
              >
                {{ pf.name }} ({{ pf.doc_type }})
              </option>
            </select>

            <button 
              @click="$emit('load-print-format')"
              :disabled="!selectedPrintFormatName || isLoadingPrintFormat"
              class="px-5 py-2 bg-studio-accent hover:bg-studio-accentHover disabled:bg-studio-border disabled:text-studio-textMuted text-studio-bg rounded-xl text-[10px] font-black uppercase tracking-wider transition shrink-0 select-none flex items-center justify-center space-x-1"
            >
              <span v-if="isLoadingPrintFormat" class="animate-spin rounded-full h-3.5 w-3.5 border-2 border-studio-bg border-t-transparent"></span>
              <span>Load</span>
            </button>
          </div>
        </div>

        <!-- Execution button when file is ready -->
        <div v-if="selectedFile" class="pt-2">
          <button 
            @click="$emit('submit-job')"
            :disabled="isSubmitting"
            class="w-full bg-studio-accent hover:bg-studio-accentHover disabled:bg-studio-border disabled:text-studio-textMuted text-studio-bg font-black uppercase tracking-widest text-xs py-4 px-6 rounded-2xl transition shadow-lg flex items-center justify-center space-x-2.5"
          >
            <span v-if="isSubmitting" class="animate-spin rounded-full h-4 w-4 border-2 border-studio-bg border-t-transparent"></span>
            <span>Start Job / Execute Pipeline</span>
          </button>
        </div>
      </template>
    </div>

    <!-- RIGHT PANEL: Stats, Pipelines & Activity Logs -->
    <div class="w-full lg:w-80 flex flex-col space-y-6 shrink-0">
      <!-- Active LLM Engine Panel -->
      <div class="bg-studio-panel rounded-2xl p-5 border border-studio-border flex flex-col justify-between min-h-[160px]">
        <div>
          <p class="text-[9px] text-studio-textMuted font-bold uppercase tracking-widest">Active AI Engine</p>
          <h4 class="text-sm font-black text-studio-text mt-1.5 uppercase">{{ activeProviderSettings.llm_provider || 'Mock' }}</h4>
        </div>
        <div class="mt-4 pt-3 border-t border-studio-border/60">
          <p class="text-[9px] font-mono text-studio-textMuted truncate">MODEL: {{ activeProviderSettings.model_name || 'System Standard' }}</p>
          <div class="flex justify-between items-center mt-2.5">
            <span class="w-2.5 h-2.5 rounded-full bg-studio-accent"></span>
            <span class="text-[9px] font-bold text-studio-textSecondary uppercase tracking-widest">Connected</span>
          </div>
        </div>
      </div>

      <!-- Pipeline Progress Details (Visible during execution) -->
      <div 
        v-if="isSubmitting"
        class="bg-studio-panel rounded-2xl p-5 border border-studio-accent/20 space-y-3.5"
      >
        <h4 class="text-[10px] font-black text-studio-accent uppercase tracking-widest">Document Analysis Pipeline</h4>
        <div class="space-y-2.5">
          <div 
            v-for="(step, idx) in pipelineSteps" 
            :key="idx"
            class="flex items-center space-x-2 text-xs"
          >
            <span 
              :class="[
                'w-1.5 h-1.5 rounded-full shrink-0',
                idx < activeStepIndex ? 'bg-studio-accent' :
                idx === activeStepIndex ? 'bg-studio-accent animate-pulse' :
                'bg-studio-border'
              ]"
            ></span>
            <span 
              :class="[
                'font-semibold',
                idx < activeStepIndex ? 'text-studio-textSecondary' :
                idx === activeStepIndex ? 'text-studio-text font-bold' :
                'text-studio-textMuted'
              ]"
            >
              {{ step }}
            </span>
          </div>
        </div>
      </div>

      <!-- Recent timeline logs -->
      <RecentActivity 
        :jobs-list="jobsList"
        @open-job="$emit('open-job', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import UploadDropzone from './UploadDropzone.vue'
import RecentActivity from './RecentActivity.vue'

const props = defineProps<{
  selectedFile: File | null
  targetDocType: string
  selectedPrintFormatName: string
  isLoadingPrintFormat: boolean
  printFormatsList: any[]
  activeProviderSettings: any
  jobsList: any[]
  isSubmitting: boolean
}>()

const emit = defineEmits([
  'update:selectedFile',
  'update:targetDocType',
  'update:selectedPrintFormatName',
  'load-print-format',
  'submit-job',
  'open-job'
])

const docTypeSearch = ref('')
const docTypes = ['Sales Invoice', 'Purchase Order', 'Quotation', 'Delivery Note', 'Purchase Invoice', 'Sales Order']

const filteredDocTypes = computed(() => {
  if (!docTypeSearch.value.trim()) return []
  const q = docTypeSearch.value.toLowerCase()
  return docTypes.filter(opt => opt.toLowerCase().includes(q))
})

const selectDocType = (val: string) => {
  emit('update:targetDocType', val)
  docTypeSearch.value = ''
}

// Pipeline progress step array
const pipelineSteps = [
  'Document loaded & parsed',
  'OCR text coordinates mapped',
  'Semantic layout zones detected',
  'Tabular grid layout extracted',
  'Fields mapped to target database schema',
  'Jinja & CSS styling generated',
  'Rendered live template preview'
]

// Cycle current step animation
const activeStepIndex = computed(() => {
  if (!props.isSubmitting) return 0
  // Simulating animation states
  const processingJobs = props.jobsList.filter(j => j.status === 'Processing' || j.status === 'Pending')
  if (processingJobs.length > 0) {
    return Math.min(4, Math.floor(Date.now() / 3000) % 7)
  }
  return 5
})
</script>
