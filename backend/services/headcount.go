package services

// HeadcountRules encodes the outreach strategy based on firm size.
// Only firms between 25–500 employees are targeted.
//
// < 50 employees   → CEO, Partner, CIO
// 50–200 employees → HR Director
// 200–500          → Early Careers Head, HR Director
// > 500            → out of scope

type HeadcountBand struct {
	Label string
	Roles []string
}

// GetTargetRolesByHeadcount returns the appropriate outreach targets for a given headcount.
// Returns nil if outside the 25–500 range.
func GetTargetRolesByHeadcount(headcount int) *HeadcountBand {
	switch {
	case headcount < 25:
		// Too small — not worth cold-outreach at scale
		return nil
	case headcount < 50:
		return &HeadcountBand{
			Label: "Micro (25–49)",
			Roles: []string{"CEO", "Partner", "CIO"},
		}
	case headcount < 200:
		return &HeadcountBand{
			Label: "Small (50–199)",
			Roles: []string{"HR Director"},
		}
	case headcount <= 500:
		return &HeadcountBand{
			Label: "Mid-size (200–500)",
			Roles: []string{"Early Careers Head", "HR Director"},
		}
	default:
		// > 500 — out of scope for this workflow
		return nil
	}
}
