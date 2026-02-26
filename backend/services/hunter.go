package services

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	"github.com/tadeyemo32/vanguard-backend/models"
)

type hunterEmailFinderResp struct {
	Data struct {
		Email string `json:"email"`
		Score int    `json:"score"`
	} `json:"data"`
	Errors []struct {
		Details string `json:"details"`
	} `json:"errors"`
}

func FindEmailHunter(fullName, domain string) (string, float64, error) {
	if email, conf, ok := GetCachedEmail(fullName, domain); ok {
		return email, conf, nil
	}

	apiKey := os.Getenv("HUNTER_API_KEY")
	if apiKey == "" {
		return "", 0, fmt.Errorf("HUNTER_API_KEY not set")
	}

	parts := strings.Fields(fullName)
	if len(parts) == 0 {
		return "", 0, fmt.Errorf("invalid name")
	}
	firstName := parts[0]
	lastName := ""
	if len(parts) > 1 {
		lastName = strings.Join(parts[1:], " ")
	}

	reqUrl := fmt.Sprintf("https://api.hunter.io/v2/email-finder?domain=%s&first_name=%s&last_name=%s&api_key=%s",
		domain, firstName, lastName, apiKey)

	resp, err := http.Get(reqUrl)
	if err != nil {
		return "", 0, err
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	var data hunterEmailFinderResp
	if err := json.Unmarshal(raw, &data); err != nil {
		return "", 0, err
	}

	if len(data.Errors) > 0 {
		return "", 0, fmt.Errorf("Hunter error: %s", data.Errors[0].Details)
	}

	email := data.Data.Email
	conf := float64(data.Data.Score) / 100.0

	if email == "" {
		return "", 0, fmt.Errorf("Hunter: no email found")
	}

	SetCachedEmail(fullName, domain, email, conf, nil)
	return email, conf, nil
}

func DomainSearchHunter(domain string) ([]models.PersonRow, error) {
	// Dummy implementation to satisfy domainSearchHandler
	return []models.PersonRow{}, nil
}
