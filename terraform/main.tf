terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- 0. Monitoring & Alerts ---
# SNS Topic for Alarms (Downtime)
resource "aws_sns_topic" "alerts" {
  name = "telegram_watcher_alerts"
}

resource "aws_sns_topic_subscription" "email_subscription" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Alarm: Reboot if Status Check Fails (Auto-Heal)
resource "aws_cloudwatch_metric_alarm" "auto_recover" {
  alarm_name          = "telegram_watcher_auto_recover"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "StatusCheckFailed_System"
  namespace           = "AWS/EC2"
  period              = "60"
  statistic           = "Minimum"
  threshold           = "0"
  alarm_description   = "Auto-recover the instance if system status check fails"
  
  dimensions = {
    InstanceId = aws_instance.server.id
  }

  alarm_actions = [
    "arn:aws:automate:${var.aws_region}:ec2:recover", # Magic ARN to reboot/recover instance
    aws_sns_topic.alerts.arn                           # Notify you
  ]
}

# AWS Budget: Warn if monthly cost > $10
resource "aws_budgets_budget" "cost_warning" {
  name              = "telegram_watcher_budget"
  budget_type       = "COST"
  limit_amount      = "10.0"
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = "2025-01-01_00:00"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}

# --- CloudWatch Log Group with 1 week retention ---
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/ec2/telegram_watcher"
  retention_in_days = 7
}

# --- 1. ECR Repository (Where Docker Image lives) ---
resource "aws_ecr_repository" "repo" {
  name                 = "telegram_watcher"
  image_tag_mutability = "MUTABLE"
  force_delete         = true # Easy cleanup for demo
}

# --- 2. SSM Parameter Store (Secrets) ---
# We combine all vars into one JSON string for easier fetching
locals {
  env_json = jsonencode({
    TELEGRAM_API_ID         = var.telegram_api_id
    TELEGRAM_API_HASH       = var.telegram_api_hash
    TELEGRAM_SESSION_STRING = var.telegram_session_string
    TARGET_KEYWORDS         = var.target_keywords
    TARGET_CHATS            = var.target_chats
    TWILIO_ACCOUNT_SID      = var.twilio_account_sid
    TWILIO_AUTH_TOKEN       = var.twilio_auth_token
    TWILIO_WHATSAPP_FROM    = var.twilio_whatsapp_from
    TWILIO_WHATSAPP_TO      = var.twilio_whatsapp_to
    WHATSAPP_WEBHOOK_URL    = var.whatsapp_webhook_url
    TELEGRAM_BOT_TOKEN      = var.telegram_bot_token
    TELEGRAM_CHAT_ID        = var.telegram_chat_id
  })
}

resource "aws_ssm_parameter" "config" {
  name  = "/telegram_watcher/config"
  type  = "SecureString"
  value = local.env_json
}

# --- 3. IAM Role (Permission for EC2) ---
resource "aws_iam_role" "ec2_role" {
  name = "telegram_watcher_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

# Allow EC2 to: Pull ECR images
resource "aws_iam_role_policy_attachment" "ecr_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Allow EC2 to: Read OUR secret (and nothing else)
resource "aws_iam_policy" "ssm_policy" {
  name        = "telegram_watcher_ssm_policy"
  description = "Read config from SSM"
  policy      = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "ssm:GetParameter"
      Resource = aws_ssm_parameter.config.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.ssm_policy.arn
}

# Allow EC2 to: Push logs to CloudWatch
resource "aws_iam_role_policy_attachment" "logs_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "telegram_watcher_profile"
  role = aws_iam_role.ec2_role.name
}

# --- 4. Network (Security Group) ---
resource "aws_security_group" "sg" {
  name        = "telegram_watcher_sg"
  description = "Allow SSH"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- 5. Key Pair (Auto-Generated) ---
resource "tls_private_key" "pk" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "kp" {
  key_name   = "telegram_watcher_key"
  public_key = tls_private_key.pk.public_key_openssh
}

resource "local_file" "ssh_key" {
  filename        = "${path.module}/../telegram_watcher_key.pem"
  content         = tls_private_key.pk.private_key_pem
  file_permission = "0400"
}

# --- 6. EC2 Instance ---
resource "aws_instance" "server" {
  ami           = "ami-0c7217cdde317cfec" # Ubuntu 22.04 LTS (us-east-1)
  instance_type = "t2.micro"
  key_name      = aws_key_pair.kp.key_name
  vpc_security_group_ids = [aws_security_group.sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  user_data_replace_on_change = true

  # User Data: The script that runs ONCE when server starts
  user_data = <<-EOF
              #!/bin/bash
              set -ex
              exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
              
              # 1. Wait for apt lock to be released (avoid race conditions)
              while fuser /var/lib/dpkg/lock >/dev/null 2>&1 ; do
                  echo "Waiting for apt lock..." 
                  sleep 5
              done
              
              # 2. Install Dependencies & Docker (Official Repo)
              apt-get update
              apt-get install -y ca-certificates curl gnupg unzip jq lsb-release

              # Add Docker's official GPG key
              mkdir -p /etc/apt/keyrings
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
              chmod a+r /etc/apt/keyrings/docker.gpg

              # Add the repository
              echo \
                "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
                $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
              
              # Install Docker Engine
              apt-get update
              apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

              # Install AWS CLI v2 (re-ordered only if needed, but keeping flow)
              curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
              unzip -o awscliv2.zip
              ./aws/install --update || ./aws/install

              # 3. Start Docker
              systemctl start docker
              systemctl enable docker
              usermod -aG docker ubuntu

              # 4. Pull Config from SSM
              REGION="${var.aws_region}"
              PARAM_NAME="${aws_ssm_parameter.config.name}"
              
              CONFIG_JSON=$(aws ssm get-parameter --name "$PARAM_NAME" --with-decryption --query "Parameter.Value" --output text --region "$REGION")
              
              # Convert JSON to .env format
              echo "$CONFIG_JSON" | jq -r 'to_entries | .[] | "\(.key)=\(.value)"' > /home/ubuntu/.env

              # 5. Login to ECR
              aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin ${aws_ecr_repository.repo.repository_url}

              # 6. Retry Loop for Image Pull
              IMAGE="${aws_ecr_repository.repo.repository_url}:latest"
              
              echo "Waiting for Docker image: $IMAGE"
              until docker pull $IMAGE; do
                echo "Image pull failed. Retrying in 10s..."
                sleep 10
              done

              # 7. Run Container
              # Stop existing if any (for idempotency)
              docker stop watcher || true
              docker rm watcher || true
              
              docker run -d \
                --name watcher \
                --restart unless-stopped \
                --log-driver=awslogs \
                --log-opt awslogs-group="${aws_cloudwatch_log_group.app_logs.name}" \
                --log-opt awslogs-region="${var.aws_region}" \
                --log-opt awslogs-stream="watcher" \
                --env-file /home/ubuntu/.env \
                $IMAGE

              echo "Deployed successfully!" > /home/ubuntu/status.txt
              EOF

  tags = {
    Name = "TelegramWatcher"
  }
}

output "ecr_url" {
  value = aws_ecr_repository.repo.repository_url
}

output "instance_ip" {
  value = aws_instance.server.public_ip
}
