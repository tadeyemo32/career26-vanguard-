package services

import (
	"log"
	"os"
	"path/filepath"

	"github.com/glebarez/sqlite"
	"github.com/tadeyemo32/vanguard-backend/models"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var DB *gorm.DB

func InitDB() {
	dbPath := os.Getenv("DATABASE_PATH")
	if dbPath == "" {
		os.MkdirAll("data", os.ModePerm)
		dbPath = filepath.Join("data", "vanguard.db")
	}

	var err error
	DB, err = gorm.Open(sqlite.Open(dbPath), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent),
	})
	if err != nil {
		log.Fatalf("failed to connect database: %v", err)
	}

	err = DB.AutoMigrate(
		&models.User{},
		&models.QueryLog{},
		&models.CompanyProfile{},
		&models.PersonRow{},
		&models.WebSnippet{},
		&AMFirmRecord{},
	)
	if err != nil {
		log.Fatalf("failed to auto-migrate database: %v", err)
	}

	log.Printf("SQLite database ready at %s", dbPath)
}

// AMFirmRecord is the normalised schema for a Companies House asset manager record.
// Written by cmd/ingest and read by the Pipeline tab.
type AMFirmRecord struct {
	gorm.Model
	CompanyName        string `gorm:"uniqueIndex" json:"company_name"`
	CompanyNumber      string `json:"company_number"`
	RegAddressTown     string `json:"reg_address_town"`
	RegAddressPostCode string `json:"reg_address_post_code"`
	CompanyType        string `json:"company_type"`
	Status             string `json:"status"`
	SICCode1           string `json:"sic_code_1"`
	SICCode2           string `json:"sic_code_2"`
}

// GetAMFirms returns up to limit firms from the Companies House AM database.
// If limit <= 0 returns all. Returns (firms, total, err).
func GetAMFirms(search string, limit int) ([]AMFirmRecord, int64, error) {
	if DB == nil {
		return nil, 0, nil
	}

	var firms []AMFirmRecord
	var total int64

	q := DB.Model(&AMFirmRecord{})
	if search != "" {
		q = q.Where("company_name LIKE ?", "%"+search+"%")
	}

	q.Count(&total)

	if limit > 0 {
		q = q.Limit(limit)
	}

	err := q.Order("company_name ASC").Find(&firms).Error
	return firms, total, err
}
