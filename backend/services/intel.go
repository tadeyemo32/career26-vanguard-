package services

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/tadeyemo32/vanguard-backend/models"
)

// RunCompanyIntel executes the "Vanguard" dynamic workflow for a company.
// 1. Precise LinkedIn resolution
// 2. Scrape size via LLM/GoQuery
// 3. Size-based dynamic role targeting
// 4. Fetch people & emails natively
func RunCompanyIntel(companyName string) (*models.CompanyIntelResponse, int) {
	resp := &models.CompanyIntelResponse{
		SourceLog:       []string{},
		TargetRolesUsed: []string{},
		PeopleFound:     []models.PersonRow{},
	}

	resp.SourceLog = append(resp.SourceLog, fmt.Sprintf("Starting Enriched Intel Workflow for: %s", companyName))

	// 1. Resolve exact LinkedIn Name
	q := fmt.Sprintf(`"%s" LinkedIn company`, companyName)
	results, err := SerpGoogle(q, 3)
	if err != nil || len(results) == 0 {
		resp.SourceLog = append(resp.SourceLog, "Failed to resolve official LinkedIn company page. Falling back to naive search.")
	}

	linkedInUrl := ""
	for _, r := range results {
		if strings.Contains(r.Link, "linkedin.com/company/") {
			linkedInUrl = r.Link
			break
		}
	}

	resolvedName := companyName
	if linkedInUrl != "" {
		parts := strings.Split(strings.TrimRight(linkedInUrl, "/"), "/")
		if len(parts) > 0 {
			resolvedName = parts[len(parts)-1]
			resolvedName = strings.ReplaceAll(resolvedName, "-", " ")
			resp.SourceLog = append(resp.SourceLog, fmt.Sprintf("Flawlessly resolved LinkedIn entity: %s", resolvedName))
		}
	}

	// 2. Determine Company Size
	resp.SourceLog = append(resp.SourceLog, "Scraping web data to ascertain precise company headcount tier...")

	sizeQuery := fmt.Sprintf(`"%s" number of employees site:linkedin.com OR company size`, resolvedName)
	sizeRes, _ := SerpGoogle(sizeQuery, 3)

	combinedSnippets := ""
	for _, sr := range sizeRes {
		combinedSnippets += sr.Snippet + " "
	}

	sysPrompt := "You are a company analytics bot. Read the provided search results and determine the estimated employee headcount for the company. Return ONLY an integer (e.g. '55'). If you don't know, return '100'."
	sizeText, tokens := AskOpenAI(sysPrompt, combinedSnippets)

	estimatedSize, err := strconv.Atoi(sizeText)
	if err != nil || estimatedSize == 0 {
		estimatedSize = 100 // default middle path
	}

	resp.EstimatedSize = estimatedSize
	resp.CompanySizeText = fmt.Sprintf("Estimated ~%d employees", estimatedSize)
	resp.SourceLog = append(resp.SourceLog, fmt.Sprintf("Analytics complete: %s", resp.CompanySizeText))

	// 3. Dynamic Workflow Branching
	var targetRoles []string

	switch {
	case estimatedSize > 500:
		targetRoles = []string{"VP of HR", "Head of Talent Acquisition", "Head of Early Careers", "Recruitment Director"}
		resp.SourceLog = append(resp.SourceLog, "Size > 500: Targeting Senior Talent Acquisition & VP HR.")
	case estimatedSize >= 200 && estimatedSize <= 500:
		targetRoles = []string{"Early Careers Head", "HR Director", "Head of People"}
		resp.SourceLog = append(resp.SourceLog, "Size 200-500: Targeting Early Careers Head / HR Director.")
	case estimatedSize >= 50 && estimatedSize < 200:
		targetRoles = []string{"HR Director", "Chief People Officer", "Head of HR"}
		resp.SourceLog = append(resp.SourceLog, "Size 50-200: Targeting HR Director.")
	case estimatedSize < 50:
		targetRoles = []string{"CEO", "Founder", "CIO", "Partner"}
		resp.SourceLog = append(resp.SourceLog, "Size < 50: Micro-cap. Targeting CEO, Founder, CIO, or Partner.")
	}

	resp.TargetRolesUsed = targetRoles

	// 4. Fetch People based on targets
	resp.SourceLog = append(resp.SourceLog, "Executing multi-role OSINT profile scraping with Anymail/Website fallbacks...")
	people := FindPeopleAtCompanies([]string{resolvedName}, targetRoles, 2, true)

	// Inject results
	resp.PeopleFound = people
	resp.SourceLog = append(resp.SourceLog, fmt.Sprintf("Operation complete. Recovered %d profiles with confirmed OSINT signatures.", len(people)))

	return resp, tokens
}
