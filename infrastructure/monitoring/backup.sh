#!/bin/bash
# Daily backup script for Unified RAG System
# Creates backups of Qdrant snapshots and SQLite dumps
# Should be run daily via cron: 0 2 * * * /path/to/backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/rag-backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Docker container names
QDRANT_CONTAINER="unified-rag-qdrant"
API_CONTAINER="unified-rag-api"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting backup at $(date)"

# Backup Qdrant data
echo "Creating Qdrant snapshot..."
docker exec "$QDRANT_CONTAINER" qdrant-client snapshot create --collection-name "*" --wait || {
    echo "Warning: Qdrant snapshot failed, continuing with other backups"
}

# Copy Qdrant snapshots
echo "Copying Qdrant snapshots..."
docker cp "$QDRANT_CONTAINER:/qdrant/storage/snapshots" "$BACKUP_DIR/qdrant_snapshots_$TIMESTAMP" 2>/dev/null || {
    echo "Warning: No Qdrant snapshots found"
}

# Backup SQLite database
echo "Creating SQLite dump..."
docker exec "$API_CONTAINER" sqlite3 /app/data/knowledge.db ".backup '$BACKUP_DIR/sqlite_backup_$TIMESTAMP.db'" || {
    echo "Warning: SQLite backup failed"
}

# Compress backups
echo "Compressing backups..."
tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" \
    "qdrant_snapshots_$TIMESTAMP" \
    "sqlite_backup_$TIMESTAMP.db" 2>/dev/null || {
    echo "Warning: Compression failed"
}

# Clean up uncompressed files
rm -rf "$BACKUP_DIR/qdrant_snapshots_$TIMESTAMP" "$BACKUP_DIR/sqlite_backup_$TIMESTAMP.db"

# Rotate old backups
echo "Rotating old backups..."
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Verify backup integrity
if [ -f "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" ]; then
    echo "Backup completed successfully: $BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
    echo "Backup size: $(du -h "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" | cut -f1)"
else
    echo "Error: Backup file not created"
    exit 1
fi

echo "Backup process completed at $(date)"
