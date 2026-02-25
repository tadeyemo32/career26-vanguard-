# ── Build stage ───────────────────────────────────────────────────────────────
FROM golang:1.23-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server ./cmd/server

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM alpine:3.19

RUN apk add --no-cache ca-certificates
WORKDIR /app

COPY --from=builder /app/server .

# Cloud Run injects $PORT — our server already respects it
ENV PORT=8080
EXPOSE 8080

CMD ["./server"]
