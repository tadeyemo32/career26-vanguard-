package api

import (
	"log"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/tadeyemo32/vanguard-backend/models"
)

func getKeys(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"SERPAPI_KEY":     os.Getenv("SERPAPI_KEY") != "",
		"ANYMAIL_API_KEY": os.Getenv("ANYMAIL_API_KEY") != "",
		"OPENAI_API_KEY":  os.Getenv("OPENAI_API_KEY") != "",
	})
}

func saveKeys(c *gin.Context) {
	var body struct {
		SerpAPIKey    string `json:"SERPAPI_KEY"`
		AnymailAPIKey string `json:"ANYMAIL_API_KEY"`
		OpenaiAPIKey  string `json:"OPENAI_API_KEY"`
	}
	if err := c.BindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid body"})
		return
	}
	// Would save to .env in real implementation
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func outreachRunHandler(c *gin.Context) {
	var req models.OutreachRunRequest
	if err := c.BindJSON(&req); err != nil {
		log.Printf("Bind error: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request parameters."})
		return
	}

	// This is the stubs connecting to Golang instead of Python
	// Real DB and scraper routing occurs here
	results := []models.PersonRow{
		{
			Name:         "John Doe",
			Title:        "HR Director",
			Company:      "London Capital Management",
			Email:        "johndoe@lcm.co.uk",
			Confidence:   0.9,
			Source:       "Golang Mock Data",
			CompanySize:  "200-500",
			Headquarters: "London, UK",
			CompanyType:  "Asset Management",
			TargetRoles:  "HR Director, Head of HR",
			SizeBand:     "200-500",
		},
	}

	c.JSON(http.StatusOK, gin.H{
		"results":      results,
		"people_added": len(results),
	})
}
