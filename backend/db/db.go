package db

import (
	"database/sql"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

func InitDB(dataSourceName string) *sql.DB {
	db, err := sql.Open("sqlite3", dataSourceName)
	if err != nil {
		log.Fatalf("Error connecting to sqlite3 db %s: %v", dataSourceName, err)
	}

	if err := db.Ping(); err != nil {
		log.Fatalf("Error pinging db: %v", err)
	}

	return db
}
