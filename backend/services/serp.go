package services

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"
	"os"
)

type SerpResult struct {
	Title   string `json:"title"`
	Link    string `json:"link"`
	Snippet string `json:"snippet"`
}

type serpAPIResponse struct {
	OrganicResults []SerpResult `json:"organic_results"`
}

// SerpGoogle queries SerpAPI for google search engine
func SerpGoogle(query string, maxResults int) ([]SerpResult, error) {
	apiKey := os.Getenv("SERPAPI_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("SERPAPI_KEY not set")
	}

	endpoint := "https://serpapi.com/search.json"
	u, err := url.Parse(endpoint)
	if err != nil {
		return nil, err
	}

	q := u.Query()
	q.Set("q", query)
	q.Set("engine", "google")
	q.Set("api_key", apiKey)
	q.Set("num", fmt.Sprintf("%d", maxResults))
	u.RawQuery = q.Encode()

	resp, err := http.Get(u.String())
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("SerpAPI returned status: %d", resp.StatusCode)
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var data serpAPIResponse
	if err := json.Unmarshal(body, &data); err != nil {
		return nil, err
	}

	return data.OrganicResults, nil
}
