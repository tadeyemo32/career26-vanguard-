package services

import (
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/tadeyemo32/vanguard-backend/models"
)

// SmartLinkedInQuery builds a precise LinkedIn search query for a person at a company.
// Uses boolean operators and site: filter for maximum accuracy.
func SmartLinkedInQuery(jobTitle, company string) string {
	// Normalise company name: drop legal suffixes for better matching
	co := company
	for _, suffix := range []string{" PLC", " Ltd", " Limited", " LLC", " Inc", " Corp", " Group", " Holdings"} {
		co = strings.TrimSuffix(co, suffix)
	}
	co = strings.TrimSpace(co)

	// Two query strategies:
	// 1. Quoted exact match: "Title" "Company" site:linkedin.com/in  (high precision)
	return fmt.Sprintf(`"%s" "%s" site:linkedin.com/in`, jobTitle, co)
}

// FindPeopleAtCompanies searches LinkedIn via SerpAPI for people matching job titles
// at each company, then attempts email resolution with caching.
func FindPeopleAtCompanies(companies []string, jobTitles []string, maxPerCompany int, findEmails bool) []models.PersonRow {
	var out []models.PersonRow
	seen := map[string]bool{} // deduplicate by LinkedIn URL

	if len(jobTitles) == 0 {
		jobTitles = []string{"director"}
	}
	if maxPerCompany == 0 {
		maxPerCompany = 5
	}

	for _, company := range companies {
		company = strings.TrimSpace(company)
		if company == "" {
			continue
		}

		perCompanyCount := 0

		for _, title := range jobTitles {
			if perCompanyCount >= maxPerCompany {
				break
			}

			q := SmartLinkedInQuery(title, company)
			log.Printf("Searching: %s", q)

			results, err := SerpGoogle(q, 5)
			if err != nil {
				log.Printf("SerpAPI error [%s @ %s]: %v", title, company, err)
				continue
			}

			// Throttle to avoid rate limiting
			time.Sleep(1000 * time.Millisecond)

			for _, r := range results {
				if perCompanyCount >= maxPerCompany {
					break
				}

				link := strings.TrimSpace(r.Link)

				// Only accept actual LinkedIn profile URLs (not /company/, /jobs/, etc.)
				if !strings.Contains(link, "linkedin.com/in/") {
					continue
				}

				// Deduplicate by URL
				if seen[link] {
					continue
				}
				seen[link] = true

				name, extractedTitle, extractedCompany := parseLinkedInTitle(r.Title, r.Snippet, company)
				if name == "" {
					continue
				}

				// Cross-verify: the result should mention the company or title
				combined := strings.ToLower(r.Title + " " + r.Snippet)
				coLower := strings.ToLower(company)
				titleLower := strings.ToLower(title)
				if !strings.Contains(combined, coLower) && !strings.Contains(combined, titleLower) {
					log.Printf("Skipping likely irrelevant result: %s", r.Title)
					continue
				}

				row := models.PersonRow{
					Name:    name,
					Title:   extractedTitle,
					Company: extractedCompany,
					Link:    link,
					Source:  "LinkedIn/SerpAPI",
				}

				if findEmails && name != "" && extractedCompany != "" {
					// Check cache first (free)
					email, conf, ok := GetCachedEmail(name, extractedCompany)
					if !ok {
						email, conf, err = FindEmailAnymailByCompany(name, extractedCompany)
						// Cache both hits and misses
						SetCachedEmail(name, extractedCompany, email, conf, err)
						time.Sleep(800 * time.Millisecond)
					}
					if err == nil && email != "" {
						row.Email = email
						row.Confidence = conf
					}
				}

				out = append(out, row)
				perCompanyCount++
			}
		}
	}

	return out
}

// parseLinkedInTitle extracts name, title, and company from a LinkedIn SERP result title.
// LinkedIn titles usually follow: "Name - Title | Company" or "Name - Title at Company"
func parseLinkedInTitle(titleStr, snippet, fallbackCompany string) (name, title, company string) {
	titleStr = strings.TrimSpace(titleStr)

	// Remove " | LinkedIn" suffix which sometimes appears
	for _, suffix := range []string{" | LinkedIn", "- LinkedIn"} {
		if idx := strings.LastIndex(titleStr, suffix); idx != -1 {
			titleStr = titleStr[:idx]
		}
	}

	company = fallbackCompany

	if strings.Contains(titleStr, " - ") {
		parts := strings.SplitN(titleStr, " - ", 2)
		name = strings.TrimSpace(parts[0])
		rest := strings.TrimSpace(parts[1])

		// "Title | Company" format
		if strings.Contains(rest, " | ") {
			chunks := strings.SplitN(rest, " | ", 2)
			title = strings.TrimSpace(chunks[0])
			if c := strings.TrimSpace(chunks[1]); c != "" {
				company = c
			}
		} else if strings.Contains(rest, " at ") {
			// "Title at Company"
			chunks := strings.SplitN(rest, " at ", 2)
			title = strings.TrimSpace(chunks[0])
			if c := strings.TrimSpace(chunks[1]); c != "" {
				company = c
			}
		} else {
			title = rest
		}
	} else if strings.Contains(titleStr, " | ") {
		parts := strings.SplitN(titleStr, " | ", 2)
		name = strings.TrimSpace(parts[0])
		title = strings.TrimSpace(parts[1])
	} else {
		name = titleStr
	}

	// Fallback: try to extract company from snippet if still using fallback
	if company == fallbackCompany && snippet != "" {
		if idx := strings.Index(strings.ToLower(snippet), " at "); idx != -1 {
			candidate := strings.TrimSpace(snippet[idx+4:])
			if dot := strings.Index(candidate, "."); dot != -1 && dot < 40 {
				candidate = strings.TrimSpace(candidate[:dot])
			}
			if candidate != "" && len(candidate) < 60 {
				company = candidate
			}
		}
	}

	// Strip trailing LinkedIn suffix from company
	company = strings.TrimSuffix(strings.TrimSpace(company), " | LinkedIn")
	title = strings.TrimSuffix(strings.TrimSpace(title), " | LinkedIn")

	return name, title, company
}
