# Hidden Agenda — Minimal Implementation

This repository implements the Hidden Agenda environment per spec.

Quick run (local):

```bash
python -m pip install -r requirements.txt
uvicorn hidden_agenda.api:app --host 0.0.0.0 --port 8000
```

Run batch via API:

```bash
curl -X POST "http://localhost:8000/run" -H "Content-Type: application/json" -d '{"num_games":2, "config": {"seed":42}}'
```

Docker build & run:

```bash
docker build -t hidden-agenda:latest .
docker run -p 8000:8000 hidden-agenda:latest
```

AWS deploy (one EC2 instance):

1. Launch Ubuntu EC2 instance.
2. Install Docker: `sudo apt update && sudo apt install -y docker.io`.
3. Copy repository to instance.
4. Build and run container (same commands as above).
5. Configure AWS credentials on instance for S3 uploads.
 
Notes on IAM/S3:

- Create an S3 bucket and an IAM user with `s3:PutObject` and `s3:GetObject` on that bucket.
- Store AWS credentials in `~/.aws/credentials` on the EC2 instance or set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` env vars for the container.

Deployment script:

```
./deploy/deploy_ec2.sh <instance-ip> <key.pem>
```

