# Hidden Agenda RL-Agent Gym

An AWS-hosted reinforcement-learning gym for the multi-agent social deduction game **Hidden Agenda** — featuring 1 Impostor and 4 Crewmates in a 40 × 31 sprite world.

Live endpoint is served over a public Cloudflare-tunnelled URL pointing to an EC2 instance.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  EC2 (t3.medium)                 │
│                                                  │
│  ┌─────────────────┐   ┌────────────────────┐   │
│  │  React frontend │   │  FastAPI backend   │   │
│  │  (Nginx :80)    │──▶│  (Uvicorn :8000)   │   │
│  └─────────────────┘   └────────────────────┘   │
│                                │                 │
└────────────────────────────────┼─────────────────┘
                                 │
                          ┌──────▼──────┐
                          │  S3 bucket  │
                          │  replays /  │
                          │  analytics  │
                          └─────────────┘
```

The entire stack is orchestrated with **Docker Compose**; infrastructure is defined in **Terraform** (`infrastructure/terraform/`).

---

## Repository layout

```
.
├── backend/
│   ├── main.py                     # FastAPI entry point
│   ├── environment/
│   │   └── hidden_agenda.py        # Gym environment
│   ├── api/
│   │   ├── experiments.py          # Launch / query experiments
│   │   ├── analytics.py            # Per-experiment metrics
│   │   └── replays.py              # Frame-by-frame replay storage
│   ├── storage/
│   │   └── s3_client.py            # S3 helpers
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Root + routing
│   │   └── components/
│   │       ├── Dashboard.jsx       # Experiment overview
│   │       ├── ExperimentDispatch.jsx
│   │       ├── Analytics.jsx       # Recharts visualisations
│   │       └── ReplayViewer.jsx    # Canvas-based replay player
│   ├── package.json
│   └── Dockerfile
├── infrastructure/
│   └── terraform/
│       ├── main.tf                 # EC2 + S3 + networking
│       ├── variables.tf
│       ├── outputs.tf
│       └── user_data.sh            # EC2 bootstrap script
├── docker-compose.yml
└── .gitignore
```

---

## Quick start (local)

```bash
# 1. Clone
git clone https://github.com/jwm-dev/cloud-computing-aws-project.git
cd cloud-computing-aws-project

# 2. Copy env template and fill in real values
cp .env.example .env   # see below for required variables

# 3. Build & start
docker compose up --build
```

Open `http://localhost` for the dashboard and `http://localhost:8000/docs` for the Swagger UI.

### Required environment variables

| Variable | Description |
|---|---|
| `S3_BUCKET_NAME` | S3 bucket for experiment storage |
| `AWS_REGION` | AWS region (default `us-east-1`) |
| `AWS_ACCESS_KEY_ID` | IAM credentials (not needed on EC2 with instance profile) |
| `AWS_SECRET_ACCESS_KEY` | IAM credentials (not needed on EC2 with instance profile) |

---

## Deploy to AWS

```bash
cd infrastructure/terraform

# Initialise
terraform init

# Review
terraform plan -var="s3_bucket_name=my-unique-bucket-name" \
               -var="key_pair_name=my-keypair"

# Apply
terraform apply -var="s3_bucket_name=my-unique-bucket-name" \
                -var="key_pair_name=my-keypair"
```

After apply, Terraform prints the public IP.  
Point a Cloudflare tunnel (or DNS record) at that IP to expose the service on a public URL.

---

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/experiments` | Launch a new experiment |
| `GET`  | `/experiments` | List all experiments |
| `GET`  | `/experiments/{id}` | Get experiment status |
| `GET`  | `/analytics/{id}` | Per-episode metrics |
| `GET`  | `/analytics/{id}/summary` | Aggregated statistics |
| `GET`  | `/replays/{id}` | List episode IDs |
| `GET`  | `/replays/{id}/{ep}` | Full frame-by-frame replay |

Full interactive docs: `http://<host>:8000/docs`

---

## Hidden Agenda game rules (summary)

* **5 players**: 4 Crewmates + 1 Impostor on a 40 × 31 grid.  
* **Situation phase** (200 ticks): Crewmates collect fuel cells (corners) and deposit them centrally; Impostor can freeze Crewmates with a short-range beam.  
* **Voting phase** (25 ticks): triggered when a freeze is witnessed or every 200 ticks. Players vote to eject one player.  
* **Crewmates win** if enough fuel is deposited *or* the Impostor is voted out.  
* **Impostor wins** if ≤1 Crewmate remains active.  
* **Draw** at 3 000 ticks.
