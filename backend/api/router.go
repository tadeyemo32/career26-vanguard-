package api

import (
	"database/sql"
	"net/http"

	"github.com/gin-gonic/gin"
)

var dbConn *sql.DB

func SetupRoutes(r *gin.Engine, db *sql.DB) {
	dbConn = db

	apiGroup := r.Group("/api")
	{
		apiGroup.GET("/health", healthCheck)
		apiGroup.GET("/keys", getKeys)
		apiGroup.POST("/keys", saveKeys)
		apiGroup.POST("/outreach/run", outreachRunHandler)
	}
}

func healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}
