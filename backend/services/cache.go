// In-memory LRU-style cache for email lookups
// Key: "fullname|company" → cached email result
package services

import (
	"fmt"
	"strings"
	"sync"
	"time"
)

type emailCacheEntry struct {
	Email      string
	Confidence float64
	Err        error
	CachedAt   time.Time
}

var (
	emailCache   = map[string]*emailCacheEntry{}
	emailCacheMu sync.RWMutex
	cacheTTL     = 24 * time.Hour
)

func cacheKey(fullName, company string) string {
	return fmt.Sprintf("%s|%s", strings.ToLower(strings.TrimSpace(fullName)), strings.ToLower(strings.TrimSpace(company)))
}

// GetCachedEmail returns a cached result if still fresh, plus a found boolean.
func GetCachedEmail(fullName, company string) (string, float64, bool) {
	emailCacheMu.RLock()
	defer emailCacheMu.RUnlock()
	k := cacheKey(fullName, company)
	e, ok := emailCache[k]
	if !ok || time.Since(e.CachedAt) > cacheTTL {
		return "", 0, false
	}
	return e.Email, e.Confidence, true
}

// SetCachedEmail stores the result for future calls.
func SetCachedEmail(fullName, company, email string, confidence float64, err error) {
	emailCacheMu.Lock()
	defer emailCacheMu.Unlock()
	emailCache[cacheKey(fullName, company)] = &emailCacheEntry{
		Email:      email,
		Confidence: confidence,
		Err:        err,
		CachedAt:   time.Now(),
	}
}
