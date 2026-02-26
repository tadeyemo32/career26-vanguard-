package services

import (
	"log"
	"strings"
	"time"

	"github.com/tadeyemo32/vanguard-backend/models"
)

// AISearch query LinkedIn natively, e.g. "IB bankers in Aberdeen"
func AISearch(query string, maxResults int) ([]models.PersonRow, int) {
	var out []models.PersonRow

	enhanced, tokens := LLMEnhanceSearchQuery(query)
	log.Printf("AISearch original: '%s', enhanced: '%s'", query, enhanced)

	q := enhanced + " site:linkedin.com/in"
	results, err := SerpGoogle(q, maxResults)
	if err != nil {
		log.Printf("AISearch SerpAPI error: %v", err)
		return out, tokens
	}

	for _, r := range results {
		titleStr := strings.TrimSpace(r.Title)
		link := strings.TrimSpace(r.Link)
		snippet := strings.TrimSpace(r.Snippet)

		name := ""
		company := ""

		if strings.Contains(titleStr, " - ") {
			parts := strings.SplitN(titleStr, " - ", 2)
			name = strings.TrimSpace(parts[0])
			rest := parts[1]
			if strings.Contains(rest, " | ") {
				cParts := strings.Split(rest, " | ")
				company = strings.TrimSpace(cParts[len(cParts)-1])
			} else if strings.Contains(rest, " at ") {
				cParts := strings.SplitN(rest, " at ", 2)
				company = strings.TrimSpace(cParts[1])
			} else {
				company = strings.TrimSpace(rest)
			}
		} else if strings.Contains(titleStr, "|") {
			name = strings.TrimSpace(strings.Split(titleStr, "|")[0])
		} else {
			name = titleStr
		}

		if name == "" {
			continue
		}

		if company == "" && strings.Contains(snippet, " at ") {
			cParts := strings.Split(snippet, " at ")
			company = strings.TrimSpace(strings.Split(cParts[len(cParts)-1], ".")[0])
		}

		// Clean up the company name to improve Anymail lookup success rates
		company = strings.ReplaceAll(company, " - LinkedIn", "")
		company = strings.ReplaceAll(company, " | LinkedIn", "")
		company = strings.ReplaceAll(company, "| LinkedIn", "")
		company = strings.ReplaceAll(company, "...", "")
		company = strings.TrimSpace(company)

		row := models.PersonRow{
			Name:       name,
			Title:      "LinkedIn Result", // snippet parsing might improve this
			Company:    company,
			Link:       link,
			Email:      "",
			Confidence: 0.0,
			Source:     "AISearch",
		}

		if company != "" && name != "" {
			email, conf, _ := FindEmailAnymailByCompany(name, company)
			if email == "" {
				// Fallback to Hunter
				hunterEmail, hunterConf, _ := FindEmailHunter(name, company)
				if hunterEmail != "" {
					email = hunterEmail
					conf = hunterConf
				}
			}

			if email != "" {
				row.Email = email
				row.Confidence = conf
			}
			time.Sleep(1200 * time.Millisecond)
		}

		out = append(out, row)
	}

	return out, tokens
}
