
#!/usr/bin/env bash
set -euo pipefail

# === Fill these in ===
PROJECT_ID="${PROJECT_ID:-YOUR_PROJECT_ID}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-mcp-clock}"

# Deploy from source (Cloud Build + Cloud Run)
gcloud run deploy "$SERVICE"   --source .   --region "$REGION"   --allow-unauthenticated   --project "$PROJECT_ID"

echo "Deployed. Service URL:"
gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT_ID"   --format='value(status.url)'
