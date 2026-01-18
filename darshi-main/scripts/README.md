# Scripts Directory

This directory contains utility scripts for deployment, migration, and maintenance tasks.

## Directory Structure

```
scripts/
├── deployment/          # Deployment automation scripts
│   ├── deploy-backend.sh
│   ├── build-docs.sh
│   ├── sync-docs.sh
│   └── export_git_history.sh
├── migration/          # Database migration scripts
│   ├── migrate_locations.py
│   ├── migrate_add_landmarks.py
│   └── migrate_dhash_bucket.py
└── README.md           # This file
```

## Deployment Scripts

### `deploy-backend.sh`

Deploys the backend to Cloud Run.

```bash
./scripts/deployment/deploy-backend.sh
```

**What it does:**
- Builds Docker image
- Pushes to Container Registry
- Deploys to Cloud Run (asia-southeast1)
- Configures environment variables and secrets

**Prerequisites:**
- `gcloud` CLI configured
- Docker installed
- Service account credentials

### `build-docs.sh`

Builds documentation site using Quartz.

```bash
./scripts/deployment/build-docs.sh
```

**What it does:**
- Clones/updates docs-quartz repository
- Syncs markdown files from /docs
- Builds static documentation site
- Outputs to frontend/static/docs

**Prerequisites:**
- Node.js 22+
- docs-quartz repository

### `sync-docs.sh`

Syncs documentation files to Quartz content directory.

```bash
./scripts/deployment/sync-docs.sh
```

**What it does:**
- Copies markdown files from /docs to docs-quartz/content
- Preserves directory structure
- Used by build-docs.sh

### `export_git_history.sh`

Exports git history for documentation purposes.

```bash
./scripts/deployment/export_git_history.sh > git-history.txt
```

**What it does:**
- Generates formatted git log
- Includes commit messages and file changes
- Useful for release notes

## Migration Scripts

### `migrate_locations.py`

**Purpose:** Add human-readable addresses to existing reports

**Usage:**
```bash
python3 scripts/migration/migrate_locations.py
```

**What it does:**
- Fetches all reports from Firestore
- Reverse geocodes coordinates to addresses
- Updates reports with `address` field
- Uses Nominatim API with rate limiting

**Options:**
- `--dry-run` - Preview changes without updating
- `--batch-size` - Number of reports to process (default: 100)

**Example:**
```bash
# Dry run first
python3 scripts/migration/migrate_locations.py --dry-run

# Process all reports
python3 scripts/migration/migrate_locations.py --batch-size 50
```

### `migrate_add_landmarks.py`

**Purpose:** Add nearby landmarks to existing reports

**Usage:**
```bash
python3 scripts/migration/migrate_add_landmarks.py
```

**What it does:**
- Fetches all reports from Firestore
- Queries Overpass API for nearby landmarks
- Updates reports with `nearby_landmarks` field (up to 5)
- Uses circuit breaker to prevent API overload

**Options:**
- `--dry-run` - Preview changes without updating
- `--radius` - Search radius in meters (default: 500m)

**Example:**
```bash
# Dry run with 1km radius
python3 scripts/migration/migrate_add_landmarks.py --dry-run --radius 1000

# Process all reports
python3 scripts/migration/migrate_add_landmarks.py
```

### `migrate_dhash_bucket.py`

**Purpose:** Migrate dHash duplicate detection to Cloud Storage

**Usage:**
```bash
python3 scripts/migration/migrate_dhash_bucket.py
```

**What it does:**
- Calculates perceptual hashes (dHash) for all report images
- Stores hash index in Cloud Storage bucket
- Updates reports with `dhash` field
- Enables efficient duplicate detection

**Options:**
- `--dry-run` - Preview changes without updating
- `--batch-size` - Number of reports to process (default: 50)

**Example:**
```bash
# Dry run
python3 scripts/migration/migrate_dhash_bucket.py --dry-run

# Process with smaller batch size (to avoid rate limits)
python3 scripts/migration/migrate_dhash_bucket.py --batch-size 25
```

## Running Migration Scripts

### Prerequisites

1. **Environment Setup:**
```bash
# Activate virtual environment
source venv/bin/activate

# Ensure .env is configured with:
# - PROJECT_ID
# - GOOGLE_APPLICATION_CREDENTIALS
# - GEMINI_API_KEY (if using AI migrations)
```

2. **Test Credentials:**
```bash
python3 -c "from google.cloud import firestore; db = firestore.Client(); print('✅ Connected')"
```

### Best Practices

1. **Always run dry-run first:**
```bash
python3 scripts/migration/migrate_*.py --dry-run
```

2. **Process in batches:**
```bash
# Small batch to test
python3 scripts/migration/migrate_*.py --batch-size 10

# Full migration
python3 scripts/migration/migrate_*.py --batch-size 100
```

3. **Monitor logs:**
```bash
# Tail logs during migration
tail -f logs/darshi.log
```

4. **Backup Firestore before major migrations:**
```bash
gcloud firestore export gs://${PROJECT_ID}-firestore-backups
```

### Troubleshooting

**Issue: Rate limit exceeded (429)**
- Reduce batch size: `--batch-size 10`
- Add delays between batches
- Use circuit breaker (built into scripts)

**Issue: Firestore permission denied**
```bash
# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --filter="bindings.members:serviceAccount:*"

# Add datastore.user role if missing
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:your-sa@project.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

**Issue: Geocoding timeouts**
- Nominatim has strict rate limits (1 req/sec)
- Scripts include built-in delays
- Consider using paid geocoding service for large migrations

## Adding New Scripts

### Deployment Scripts

1. Create script in `scripts/deployment/`
2. Make executable: `chmod +x scripts/deployment/your-script.sh`
3. Add to this README with usage instructions
4. Test thoroughly before committing

### Migration Scripts

1. Create script in `scripts/migration/`
2. Follow this template:

```python
"""
Migration: [Description]

Usage:
    python3 scripts/migration/migrate_*.py [--dry-run] [--batch-size N]

Options:
    --dry-run       Preview changes without updating
    --batch-size N  Process N records at a time (default: 100)
"""

import argparse
from app.services.db_service import db
from app.core.logging_config import setup_logging, get_logger

logger = get_logger(__name__)

def migrate(dry_run=False, batch_size=100):
    """Main migration logic."""
    # Implementation here
    pass

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser(description="Migration: [Description]")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    migrate(dry_run=args.dry_run, batch_size=args.batch_size)
```

3. Test with dry-run first
4. Document in this README
5. Add error handling and logging
6. Include progress indicators

## Script Maintenance

- **Review quarterly** - Check if scripts still work with latest code
- **Update on API changes** - If external APIs change
- **Test before releases** - Ensure migrations work with new schema
- **Archive old scripts** - Move obsolete scripts to archive/

---

**Last Updated**: December 2025
**Maintained By**: Darshi Development Team
