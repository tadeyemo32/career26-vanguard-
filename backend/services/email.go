package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
)

type ResendPayload struct {
	From    string   `json:"from"`
	To      []string `json:"to"`
	Subject string   `json:"subject"`
	HTML    string   `json:"html"`
	Text    string   `json:"text"`
}

// SendVerificationEmail triggers the Resend API to deliver a 6-digit verification code.
func SendVerificationEmail(toEmail, code string) error {
	log.Printf("[RESEND] Preparing to send verification code [%s] to [%s]", code, toEmail)
	apiKey := os.Getenv("RESEND_API_KEY")
	if apiKey == "" {
		log.Println("WARNING: RESEND_API_KEY is not set. Verification email will not be sent.")
		return fmt.Errorf("RESEND_API_KEY not set")
	}

	htmlContent := fmt.Sprintf(`
		<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
			<h2>Welcome to Vanguard!</h2>
			<p>Thank you for signing up. Please verify your email address to continue.</p>
			<p>Your 6-digit verification code is:</p>
			<h1 style="color: #2563eb; letter-spacing: 5px; font-size: 36px; background: #f0f9ff; padding: 10px 20px; border-radius: 8px; display: inline-block;">%s</h1>
			<p>If you did not request this code, you can safely ignore this email.</p>
		</div>
	`, code)

	payload := ResendPayload{
		From:    "Vanguard <onboarding@theturingproject.com>",
		To:      []string{toEmail},
		Subject: fmt.Sprintf("%s is your Vanguard verification code", code),
		HTML:    htmlContent,
		Text:    fmt.Sprintf("Your Vanguard verification code is: %s", code),
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal resend payload: %w", err)
	}

	req, err := http.NewRequest("POST", "https://api.resend.com/emails", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create resend request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request to resend: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("resend API error (status %d): %s", resp.StatusCode, string(bodyBytes))
	}

	log.Printf("Successfully triggered Resend email to %s", toEmail)
	return nil
}
