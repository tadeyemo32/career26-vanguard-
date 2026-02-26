# Vanguard Deployment Documentation

This document outlines the deployment architecture and processes for the Vanguard application.

## Architecture Overview

Vanguard is a full-stack application consisting of:
1.  **Go Backend**: A high-performance Gin-based API deployed on **Google Cloud Run**.
2.  **React Frontend**: A Vite/TypeScript single-page application deployed on **Vercel**.

## Backend Deployment (Google Cloud Run)

The backend is packaged and deployed as a containerized service. 

### Prerequisites
- Google Cloud CLI (`gcloud`) installed and authenticated.
- Configuration for the project `hair-by-v` and region `europe-west1`.

### Environment Variables
The following secrets must be configured in the Cloud Run service:
- `VANGUARD_API_KEY`: Secret key for server-to-server auth.
- `JWT_SECRET`: For signing user session tokens.
- `RESEND_API_KEY`: API key for Resend email service.
- `DATABASE_PATH`: Path to the SQLite DB (usually `/data/vanguard.db` in a persistent volume or ephemeral container).

## Frontend Deployment (Vercel)

The frontend is deployed to Vercel with automatic CI/CD on pushes to the `main` branch.

### Environment Variables
Configure these in the Vercel Dashboard:
- `VITE_API_URL`: The URL of the deployed Cloud Run service (e.g., `https://vanguard26-sac4otr44q-ew.a.run.app`).
- `VITE_VANGUARD_API_KEY`: Must match the backend's `VANGUARD_API_KEY`.

## Automation Script

A unified deployment script is located at `scripts/deploy.sh`. This script automates:
1.  **Testing**: Runs Go unit tests.
2.  **Deployment**: Pushes the latest backend code to Cloud Run.
3.  **Verification**: Smoke tests the `/api/health` and `/api/auth/signup` endpoints via CURL.

### Usage
```bash
./scripts/deploy.sh
```
