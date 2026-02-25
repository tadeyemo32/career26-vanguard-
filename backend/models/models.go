package models

type PersonRow struct {
	Name         string  `json:"name"`
	Title        string  `json:"title"`
	Company      string  `json:"company"`
	Link         string  `json:"link"`
	Email        string  `json:"email"`
	Confidence   float64 `json:"confidence"`
	Source       string  `json:"source"`
	CompanySize  string  `json:"company_size,omitempty"`
	Headquarters string  `json:"headquarters,omitempty"`
	CompanyType  string  `json:"company_type,omitempty"`
	SizeBand     string  `json:"size_band,omitempty"`
	TargetRoles  string  `json:"target_roles,omitempty"`
}

type OutreachRunRequest struct {
	Count         int     `json:"count"`
	MaxPerCompany int     `json:"max_per_company"`
	FetchMetadata bool    `json:"fetch_metadata"`
	MinScore      float64 `json:"min_score"`
}
