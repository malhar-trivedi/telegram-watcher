variable "aws_region" {
  description = "AWS Region to deploy to"
  default     = "us-east-1"
}

variable "alert_email" {
  description = "Email to receive Budget and Downtime ALERTS"
  type        = string
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token for notifications"
  type        = string
  sensitive   = true
  default     = ""
}

variable "telegram_chat_id" {
  description = "Telegram Chat ID for notifications"
  type        = string
  default     = ""
}

# --- Secrets to be stored in SSM Parameter Store ---

variable "telegram_api_id" {
  description = "Telegram API ID"
  type        = string
  sensitive   = true
}

variable "telegram_api_hash" {
  description = "Telegram API Hash"
  type        = string
  sensitive   = true
}

variable "telegram_session_string" {
  description = "Telegram Session String (from generate_session.py)"
  type        = string
  sensitive   = true
}

variable "target_keywords" {
  description = "Comma-separated list of keywords"
  type        = string
  default     = "urgent,help,alert"
}

variable "target_chats" {
  description = "Comma-separated list of chat IDs or Titles"
  type        = string
  default     = ""
}

variable "twilio_account_sid" {
  description = "Twilio Account SID"
  type        = string
  default     = ""
}

variable "twilio_auth_token" {
  description = "Twilio Auth Token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "twilio_whatsapp_from" {
  description = "Twilio From Number (e.g. whatsapp:+1415...)"
  type        = string
  default     = ""
}

variable "twilio_whatsapp_to" {
  description = "Twilio To Number (e.g. whatsapp:+1234...)"
  type        = string
  default     = ""
}

variable "whatsapp_webhook_url" {
  description = "Generic Webhook URL (CallMeBot)"
  type        = string
  default     = ""
}
