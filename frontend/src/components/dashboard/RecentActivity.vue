<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="text-[10px] font-black text-studio-textSecondary uppercase tracking-widest">Recent Activity</h3>
    </div>

    <div v-if="jobsList.length === 0" class="p-6 text-center text-studio-textMuted text-xs border border-dashed border-studio-border rounded-xl">
      No recent activity recorded.
    </div>
    
    <div v-else class="space-y-3.5 max-h-[300px] overflow-y-auto no-scrollbar pr-1">
      <div 
        v-for="job in jobsList.slice(0, 5)" 
        :key="job.name"
        @click="$emit('open-job', job.name)"
        class="flex items-start space-x-3 p-3 bg-studio-panel border border-studio-border hover:border-studio-borderStrong rounded-xl cursor-pointer transition select-none group"
      >
        <!-- Icon indicating status -->
        <div class="w-6 h-6 rounded-lg bg-studio-bg flex items-center justify-center shrink-0 border border-studio-border text-studio-textMuted group-hover:text-studio-accent transition">
          <svg v-if="job.status === 'Completed'" class="h-3.5 w-3.5 text-studio-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <svg v-else-if="job.status === 'Failed'" class="h-3.5 w-3.5 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <svg v-else class="h-3.5 w-3.5 text-studio-accent animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>

        <!-- Details -->
        <div class="flex-1 min-w-0">
          <div class="flex justify-between items-start">
            <p class="text-xs font-black text-studio-text truncate leading-tight group-hover:text-studio-accent transition">{{ job.target_doctype }}</p>
            <span 
              :class="[
                'text-[8px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded border ml-2 shrink-0',
                job.status === 'Completed' ? 'bg-studio-accent/5 text-studio-accent border-studio-accent/20' :
                job.status === 'Failed' ? 'bg-rose-500/5 text-rose-450 border-rose-500/10' :
                'bg-studio-secondary text-studio-textSecondary border-studio-border'
              ]"
            >
              {{ job.status }}
            </span>
          </div>
          <div class="flex items-center space-x-1.5 mt-1">
            <span class="text-[9px] font-mono text-studio-textMuted truncate max-w-[80px]">{{ job.name }}</span>
            <span class="text-studio-textMuted text-[8px]">•</span>
            <span class="text-[9px] text-studio-textSecondary font-semibold">{{ formatTimeAgo(job.creation) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  jobsList: any[]
}>()

defineEmits(['open-job'])

const formatTimeAgo = (dateStr: string) => {
  if (!dateStr) return ''
  try {
    const created = new Date(dateStr.replace(' ', 'T')).getTime()
    const now = new Date().getTime()
    const seconds = Math.floor((now - created) / 1000)
    
    if (seconds < 60) return 'just now'
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    if (days === 1) return 'yesterday'
    return `${days} days ago`
  } catch (e) {
    return dateStr
  }
}
</script>
