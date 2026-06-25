#!/usr/bin/env bash
# Backup strategy for the RAG service.
#
# Archives the FAISS index, chunk metadata, and uploaded source files, then
# syncs them to an S3 bucket. Intended to run from cron on the EC2 host, e.g.:
#
#   0 2 * * *  /opt/manas-rag-app/scripts/backup.sh >> /var/log/rag-backup.log 2>&1
#
# Requires the AWS CLI configured with an IAM role/credentials that can write
# to ${BACKUP_BUCKET}.
set -euo pipefail

# ---- Configuration (override via environment) ----
DATA_DIR="${DATA_DIR:-/opt/manas-rag-app/data}"
BACKUP_BUCKET="${BACKUP_BUCKET:-s3://manas-rag-backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="/tmp/rag-backup-${STAMP}.tar.gz"

echo "[backup] creating archive ${ARCHIVE} from ${DATA_DIR}"
tar -czf "${ARCHIVE}" -C "${DATA_DIR}" .

echo "[backup] uploading to ${BACKUP_BUCKET}/${STAMP}/"
aws s3 cp "${ARCHIVE}" "${BACKUP_BUCKET}/${STAMP}/$(basename "${ARCHIVE}")"

# Keep the local disk clean.
rm -f "${ARCHIVE}"
echo "[backup] done"
