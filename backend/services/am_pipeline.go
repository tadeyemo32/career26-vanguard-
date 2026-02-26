package services

import (
	"fmt"
	"log"
	"strings"

	"github.com/tadeyemo32/vanguard-backend/models"
)

// ProcessAMFirm executes the evaluation and people extraction pipeline for an AM firm.
func ProcessAMFirm(firmName string) ([]models.PersonRow, int, error) {
	log.Printf("[AM Pipeline] Processing firm: %s", firmName)

	var output []models.PersonRow
	totalTokens := 0

	// 1. Resolve domain and LinkedIn via SERP
	q := fmt.Sprintf(`"%s" official website OR site:linkedin.com/company`, firmName)
	results, err := SerpGoogle(q, 5)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to search firm details: %v", err)
	}

	linkedInUrl := ""
	domainUrl := ""
	combinedSnippetText := ""

	for _, r := range results {
		combinedSnippetText += r.Snippet + " "
		if strings.Contains(r.Link, "linkedin.com/company/") && linkedInUrl == "" {
			linkedInUrl = r.Link
		} else if !strings.Contains(r.Link, "linkedin.com") && strings.HasPrefix(r.Link, "http") && domainUrl == "" {
			domainUrl = r.Link
		}
	}

	// 2. Feed descriptions to LLM to confirm AM status and get details
	sysPrompt := `You are a financial services classification expert. 
Based on the provided snippets, determine:
1. Is this firm an Asset Management (AM) firm, Investment Manager, Wealth Manager, or Private Equity firm? (Yes/No)
2. What specific kind of firm is it? (e.g., Quantitative Hedge Fund, Long-Only Asset Manager, Real Estate PE, etc.)
If Yes, return: "YES|Type" (e.g., "YES|Quantitative Hedge Fund").
If No, return: "NO|Reason".`

	llmRes, t1 := AskOpenAI(sysPrompt, fmt.Sprintf("Company name: %s\nSnippets: %s", firmName, combinedSnippetText))
	totalTokens += t1
	log.Printf("[AM Pipeline] LLM Classification for %s: %s", firmName, llmRes)

	if !strings.HasPrefix(strings.ToUpper(llmRes), "YES") {
		return nil, totalTokens, fmt.Errorf("Firm rejected by LLM: %s", llmRes)
	}

	// AM confirmed. Extract type if possible.
	parts := strings.SplitN(llmRes, "|", 2)
	amType := "Asset Manager"
	if len(parts) > 1 {
		amType = strings.TrimSpace(parts[1])
	}

	// 3. Determine size for Career26 rules
	sizeQuery := fmt.Sprintf(`"%s" number of employees site:linkedin.com OR company size`, firmName)
	sizeRes, _ := SerpGoogle(sizeQuery, 3)
	sizeSnippets := ""
	for _, sr := range sizeRes {
		sizeSnippets += sr.Snippet + " "
	}

	sizeSysPrompt := "Determine the estimated employee headcount for the company. Return ONLY an integer (e.g. '55'). If you don't know, return '100'."
	sizeText, t2 := AskOpenAI(sizeSysPrompt, sizeSnippets)
	totalTokens += t2
	var estimatedSize int
	fmt.Sscanf(strings.TrimSpace(sizeText), "%d", &estimatedSize)
	if estimatedSize == 0 {
		estimatedSize = 100 // fallback
	}

	targetBand := GetTargetRolesByHeadcount(estimatedSize)
	if targetBand == nil {
		// If size > 500, skip per headless rules (or default to something if needed)
		log.Printf("[AM Pipeline] Skipping %s: size %d is out of bounds for outreach", firmName, estimatedSize)
		return nil, totalTokens, nil // Or target specific roles anyway
	}

	log.Printf("[AM Pipeline] Attempting to find roles %v for %s", targetBand.Roles, firmName)

	// 4. Fetch people at the company
	people := FindPeopleAtCompanies([]string{firmName}, targetBand.Roles, 3, true)

	// Enrich people data with AM details
	for _, p := range people {
		p.CompanyType = amType
		p.SizeBand = targetBand.Label
		output = append(output, p)
	}

	return output, totalTokens, nil
}
