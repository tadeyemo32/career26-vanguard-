package main

import (
	"log"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/tadeyemo32/vanguard-backend/api"
	"github.com/tadeyemo32/vanguard-backend/db"
)

func main() {
	// Load environment variables
	_ = godotenv.Load("../.env")

	// Initialize database
	database := db.InitDB("./data/vanguard.db")
	defer database.Close()

	r := gin.Default()

	// CORS Setup for Vite connection
	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	api.SetupRoutes(r, database)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8765" // Default port Vanguard UI expects
	}

	log.Printf("Starting Vanguard Go Backend on port %s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Error starting Go server: %v", err)
	}
}
