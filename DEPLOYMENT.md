# Deployment Plan — `manas-rag-app` (Task 1)

Step-by-step guide to deploy the RAG service on **AWS Free Tier** (a single
`t3.micro` EC2 instance) with **HTTPS**, **automated CI/CD**, **logging**, and
**S3 backups**.

> This app shares one EC2 instance with `manas-fullstack-app`. **Part A
> (host setup) is one-time** — if you already did it while deploying the other
> repo, skip straight to **Part B**.

```
Internet ──443──> Nginx + Let's Encrypt ──> 127.0.0.1:8000 (RAG container)
                  rag.<your-domain>
```

---

## Prerequisites

- [ ] AWS account (Free Tier) with permission to create EC2, S3, IAM.
- [ ] A domain (or a free **DuckDNS** subdomain) you can point at an IP.
- [ ] A **Gemini API key** from Google AI Studio (free).
- [ ] This repo pushed to GitHub (CI builds images to **GHCR**).
- [ ] A **SonarCloud** account + `SONAR_TOKEN` (for the quality gate).

---

## Part A — One-time AWS host setup (shared with the other repo)

### A1. Launch the EC2 instance
1. EC2 → **Launch instance**.
2. AMI: **Ubuntu Server 22.04 LTS**. Type: **t3.micro** (or t2.micro).
3. Create/download a key pair (`manas-key.pem`) — you'll need it for SSH + CI.
4. Storage: 20–30 GB gp3 (within the 30 GB free allowance).
5. **Security group** — inbound rules:
   | Type  | Port | Source            |
   |-------|------|-------------------|
   | SSH   | 22   | My IP             |
   | HTTP  | 80   | 0.0.0.0/0         |
   | HTTPS | 443  | 0.0.0.0/0         |

### A2. Allocate an Elastic IP
EC2 → **Elastic IPs** → Allocate → Associate with the instance. This gives you
a stable public IP for DNS.

### A3. SSH in and install Docker
```bash
ssh -i manas-key.pem ubuntu@<ELASTIC_IP>

sudo apt-get update && sudo apt-get upgrade -y
# Docker engine + compose plugin
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Nginx + Certbot for the reverse proxy and TLS
sudo apt-get install -y nginx certbot python3-certbot-nginx
# Log out/in so the docker group applies
exit && ssh -i manas-key.pem ubuntu@<ELASTIC_IP>
```

### A4. Add 2 GB swap (safety on a 1 GB box)
```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### A5. Create an S3 backup bucket + give EC2 write access
1. S3 → create a private bucket, e.g. `manas-rag-backups`.
2. IAM → create a role (trusted entity: EC2) with an inline policy allowing
   `s3:PutObject` on `arn:aws:s3:::manas-rag-backups/*`, then attach it to the
   instance (EC2 → Actions → Security → Modify IAM role).
3. Install the AWS CLI on the host: `sudo apt-get install -y awscli`.

---

## Part B — DNS

Point a subdomain at your Elastic IP:

- **Real domain**: add an **A record** `rag.<your-domain>` → `<ELASTIC_IP>`.
- **DuckDNS (free)**: create `manas-rag.duckdns.org` and set its IP to
  `<ELASTIC_IP>`.

Verify: `dig +short rag.<your-domain>` returns your Elastic IP.

---

## Part C — Deploy the container

### C1. Put the app directory on the host
```bash
sudo mkdir -p /opt/manas-rag-app/data /opt/manas-rag-app/logs
sudo chown -R $USER:$USER /opt/manas-rag-app
cd /opt/manas-rag-app
```

### C2. Add the production compose file
Copy `deploy/docker-compose.prod.yml` from this repo to
`/opt/manas-rag-app/docker-compose.yml` and replace `OWNER/REPO` with your
GitHub path (e.g. `ghcr.io/dev-roy/manas-rag-app`).

### C3. Add the host env file (secrets)
```bash
cat > /opt/manas-rag-app/.env <<'EOF'
GEMINI_API_KEY=your_real_gemini_key
OFFLINE_MODE=false
LOG_LEVEL=INFO
EOF
chmod 600 /opt/manas-rag-app/.env
```

### C4. Authenticate to GHCR and start
```bash
# Use a GitHub Personal Access Token with read:packages scope.
echo <GHCR_PAT> | docker login ghcr.io -u <github-username> --password-stdin
docker compose pull
docker compose up -d
curl http://127.0.0.1:8000/health   # -> {"status":"ok",...}
```

---

## Part D — Nginx reverse proxy + HTTPS

### D1. Install the vhost
```bash
sudo cp /path/to/repo/deploy/nginx-rag.conf /etc/nginx/sites-available/rag
# edit server_name to rag.<your-domain>
sudo ln -s /etc/nginx/sites-available/rag /etc/nginx/sites-enabled/rag
sudo nginx -t && sudo systemctl reload nginx
```

### D2. Issue the TLS certificate
```bash
sudo certbot --nginx -d rag.<your-domain> --redirect -m you@email.com --agree-tos -n
```
Certbot rewrites the vhost to listen on 443 and sets up auto-renewal (timer).

Verify: open `https://rag.<your-domain>/health` — valid padlock, `status: ok`.

---

## Part E — Automated CI/CD (GitHub Actions)

The pipeline (`.github/workflows/ci-cd.yml`) already does
**test → SonarCloud → build → push → SSH deploy**. Add these repository secrets
(**Settings → Secrets and variables → Actions**):

| Secret | Value |
|--------|-------|
| `SONAR_TOKEN` | From SonarCloud (your project) |
| `EC2_HOST` | `<ELASTIC_IP>` |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | Contents of `manas-key.pem` (the private key) |

> `GITHUB_TOKEN` is built in and lets the workflow push to GHCR.

Now every push to `main` builds a new image and rolls the container on EC2 via
`docker compose pull && up -d`.

---

## Part F — Logging & backup

- **Logs**: JSON to stdout (`docker compose logs -f rag`) and a rotating file in
  `/opt/manas-rag-app/logs/app.log` (5 × 5 MB).
- **Backup cron** — schedule the bundled script nightly:
  ```bash
  sudo cp /path/to/repo/scripts/backup.sh /opt/manas-rag-app/scripts/backup.sh
  sudo chmod +x /opt/manas-rag-app/scripts/backup.sh
  ( crontab -l 2>/dev/null; \
    echo "0 2 * * * BACKUP_BUCKET=s3://manas-rag-backups DATA_DIR=/opt/manas-rag-app/data /opt/manas-rag-app/scripts/backup.sh >> /var/log/rag-backup.log 2>&1" ) | crontab -
  ```
  Test once: `BACKUP_BUCKET=s3://manas-rag-backups DATA_DIR=/opt/manas-rag-app/data /opt/manas-rag-app/scripts/backup.sh`
  then confirm the object appears in S3.

---

## Verification checklist

- [ ] `https://rag.<your-domain>/health` returns `200` over valid TLS.
- [ ] Upload a doc: `curl -F "file=@sample.txt" https://rag.<your-domain>/upload`.
- [ ] Query it: `curl -X POST https://rag.<your-domain>/query -H 'Content-Type: application/json' -d '{"question":"..."}'` returns an answer + sources.
- [ ] Push to `main` → Actions is green → new image deployed automatically.
- [ ] SonarCloud shows a passing quality gate.
- [ ] Backup script writes an object to the S3 bucket; cron entry exists.

---

## Rollback & ops cheatsheet

```bash
docker compose logs -f rag                 # tail logs
docker compose restart rag                 # restart
docker compose pull && docker compose up -d  # redeploy latest
# pin a previous version: set image tag to a specific :<sha> in compose, then up -d
```
