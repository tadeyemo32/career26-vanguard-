// cmd/ingest/main.go
// Companies House Asset Manager ETL Ingester
// Usage: go run cmd/ingest/main.go --csv /path/to/BasicCompanyData.csv
//
// Filters records where SICCode matches UK Asset Management / Fund Management codes,
// normalises the data, and upserts into the local SQLite database.
//
// Asset Manager SIC codes targeted:
//   64301 - Investment trusts
//   64302 - Unit trusts
//   64303 - Venture / development capital
//   64304 - Open-ended investment companies (OEICs)
//   64305 - Investment clubs
//   64306 - Real estate investment trusts (REITs)
//   64991 - Security dealing on own account
//   66120 - Security & commodity contracts dealing
//   66300 - Fund management activities (PRIMARY)

package main

import (
	"encoding/csv"
	"flag"
	"io"
	"log"
	"os"
	"strings"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// AMSicCodes — set of UK SIC codes that map to asset management activity
var AMSicCodes = map[string]bool{
	"64301": true,
	"64302": true,
	"64303": true,
	"64304": true,
	"64305": true,
	"64306": true,
	"64991": true,
	"66120": true,
	"66300": true,
}

// CompanyHouseRecord is the ETL-normalised schema for an AM firm
type CompanyHouseRecord struct {
	gorm.Model
	CompanyName        string `gorm:"uniqueIndex"`
	CompanyNumber      string
	RegAddressLine1    string
	RegAddressTown     string
	RegAddressPostCode string
	CompanyType        string
	Status             string
	SICCode1           string
	SICCode2           string
	SICCode3           string
	SICCode4           string
}

func main() {
	csvPath := flag.String("csv", "", "Path to Companies House BasicCompanyData CSV")
	dbPath := flag.String("db", "./data/vanguard.db", "Path to SQLite database file")
	flag.Parse()

	if *csvPath == "" {
		log.Fatal("--csv flag is required. Download from: https://download.companieshouse.gov.uk/en_output.html")
	}

	os.MkdirAll("data", os.ModePerm)

	db, err := gorm.Open(sqlite.Open(*dbPath), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Warn),
	})
	if err != nil {
		log.Fatalf("Failed to open database: %v", err)
	}

	if err := db.AutoMigrate(&CompanyHouseRecord{}); err != nil {
		log.Fatalf("Migration failed: %v", err)
	}

	f, err := os.Open(*csvPath)
	if err != nil {
		log.Fatalf("Cannot open CSV: %v", err)
	}
	defer f.Close()

	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	reader.TrimLeadingSpace = true
	reader.FieldsPerRecord = -1 // tolerate malformed rows

	headers, err := reader.Read()
	if err != nil {
		log.Fatalf("Failed to read CSV headers: %v", err)
	}

	// Build header index — Companies House column names vary slightly between releases
	idx := map[string]int{}
	for i, h := range headers {
		idx[strings.TrimSpace(strings.ToLower(h))] = i
	}

	getCol := func(row []string, names ...string) string {
		for _, n := range names {
			if i, ok := idx[n]; ok && i < len(row) {
				return strings.TrimSpace(row[i])
			}
		}
		return ""
	}

	sicCols := []string{
		"siccode.sic text 1", "sic code 1", "siccode1",
		"siccode.sic text 2", "sic code 2", "siccode2",
		"siccode.sic text 3", "sic code 3", "siccode3",
		"siccode.sic text 4", "sic code 4", "siccode4",
	}

	var total, inserted, skipped int

	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Printf("Warning: skipping malformed row: %v", err)
			continue
		}

		total++

		// Gather all SIC codes for this company
		var sics []string
		// SIC columns may be grouped or individual
		for j, h := range headers {
			hl := strings.TrimSpace(strings.ToLower(h))
			if strings.Contains(hl, "sic") && j < len(row) {
				v := strings.TrimSpace(row[j])
				if v != "" && v != "None" {
					// Strip description text — Companies House includes "66300 - Fund management activities"
					code := strings.SplitN(v, " ", 2)[0]
					if len(code) >= 5 {
						sics = append(sics, code)
					}
				}
			}
		}

		if len(sics) == 0 {
			// Try the explicitly named cols
			for _, c := range sicCols {
				if v := getCol(row, c); v != "" {
					code := strings.SplitN(v, " ", 2)[0]
					sics = append(sics, code)
				}
			}
		}

		matched := false
		for _, s := range sics {
			if AMSicCodes[s] {
				matched = true
				break
			}
		}

		if !matched {
			skipped++
			continue
		}

		// Only ingest active companies
		status := strings.ToLower(getCol(row, "companystatus", "company status", "status"))
		if status != "" && status != "active" && status != "registered" {
			skipped++
			continue
		}

		// Pad sics to 4
		for len(sics) < 4 {
			sics = append(sics, "")
		}

		record := CompanyHouseRecord{
			CompanyName:        getCol(row, "companyname", "company name"),
			CompanyNumber:      getCol(row, "companynumber", "company number"),
			RegAddressLine1:    getCol(row, "regaddress.addressline1", "registered office address line 1"),
			RegAddressTown:     getCol(row, "regaddress.posttrown", "registered office address post town"),
			RegAddressPostCode: getCol(row, "regaddress.postcode", "registered office address post code"),
			CompanyType:        getCol(row, "companytype", "company type"),
			Status:             getCol(row, "companystatus", "company status"),
			SICCode1:           sics[0],
			SICCode2:           sics[1],
			SICCode3:           sics[2],
			SICCode4:           sics[3],
		}

		if record.CompanyName == "" {
			skipped++
			continue
		}

		result := db.Where(CompanyHouseRecord{CompanyName: record.CompanyName}).
			Assign(record).
			FirstOrCreate(&record)
		if result.Error != nil {
			log.Printf("DB error for '%s': %v", record.CompanyName, result.Error)
		} else {
			inserted++
		}

		if total%50000 == 0 {
			log.Printf("Progress: %d rows processed, %d AM firms found...", total, inserted)
		}
	}

	log.Printf("ETL complete. Processed %d rows. Inserted/Updated %d asset managers. Skipped %d.", total, inserted, skipped)
}
