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
	Error *struct {
		Message string `json:"message"`
	} `json:"error"`
}

// AskOpenAIModel calls OpenAI with an explicit model name.
func AskOpenAIModel(model, systemPrompt, userPrompt string) string {
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" || strings.TrimSpace(userPrompt) == "" {
		return ""
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
		return ""
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		log.Printf("[OpenAI] request error: %v", err)
		return ""
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	var data openAIResponse
	if err := json.Unmarshal(raw, &data); err != nil {
		return ""
	}
	if data.Error != nil {
		log.Printf("[OpenAI] error: %s", data.Error.Message)
		return ""
	}
	if len(data.Choices) > 0 {
		return strings.TrimSpace(data.Choices[0].Message.Content)
	}
	return ""
}

// AskOpenAI calls OpenAI using the currently active model (backwards compat).
func AskOpenAI(systemPrompt, userPrompt string) string {
	provider, model := GetLLM()
	if provider != "openai" {
		model = "gpt-4o-mini" // fallback when called directly on wrong provider
	}
	return AskOpenAIModel(model, systemPrompt, userPrompt)
}

// LLMEnhanceSearchQuery converts natural language into a LinkedIn search query.
func LLMEnhanceSearchQuery(userQuery string) string {
	sys := "Convert the user's natural language request into a short LinkedIn-style search query to find people. Output only the query, no explanation. Include role, company or sector, and location when mentioned. Keep it under 10 words."
	res := AskLLM(sys, userQuery)
	if res == "" {
		return strings.TrimSpace(userQuery)
	}
	return res
}
