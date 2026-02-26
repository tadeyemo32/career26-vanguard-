package services

import (
	"log"
	"strings"
)

// ExtractCompanies sends raw text to the LLM and asks it to return
// only the company names it can identify. Falls back to line-by-line
// parsing if OpenAI is unavailable.
func ExtractCompanies(data string) ([]string, int) {
	data = strings.TrimSpace(data)
	if data == "" {
		return nil, 0
	}

	// Truncate to avoid excessive token usage (~12k chars ≈ ~3k tokens)
	if len(data) > 12000 {
		data = data[:12000]
	}

	sysPrompt := `You are a company name extractor. 
The user will provide raw text that may contain company names mixed with other data (CSV rows, PDF text, spreadsheet content, etc.).
Your task: identify and return ONLY the names of companies, financial firms, asset managers, organisations, or employers.
Rules:
- Return one company name per line
- Do NOT include individuals' names, job titles, emails, addresses, or generic words
- Do NOT add explanations, numbering, bullet points, or any other text
- If a name appears multiple times, include it only once
- Normalise obvious abbreviations (e.g. "JPM" → "JPMorgan") but keep official names intact
- If no companies are found, return the single word: NONE`

	userPrompt := "Extract all company names from this text:\n\n" + data

	log.Printf("[Extractor] Sending %d chars to LLM for company extraction", len(data))
	result, tokens := AskOpenAI(sysPrompt, userPrompt)

	if result == "" || strings.TrimSpace(result) == "NONE" {
		log.Printf("[Extractor] LLM returned nothing — falling back to line-by-line parse")
		return fallbackExtract(data), tokens
	}

	// Parse the LLM's newline-delimited response
	seen := map[string]bool{}
	var companies []string
	for _, line := range strings.Split(result, "\n") {
		name := strings.TrimSpace(line)
		name = strings.TrimLeft(name, "-•*·") // clean any stray bullets
		name = strings.TrimSpace(name)
		if name == "" || seen[name] || strings.EqualFold(name, "NONE") {
			continue
		}
		seen[name] = true
		companies = append(companies, name)
	}

	log.Printf("[Extractor] LLM extracted %d companies", len(companies))

	if len(companies) == 0 {
		return fallbackExtract(data), tokens
	}

	return companies, tokens
}

// fallbackExtract is a simple line-by-line parser used when the LLM is unavailable.
func fallbackExtract(data string) []string {
	seen := map[string]bool{}
	var out []string
	for _, line := range strings.Split(data, "\n") {
		c := strings.TrimSpace(line)
		c = strings.Trim(c, `"'`)
		if c == "" || seen[c] {
			continue
		}
		// Take first comma-delimited field if it looks like a CSV row
		if strings.Contains(c, ",") {
			parts := strings.SplitN(c, ",", 2)
			c = strings.TrimSpace(parts[0])
		}
		if c == "" || seen[c] {
			continue
		}
		seen[c] = true
		out = append(out, c)
	}
	return out
}
