package services

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
)

type openAIRequest struct {
	Model       string          `json:"model"`
	Messages    []openAIMessage `json:"messages"`
	Temperature float64         `json:"temperature"`
}

type openAIMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type openAIResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
	Usage struct {
		TotalTokens int `json:"total_tokens"`
	} `json:"usage"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error"`
}

// AskOpenAIModel calls OpenAI with an explicit model name.
func AskOpenAIModel(model, systemPrompt, userPrompt string) (string, int) {
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" || strings.TrimSpace(userPrompt) == "" {
		return "", 0
	}
	if model == "" {
		model = "gpt-4o-mini"
	}

	payload := openAIRequest{
		Model: model,
		Messages: []openAIMessage{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: strings.TrimSpace(userPrompt)},
		},
		Temperature: 0.1,
	}

	body, _ := json.Marshal(payload)
	req, err := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewBuffer(body))
	if err != nil {
		return "", 0
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		log.Printf("[OpenAI] request error: %v", err)
		return "", 0
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	var data openAIResponse
	if err := json.Unmarshal(raw, &data); err != nil {
		return "", 0
	}
	if data.Error != nil {
		log.Printf("[OpenAI] error: %s", data.Error.Message)
		return "", 0
	}
	if len(data.Choices) > 0 {
		return strings.TrimSpace(data.Choices[0].Message.Content), data.Usage.TotalTokens
	}
	return "", 0
}

// AskOpenAI calls OpenAI using the currently active model (backwards compat).
func AskOpenAI(systemPrompt, userPrompt string) (string, int) {
	provider, model := GetLLM()
	if provider != "openai" {
		model = "gpt-4o-mini" // fallback when called directly on wrong provider
	}
	return AskOpenAIModel(model, systemPrompt, userPrompt)
}

// LLMEnhanceSearchQuery converts natural language into a LinkedIn search query.
func LLMEnhanceSearchQuery(userQuery string) (string, int) {
	sys := "Convert the user's natural language request into a precise LinkedIn-style search query to find people. Output ONLY the raw query string, no explanation. Include role, company or sector, and location when mentioned. If the user mentions specific communities like 'career 26 fellows', include that in quotes. Keep it under 10 words."
	res, tokens := AskLLM(sys, userQuery)
	if res == "" {
		return strings.TrimSpace(userQuery), 0
	}
	return res, tokens
}
