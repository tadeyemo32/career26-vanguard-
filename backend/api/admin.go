package api

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/tadeyemo32/vanguard-backend/models"
	"github.com/tadeyemo32/vanguard-backend/services"
)

// ListUsersHandler returns all users for admin management
func listUsersHandler(c *gin.Context) {
	var users []models.User
	if err := services.DB.Find(&users).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch users"})
		return
	}
	c.JSON(http.StatusOK, users)
}

type UpdateCreditsRequest struct {
	Credits int `json:"credits" binding:"required"`
}

// UpdateUserCreditsHandler allows admins to adjust user balances
func updateUserCreditsHandler(c *gin.Context) {
	id := c.Param("id")
	userID, err := strconv.ParseUint(id, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid user ID"})
		return
	}

	var req UpdateCreditsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
		return
	}

	if err := services.DB.Model(&models.User{}).Where("id = ?", userID).Update("credits", req.Credits).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update credits"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Credits updated successfully"})
}

type UpdateRoleRequest struct {
	Role string `json:"role" binding:"required"`
}

// UpdateUserRoleHandler allows admins to promote/demote users
func updateUserRoleHandler(c *gin.Context) {
	id := c.Param("id")
	userID, err := strconv.ParseUint(id, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid user ID"})
		return
	}

	var req UpdateRoleRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
		return
	}

	if req.Role != "admin" && req.Role != "user" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid role"})
		return
	}

	if err := services.DB.Model(&models.User{}).Where("id = ?", userID).Update("role", req.Role).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update role"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Role updated successfully"})
}

// GetSystemStatsHandler returns aggregate system monitoring data
func getSystemStatsHandler(c *gin.Context) {
	var userCount int64
	var totalTokens int64
	var verifiedUsers int64

	services.DB.Model(&models.User{}).Count(&userCount)
	services.DB.Model(&models.User{}).Where("is_verified = ?", true).Count(&verifiedUsers)
	services.DB.Model(&models.QueryLog{}).Select("sum(tokens_used)").Row().Scan(&totalTokens)

	c.JSON(http.StatusOK, gin.H{
		"total_users":    userCount,
		"verified_users": verifiedUsers,
		"total_tokens":   totalTokens,
	})
}
