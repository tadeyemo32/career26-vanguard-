package main

import (
	"bytes"
	"fmt"
	"net/http"
	"sync"
	"time"
)

func main() {
	url := "http://localhost:8765/api/auth/signup"
	payload := []byte(`{"first_name":"Load","last_name":"Test","email":"loadtest@vanguard26.com","password":"pass"}`)

	concurrency := 50
	var wg sync.WaitGroup

	start := time.Now()

	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(payload))
			req.Header.Set("Content-Type", "application/json")
			// Empty Vanguard Key so local server lets it through (assuming its still unset in our shell)
			req.Header.Set("X-Vanguard-Key", "")

			client := &http.Client{Timeout: 5 * time.Second}
			resp, err := client.Do(req)

			if err != nil {
				fmt.Printf("[Req %d] Err: %v\n", id, err)
				return
			}
			defer resp.Body.Close()
			fmt.Printf("[Req %d] Status %d\n", id, resp.StatusCode)
		}(i)
	}

	wg.Wait()
	fmt.Printf("\nCompleted %d requests in %v\n", concurrency, time.Since(start))
}
