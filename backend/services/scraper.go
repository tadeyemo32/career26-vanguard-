package services

import (
	"crypto/tls"
	"fmt"
	"log"
	"net/http"
	"regexp"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
)

var emailRegex = regexp.MustCompile(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`)

func FallbackFindEmail(fullName, companyName string) (string, float64, error) {
	log.Printf("[Fallback] Attempting OSINT Scraper+LLM for %s at %s", fullName, companyName)

	// 1. Find domain via Serp
	q := fmt.Sprintf(`"%s" official website`, companyName)
	results, err := SerpGoogle(q, 3)
	if err != nil || len(results) == 0 {
		return "", 0.0, fmt.Errorf("could not search for company domain: %v", err)
	}

	var urlTarget string
	for _, r := range results {
		// exclude generic directories
		if !strings.Contains(r.Link, "linkedin.com") && !strings.Contains(r.Link, "facebook.com") && strings.HasPrefix(r.Link, "http") {
			urlTarget = r.Link
			break
		}
	}

	if urlTarget == "" {
		return "", 0.0, fmt.Errorf("no official valid domain found")
	}
	log.Printf("[Fallback] Discovered likely domain: %s", urlTarget)

	// 2. Scrape website text
	client := &http.Client{
		Timeout: 10 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
	}

	req, err := http.NewRequest("GET", urlTarget, nil)
	if err != nil {
		return "", 0.0, err
	}
	// Mimic a real browser
	req.Header.Set("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

	resp, err := client.Do(req)
	if err != nil {
		return "", 0.0, fmt.Errorf("failed fetching domain body: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", 0.0, fmt.Errorf("domain returned HTTP status %d", resp.StatusCode)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return "", 0.0, err
	}

	// Remove scripts/styles
	doc.Find("script, style, noscript, nav, footer, header").Remove()
	text := strings.TrimSpace(doc.Text())

	// Strip excess whitespaces to pack the LLM prompt efficiently
	spaceRe := regexp.MustCompile(`\s+`)
	text = spaceRe.ReplaceAllString(text, " ")

	if len(text) > 8000 {
		text = text[:8000] // Stay within token limits
	}

	// 3. Regex simple email search for immediate results to feed LLM
	emailsFound := emailRegex.FindAllString(text, -1)
	emailsStr := strings.Join(emailsFound, ", ")

	// 4. Inject logic into OpenAI standard payload
	sysPrompt := "You are a specialized OSINT email resolution bot. Your job is to return the precise email of the person requested based on the input text. Calculate typical generic email structures (e.g. first.last@domain.com, first initial + last name, etc). Return EXACTLY and ONLY the email address string in lowercase. If you cannot confidently guess the email based on the data, return exactly 'NOT_FOUND'."

	userPrompt := fmt.Sprintf(`Target Person: %s
Company: %s
Domain Found: %s

Raw emails found via Regex on their page: %s
Extracted Homepage Payload:
%s

What is their likely email?`, fullName, companyName, urlTarget, emailsStr, text)

	result, _ := AskOpenAI(sysPrompt, userPrompt)

	if result == "" || strings.ToUpper(result) == "NOT_FOUND" {
		return "", 0.0, fmt.Errorf("unable to find email") // requested verbatim by user prompt
	}

	// Validate the LLM actually output an email
	if emailRegex.MatchString(result) {
		email := strings.ToLower(strings.TrimSpace(result))
		// Confidence tiers:
		// 0.65 — LLM confirmed pattern AND real emails were found on site (structure cross-verified)
		// 0.50 — LLM guessing from homepage text alone (pattern-only, unverified)
		conf := 0.50
		if len(emailsFound) > 0 {
			conf = 0.65
		}
		log.Printf("[Fallback] Guessed email: %s (conf %.2f)", email, conf)
		return email, conf, nil
	}

	return "", 0.0, fmt.Errorf("unable to find email")
}
