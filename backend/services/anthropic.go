package services

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
)

// ─── Anthropic Claude REST API ────────────────────────────────────────────────
// Docs: https://docs.anthropic.com/en/api/messages

type claudeRequest struct {
	Model     string          `json:"model"`
	MaxTokens int             `json:"max_tokens"`
	System    string          `json:"system,omitempty"`
	Messages  []claudeMessage `json:"messages"`
}

type claudeMessage struct {
	Role    string `json:"role"` // "user" | "assistant"
	Content string `json:"content"`
}

type claudeResponse struct {
	Content []struct {
		Text string `json:"text"`
		Type string `json:"type"`
	} `json:"content"`
	Error *struct {
		Type    string `json:"type"`
		Message string `json:"message"`
	} `json:"error"`
}

// AskClaude sends a system + user prompt to the Anthropic Messages API.
func AskClaude(model, sysPrompt, userPrompt string) string {
	apiKey := os.Getenv("ANTHROPIC_API_KEY")
	if apiKey == "" {
		log.Println("[Claude] ANTHROPIC_API_KEY not set")
		return ""
	}
	if model == "" {
		model = "claude-3-haiku-20240307"
	}

	payload := claudeRequest{
		Model:     model,
		MaxTokens: 1024,
		System:    sysPrompt,
		Messages:  []claudeMessage{{Role: "user", Content: userPrompt}},
	}

	body, _ := json.Marshal(payload)
	req, err := http.NewRequest("POST", "https://api.anthropic.com/v1/messages", bytes.NewBuffer(body))
	if err != nil {
		log.Printf("[Claude] request build error: %v", err)
		return ""
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", apiKey)
	req.Header.Set("anthropic-version", "2023-06-01")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		log.Printf("[Claude] request error: %v", err)
		return ""
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	var result claudeResponse
	if err := json.Unmarshal(raw, &result); err != nil {
		log.Printf("[Claude] parse error: %v — body: %s", err, string(raw))
		return ""
	}
	if result.Error != nil {
		log.Printf("[Claude] API error [%s]: %s", result.Error.Type, result.Error.Message)
		return ""
	}
	for _, block := range result.Content {
		if block.Type == "text" {
			return block.Text
		}
	}
	return ""
}
