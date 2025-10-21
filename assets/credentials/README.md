# Verifiable Credentials Directory

This directory is mounted into the IdentityHub container at `/etc/credentials/`.

## Important: Pre-signed Credentials Removed

Pre-signed credential files have been **removed** from this repository because they contained hardcoded DIDs that didn't match the configurable environment setup.

## How to Obtain Credentials

To obtain verifiable credentials for your participant, use the **Issuer Service**:

### Setup Issuer Service

```bash
# 1. Generate issuer keys
task generate-issuer-keys

# 2. Build issuer service
task build-issuer

# 3. Configure issuer
task configure-issuer

# 4. Start issuer services
task issuer-up

# 5. Seed issuer attestation database
task seed-issuer

# 6. Request credentials
task request-credential TYPE=MembershipCredential
```

See `ISSUER.md` for detailed documentation.

## Alternative: External Issuer

If you have an external issuer service, configure it in `.env`:

```bash
ISSUER_MODE=external
ISSUER_EXTERNAL_STS_URL=https://issuer.yourdomain.com/api/sts
ISSUER_EXTERNAL_ISSUANCE_URL=https://issuer.yourdomain.com/api/issuance
...
```

## For Development/Testing

If you need to manually place credential files here for testing:

1. Ensure the credential DIDs match your `.env` configuration (`PARTICIPANT_DID`)
2. Ensure credentials are properly signed by a trusted issuer
3. Place the credential JSON files in this directory
4. Restart the IdentityHub service: `task down && task up`

## Why This Matters

The EDC framework uses Verifiable Credentials for authentication and authorization in the dataspace. Credentials must:
- Be signed by a trusted issuer
- Reference the correct participant DID
- Be valid (not expired)
- Meet the policy requirements of the data provider

Using the issuer service ensures credentials are generated with the correct DIDs from your `.env` configuration.
