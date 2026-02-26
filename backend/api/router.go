package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func SetupRoutes(r *gin.Engine) {
	// Health check stays completely public
	r.GET("/api/health", healthCheck)

	// Create base /api group that requires the server-to-server VANGUARD_API_KEY
	apiBase := r.Group("/api")
	apiBase.Use(BackendKeyMiddleware())

	// Auth routes (unauthenticated user, but protected by server key)
	authGroup := apiBase.Group("/auth")
	{
		authGroup.POST("/signup", signupHandler)
		authGroup.POST("/login", loginHandler)
		authGroup.POST("/verify", verifyHandler)
	}

	// Group the rest with user authentication
	apiGroup := apiBase.Group("")
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
