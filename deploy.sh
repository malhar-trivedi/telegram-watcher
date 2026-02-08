#!/bin/bash
set -e

# 1. Terraform Apply
echo "🚀 Applying Infrastructure..."
cd terraform
./terraform init
./terraform apply -auto-approve -lock=false
ECR_URL=$(./terraform output -raw ecr_url)
cd ..

# 2. Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URL

# 3. Build & Push
echo "📦 Building & Pushing Image..."
docker build --platform linux/amd64 -t telegram_watcher ./telegram_watcher
docker tag telegram_watcher:latest $ECR_URL:latest
docker push $ECR_URL:latest

echo "✅ Done! The EC2 instance will automatically pull this image in ~1-2 minutes."
echo "You can check status by SSH-ing into the instance IP output by terraform."
