// Copyright (c) 2026, harrish and contributors
// For license information, please see license.txt

frappe.ui.form.on('Print Studio Settings', {
	refresh: function(frm) {
		frm.trigger('setup_model_options');
	},
	llm_provider: function(frm) {
		frm.trigger('setup_model_options');
		
		// Auto select standard model if the current selection is not valid for the new provider
		let allowed_models = frm.fields_dict['model_name'].get_options();
		if (frm.doc.model_name && !allowed_models.includes(frm.doc.model_name)) {
			if (frm.doc.llm_provider === 'Gemini') {
				frm.set_value('model_name', 'gemini-3.5-flash');
			} else if (frm.doc.llm_provider === 'OpenAI') {
				frm.set_value('model_name', 'gpt-4o-mini');
			} else if (frm.doc.llm_provider === 'DeepSeek') {
				frm.set_value('model_name', 'deepseek-chat');
			} else if (frm.doc.llm_provider === 'Ollama') {
				frm.set_value('model_name', 'llama3');
			} else {
				frm.set_value('model_name', 'mock-model');
			}
		}
	},
	setup_model_options: function(frm) {
		let options = [];
		if (frm.doc.llm_provider === 'Gemini') {
			options = ['gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-flash-latest'];
		} else if (frm.doc.llm_provider === 'OpenAI') {
			options = ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo'];
		} else if (frm.doc.llm_provider === 'DeepSeek') {
			options = ['deepseek-chat', 'deepseek-coder', 'deepseek-v4-flash'];
		} else if (frm.doc.llm_provider === 'Ollama') {
			options = ['llama3', 'mistral', 'codellama'];
		} else {
			options = ['mock-model'];
		}
		
		frm.set_df_property('model_name', 'options', options);
		frm.refresh_field('model_name');
	}
});
