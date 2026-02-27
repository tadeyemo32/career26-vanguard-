package services

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
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

// FindEmailsHunterByCompany returns up to 10 emails for a given domain/company.
func FindEmailsHunterByCompany(domain string) ([]models.FindEmailResultItem, error) {
	if domain == "" {
		return nil, fmt.Errorf("domain is required")
	}

	apiKey := os.Getenv("HUNTER_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("HUNTER_API_KEY not set")
	}

	reqUrl := fmt.Sprintf("https://api.hunter.io/v2/domain-search?domain=%s&api_key=%s", url.QueryEscape(domain), apiKey)

	return callHunterDomainSearch(reqUrl)
}

// FindDecisionMakersHunter returns emails for a specific role/department at a domain.
func FindDecisionMakersHunter(domain string, role string) ([]models.FindEmailResultItem, error) {
	if domain == "" {
		return nil, fmt.Errorf("domain is required")
	}

	apiKey := os.Getenv("HUNTER_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("HUNTER_API_KEY not set")
	}

	reqUrl := fmt.Sprintf("https://api.hunter.io/v2/domain-search?domain=%s&department=%s&api_key=%s", url.QueryEscape(domain), url.QueryEscape(role), apiKey)

	return callHunterDomainSearch(reqUrl)
}

type hunterDomainSearchResp struct {
	Data struct {
		Emails []struct {
			Value      string `json:"value"`
			FirstName  string `json:"first_name"`
			LastName   string `json:"last_name"`
			Position   string `json:"position"`
			Confidence int    `json:"confidence"`
		} `json:"emails"`
	} `json:"data"`
	Errors []struct {
		Details string `json:"details"`
	} `json:"errors"`
}

func callHunterDomainSearch(reqUrl string) ([]models.FindEmailResultItem, error) {
	resp, err := http.Get(reqUrl)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusPaymentRequired {
		return nil, fmt.Errorf("Payment Needed (out of credits)")
	}
	if resp.StatusCode == http.StatusUnauthorized {
		return nil, fmt.Errorf("Unauthorized (check API key)")
	}

	raw, _ := io.ReadAll(resp.Body)
	var data hunterDomainSearchResp
	if err := json.Unmarshal(raw, &data); err != nil {
		return nil, err
	}

	if len(data.Errors) > 0 {
		return nil, fmt.Errorf("Hunter error: %s", data.Errors[0].Details)
	}

	var results []models.FindEmailResultItem
	for _, e := range data.Data.Emails {
		fullName := strings.TrimSpace(e.FirstName + " " + e.LastName)
		results = append(results, models.FindEmailResultItem{
			Email:      e.Value,
			FullName:   fullName,
			JobTitle:   e.Position,
			Confidence: float64(e.Confidence) / 100.0,
			Source:     "Hunter.io",
		})
	}

	if len(results) == 0 {
		return nil, fmt.Errorf("Hunter: no emails found for this domain")
	}

	return results, nil
}

// FindEmailHunterByLinkedIn uses SerpAPI to reverse-search the LinkedIn profile
// to find the full name and company name, then queries Hunter for the email.
func FindEmailHunterByLinkedIn(linkedinURL string) (*models.FindEmailResultItem, error) {
	// 1. Resolve LinkedIn URL to Name via SerpAPI
	query := fmt.Sprintf("site:linkedin.com/in \"%s\"", linkedinURL)
	results, err := SerpGoogle(query, 1)
	if err != nil || len(results) == 0 {
		return nil, fmt.Errorf("failed to resolve linkedin profile via SerpAPI")
	}

	title := results[0].Title
	// LinkedIn titles look like: "Satya Nadella - Chairman and CEO - Microsoft | LinkedIn"
	parts := strings.Split(title, " - ")
	if len(parts) < 3 {
		return nil, fmt.Errorf("could not extract name and company from LinkedIn result")
	}

	fullName := strings.TrimSpace(parts[0])
	companyPart := strings.Split(parts[len(parts)-2], " | ")[0]
	company := strings.TrimSpace(companyPart)

	// 2. Resolve domain
	domain := company
	companyQuery := fmt.Sprintf("%s official website", company)
	websiteResults, err := SerpGoogle(companyQuery, 1)
	if err == nil && len(websiteResults) > 0 {
		if parsedUrl, err := url.Parse(websiteResults[0].Link); err == nil {
			domain = strings.TrimPrefix(parsedUrl.Hostname(), "www.")
		}
	}

	// 3. Find via standard Hunter
	email, conf, err := FindEmailHunter(fullName, domain)
	if err != nil {
		return nil, err
	}

	return &models.FindEmailResultItem{
		Email:      email,
		FullName:   fullName,
		Confidence: conf,
		Source:     "Hunter.io (via LinkedIn SERP)",
	}, nil
}

func DomainSearchHunter(domain string) ([]models.PersonRow, error) {
	// Dummy implementation to satisfy domainSearchHandler
	return []models.PersonRow{}, nil
}
