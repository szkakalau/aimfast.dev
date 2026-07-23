#!/bin/bash
# Stripe CLI webhook listener — run in WSL
# Usage: wsl -d ubuntu -- bash scripts/start-webhook.sh

# Kill existing stripe processes
pkill stripe 2>/dev/null
sleep 1

# Start listener with trailing slash in forward URL (CRITICAL: without it, Next.js returns 308)
stripe listen \
  --api-key "$STRIPE_API_KEY" \
  --forward-to 172.23.240.1:3000/api/stripe/webhook/ \
  2>&1 | while IFS= read -r line; do
    echo "[$(date '+%H:%M:%S')] $line"
  done
