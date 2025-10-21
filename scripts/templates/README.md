# Seed Script Templates

This directory contains JSON templates used by the `seed.sh` script to populate the MVD dataspace.

## Purpose

Separating JSON templates from the shell script provides several benefits:

- **Maintainability**: JSON templates are easier to read, validate, and modify
- **Validation**: Templates can be validated using JSON schema validators or IDE features
- **Reusability**: Templates can be used by other tools or scripts
- **Version Control**: Changes to JSON structure are more visible in diffs
- **Testing**: Templates can be tested independently from the shell script

## Template Files

### `participant.json`
Defines the participant context structure for the IdentityHub.

**Placeholders:**
- `{{PARTICIPANT_DID}}`: Replaced with the participant DID
- `{{PUBLIC_KEY_PEM}}`: Replaced with the public key in PEM format

**Usage:**
```bash
PEM_PUBLIC=$(awk '{printf "%s\\n", $0}' assets/keys/consumer_public.pem)
DATA=$(jq \
  --arg did "$PARTICIPANT_DID" \
  --arg pem "$PEM_PUBLIC" \
  '.participantId = $did | .did = $did | .key.keyId = ($did + "#key-1") | .key.publicKeyPem = $pem' \
  participant.json)
```

### `secret.json`
Defines the secret structure for storing client credentials in the vault.

**Fields set dynamically:**
- `@id`: Secret identifier
- `https://w3id.org/edc/v0.0.1/ns/value`: Secret value

**Usage:**
```bash
DATA=$(jq \
  --arg secretId "$SECRET_ID" \
  --arg secretValue "$SECRET_VALUE" \
  '."@id" = $secretId | ."https://w3id.org/edc/v0.0.1/ns/value" = $secretValue' \
  secret.json)
```

### `asset.json`
Defines a test asset for demonstrating data sharing.

**Static template** - no dynamic substitution needed.

### `policy.json`
Defines the membership policy that requires active MembershipCredential.

**Static template** - no dynamic substitution needed.

Uses the correct EDC Management API context and ODRL structure.

### `contract-definition.json`
Defines the contract that links the asset with the membership policy.

**Static template** - no dynamic substitution needed.

## Validation

Templates can be validated using `jq`:

```bash
# Validate all templates
for file in *.json; do
  echo "Validating $file..."
  jq empty "$file" && echo "✓ Valid" || echo "✗ Invalid"
done
```

## Adding New Templates

1. Create a new `.json` file in this directory
2. Use `{{PLACEHOLDER}}` syntax for values that need dynamic substitution
3. Update `seed.sh` to load and populate the template using `jq`
4. Document the template in this README
