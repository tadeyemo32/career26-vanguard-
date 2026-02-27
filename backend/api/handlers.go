package api

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/tadeyemo32/vanguard-backend/models"
	"github.com/tadeyemo32/vanguard-backend/services"
)

var keyIDs = []string{"SERPAPI_KEY", "ANYMAIL_API_KEY", "HUNTER_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"}

func maskKey(v string) string {
	if len(v) <= 8 {
		return strings.Repeat("•", len(v))
	}
	return v[:6] + "..." + v[len(v)-4:]
}

// keyStatusHandler returns only boolean connected status for each key.
// Available to all authenticated users (not just admins) so KeyGate works for everyone.
func keyStatusHandler(c *gin.Context) {
	result := gin.H{}
	for _, id := range keyIDs {
		result[id] = os.Getenv(id) != ""
	}
	c.JSON(http.StatusOK, result)
}

func getKeys(c *gin.Context) {
	result := gin.H{}
	for _, id := range keyIDs {
		v := os.Getenv(id)
		result[id] = gin.H{
			"connected": v != "",
			"masked":    maskKey(v), // empty string if not set
		}
	}
	c.JSON(http.StatusOK, result)
}

func saveKeys(c *gin.Context) {
	// Accept a flat map of key-id → value for flexibility
	var payload map[string]string
	if err := c.BindJSON(&payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid body"})
		return
	}

	// Set in-process immediately so the server can use them right away
	for _, id := range keyIDs {
		if v, ok := payload[id]; ok && v != "" {
			os.Setenv(id, v)
		}
	}

	// Also persist to .env so they survive a server restart
	if err := persistToEnv(payload); err != nil {
		log.Printf("[saveKeys] warning: could not write .env: %v", err)
		// Don't fail the request — in-process env is already updated
	}

	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

// persistToEnv reads the existing .env, updates matching KEY=VALUE lines, and writes it back.
func persistToEnv(updates map[string]string) error {
	envPath := "../.env"
	data, err := os.ReadFile(envPath)
	if err != nil {
		// Create a new .env if it doesn't exist
		data = []byte{}
	}

	lines := strings.Split(string(data), "\n")
	updated := map[string]bool{}

	for i, line := range lines {
		if strings.HasPrefix(line, "#") || !strings.Contains(line, "=") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		key := strings.TrimSpace(parts[0])
		if v, ok := updates[key]; ok && v != "" {
			lines[i] = key + "=" + v
			updated[key] = true
		}
	}

	// Append any keys not already in .env
	for k, v := range updates {
		if v != "" && !updated[k] {
			lines = append(lines, k+"="+v)
		}
	}

	return os.WriteFile(envPath, []byte(strings.Join(lines, "\n")), 0600)
}

func getModelHandler(c *gin.Context) {
	provider, model := services.GetLLM()
	c.JSON(http.StatusOK, gin.H{"provider": provider, "model": model})
}

func setModelHandler(c *gin.Context) {
	var body struct {
		Provider string `json:"provider"`
		Model    string `json:"model"`
	}
	if err := c.BindJSON(&body); err != nil || body.Provider == "" || body.Model == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "provider and model are required"})
		return
	}
	services.SetLLM(body.Provider, body.Model)
	c.JSON(http.StatusOK, gin.H{"status": "ok", "provider": body.Provider, "model": body.Model})
}

func getUserMeHandler(c *gin.Context) {
	// DEV BYPASS: return a synthetic admin user without hitting the DB
	if _, isBypass := c.Get("devBypass"); isBypass {
		c.JSON(http.StatusOK, gin.H{
			"email":       "dev@local.dev",
			"credits":     9999999,
			"role":        "admin",
			"is_verified": true,
		})
		return
	}

	userIDVal, exists := c.Get("userID")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}
	userID, ok := userIDVal.(uint)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	var user models.User
	if err := services.DB.First(&user, userID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"email":       user.Email,
		"credits":     user.Credits,
		"role":        user.Role,
		"is_verified": user.IsVerified,
	})
}

func logQueryTokens(c *gin.Context, queryType, queryText string, tokens int) {
	if tokens == 0 {
		return
	}
	userIDVal, exists := c.Get("userID")
	if !exists {
		return // Not an authenticated request or no user associated
	}
	userID, ok := userIDVal.(uint)
	if !ok {
		return
	}

	record := &models.QueryLog{
		UserID:     userID,
		QueryType:  queryType,
		QueryText:  queryText,
		TokensUsed: tokens,
	}
	if err := services.DB.Create(record).Error; err != nil {
		log.Printf("[API] Failed to log query tokens for user %d: %v", userID, err)
	}

	// Deduct credits
	var usr models.User
	if err := services.DB.First(&usr, userID).Error; err == nil {
		usr.Credits -= tokens
		services.DB.Save(&usr)
	}
}

func extractDataHandler(c *gin.Context) {
	var req models.ExtractDataRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request payload."})
		return
	}
	companies, tokens := services.ExtractCompanies(req.Payload)
	logQueryTokens(c, "ExtractCompanies", "Company extraction payload", tokens)
	c.JSON(http.StatusOK, gin.H{"companies": companies})
}

func aiSearchHandler(c *gin.Context) {
	var req models.AISearchRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request parameters."})
		return
	}
	limit := req.Limit
	if limit <= 0 {
		limit = 15
	}
	if limit > 50 {
		limit = 50
	}
	results, tokens := services.AISearch(req.Query, limit)
	logQueryTokens(c, "AISearch", req.Query, tokens)
	c.JSON(http.StatusOK, gin.H{"results": results})
}

func companyIntelHandler(c *gin.Context) {
	var req models.CompanyIntelRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request parameters."})
		return
	}
	intel, tokens := services.RunCompanyIntel(req.CompanyName)
	logQueryTokens(c, "CompanyIntel", req.CompanyName, tokens)
	c.JSON(http.StatusOK, gin.H{"intel": intel})
}

func outreachRunHandler(c *gin.Context) {
	var req models.OutreachRunRequest
	if err := c.BindJSON(&req); err != nil {
		log.Printf("Bind error: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request parameters."})
		return
	}
	if len(req.Companies) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "No companies provided."})
		return
	}
	if len(req.JobTitles) == 0 {
		req.JobTitles = []string{"Director", "Partner"}
	}
	if req.MaxPerCompany == 0 {
		req.MaxPerCompany = 5
	}
	log.Printf("Outreach pipeline: %d companies", len(req.Companies))
	results := services.FindPeopleAtCompanies(req.Companies, req.JobTitles, req.MaxPerCompany, true)
	c.JSON(http.StatusOK, gin.H{"results": results, "people_added": len(results)})
}

// knownDomains maps normalised company name tokens → authoritative apex domain.
// This is checked BEFORE any SERP call so well-known firms always resolve correctly.
var knownDomains = map[string]string{
	// Banks & Investment Banks
	"goldman sachs":       "gs.com",
	"goldman":             "gs.com",
	"gs":                  "gs.com",
	"jp morgan":           "jpmorgan.com",
	"jpmorgan":            "jpmorgan.com",
	"morgan stanley":      "morganstanley.com",
	"barclays":            "barclays.com",
	"barclays bank":       "barclays.com",
	"barclays investment": "barclays.com",
	"hsbc":                "hsbc.com",
	"deutsche bank":       "db.com",
	"ubs":                 "ubs.com",
	"credit suisse":       "credit-suisse.com",
	"citigroup":           "citi.com",
	"citi":                "citi.com",
	"bnp paribas":         "bnpparibas.com",
	"bnp":                 "bnpparibas.com",
	"societe generale":    "societegenerale.com",
	"socgen":              "societegenerale.com",
	"nomura":              "nomura.com",
	"mizuho":              "mizuho-fg.com",
	"wells fargo":         "wellsfargo.com",
	"bank of america":     "bankofamerica.com",
	"bofa":                "bankofamerica.com",
	"merrill lynch":       "ml.com",
	"lazard":              "lazard.com",
	"rothschild":          "rothschildandco.com",
	"evercore":            "evercore.com",
	"jefferies":           "jefferies.com",
	"piper sandler":       "pipersandler.com",
	"raymond james":       "raymondjames.com",
	"cowen":               "cowen.com",
	"stifel":              "stifel.com",
	// Asset Managers
	"blackrock":                "blackrock.com",
	"vanguard":                 "vanguard.com",
	"fidelity":                 "fidelity.com",
	"state street":             "statestreet.com",
	"pimco":                    "pimco.com",
	"t rowe price":             "troweprice.com",
	"invesco":                  "invesco.com",
	"franklin templeton":       "franklintempleton.com",
	"capital group":            "capitalgroup.com",
	"wellington management":    "wellington.com",
	"wellington":               "wellington.com",
	"dimensional":              "dimensional.com",
	"dfa":                      "dimensional.com",
	"aberdeen":                 "aberdeengroup.com",
	"abrdn":                    "abrdn.com",
	"schroders":                "schroders.com",
	"schroder":                 "schroders.com",
	"man group":                "man.com",
	"man investments":          "man.com",
	"brevan howard":            "brevanhoward.com",
	"paulson":                  "paulsonandc.com",
	"aqr":                      "aqr.com",
	"two sigma":                "twosigma.com",
	"renaissance":              "rentec.com",
	"renaissance technologies": "rentec.com",
	"citadel":                  "citadel.com",
	"millennium":               "mlp.com",
	"point72":                  "point72.com",
	"bridgewater":              "bridgewater.com",
	"tudor":                    "tudor.com",
	"third point":              "thirdpointllc.com",
	"elliot management":        "elliottmgmt.com",
	"blue owl":                 "blueowl.com",
	"ares management":          "aresmgmt.com",
	"ares":                     "aresmgmt.com",
	"apollo":                   "apollo.com",
	"apollo global":            "apollo.com",
	"carlyle":                  "carlyle.com",
	"kkr":                      "kkr.com",
	"blackstone":               "blackstone.com",
	"tpg":                      "tpg.com",
	"warburg pincus":           "warburgpincus.com",
	"advent international":     "adventinternational.com",
	"bain capital":             "baincapital.com",
	"general atlantic":         "generalatlantic.com",
	"tiger global":             "tigerglobal.com",
	"sequoia":                  "sequoiacap.com",
	"andreessen horowitz":      "a16z.com",
	"a16z":                     "a16z.com",
	"coatue":                   "coatue.com",
	"insight partners":         "insightpartners.com",
	"softbank":                 "softbank.com",
	"temasek":                  "temasek.com",
	"gic":                      "gic.com.sg",
	"norges bank":              "norges-bank.no",
	"canada pension":           "cppinvestments.com",
	"cpp":                      "cppinvestments.com",
	"ontario teachers":         "otpp.com",
	"otpp":                     "otpp.com",
	"calpers":                  "calpers.ca.gov",
	"calstrs":                  "calstrs.com",
	// Brokers & Platforms
	"interactive brokers": "interactivebrokers.com",
	"ibkr":                "interactivebrokers.com",
	"charles schwab":      "schwab.com",
	"schwab":              "schwab.com",
	"td ameritrade":       "tdameritrade.com",
	"etrade":              "etrade.com",
	"robinhood":           "robinhood.com",
	"coinbase":            "coinbase.com",
	// Big Tech / Other
	"google":            "google.com",
	"alphabet":          "abc.xyz",
	"microsoft":         "microsoft.com",
	"apple":             "apple.com",
	"amazon":            "amazon.com",
	"meta":              "meta.com",
	"facebook":          "meta.com",
	"netflix":           "netflix.com",
	"tesla":             "tesla.com",
	"nvidia":            "nvidia.com",
	"ibm":               "ibm.com",
	"oracle":            "oracle.com",
	"salesforce":        "salesforce.com",
	"mckinsey":          "mckinsey.com",
	"bain":              "bain.com",
	"bcg":               "bcg.com",
	"boston consulting": "bcg.com",
	"deloitte":          "deloitte.com",
	"kpmg":              "kpmg.com",
	"pwc":               "pwc.com",
	"ey":                "ey.com",
	"ernst young":       "ey.com",
}

// resolveCompanyDomain attempts to find the canonical domain for a company name.
// Priority: (1) exact/prefix match in curated knownDomains, (2) SERP fallback.
func resolveCompanyDomain(companyInput string) (string, bool) {
	lower := strings.ToLower(strings.TrimSpace(companyInput))

	// If it already looks like a domain, use it directly
	if strings.Contains(lower, ".") {
		domain := lower
		domain = strings.TrimPrefix(domain, "https://")
		domain = strings.TrimPrefix(domain, "http://")
		domain = strings.Split(domain, "/")[0]
		return domain, true
	}

	// 1. Exact match
	if d, ok := knownDomains[lower]; ok {
		return d, true
	}

	// 2. Prefix match (e.g. "goldman" → "goldman sachs" entry)
	for key, domain := range knownDomains {
		if strings.HasPrefix(key, lower) || strings.HasPrefix(lower, key) {
			return domain, true
		}
	}

	// 3. Token overlap match — any known key that shares all input tokens
	inputTokens := strings.Fields(lower)
	for key, domain := range knownDomains {
		keyTokens := strings.Fields(key)
		matchCount := 0
		for _, t := range inputTokens {
			for _, kt := range keyTokens {
				if kt == t {
					matchCount++
				}
			}
		}
		if matchCount > 0 && matchCount >= len(inputTokens) {
			return domain, true
		}
	}

	return "", false
}

// findEmailHandler routes searches to Anymail based on SearchType.
// Supported search types: person, company, decision_maker, linkedin.
func findEmailHandler(c *gin.Context) {
	var req models.FindEmailRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request format."})
		return
	}

	req.SearchType = strings.TrimSpace(req.SearchType)
	req.FullName = strings.TrimSpace(req.FullName)
	req.Company = strings.TrimSpace(req.Company)
	req.Domain = strings.TrimSpace(req.Domain)
	req.LinkedInURL = strings.TrimSpace(req.LinkedInURL)
	req.JobRoles = strings.TrimSpace(req.JobRoles)

	// Fallback to legacy behavior if not specified
	if req.SearchType == "" {
		if req.LinkedInURL != "" {
			req.SearchType = "linkedin"
		} else {
			req.SearchType = "person"
		}
	}

	var logs []string
	add := func(s string) { logs = append(logs, s) }

	// Ensure we have a domain or company for non-linkedin searches
	targetDomain := req.Domain
	if targetDomain == "" {
		targetDomain = req.Company
	}

	switch req.SearchType {
	case "company":
		if targetDomain == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "domain or company is required for Company search."})
			return
		}
		add(fmt.Sprintf("Input: Company Search for %q", targetDomain))
		add("Anymail Finder: Searching for all emails at company…")

		rawResults, anyErr := services.FindEmailsAnymailByCompanyDomain(targetDomain)
		var results []models.FindEmailResultItem
		if anyErr == nil {
			for _, r := range rawResults {
				results = append(results, models.FindEmailResultItem{
					Email:    r.Email,
					FullName: r.FullName,
					JobTitle: r.JobTitle,
					Source:   "Anymail Finder",
				})
			}
		}

		if anyErr != nil || len(results) == 0 {
			if anyErr != nil {
				add(fmt.Sprintf("Anymail: %v", anyErr))
			} else {
				add("Anymail Finder: no valid emails found.")
			}
			add("Hunter.io: Falling back to domain search…")
			hunterResults, hunterErr := services.FindEmailsHunterByCompany(targetDomain)
			if hunterErr != nil {
				add(fmt.Sprintf("Hunter.io: %v", hunterErr))
				c.JSON(http.StatusOK, models.FindEmailResponse{Logs: logs, Error: hunterErr.Error()})
				return
			}
			results = hunterResults
			add(fmt.Sprintf("✓ Hunter.io found %d emails.", len(results)))
		} else {
			add(fmt.Sprintf("✓ Anymail found %d verified emails.", len(results)))
		}

		var responseEmails []models.FindEmailResultItem
		for _, r := range results {
			responseEmails = append(responseEmails, models.FindEmailResultItem{
				Email:    r.Email,
				FullName: r.FullName,
				JobTitle: r.JobTitle,
				Source:   "Anymail Finder",
			})
		}

		c.JSON(http.StatusOK, models.FindEmailResponse{
			Emails: responseEmails,
			Logs:   logs,
			Source: "Anymail Finder",
		})

	case "decision_maker":
		if targetDomain == "" || req.JobRoles == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Both domain/company and job_roles are required."})
			return
		}
		add(fmt.Sprintf("Input: Decision Maker Search for %q roles at %q", req.JobRoles, targetDomain))
		add("Anymail Finder: Searching for decision makers…")

		rawResults, err := services.FindDecisionMakerAnymail(targetDomain, req.JobRoles)
		var results []models.FindEmailResultItem
		if err == nil {
			for _, r := range rawResults {
				results = append(results, models.FindEmailResultItem{
					Email:    r.Email,
					FullName: r.FullName,
					JobTitle: r.JobTitle,
					Source:   "Anymail Finder",
				})
			}
		}

		if err != nil || len(results) == 0 {
			if err != nil {
				add(fmt.Sprintf("Anymail: %v", err))
			} else {
				add("Anymail Finder: no decision makers found.")
			}
			add("Hunter.io: Falling back to department search…")
			hunterResults, hunterErr := services.FindDecisionMakersHunter(targetDomain, req.JobRoles)
			if hunterErr != nil {
				add(fmt.Sprintf("Hunter.io: %v", hunterErr))
				c.JSON(http.StatusOK, models.FindEmailResponse{Logs: logs, Error: hunterErr.Error()})
				return
			}
			results = hunterResults
			add(fmt.Sprintf("✓ Hunter.io found %d decision makers.", len(results)))
		} else {
			add(fmt.Sprintf("✓ Anymail found %d verified decision makers.", len(results)))
		}

		c.JSON(http.StatusOK, models.FindEmailResponse{
			Emails: results,
			Logs:   logs,
			Source: "Anymail Finder",
		})

	case "linkedin":
		if req.LinkedInURL == "" && strings.Contains(req.Company, "linkedin.com/in/") {
			req.LinkedInURL = req.Company // auto-detect legacy UI behavior
		}
		if req.LinkedInURL == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "linkedin_url is required."})
			return
		}
		add(fmt.Sprintf("Input: LinkedIn URL %q", req.LinkedInURL))
		add("Anymail Finder (LinkedIn URL): looking up profile…")
		var result services.AnymailLinkedInResult
		var isHunter bool
		var hunterConfidence float64
		var hunterSource string

		rawResult, anymailErr := services.FindEmailAnymailByLinkedIn(req.LinkedInURL)
		if anymailErr == nil && rawResult.Email != "" {
			result = rawResult
		}

		if anymailErr != nil || result.Email == "" {
			if anymailErr != nil {
				add(fmt.Sprintf("Anymail LinkedIn: %v", anymailErr))
			}
			add("Anymail LinkedIn: no verified email found.")
			add("Hunter.io: Falling back to LinkedIn reverse search…")

			hunterResult, hunterErr := services.FindEmailHunterByLinkedIn(req.LinkedInURL)
			if hunterErr != nil {
				add(fmt.Sprintf("Hunter.io LinkedIn: %v", hunterErr))
				c.JSON(http.StatusOK, models.FindEmailResponse{Logs: logs, Error: hunterErr.Error()})
				return
			}
			result.Email = hunterResult.Email
			result.FullName = hunterResult.FullName
			result.JobTitle = hunterResult.JobTitle
			// Confidence/Source manually overridden below since they aren't in AnymailLinkedInResult
			isHunter = true
			hunterConfidence = hunterResult.Confidence
			hunterSource = hunterResult.Source
		}

		if result.Email != "" {
			add(fmt.Sprintf("✓ Found: %s", result.Email))
			if result.FullName != "" {
				add(fmt.Sprintf("  Name: %s — %s @ %s", result.FullName, result.JobTitle, result.Company))
			}

			conf := 1.0
			src := "Anymail Finder (LinkedIn)"
			if isHunter {
				conf = hunterConfidence
				src = hunterSource
			}

			c.JSON(http.StatusOK, models.FindEmailResponse{
				Email:      result.Email, // legacy single return
				Confidence: conf,
				Emails: []models.FindEmailResultItem{{
					Email:      result.Email,
					FullName:   result.FullName,
					JobTitle:   result.JobTitle,
					Confidence: conf,
					Source:     src,
				}},
				Logs:   logs,
				Source: src,
			})
			return
		}
		// if result is still nil/empty this will process correctly
		add("No verified email found.")
		c.JSON(http.StatusOK, models.FindEmailResponse{Logs: logs})

	default: // "person"
		if req.FullName == "" || req.Company == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "full_name and company are required for Person search."})
			return
		}

		add(fmt.Sprintf("Input: Person Search for %q at %q", req.FullName, req.Company))

		// Step 1: Anymail Finder
		add(fmt.Sprintf("Anymail Finder: searching %s @ %s…", req.FullName, req.Company))
		email, conf, err := services.FindEmailAnymailByCompany(req.FullName, req.Company)
		if err == nil && email != "" {
			add(fmt.Sprintf("✓ Anymail found: %s (%.0f%% confidence)", email, conf*100))
			c.JSON(http.StatusOK, models.FindEmailResponse{
				Email:      email,
				Confidence: conf,
				Emails: []models.FindEmailResultItem{{
					Email:      email,
					Confidence: conf,
					Source:     "Anymail Finder",
				}},
				Logs:   logs,
				Source: "Anymail Finder",
			})
			return
		}
		add(fmt.Sprintf("Anymail: %v", err))

		// Step 2: Hunter.io fallback
		add(fmt.Sprintf("Hunter.io: searching %s @ %s…", req.FullName, req.Company))
		email, conf, err = services.FindEmailHunter(req.FullName, req.Company)
		if err == nil && email != "" {
			add(fmt.Sprintf("✓ Hunter.io found: %s (%.0f%% confidence)", email, conf*100))
			c.JSON(http.StatusOK, models.FindEmailResponse{
				Email:      email,
				Confidence: conf,
				Emails: []models.FindEmailResultItem{{
					Email:      email,
					Confidence: conf,
					Source:     "Hunter.io",
				}},
				Logs:   logs,
				Source: "Hunter.io",
			})
			return
		}
		add(fmt.Sprintf("Hunter.io: %v", err))

		add(fmt.Sprintf("No verified email found. Error: %v", err))
		c.JSON(http.StatusOK, models.FindEmailResponse{Logs: logs, Error: err.Error()})
	}
}

// amFirmsHandler lists asset manager firms from the Companies House SQLite database.
func amFirmsHandler(c *gin.Context) {
	search := c.Query("search")
	firms, total, err := services.GetAMFirms(search, 200)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"firms": firms, "total": total})
}

// pipelineRunHandler applies headcount-based outreach rules.
// Companies outside the 25–500 range are skipped automatically.
func pipelineRunHandler(c *gin.Context) {
	var req struct {
		Companies []struct {
			Name      string `json:"company_name"`
			Headcount int    `json:"headcount"`
		} `json:"companies"`
		MaxPerCompany int `json:"max_per_company"`
	}
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request."})
		return
	}
	if req.MaxPerCompany == 0 {
		req.MaxPerCompany = 5
	}

	type target struct {
		Name  string
		Roles []string
		Band  string
	}

	var targets []target
	var skipped []string

	for _, co := range req.Companies {
		band := services.GetTargetRolesByHeadcount(co.Headcount)
		if band == nil {
			skipped = append(skipped, co.Name)
			continue
		}
		targets = append(targets, target{Name: co.Name, Roles: band.Roles, Band: band.Label})
	}

	log.Printf("[Pipeline] %d targetable / %d skipped", len(targets), len(skipped))

	type row struct {
		Company string             `json:"company"`
		Band    string             `json:"band"`
		People  []models.PersonRow `json:"people"`
	}

	var results []row
	for _, t := range targets {
		people := services.FindPeopleAtCompanies([]string{t.Name}, t.Roles, req.MaxPerCompany, true)
		results = append(results, row{Company: t.Name, Band: t.Band, People: people})
	}

	c.JSON(http.StatusOK, gin.H{"results": results, "skipped": skipped})
}

// domainSearchHandler finds all emails at a company domain via Hunter.io domain-search.
// Query param: ?company=<name or domain>
func domainSearchHandler(c *gin.Context) {
	company := strings.TrimSpace(c.Query("company"))
	if company == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "company query param is required"})
		return
	}
	people, err := services.DomainSearchHunter(company)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"results": people, "total": len(people)})
}

// amPipelineRunHandler triggers the AM firm evaluation workflow for one or more firm names.
func amPipelineRunHandler(c *gin.Context) {
	var req struct {
		Firms []string `json:"firms"`
	}
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request."})
		return
	}

	type Result struct {
		Firm   string             `json:"firm"`
		People []models.PersonRow `json:"people"`
		Error  string             `json:"error,omitempty"`
	}

	var results []Result
	totalTokens := 0
	for _, firm := range req.Firms {
		people, tokens, err := services.ProcessAMFirm(firm)
		totalTokens += tokens
		if err != nil {
			results = append(results, Result{Firm: firm, Error: err.Error()})
		} else {
			results = append(results, Result{Firm: firm, People: people})
		}
	}

	logQueryTokens(c, "AMPipeline", fmt.Sprintf("Firms: %d", len(req.Firms)), totalTokens)

	c.JSON(http.StatusOK, gin.H{"results": results})
}
