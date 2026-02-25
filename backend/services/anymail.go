package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
)

type anymailReq struct {
	FullName string `json:"full_name"`
	Company  string `json:"company_name"`
}

type anymailResp struct {
	Email string  `json:"email"`
	Score float64 `json:"score"`
}

// FindEmailAnymailByCompany searches for a person's email using the Anymail Finder API.
// Returns ("", 0, err) on failure — never falls back to LLM guessing.
func FindEmailAnymailByCompany(fullName, companyName string) (string, float64, error) {
	// Cache hit — free lookup
	if email, conf, ok := GetCachedEmail(fullName, companyName); ok {
		log.Printf("[Anymail] Cache hit: %s @ %s → %s (%.0f%%)", fullName, companyName, email, conf*100)
		return email, conf, nil
	}

	apiKey := os.Getenv("ANYMAIL_API_KEY")
	if apiKey == "" {
		return "", 0, fmt.Errorf("ANYMAIL_API_KEY not set")
	}

	body, _ := json.Marshal(anymailReq{FullName: fullName, Company: companyName})
	req, err := http.NewRequest("POST", "https://api.anymailfinder.com/v5.0/search/company.json", bytes.NewBuffer(body))
	if err != nil {
		return "", 0, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", 0, err
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != http.StatusOK {
		// Try to extract a useful error from the JSON body
		var errBody struct {
			Error          string `json:"error"`
			ErrorExplained string `json:"error_explained"`
		}
		if jsonErr := json.Unmarshal(raw, &errBody); jsonErr == nil && errBody.Error != "" {
			return "", 0, fmt.Errorf("Anymail: %s — %s", errBody.Error, errBody.ErrorExplained)
		}
		return "", 0, fmt.Errorf("Anymail: HTTP %d", resp.StatusCode)
	}

	var data anymailResp
	if err := json.Unmarshal(raw, &data); err != nil {
		return "", 0, fmt.Errorf("Anymail parse error: %w", err)
	}

	if data.Email == "" {
		return "", 0, fmt.Errorf("Anymail: no email found")
	}

	if data.Score < 0.5 {
		return "", 0, fmt.Errorf("Anymail: score too low (%.0f%%)", data.Score*100)
	}

	email := strings.ToLower(strings.TrimSpace(data.Email))
	SetCachedEmail(fullName, companyName, email, data.Score, nil)
	log.Printf("[Anymail] Found: %s (%.0f%%)", email, data.Score*100)
	return email, data.Score, nil
}
