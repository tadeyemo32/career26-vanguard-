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
	FullName    string `json:"full_name"`
	CompanyName string `json:"company_name"`
}

type anymailResp struct {
	Email       string  `json:"email"`
	EmailStatus string  `json:"email_status"`
	ValidEmail  string  `json:"valid_email"`
	Score       float64 `json:"score"`
	Confidence  float64 `json:"confidence"` // some versions return "confidence" instead of "score"
}

// FindEmailAnymailByCompany searches for a person's email using the Anymail Finder API v5.1.
// Endpoint: POST /v5.1/find-email/person (person lookup by name + company/domain).
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

	body, _ := json.Marshal(anymailReq{FullName: fullName, CompanyName: companyName})
	req, err := http.NewRequest("POST", "https://api.anymailfinder.com/v5.1/find-email/person", bytes.NewBuffer(body))
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
	log.Printf("[Anymail] HTTP %d body: %s", resp.StatusCode, string(raw))

	if resp.StatusCode != http.StatusOK {
		// Try to extract a useful error from the JSON body
		var errBody struct {
			Error          string `json:"error"`
			ErrorExplained string `json:"error_explained"`
			Message        string `json:"message"`
		}
		_ = json.Unmarshal(raw, &errBody)
		msg := errBody.Error
		if errBody.ErrorExplained != "" {
			msg += " — " + errBody.ErrorExplained
		}
		if msg == "" {
			msg = errBody.Message
		}

		if msg == "" {
			switch resp.StatusCode {
			case http.StatusBadRequest:
				msg = "Bad Request (check input format)"
			case http.StatusUnauthorized:
				msg = "Unauthorized (check Anymail API key)"
			case http.StatusPaymentRequired: // 402
				msg = "Payment Needed (out of credits)"
			case http.StatusTooManyRequests: // 429
				msg = "Too Many Requests (rate limit exceeded)"
			default:
				msg = fmt.Sprintf("HTTP %d", resp.StatusCode)
			}
		}
		return "", 0, fmt.Errorf("Anymail: %s", msg)
	}

	var data anymailResp
	if err := json.Unmarshal(raw, &data); err != nil {
		return "", 0, fmt.Errorf("Anymail parse error: %w", err)
	}

	// Handle specific email statuses as per Anymail documentation
	switch data.EmailStatus {
	case "not_found":
		return "", 0, fmt.Errorf("Anymail: person not found")
	case "blacklisted":
		return "", 0, fmt.Errorf("Anymail: email/domain is blacklisted")
	case "risky":
		return "", 0, fmt.Errorf("Anymail: found risky email (discarding to protect sender reputation)")
	}

	// Prefer valid_email if present
	if data.ValidEmail != "" {
		data.Email = data.ValidEmail
	}

	if data.Email == "" {
		return "", 0, fmt.Errorf("Anymail: no verified email returned")
	}

	// Normalise: some response versions use "confidence", others use "score"
	conf := data.Score
	if conf == 0 {
		conf = data.Confidence
	}

	if conf < 0.5 {
		return "", 0, fmt.Errorf("Anymail: score too low (%.0f%%)", conf*100)
	}

	email := strings.ToLower(strings.TrimSpace(data.Email))
	SetCachedEmail(fullName, companyName, email, conf, nil)
	log.Printf("[Anymail] Found: %s (%.0f%%)", email, conf*100)
	return email, conf, nil
}

// ── LinkedIn URL endpoint ─────────────────────────────────────────────────────

// AnymailLinkedInResult holds the richer response from the LinkedIn URL endpoint.
type AnymailLinkedInResult struct {
	Email       string `json:"email"`
	EmailStatus string `json:"email_status"`
	FullName    string `json:"person_full_name"`
	JobTitle    string `json:"person_job_title"`
	Company     string `json:"person_company_name"`
	ValidEmail  string `json:"valid_email"`
}

// FindEmailAnymailByLinkedIn calls POST /v5.1/find-email/linkedin-url.
// Only returns a non-empty Email when valid_email is present (risky/blacklisted are discarded).
func FindEmailAnymailByLinkedIn(linkedInURL string) (AnymailLinkedInResult, error) {
	var empty AnymailLinkedInResult

	apiKey := os.Getenv("ANYMAIL_API_KEY")
	if apiKey == "" {
		return empty, fmt.Errorf("ANYMAIL_API_KEY not set")
	}

	body, _ := json.Marshal(map[string]string{"linkedin_url": linkedInURL})
	req, err := http.NewRequest("POST", "https://api.anymailfinder.com/v5.1/find-email/linkedin-url", bytes.NewBuffer(body))
	if err != nil {
		return empty, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return empty, err
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	log.Printf("[Anymail/LinkedIn] HTTP %d body: %s", resp.StatusCode, string(raw))

	if resp.StatusCode != http.StatusOK {
		var errBody struct {
			Error          string `json:"error"`
			ErrorExplained string `json:"error_explained"`
		}
		_ = json.Unmarshal(raw, &errBody)
		msg := errBody.Error
		if errBody.ErrorExplained != "" {
			msg += " — " + errBody.ErrorExplained
		}

		if msg == "" {
			switch resp.StatusCode {
			case http.StatusBadRequest:
				msg = "Bad Request (check LinkedIn URL format)"
			case http.StatusUnauthorized:
				msg = "Unauthorized (check Anymail API key)"
			case http.StatusPaymentRequired: // 402
				msg = "Payment Needed (out of credits)"
			default:
				msg = fmt.Sprintf("HTTP %d", resp.StatusCode)
			}
		}
		return empty, fmt.Errorf("Anymail LinkedIn: %s", msg)
	}

	var result AnymailLinkedInResult
	if err := json.Unmarshal(raw, &result); err != nil {
		return empty, fmt.Errorf("Anymail LinkedIn parse error: %w", err)
	}

	// Handle specific email statuses as per Anymail documentation
	switch result.EmailStatus {
	case "not_found":
		return result, fmt.Errorf("no email found for this profile")
	case "blacklisted":
		return result, fmt.Errorf("email/domain is blacklisted")
	case "risky":
		// We return the result (so we get name/company), but clear the email to prevent bounces
		result.Email = ""
		return result, fmt.Errorf("email is risky (provided for free but discarded to protect sender reputation)")
	}

	// Prefer valid_email (guaranteed deliverable)
	if result.ValidEmail != "" {
		result.Email = strings.ToLower(strings.TrimSpace(result.ValidEmail))
	} else if result.EmailStatus != "valid" {
		result.Email = "" // Safety fallback: if not explicitly valid, discard
	}

	return result, nil
}

// ── Company Search endpoint ───────────────────────────────────────────────────

// AnymailCompanyResult holds the response for finding all emails at a company.
type AnymailCompanyResult struct {
	Emails []struct {
		Email       string `json:"email"`
		EmailStatus string `json:"email_status"`
		ValidEmail  string `json:"valid_email"`
		JobTitle    string `json:"person_job_title"`
		FullName    string `json:"person_full_name"`
	} `json:"emails"`
}

// FindEmailsAnymailByCompanyDomain calls POST /v5.1/find-email/company.
// Takes a domain or company name. Returns up to 20 emails.
func FindEmailsAnymailByCompanyDomain(domainOrCompany string) ([]AnymailLinkedInResult, error) {
	apiKey := os.Getenv("ANYMAIL_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("ANYMAIL_API_KEY not set")
	}

	body, _ := json.Marshal(map[string]string{
		"domain":       domainOrCompany,
		"company_name": domainOrCompany,
	})

	req, err := http.NewRequest("POST", "https://api.anymailfinder.com/v5.1/find-email/company", bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	log.Printf("[Anymail/Company] HTTP %d body: %s", resp.StatusCode, string(raw))

	if resp.StatusCode != http.StatusOK {
		var errBody struct {
			Error          string `json:"error"`
			ErrorExplained string `json:"error_explained"`
		}
		_ = json.Unmarshal(raw, &errBody)
		msg := errBody.Error
		if errBody.ErrorExplained != "" {
			msg += " — " + errBody.ErrorExplained
		}

		if msg == "" {
			switch resp.StatusCode {
			case http.StatusBadRequest:
				msg = "Bad Request (check company/domain format)"
			case http.StatusUnauthorized:
				msg = "Unauthorized (check Anymail API key)"
			case http.StatusPaymentRequired:
				msg = "Payment Needed (out of credits)"
			default:
				msg = fmt.Sprintf("HTTP %d", resp.StatusCode)
			}
		}
		return nil, fmt.Errorf("Anymail Company API: %s", msg)
	}

	var data AnymailCompanyResult
	if err := json.Unmarshal(raw, &data); err != nil {
		return nil, fmt.Errorf("Anymail Company parse error: %w", err)
	}

	var validResults []AnymailLinkedInResult
	for _, e := range data.Emails {
		// Only take explicitly valid emails to protect sender reputation
		if e.EmailStatus != "valid" && e.ValidEmail == "" {
			continue
		}
		
		email := e.ValidEmail
		if email == "" {
			email = e.Email
		}
		
		if email == "" {
			continue
		}

		validResults = append(validResults, AnymailLinkedInResult{
			Email:      strings.ToLower(strings.TrimSpace(email)),
			FullName:   e.FullName,
			JobTitle:   e.JobTitle,
			Company:    domainOrCompany, // From query
			ValidEmail: email,
			EmailStatus: e.EmailStatus,
		})
	}

	if len(validResults) == 0 {
		return nil, fmt.Errorf("no verified emails found for this company")
	}

	return validResults, nil
}

// ── Decision Maker Search endpoint ────────────────────────────────────────────

// FindDecisionMakerAnymail calls POST /v5.1/find-email/decision-maker.
func FindDecisionMakerAnymail(domainOrCompany string, roles string) ([]AnymailLinkedInResult, error) {
	apiKey := os.Getenv("ANYMAIL_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("ANYMAIL_API_KEY not set")
	}

	// Anymail expects array of job titles/roles
	roleTokens := strings.Split(roles, ",")
	for i := range roleTokens {
		roleTokens[i] = strings.TrimSpace(roleTokens[i])
	}

	body, _ := json.Marshal(map[string]any{
		"domain":       domainOrCompany,
		"company_name": domainOrCompany,
		"job_titles":   roleTokens,
	})

	req, err := http.NewRequest("POST", "https://api.anymailfinder.com/v5.1/find-email/decision-maker", bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	log.Printf("[Anymail/DM] HTTP %d body: %s", resp.StatusCode, string(raw))

	if resp.StatusCode != http.StatusOK {
		var errBody struct {
			Error          string `json:"error"`
			ErrorExplained string `json:"error_explained"`
		}
		_ = json.Unmarshal(raw, &errBody)
		msg := errBody.Error
		if errBody.ErrorExplained != "" {
			msg += " — " + errBody.ErrorExplained
		}

		if msg == "" {
			switch resp.StatusCode {
			case http.StatusBadRequest:
				msg = "Bad Request (check company/domain or roles format)"
			case http.StatusUnauthorized:
				msg = "Unauthorized (check Anymail API key)"
			case http.StatusPaymentRequired:
				msg = "Payment Needed (out of credits)"
			default:
				msg = fmt.Sprintf("HTTP %d", resp.StatusCode)
			}
		}
		return nil, fmt.Errorf("Anymail Decision Maker API: %s", msg)
	}

	var data AnymailCompanyResult // The response structure is identical to company search (array of emails)
	if err := json.Unmarshal(raw, &data); err != nil {
		return nil, fmt.Errorf("Anymail DM parse error: %w", err)
	}

	var validResults []AnymailLinkedInResult
	for _, e := range data.Emails {
		if e.EmailStatus != "valid" && e.ValidEmail == "" {
			continue
		}
		
		email := e.ValidEmail
		if email == "" {
			email = e.Email
		}
		
		if email == "" {
			continue
		}

		validResults = append(validResults, AnymailLinkedInResult{
			Email:      strings.ToLower(strings.TrimSpace(email)),
			FullName:   e.FullName,
			JobTitle:   e.JobTitle,
			Company:    domainOrCompany,
			ValidEmail: email,
			EmailStatus: e.EmailStatus,
		})
	}

	if len(validResults) == 0 {
		return nil, fmt.Errorf("no verified decision makers found at this company for the requested roles")
	}

	return validResults, nil
}
