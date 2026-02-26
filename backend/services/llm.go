package services

import (
	"log"
	"sync"
)

// ─── Active LLM config ────────────────────────────────────────────────────────

var (
	llmMu       sync.RWMutex
	llmProvider = "openai"
	llmModel    = "gpt-4o-mini"
)

// SetLLM updates the active provider and model at runtime.
func SetLLM(provider, model string) {
	llmMu.Lock()
	defer llmMu.Unlock()
	llmProvider = provider
	llmModel = model
	log.Printf("[LLM] Provider set to %s / %s", provider, model)
}

// GetLLM returns the currently configured provider and model.
func GetLLM() (provider, model string) {
	llmMu.RLock()
	defer llmMu.RUnlock()
	return llmProvider, llmModel
}

// AskLLM is the single call-site for all LLM usage in the backend.
// It routes to OpenAI, Gemini, or Claude based on the active provider.
func AskLLM(sysPrompt, userPrompt string) (string, int) {
	provider, model := GetLLM()
	log.Printf("[LLM] Calling %s/%s", provider, model)

	switch provider {
	case "gemini":
		return AskGemini(model, sysPrompt, userPrompt)
	case "anthropic":
		return AskClaude(model, sysPrompt, userPrompt)
	default:
		// openai (default)
		return AskOpenAIModel(model, sysPrompt, userPrompt)
	}
}
