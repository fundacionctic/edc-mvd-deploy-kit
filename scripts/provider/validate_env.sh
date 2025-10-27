#!/bin/bash
# ============================================================
# Environment Variable Validation Script
# ============================================================
# This script validates that all required environment variables
# are set before generating configuration files with envsubst.
#
# Usage: ./scripts/provider/validate_env.sh
# Exit codes: 0 = success, 1 = missing variables

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Required environment variables for provider configuration
REQUIRED_VARS=(
    "PROVIDER_PUBLIC_HOST"
    "PROVIDER_PARTICIPANT_NAME"
    "PROVIDER_CP_WEB_PORT"
    "PROVIDER_CP_MANAGEMENT_PORT"
    "PROVIDER_CP_PROTOCOL_PORT"
    "PROVIDER_CP_CONTROL_PORT"
    "PROVIDER_CP_CATALOG_PORT"
    "PROVIDER_CP_DEBUG_PORT"
    "PROVIDER_DP_WEB_PORT"
    "PROVIDER_DP_CONTROL_PORT"
    "PROVIDER_DP_PUBLIC_PORT"
    "PROVIDER_DP_DEBUG_PORT"
    "PROVIDER_IH_WEB_PORT"
    "PROVIDER_IH_CREDENTIALS_PORT"
    "PROVIDER_IH_STS_PORT"
    "PROVIDER_IH_DID_PORT"
    "PROVIDER_IH_IDENTITY_PORT"
    "PROVIDER_IH_DEBUG_PORT"
    "PROVIDER_DB_NAME"
    "PROVIDER_CP_DB_USER"
    "PROVIDER_CP_DB_PASSWORD"
    "PROVIDER_DP_DB_USER"
    "PROVIDER_DP_DB_PASSWORD"
    "PROVIDER_IH_DB_USER"
    "PROVIDER_IH_DB_PASSWORD"
    "PROVIDER_VAULT_TOKEN"
    "PROVIDER_MANAGEMENT_API_KEY"
    "PROVIDER_CATALOG_API_KEY"
    "PROVIDER_IDENTITY_API_KEY"
    "ISSUER_SUPERUSER_KEY"
)

echo -e "${YELLOW}Validating environment variables for provider configuration...${NC}"

missing_vars=()

# Check each required variable
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        missing_vars+=("$var")
    fi
done

# Report results
if [[ ${#missing_vars[@]} -eq 0 ]]; then
    echo -e "${GREEN}✓ All required environment variables are set${NC}"
    exit 0
else
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "  ${RED}- $var${NC}"
    done
    echo
    echo -e "${YELLOW}Please ensure your .env file is properly configured and sourced.${NC}"
    echo -e "${YELLOW}Example: source .env${NC}"
    exit 1
fi