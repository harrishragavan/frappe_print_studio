<template>
  <div class="print-studio-container w-screen h-screen flex flex-col bg-studio-bg text-studio-text font-sans overflow-hidden">
    <!-- Compact Studio Shell TopBar -->
    <TopBar 
      :selected-job-name="selectedJobName"
      :selected-job="selectedJob"
      :active-view-mode="activeViewMode"
      :is-submitting="isSubmitting"
      :is-deploying="isDeploying"
      :boot-user="bootUser"
      @go-home="selectedJobName = null"
      @toggle-settings="showSettingsModal = true"
      @set-view-mode="activeViewMode = $event"
      @deploy="deployJob"
      @undo="handleUndo"
      @redo="handleRedo"
      @trigger-spotlight="showSpotlightModal = true"
    />

    <!-- Main Workspace body -->
    <div class="flex-1 flex min-h-0 relative">
      <!-- VIEW 1: STUDIO DASHBOARD -->
      <StudioDashboard
        v-if="!selectedJobName"
        v-model:selected-file="selectedFile"
        v-model:target-doc-type="targetDocType"
        v-model:selected-print-format-name="selectedPrintFormatName"
        :is-loading-print-format="isLoadingPrintFormat"
        :print-formats-list="printFormatsList"
        :active-provider-settings="settingsForm"
        :jobs-list="jobsList"
        :is-submitting="isSubmitting"
        @load-print-format="loadPrintFormat"
        @submit-job="submitJob"
        @open-job="openJob"
      />

      <!-- VIEW 2: WORKSPACE (Figma-style workbench canvas with left layer sidebar and right properties inspector) -->
      <div v-else class="flex-1 flex min-h-0 relative">
        <!-- Mode A: Design View -->
        <div v-if="activeViewMode === 'design'" class="flex-1 flex min-h-0 relative">
          <!-- Col 1: Layers Panel -->
          <div class="w-64 shrink-0 hidden md:block">
            <LayersPanel 
              :spatial-regions="spatialRegions"
              :active-region-id="selectedRegionId"
              :hover-region-id="hoverRegionId"
              @select-region="selectRegion"
              @hover-region="hoverRegion"
            />
          </div>

          <!-- Col 2: Central Document Canvas & bottom AI command -->
          <div class="flex-1 flex flex-col min-h-0 relative">
            <DocumentCanvas 
              :spatial-regions="spatialRegions"
              :active-region-id="selectedRegionId"
              :hover-region-id="hoverRegionId"
              :iframe-src-doc="debouncedSrcDoc"
              :doc-width="docWidth"
              :doc-height="docHeight"
              @select-region="selectRegion"
              @hover-region="hoverRegion"
              @apply-pill="applyFloatingPill"
              @trigger-prompt="triggerSpotlightForRegion"
            />
          </div>

          <!-- Col 3: Inspector Panel -->
          <div class="w-80 shrink-0 hidden lg:block border-l border-studio-border">
            <InspectorPanel 
              :spatial-regions="spatialRegions"
              :selected-region-id="selectedRegionId"
              :selected-job="selectedJob"
            />
          </div>
        </div>

        <!-- Mode B: Code View -->
        <div v-else class="flex-1 flex min-h-0 relative">
          <CodeWorkspace 
            v-model:generated-jinja="selectedJob.generated_jinja"
            v-model:generated-css="selectedJob.generated_css"
            :iframe-src-doc="debouncedSrcDoc"
          />
        </div>
      </div>
    </div>

    <!-- Global Settings Modal Dialog -->
    <LLMSettingsModal 
      v-model="showSettingsModal"
      :settings="settingsForm"
      @save="saveSettings"
    />

    <!-- Spotlight Command Palette Modal Dialog -->
    <Dialog
      v-model="showSpotlightModal"
      :options="{
        title: 'Typesetter\'s Command Palette',
        size: 'md'
      }"
    >
      <template #body>
        <div class="space-y-4 text-studio-text p-4 bg-studio-panel rounded-2xl flex flex-col max-h-[480px] overflow-hidden select-none">
          <!-- Selection info bar -->
          <div class="flex items-center justify-between bg-studio-secondary px-3 py-2 rounded-xl border border-studio-border text-xs">
            <span class="text-studio-textSecondary font-semibold">Active Focus:</span>
            <span v-if="selectedRegionId" class="font-mono text-studio-accent font-bold uppercase">
              Region: {{ spatialRegions.find(r => r.id === selectedRegionId)?.region_type || selectedRegionId }}
            </span>
            <span v-else class="font-mono text-studio-textSecondary uppercase">
              Global Document
            </span>
          </div>

          <!-- Prompt Command Input -->
          <div class="relative">
            <input 
              type="text" 
              v-model="chatInput"
              @keyup.enter="submitSpotlightPrompt"
              placeholder="Ask the Typesetting Apprentice to refine layout... (e.g. Add signed-by signature line)" 
              class="w-full bg-studio-bg border border-studio-border rounded-xl pl-4 pr-16 py-3 text-xs focus:outline-none focus:border-studio-accent"
              ref="spotlightInputRef"
            />
            <button
              @click="submitSpotlightPrompt"
              :disabled="isRefining || !chatInput.trim()"
              class="absolute right-2 top-2 px-3.5 py-1.5 bg-studio-accent text-studio-bg hover:bg-studio-accentHover disabled:bg-studio-border disabled:text-studio-textMuted rounded-lg text-[10px] font-bold uppercase transition"
            >
              Run
            </button>
          </div>

          <!-- Command Modifiers list -->
          <div class="space-y-1">
            <p class="text-[9px] uppercase tracking-widest text-studio-textMuted font-bold">Quick Command Modifiers</p>
            <div class="grid grid-cols-2 gap-2">
              <button 
                v-for="cmd in spotlightCommands" 
                :key="cmd.text"
                @click="applySpotlightCommand(cmd.text)"
                class="flex items-center justify-between p-2.5 bg-studio-bg hover:bg-studio-secondary border border-studio-border rounded-xl text-left transition group"
              >
                <div>
                  <p class="text-xs font-bold text-studio-textSecondary group-hover:text-studio-text leading-tight">{{ cmd.title }}</p>
                  <p class="text-[9px] text-studio-textMuted mt-0.5">{{ cmd.desc }}</p>
                </div>
                <span class="text-[9px] font-mono text-studio-accent bg-studio-secondary px-1.5 py-0.5 rounded border border-studio-border group-hover:bg-studio-accent group-hover:text-studio-bg transition">
                  {{ cmd.shortcut }}
                </span>
              </button>
            </div>
          </div>

          <!-- Attachments Row in Spotlight -->
          <div class="pt-2 border-t border-studio-border flex justify-between items-center text-xs">
            <div class="flex items-center space-x-2 text-studio-textSecondary">
              <svg class="h-4 w-4 text-studio-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              <span class="font-bold">{{ chatAttachments.length }} references attached</span>
            </div>
            <button 
              @click="openSiteFilesSelector"
              class="px-2.5 py-1 hover:bg-studio-secondary border border-studio-border rounded-lg text-[9px] font-bold uppercase tracking-wider text-studio-textSecondary transition"
            >
              Add Reference
            </button>
          </div>
        </div>
      </template>
    </Dialog>

    <!-- Site Files Selector Modal Dialog -->
    <Dialog
      v-model="showSiteFilesModal"
      :options="{
        title: 'Select File from Site',
        size: 'sm'
      }"
    >
      <template #body>
        <div class="space-y-4 text-studio-text p-4 bg-studio-panel rounded-2xl flex flex-col max-h-[450px] overflow-hidden select-none">
          <div class="relative">
            <svg class="absolute left-4 top-3.5 h-4 w-4 text-studio-textMuted" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input 
              type="text" 
              v-model="fileSearchQuery"
              placeholder="Search files by name..." 
              class="w-full bg-studio-bg border border-studio-border rounded-xl pl-11 pr-4 py-2 text-xs focus:outline-none focus:border-studio-accent"
            />
          </div>

          <div class="flex-1 overflow-y-auto min-h-0 divide-y divide-studio-border border border-studio-border rounded-xl bg-studio-bg/40">
            <div v-if="filteredSiteFiles.length === 0" class="p-8 text-center text-studio-textMuted text-xs font-semibold">
              No files found on site.
            </div>
            <div 
              v-for="file in filteredSiteFiles" 
              :key="file.name"
              @click="attachSiteFile(file)"
              class="flex items-center justify-between p-3 hover:bg-studio-elevated cursor-pointer transition"
            >
              <div class="flex items-center space-x-3 truncate">
                <div class="w-8 h-8 rounded-lg bg-studio-bg border border-studio-border flex items-center justify-center text-studio-textMuted shrink-0 shadow-sm">
                  <svg class="h-4 w-4 text-studio-accent" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div class="truncate text-left">
                  <p class="text-xs font-black text-studio-text truncate leading-tight">{{ file.file_name }}</p>
                  <p class="text-[9px] text-studio-textMuted font-mono truncate mt-0.5">{{ file.file_url }}</p>
                </div>
              </div>
              <span v-if="file.file_size" class="text-[9px] font-mono text-studio-textSecondary bg-studio-elevated px-2 py-0.5 rounded border border-studio-border shadow-sm shrink-0">
                {{ Math.round(file.file_size / 1024) }} KB
              </span>
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-3 border-t border-studio-border shrink-0">
            <button 
              @click="showSiteFilesModal = false"
              class="px-4 py-2 bg-studio-secondary hover:bg-studio-elevated text-studio-textSecondary rounded-lg text-xs font-bold uppercase tracking-wider transition select-none"
            >
              Cancel
            </button>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { Dialog, createResource } from 'frappe-ui'

// Child components
import TopBar from '../components/shell/TopBar.vue'
import LLMSettingsModal from '../components/shell/LLMSettingsModal.vue'
import StudioDashboard from '../components/dashboard/StudioDashboard.vue'
import LayersPanel from '../components/canvas/LayersPanel.vue'
import InspectorPanel from '../components/canvas/InspectorPanel.vue'
import DocumentCanvas from '../components/canvas/DocumentCanvas.vue'
import CodeWorkspace from '../components/code/CodeWorkspace.vue'

// State variables
const bootUser = ref(window.user || 'Guest')
const showSettingsModal = ref(false)
const selectedFile = ref<File | null>(null)
const targetDocType = ref('Sales Invoice')
const isSubmitting = ref(false)
const selectedJobName = ref<string | null>(null)
const jobsList = ref<any[]>([])

const activeViewMode = ref<'design' | 'code'>('design')
const selectedRegionId = ref<string | null>(null)
const hoverRegionId = ref<string | null>(null)

// History Undo/Redo stack
const historyStack = ref<{ jinja: string; css: string }[]>([])
const historyIndex = ref(-1)

const pushHistoryState = (jinja: string, css: string) => {
  if (historyIndex.value < historyStack.value.length - 1) {
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
  }
  historyStack.value.push({ jinja, css })
  historyIndex.value++
}

const handleUndo = () => {
  if (historyIndex.value > 0) {
    historyIndex.value--
    const state = historyStack.value[historyIndex.value]
    selectedJob.value.generated_jinja = state.jinja
    selectedJob.value.generated_css = state.css
  }
}

const handleRedo = () => {
  if (historyIndex.value < historyStack.value.length - 1) {
    historyIndex.value++
    const state = historyStack.value[historyIndex.value]
    selectedJob.value.generated_jinja = state.jinja
    selectedJob.value.generated_css = state.css
  }
}

// Region Selectors
const selectRegion = (id: string | null) => {
  selectedRegionId.value = id
}
const hoverRegion = (id: string | null) => {
  hoverRegionId.value = id
}

// Chat Input / attachments state
const chatInput = ref('')
const chatAttachments = ref<{ name: string; file_url: string; type: string }[]>([])
const isUploadingAttachment = ref(false)

// Site print formats state
const selectedPrintFormatName = ref('')
const isLoadingPrintFormat = ref(false)
const printFormatsList = ref<any[]>([])

// Site files state
const showSiteFilesModal = ref(false)
const siteFilesList = ref<any[]>([])
const fileSearchQuery = ref('')

// Form states
const settingsForm = ref({
  llm_provider: 'Mock',
  api_key: '',
  api_base: '',
  model_name: ''
})

// Current Job Data
const selectedJob = ref<any>({
  name: '',
  status: '',
  intermediate_schema: {},
  generated_html: '',
  generated_css: '',
  generated_jinja: '',
  field_mappings: []
})

// Active Provider settings from backend
const activeProviderSettings = ref({
  llm_provider: 'Mock',
  api_base: '',
  model_name: '',
  has_api_key: false
})

// Computed values
const docWidth = computed(() => {
  const schema = selectedJob.value.intermediate_schema
  return schema?.metadata?.width || 612.0
})

const docHeight = computed(() => {
  const schema = selectedJob.value.intermediate_schema
  return schema?.metadata?.height || 792.0
})

const spatialRegions = computed(() => {
  const schema = selectedJob.value.intermediate_schema
  if (!schema || !schema.regions) return []
  
  const widthVal = docWidth.value
  const heightVal = docHeight.value

  return schema.regions.map((r: any) => {
    const textSnippet = r.contained_blocks ? r.contained_blocks.map((b: any) => b.text).join(' ') : ''
    
    let style = {}
    if (r.bbox && widthVal && heightVal) {
      const left = (r.bbox[0] / widthVal) * 100
      const top = (r.bbox[1] / heightVal) * 100
      const width = ((r.bbox[2] - r.bbox[0]) / widthVal) * 100
      const height = ((r.bbox[3] - r.bbox[1]) / heightVal) * 100
      style = {
        left: `${left}%`,
        top: `${top}%`,
        width: `${width}%`,
        height: `${height}%`
      }
    }

    return {
      id: r.id,
      region_type: r.region_type,
      bbox: r.bbox,
      confidence: r.confidence || 1.0,
      text_snippet: textSnippet,
      style: style
    }
  })
})

const iframeSrcDoc = computed(() => {
  const html = selectedJob.value.generated_jinja || selectedJob.value.generated_html || ''
  const css = selectedJob.value.generated_css || ''
  return `
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>${css}</style>
      </head>
      <body style="margin:0; padding:10px; background:#f1f5f9;">
        ${html}
      </body>
    </html>
  `
})

const debouncedSrcDoc = ref('')
let debounceTimeout: any = null

watch(iframeSrcDoc, (newVal) => {
  if (debounceTimeout) {
    clearTimeout(debounceTimeout)
  }
  debounceTimeout = setTimeout(() => {
    debouncedSrcDoc.value = newVal
  }, 400)
}, { immediate: true })

watch(() => selectedJob.value?.name, (newName) => {
  if (newName) {
    if (debounceTimeout) clearTimeout(debounceTimeout)
    debouncedSrcDoc.value = iframeSrcDoc.value
  }
})

// Resources & APIs
const getSettingsResource = createResource({
  url: 'frappe_print_studio.frappe_print_studio.api.get_llm_settings',
  onSuccess(data) {
    activeProviderSettings.value = data
    settingsForm.value.llm_provider = data.llm_provider
    settingsForm.value.api_base = data.api_base
    settingsForm.value.model_name = data.model_name
  }
})

const saveSettingsResource = createResource({
  url: 'frappe_print_studio.frappe_print_studio.api.save_llm_settings'
})

const listJobsResource = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Print Studio Job',
    fields: ['name', 'document_file', 'target_doctype', 'status', 'creation'],
    order_by: 'creation desc'
  },
  onSuccess(data) {
    jobsList.value = data
    if (data && Array.isArray(data)) {
      data.forEach((job: any) => {
        if (job.status === 'Processing' || job.status === 'Pending') {
          const createdTime = new Date(job.creation.replace(' ', 'T')).getTime()
          const nowTime = new Date().getTime()
          const minutesDiff = (nowTime - createdTime) / 60000
          if (minutesDiff < 15) {
            pollJobStatus(job.name)
          }
        }
      })
    }
  }
})

const createJobResource = createResource({
  url: 'frappe_print_studio.frappe_print_studio.api.create_job'
})

const getJobResource = createResource({
  url: 'frappe_print_studio.frappe_print_studio.api.get_job'
})

const deployPrintFormatResource = createResource({
  url: 'frappe_print_studio.frappe_print_studio.api.deploy_print_format'
})

const refineLayoutResource = createResource({
  url: 'frappe_print_studio.frappe_print_studio.api.refine_layout'
})

const listPrintFormatsResource = createResource({
  url: 'frappe_print_studio.frappe_print_studio.api.get_custom_print_formats',
  onSuccess(data) {
    printFormatsList.value = data || []
  }
})

const listSiteFilesResource = createResource({
  url: 'frappe_print_studio.frappe_print_studio.api.get_site_files',
  onSuccess(data) {
    siteFilesList.value = data || []
  }
})

const createJobFromPrintFormatResource = createResource({
  url: 'frappe_print_studio.frappe_print_studio.api.create_job_from_print_format'
})

// Methods
const loadJobsList = () => {
  listJobsResource.fetch()
}

const loadActiveSettings = () => {
  getSettingsResource.fetch()
}

// Spotlight & keyboard states
const showSpotlightModal = ref(false)
const spotlightInputRef = ref<HTMLInputElement | null>(null)

const spotlightCommands = computed(() => {
  if (selectedRegionId.value) {
    const region = spatialRegions.value.find(r => r.id === selectedRegionId.value)
    if (region && region.region_type === 'header') {
      return [
        { title: 'Align Header Left', desc: 'Move all header elements to the left margin', text: 'Align header left', shortcut: '/left' },
        { title: 'Increase Logo Spacing', desc: 'Add more vertical space after logo/branding', text: 'Increase logo spacing', shortcut: '/space' },
        { title: 'Add Header Line', desc: 'Draw a subtle horizontal border below the header', text: 'Add faint border below header', shortcut: '/line' },
        { title: 'Make Header Bold', desc: 'Increase text weight of main header titles', text: 'Make header bold', shortcut: '/bold' }
      ]
    } else if (region && region.region_type === 'table') {
      return [
        { title: 'Striped Grid Rows', desc: 'Add alternate row light-slate backgrounds', text: 'Add striped background to rows', shortcut: '/stripe' },
        { title: 'Add Grid Borders', desc: 'Draw thin, crisp grid lines around columns', text: 'Add border to table grid', shortcut: '/border' },
        { title: 'Align Columns', desc: 'Left-align labels, right-align amount columns', text: 'Align table columns properly', shortcut: '/align' },
        { title: 'Remove Rates', desc: 'Hide item unit rates and display quantities only', text: 'Remove item rates', shortcut: '/norate' }
      ]
    } else if (region && region.region_type === 'totals') {
      return [
        { title: 'Highlight Grand Total', desc: 'Enlarge total text and color it Vermilion', text: 'Highlight grand total text in vermilion', shortcut: '/total' },
        { title: 'Right Align Labels', desc: 'Push summary calculations to the right margin', text: 'Move total label to right', shortcut: '/right' },
        { title: 'Compact Margins', desc: 'Minimize spacing to pull totals upward', text: 'Compact totals margins', shortcut: '/tight' },
        { title: 'Add Double Line', desc: 'Draw classic accounting double borders below total', text: 'Add double line below grand total', shortcut: '/double' }
      ]
    }
  }
  return [
    { title: 'Add Page Border', desc: 'Apply a thin drafting-mat border around pages', text: 'Add elegant page border', shortcut: '/border' },
    { title: 'Compact Layout', desc: 'Tighten overall vertical margins and padding', text: 'Make layout more compact', shortcut: '/compact' },
    { title: 'Enlarge Text', desc: 'Increase body font sizing for accessibility', text: 'Enlarge body text slightly', shortcut: '/larger' },
    { title: 'Signature Block', desc: 'Insert an elegant signed-by signature line', text: 'Add a signed-by signature line at the bottom', shortcut: '/sign' }
  ]
})

const applySpotlightCommand = (cmdText: string) => {
  chatInput.value = cmdText
  submitSpotlightPrompt()
}

const submitSpotlightPrompt = () => {
  showSpotlightModal.value = false
  refineJob()
}

const applyFloatingPill = (pillText: string) => {
  chatInput.value = pillText
  refineJob()
}

const triggerSpotlightForRegion = (regionId: string) => {
  selectedRegionId.value = regionId
  showSpotlightModal.value = true
  nextTick(() => {
    spotlightInputRef.value?.focus()
  })
}

const handleKeyDown = (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    if (selectedJobName.value) {
      showSpotlightModal.value = !showSpotlightModal.value
      if (showSpotlightModal.value) {
        nextTick(() => {
          spotlightInputRef.value?.focus()
        })
      }
    }
  }
}

onMounted(() => {
  loadJobsList()
  loadActiveSettings()
  listPrintFormatsResource.fetch()
  window.addEventListener('keydown', handleKeyDown)
})

const saveSettings = async (formData: any) => {
  await saveSettingsResource.submit({
    llm_provider: formData.llm_provider,
    api_key: formData.api_key,
    api_base: formData.api_base,
    model_name: formData.model_name
  })
  showSettingsModal.value = false
  loadActiveSettings()
}

const loadPrintFormat = async () => {
  if (!selectedPrintFormatName.value) return
  isLoadingPrintFormat.value = true
  try {
    const res = await createJobFromPrintFormatResource.submit({
      print_format_name: selectedPrintFormatName.value
    })
    selectedPrintFormatName.value = ''
    loadJobsList()
    openJob(res.job_name)
  } catch (err: any) {
    alert('Failed to load print format: ' + err.message)
  } finally {
    isLoadingPrintFormat.value = false
  }
}

const openSiteFilesSelector = () => {
  fileSearchQuery.value = ''
  listSiteFilesResource.fetch()
  showSiteFilesModal.value = true
}

const attachSiteFile = (file: any) => {
  chatAttachments.value.push({
    name: file.file_name,
    file_url: file.file_url,
    type: file.file_name.split('.').pop() || 'unknown'
  })
  showSiteFilesModal.value = false
}

const filteredSiteFiles = computed(() => {
  if (!fileSearchQuery.value.trim()) {
    return siteFilesList.value
  }
  const q = fileSearchQuery.value.toLowerCase()
  return siteFilesList.value.filter((f: any) => 
    f.file_name.toLowerCase().includes(q) || f.file_url.toLowerCase().includes(q)
  )
})

const uploadFile = async (file: File): Promise<{ name: string; file_url: string }> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_private', '0')
  formData.append('folder', 'Home')
  
  const csrfToken = window.csrf_token || (window as any).boot?.csrf_token
  
  const response = await fetch('/api/method/upload_file', {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'X-Frappe-CSRF-Token': csrfToken || ''
    },
    body: formData
  })
  
  if (!response.ok) {
    throw new Error('File upload failed')
  }
  
  const data = await response.json()
  if (!data.message || !data.message.name) {
    throw new Error('File upload did not return document name')
  }
  
  return {
    name: data.message.name,
    file_url: data.message.file_url
  }
}

const handleAttachmentUpload = async (file: File) => {
  isUploadingAttachment.value = true
  try {
    const res = await uploadFile(file)
    chatAttachments.value.push({
      name: file.name,
      file_url: res.file_url,
      type: file.type
    })
  } catch (err: any) {
    alert('Failed to upload attachment: ' + err.message)
  } finally {
    isUploadingAttachment.value = false
  }
}

const removeAttachment = (index: number) => {
  chatAttachments.value.splice(index, 1)
}

const submitJob = async () => {
  if (!selectedFile.value) return
  
  isSubmitting.value = true
  try {
    const fileDoc = await uploadFile(selectedFile.value)
    const result = await createJobResource.submit({
      file_url: fileDoc.name,
      target_doctype: targetDocType.value
    })
    selectedFile.value = null
    loadJobsList()
    pollJobStatus(result.job_name)
  } catch (err: any) {
    alert('Failed to process file: ' + err.message)
    isSubmitting.value = false
  }
}

const activeIntervals = new Map<string, any>()

const clearJobPoller = (jobName: string) => {
  const interval = activeIntervals.get(jobName)
  if (interval) {
    clearInterval(interval)
    activeIntervals.delete(jobName)
  }
}

const pollJobStatus = (jobName: string) => {
  if (activeIntervals.has(jobName)) return

  let attempts = 0
  const interval = setInterval(async () => {
    attempts++
    try {
      const jobResult = await getJobResource.submit({ job_name: jobName })
      loadJobsList()

      if (jobResult.status === 'Completed') {
        clearJobPoller(jobName)
        isSubmitting.value = false
        openJob(jobName)
      } else if (jobResult.status === 'Failed') {
        clearJobPoller(jobName)
        isSubmitting.value = false
        alert('AI Pipeline processing failed: ' + jobResult.error_message)
      } else if (attempts > 60) {
        clearJobPoller(jobName)
        isSubmitting.value = false
        alert('Analysis timeout. Please check job status on dashboard.')
      }
    } catch (err) {
      if (attempts > 60) {
        clearJobPoller(jobName)
        isSubmitting.value = false
      }
    }
  }, 2000)

  activeIntervals.set(jobName, interval)
}

onBeforeUnmount(() => {
  for (const [jobName, interval] of activeIntervals.entries()) {
    clearInterval(interval)
  }
  activeIntervals.clear()
  window.removeEventListener('keydown', handleKeyDown)
})

const openJob = async (jobName: string) => {
  const jobResult = await getJobResource.submit({ job_name: jobName })
  selectedJob.value = jobResult
  selectedJobName.value = jobName
  
  // Set initial view state and history stack
  activeViewMode.value = 'design'
  historyStack.value = [{ 
    jinja: jobResult.generated_jinja || jobResult.generated_html || '', 
    css: jobResult.generated_css || '' 
  }]
  historyIndex.value = 0
}

const isDeploying = ref(false)
const deployJob = async () => {
  if (!selectedJob.value) return
  isDeploying.value = true
  try {
    const result = await deployPrintFormatResource.submit({
      job_name: selectedJob.value.name,
      html: selectedJob.value.generated_jinja || selectedJob.value.generated_html,
      css: selectedJob.value.generated_css
    })
    alert(result.message || 'Print Format deployed successfully!')
  } catch (err: any) {
    alert('Deployment failed: ' + err.message)
  } finally {
    isDeploying.value = false
  }
}

const isRefining = ref(false)
const refineJob = async () => {
  if (!selectedJob.value || (!chatInput.value.trim() && chatAttachments.value.length === 0)) return
  isRefining.value = true
  const promptVal = chatInput.value
  chatInput.value = ''
  try {
    const result = await refineLayoutResource.submit({
      job_name: selectedJob.value.name,
      html: selectedJob.value.generated_jinja || selectedJob.value.generated_html,
      css: selectedJob.value.generated_css,
      prompt: promptVal,
      attachments: chatAttachments.value.map(a => a.file_url)
    })
    selectedJob.value.generated_html = result.html
    selectedJob.value.generated_css = result.css
    selectedJob.value.generated_jinja = result.jinja || result.html
    chatAttachments.value = []

    // Push state to history
    pushHistoryState(selectedJob.value.generated_jinja, selectedJob.value.generated_css)

    nextTick(() => {
      if (debounceTimeout) clearTimeout(debounceTimeout)
      debouncedSrcDoc.value = iframeSrcDoc.value
    })
  } catch (err: any) {
    alert('Refinement failed: ' + err.message)
  } finally {
    isRefining.value = false
  }
}
</script>

<style scoped>
/* Main studio layout classes */
.print-studio-container {
  background-color: #EFECE6 !important;
  color: #2A2B2A !important;
}

/* Rounded and typography configurations */
.rounded-3xl {
  border-radius: 24px !important;
}

/* Global inputs overriding for studio style dark inputs */
.print-studio-container select,
.print-studio-container input[type="password"],
.print-studio-container input[type="text"],
.print-studio-container textarea {
  background-color: #FFFFFF !important;
  color: #2A2B2A !important;
  border: 1px solid #D1CDC7 !important;
}
.print-studio-container select:focus,
.print-studio-container input:focus,
.print-studio-container textarea:focus {
  border-color: #F0533A !important;
  box-shadow: 0 0 0 1px rgba(240, 83, 58, 0.25) !important;
  background-color: #FFFFFF !important;
}
</style>
