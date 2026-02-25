package models

import "gorm.io/gorm"

// ========================
// DATABASE ETL & RAG MODELS
// ========================

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
	FullName    string `json:"full_name"`
	Company     string `json:"company"`
	ResolveOnly bool   `json:"resolve_only"`
}

type FindEmailResponse struct {
	Email      string   `json:"email"`
	Confidence float64  `json:"confidence"`
	Source     string   `json:"source"`
	Logs       []string `json:"logs"`
}
