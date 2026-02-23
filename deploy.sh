#!/bin/bash
set -e

# 1. Terraform Apply
echo "🚀 Applying Infrastructure..."
cd terraform
./terraform init
./terraform apply -auto-approve -lock=false
ECR_URL=$(./terraform output -raw ecr_url)
INSTANCE_IP=$(./terraform output -raw instance_ip)
cd ..

# 2. Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URL

# 3. Build & Push
echo "📦 Building & Pushing Image..."
docker build --platform linux/arm64 -t telegram_watcher ./telegram_watcher
docker tag telegram_watcher:latest $ECR_URL:latest
docker push $ECR_URL:latest

# 4. Restart Container on EC2
echo "🔄 Refreshing EC2 Instance..."
ssh -i telegram_watcher_key.pem -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "
  set -ex
  # Update .env from SSM
  CONFIG_JSON=\$(aws ssm get-parameter --name \"/telegram_watcher/config\" --with-decryption --query \"Parameter.Value\" --output text --region \"us-east-1\")
  echo \"\$CONFIG_JSON\" | jq -r 'to_entries | .[] | \"\(.key)=\(.value)\"' | sudo tee /home/ubuntu/.env > /dev/null
  
  # Login and Pull
  aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URL
  docker pull $ECR_URL:latest
  
  # Restart Container
  sudo docker stop watcher || true
  sudo docker rm watcher || true
  sudo docker run -d \\
    --name watcher \\
    --restart unless-stopped \\
    --log-driver=awslogs \\
    --log-opt awslogs-group=\"/aws/ec2/telegram_watcher\" \\
    --log-opt awslogs-region=\"us-east-1\" \\
    --log-opt awslogs-stream=\"watcher\" \\
    --env-file /home/ubuntu/.env \\
    $ECR_URL:latest
"

echo "✅ Done! Application successfully redeployed and container restarted on $INSTANCE_IP"
