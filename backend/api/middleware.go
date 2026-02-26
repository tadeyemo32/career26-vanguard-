package api

import (
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/tadeyemo32/vanguard-backend/models"
	"github.com/tadeyemo32/vanguard-backend/services"
)

// AuthMiddleware checks the Authorization header for a valid JWT
func AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Authorization header required"})
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Authorization header format must be Bearer {token}"})
			return
		}

		tokenString := parts[1]

		// DEV BYPASS: if APP_ENV=dev and token matches DEV_BYPASS_TOKEN, inject admin session
		if os.Getenv("APP_ENV") == "dev" {
			bypassToken := os.Getenv("DEV_BYPASS_TOKEN")
			if bypassToken != "" && tokenString == bypassToken {
				c.Set("userID", uint(1))
				c.Set("devBypass", true)
				c.Next()
				return
			}
		}

		userID, err := services.ValidateJWT(tokenString)
		if err != nil {
			log.Printf("Auth Error: %v", err)
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Invalid or expired token"})
			return
		}

		// Store user ID in context for downstream handlers
		c.Set("userID", userID)
		c.Next()
	}
}

// BackendKeyMiddleware strictly ensures external traffic has the master key.
// This prevents anyone from hitting the deployed Render backend directly
// without routing through the Vercel frontend.
func BackendKeyMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		expected := os.Getenv("VANGUARD_API_KEY")
		if expected != "" {
			actual := c.GetHeader("X-Vanguard-Key")
			if actual != expected {
				c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Invalid backend access key"})
				return
			}
		}
		c.Next()
	}
}

// AdminMiddleware ensures the authenticated user has the "admin" role.
// Must be used after AuthMiddleware.
func AdminMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// DEV BYPASS: if dev bypass is active, treat as admin
		if _, isBypass := c.Get("devBypass"); isBypass {
			c.Next()
			return
		}

		userID, exists := c.Get("userID")
		if !exists {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
			return
		}

		var user models.User
		if err := services.DB.First(&user, userID).Error; err != nil {
			c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "Failed to verify user role"})
			return
		}

		if user.Role != "admin" {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "Admin access required"})
			return
		}

		c.Next()
	}
}
