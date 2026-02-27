package models

import (
	"time"

	"gorm.io/gorm"
)

// ========================
// DATABASE ETL & RAG MODELS
// ========================

// User represents a registered user in the system
type User struct {
	gorm.Model
	FirstName        string `json:"first_name"`
	LastName         string `json:"last_name"`
	Email            string `gorm:"uniqueIndex;not null"`
	PasswordHash     string `gorm:"not null"`
	VerificationCode string
	IsVerified       bool      `gorm:"default:false"`
	Credits          int       `gorm:"default:100000"`
	Role             string    `gorm:"default:user" json:"role"`
	CreatedAt        time.Time `json:"created_at"`
}

// QueryLog tracks token usage per user for LLM queries
type QueryLog struct {
	gorm.Model
	UserID     uint   `gorm:"index;not null"`
	QueryType  string // e.g., "ai-search", "company-intel", "extract"
	QueryText  string
	TokensUsed int `gorm:"default:0"`
}

// CompanyProfile represents the extracted and transformed target company logic
type CompanyProfile struct {
	gorm.Model
	Name            string `gorm:"uniqueIndex"`
	ResolvedDomain  string
	EstimatedSize   int
	CompanySizeText string
	TargetRolesUsed string
}

// PersonRow represents a candidate in the pipeline
type PersonRow struct {
	ID           uint    `json:"-" gorm:"primarykey"`
	Name         string  `json:"name"`
	Title        string  `json:"title"`
	Company      string  `json:"company"`
	Link         string  `json:"link" gorm:"uniqueIndex"` // LinkedIn URL
	Email        string  `json:"email"`
	Confidence   float64 `json:"confidence"`
	Source       string  `json:"source"`
	CompanySize  string  `json:"company_size,omitempty" gorm:"-"`
	Headquarters string  `json:"headquarters,omitempty" gorm:"-"`
	CompanyType  string  `json:"company_type,omitempty" gorm:"-"`
	SizeBand     string  `json:"size_band,omitempty" gorm:"-"`
	TargetRoles  string  `json:"target_roles,omitempty" gorm:"-"`
}

// WebSnippet represents RAG document chunks scraped from company URLs
type WebSnippet struct {
	gorm.Model
	CompanyName string `gorm:"index"`
	SourceURL   string
	Content     string
}

// ========================
// API REQUEST PAYLOADS
// ========================

type OutreachRunRequest struct {
	Count         int      `json:"count"`
	MaxPerCompany int      `json:"max_per_company"`
	FetchMetadata bool     `json:"fetch_metadata"`
	MinScore      float64  `json:"min_score"`
	Companies     []string `json:"companies"`
	JobTitles     []string `json:"job_titles"`
}

type ExtractDataRequest struct {
	Payload string `json:"payload"`
}

type AISearchRequest struct {
	Query string `json:"query"`
	Limit int    `json:"limit"`
}

type CompanyIntelRequest struct {
	CompanyName string `json:"company_name"`
}

type CompanyIntelResponse struct {
	ResolvedDomain  string      `json:"resolved_domain"`
	CompanySizeText string      `json:"company_size_text"`
	EstimatedSize   int         `json:"estimated_size"`
	TargetRolesUsed []string    `json:"target_roles_used"`
	PeopleFound     []PersonRow `json:"people_found"`
	SourceLog       []string    `json:"source_log"`
}

type FindEmailRequest struct {
	SearchType  string `json:"search_type"` // "person", "company", "decision_maker", "linkedin"
	FullName    string `json:"full_name,omitempty"`
	Company     string `json:"company,omitempty"`
	Domain      string `json:"domain,omitempty"`
	LinkedInURL string `json:"linkedin_url,omitempty"`
	JobRoles    string `json:"job_roles,omitempty"` // comma separated list
}

type FindEmailResultItem struct {
	Email      string  `json:"email"`
	FullName   string  `json:"full_name,omitempty"`
	JobTitle   string  `json:"job_title,omitempty"`
	Confidence float64 `json:"confidence,omitempty"`
	Source     string  `json:"source"`
}

type FindEmailResponse struct {
	Email      string                `json:"email,omitempty"`      // legacy single result
	Confidence float64               `json:"confidence,omitempty"` // legacy single result
	Source     string                `json:"source"`               // legacy single result
	Emails     []FindEmailResultItem `json:"emails,omitempty"`     // multiple results
	Logs       []string              `json:"logs"`
}
