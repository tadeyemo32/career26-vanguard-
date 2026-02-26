package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func SetupRoutes(r *gin.Engine) {
	// Health check stays completely public
	r.GET("/api/health", healthCheck)

	// Auth routes (unauthenticated)
	authGroup := r.Group("/api/auth")
	{
		authGroup.POST("/signup", signupHandler)
		authGroup.POST("/login", loginHandler)
		authGroup.POST("/verify", verifyHandler)
	}

	// Group the rest with authentication
	apiGroup := r.Group("/api")
	apiGroup.Use(AuthMiddleware())
	{
		apiGroup.GET("/auth/me", getUserMeHandler)
		apiGroup.GET("/keys", getKeys)
		apiGroup.POST("/keys", saveKeys)
		apiGroup.POST("/extract", extractDataHandler)
		apiGroup.POST("/ai-search", aiSearchHandler)
		apiGroup.POST("/company-intel", companyIntelHandler)
		apiGroup.POST("/outreach/run", outreachRunHandler)
		apiGroup.POST("/find-email", findEmailHandler)
		apiGroup.GET("/am-firms", amFirmsHandler)
		apiGroup.POST("/am-pipeline/run", amPipelineRunHandler)
		apiGroup.POST("/pipeline/run", pipelineRunHandler)
		apiGroup.GET("/model", getModelHandler)
		apiGroup.POST("/model", setModelHandler)
	}
}

func healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}
