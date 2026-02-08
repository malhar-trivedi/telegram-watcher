# 🤖 Telegram Watcher

A robust, cloud-native Telegram monitoring bot that listens to specific chats for keywords and sends instant WhatsApp alerts. Designed to run 24/7 on AWS with automated health monitoring and cost controls.

## 🚀 Features

- **Real-time Monitoring**: Uses Telethon (MTProto) to listen for messages in specific Telegram groups or channels.
- **Instant Alerts**: Sends notifications to WhatsApp via Twilio or CallMeBot.
- **Production-Ready Infrastructure**:
  - **AWS EC2**: Runs in a lightweight, self-healing Docker container.
  - **Terraform**: Entire infrastructure is managed as code.
  - **AWS SSM**: Secrets (API keys, session strings) are stored securely in AWS Parameter Store.
  - **CloudWatch Logs**: Centralized logging with 1-week retention.
  - **Budget Alerts**: Automatic email notifications if monthly AWS costs exceed $10.
  - **Auto-Recovery**: Automatic instance reboot if system health checks fail.

---

## 🛠️ Installation & Deployment

### 1. Prerequisites
- **AWS Account** with CLI configured locally.
- **Terraform** installed.
- **Docker** installed.
- **Telegram API Credentials**: Get your `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org).

### 2. Generate Telegram Session
Telegram requires a session string for persistent login.
```bash
cd telegram_watcher
pip install -r requirements.txt
python generate_session.py
```
Follow the prompts to log in. Copy the **string session** printed at the end.

### 3. Configure Terraform
Navigate to the `terraform` directory and create your variables file:
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```
Edit `terraform.tfvars` and fill in:
- `telegram_api_id`
- `telegram_api_hash`
- `telegram_session_string` (from step 2)
- `target_chats` (Comma-separated list of Chat Titles or IDs)
- `alert_email` (To receive budget and downtime alerts)
- `twilio_...` (If using Twilio for WhatsApp)

### 4. Deploy
Run the deployment script from the root directory:
```bash
./deploy.sh
```
This script will:
1. Initialize and apply Terraform infrastructure.
2. Build the Docker image (targeting `linux/amd64`).
3. Push the image to AWS ECR.
4. Trigger the EC2 instance to pull and run the latest bot.

---

## 📊 Monitoring & Operations

### View Logs
Logs are automatically streamed to AWS CloudWatch.
- **Log Group**: `/aws/ec2/telegram_watcher`
- **Retention**: 7 Days

Alternatively, view logs directly on the server:
```bash
ssh -i telegram_watcher_key.pem ubuntu@<INSTANCE_IP> "sudo docker logs -f watcher"
```

### Manual Restart
To force a restart of the bot:
```bash
ssh -i telegram_watcher_key.pem ubuntu@<INSTANCE_IP> "sudo docker restart watcher"
```

### Healthchecks
The container includes a built-in healthcheck. If the Python loop freezes, the container will report `unhealthy` and Docker will restart it automatically (via `restart: unless-stopped`).

---

## 🔒 Security
- **No Credentials in Git**: All secrets are stored in AWS SSM (Encrypted `SecureString`).
- **SSH Access**: Secured via an auto-generated private key (`telegram_watcher_key.pem`) created during deployment.
- **Least Privilege**: The EC2 instance uses an IAM Role restricted only to the necessary SSM and ECR resources.
