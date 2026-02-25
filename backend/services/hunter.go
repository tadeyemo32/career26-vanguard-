package services

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
)

// HunterResponse maps the relevant fields from Hunter.io's email-finder endpoint
type HunterResponse struct {
	Data struct {
		Email    string `json:"email"`
		Score    int    `json:"score"` // 0–100 confidence score
		Position string `json:"position"`
		Company  string `json:"company"`
		Domain   string `json:"domain"`
	} `json:"data"`
	Errors []struct {
		Details string `json:"details"`
		ID      string `json:"id"`
	} `json:"errors"`
}

// FindEmailHunter calls the Hunter.io Email Finder API.
// It splits fullName into first/last and queries by domain or company name.
// Returns email, confidence (0.0–1.0), and error.
func FindEmailHunter(fullName, companyOrDomain string) (string, float64, error) {
	apiKey := os.Getenv("HUNTER_API_KEY")
	if apiKey == "" {
		return "", 0, fmt.Errorf("HUNTER_API_KEY not set")
	}

	// Split name into first / last
	parts := strings.Fields(strings.TrimSpace(fullName))
	if len(parts) < 2 {
		return "", 0, fmt.Errorf("need at least first and last name")
	}
	firstName := parts[0]
	lastName := strings.Join(parts[1:], " ")

	// Build query — use domain if it looks like one, else company name
	params := url.Values{}
	params.Set("first_name", firstName)
	params.Set("last_name", lastName)
	params.Set("api_key", apiKey)

	if strings.Contains(companyOrDomain, ".") {
		// Strip http(s):// prefix if present
		domain := companyOrDomain
		domain = strings.TrimPrefix(domain, "https://")
		domain = strings.TrimPrefix(domain, "http://")
		domain = strings.Split(domain, "/")[0] // apex domain only
		params.Set("domain", domain)
	} else {
		params.Set("company", companyOrDomain)
	}

	endpoint := "https://api.hunter.io/v2/email-finder?" + params.Encode()
	resp, err := http.Get(endpoint)
	if err != nil {
		return "", 0, fmt.Errorf("hunter.io request failed: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode == 401 {
		return "", 0, fmt.Errorf("Hunter.io: invalid API key")
	}
	if resp.StatusCode == 429 {
		return "", 0, fmt.Errorf("Hunter.io: rate limit exceeded")
	}
	if resp.StatusCode != http.StatusOK {
		return "", 0, fmt.Errorf("Hunter.io: status %d", resp.StatusCode)
	}

	var data HunterResponse
	if err := json.Unmarshal(body, &data); err != nil {
		return "", 0, fmt.Errorf("hunter.io parse error: %w", err)
	}

	if len(data.Errors) > 0 {
		return "", 0, fmt.Errorf("hunter.io error: %s", data.Errors[0].Details)
	}

	if data.Data.Email == "" {
		return "", 0, fmt.Errorf("hunter.io: no email found")
	}

	// Hunter score is 0–100 → normalise to 0.0–1.0
	conf := float64(data.Data.Score) / 100.0

	return strings.ToLower(data.Data.Email), conf, nil
}
