package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
)

// ─── Gemini REST API ──────────────────────────────────────────────────────────
// Docs: https://ai.google.dev/api/rest/v1beta/models/generateContent

type geminiRequest struct {
	Contents []geminiContent `json:"contents"`
}

type geminiContent struct {
	Parts []geminiPart `json:"parts"`
}

type geminiPart struct {
	Text string `json:"text"`
}

type geminiResponse struct {
	Candidates []struct {
		Content struct {
			Parts []struct {
				Text string `json:"text"`
			} `json:"parts"`
		} `json:"content"`
	} `json:"candidates"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error"`
}

// AskGemini sends a system + user prompt to the Google Gemini REST API.
func AskGemini(model, sysPrompt, userPrompt string) string {
	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		log.Println("[Gemini] GEMINI_API_KEY not set")
		return ""
	}
	if model == "" {
		model = "gemini-1.5-flash"
	}

	// Gemini doesn't have a separate system role in the basic REST API —
	// we prepend the system prompt as the first user turn.
	combined := sysPrompt + "\n\n" + userPrompt

	payload := geminiRequest{
		Contents: []geminiContent{
			{Parts: []geminiPart{{Text: combined}}},
		},
	}

	body, _ := json.Marshal(payload)
	url := fmt.Sprintf(
		"https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s",
		model, apiKey,
	)

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		log.Printf("[Gemini] request error: %v", err)
		return ""
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	var result geminiResponse
	if err := json.Unmarshal(raw, &result); err != nil {
		log.Printf("[Gemini] parse error: %v", err)
		return ""
	}
	if result.Error != nil {
		log.Printf("[Gemini] API error: %s", result.Error.Message)
		return ""
	}
	if len(result.Candidates) == 0 || len(result.Candidates[0].Content.Parts) == 0 {
		return ""
	}
	return result.Candidates[0].Content.Parts[0].Text
}
