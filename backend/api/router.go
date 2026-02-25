package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func SetupRoutes(r *gin.Engine) {
	apiGroup := r.Group("/api")
	{
		apiGroup.GET("/health", healthCheck)
		apiGroup.GET("/keys", getKeys)
		apiGroup.POST("/keys", saveKeys)
		apiGroup.POST("/extract", extractDataHandler)
		apiGroup.POST("/ai-search", aiSearchHandler)
		apiGroup.POST("/company-intel", companyIntelHandler)
		apiGroup.POST("/outreach/run", outreachRunHandler)
		apiGroup.POST("/find-email", findEmailHandler)
		apiGroup.GET("/am-firms", amFirmsHandler)
		apiGroup.POST("/pipeline/run", pipelineRunHandler)
		apiGroup.GET("/model", getModelHandler)
		apiGroup.POST("/model", setModelHandler)
	}
}

func healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}
