<template>
  <Dialog
    :value="modelValue"
    @input="$emit('update:modelValue', $event)"
    :options="{
      title: 'LLM Engine Settings',
      size: 'sm'
    }"
  >
    <template #body>
      <div class="space-y-4 text-studio-text p-4 bg-studio-panel rounded-2xl select-none">
        <div class="space-y-1.5">
          <label class="block text-[10px] font-bold uppercase tracking-wider text-studio-textSecondary">LLM Provider</label>
          <select 
            v-model="form.llm_provider"
            class="w-full bg-studio-bg border border-studio-border rounded-lg py-2 px-3 text-studio-text text-sm focus:outline-none focus:border-studio-accent focus:ring-1 focus:ring-studio-accent"
          >
            <option value="Mock">Mock (Generates default beautiful template)</option>
            <option value="Gemini">Google Gemini</option>
            <option value="OpenAI">OpenAI Chat</option>
            <option value="DeepSeek">DeepSeek AI</option>
          </select>
        </div>

        <div v-if="form.llm_provider !== 'Mock'" class="space-y-1.5">
          <label class="block text-[10px] font-bold uppercase tracking-wider text-studio-textSecondary">API Key</label>
          <input 
            type="password" 
            v-model="form.api_key"
            placeholder="••••••••••••••••"
            class="w-full bg-studio-bg border border-studio-border rounded-lg py-2 px-3 text-studio-text text-sm focus:outline-none focus:border-studio-accent focus:ring-1 focus:ring-studio-accent"
          />
        </div>

        <div v-if="form.llm_provider !== 'Mock'" class="space-y-1.5">
          <label class="block text-[10px] font-bold uppercase tracking-wider text-studio-textSecondary">API Base URL (Optional)</label>
          <input 
            type="text" 
            v-model="form.api_base"
            placeholder="e.g. https://api.openai.com/v1"
            class="w-full bg-studio-bg border border-studio-border rounded-lg py-2 px-3 text-studio-text text-sm focus:outline-none focus:border-studio-accent focus:ring-1 focus:ring-studio-accent"
          />
        </div>

        <div v-if="form.llm_provider !== 'Mock'" class="space-y-1.5">
          <label class="block text-[10px] font-bold uppercase tracking-wider text-studio-textSecondary">Model Name</label>
          <input 
            type="text" 
            v-model="form.model_name"
            placeholder="e.g. gemini-3.5-flash, gpt-4o-mini"
            class="w-full bg-studio-bg border border-studio-border rounded-lg py-2 px-3 text-studio-text text-sm focus:outline-none focus:border-studio-accent focus:ring-1 focus:ring-studio-accent"
          />
        </div>

        <div class="flex justify-end space-x-2.5 mt-6 pt-4 border-t border-studio-border">
          <button 
            @click="$emit('update:modelValue', false)"
            class="px-4 py-2 bg-studio-secondary hover:bg-studio-elevated text-studio-textSecondary hover:text-studio-text border border-studio-border rounded-lg text-[10px] font-bold uppercase tracking-wider transition select-none"
          >
            Cancel
          </button>
          <button 
            @click="onSave"
            class="px-5 py-2 bg-studio-accent hover:bg-studio-accentHover text-studio-bg rounded-lg text-[10px] font-bold uppercase tracking-wider transition shadow-sm select-none"
          >
            Save Settings
          </button>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Dialog } from 'frappe-ui'

const props = defineProps<{
  modelValue: boolean
  settings: {
    llm_provider: string
    api_key: string
    api_base: string
    model_name: string
  }
}>()

const emit = defineEmits(['update:modelValue', 'save'])

const form = ref({ ...props.settings })

watch(() => props.settings, (newVal) => {
  form.value = { ...newVal }
}, { deep: true })

const onSave = () => {
  emit('save', form.value)
}
</script>
