variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "etherscan_api_key" {
  description = "Etherscan API key"
  type        = string
  sensitive   = true
}

variable "openrouter_api_key" {
  description = "OpenRouter API key (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "bedrock_bearer_token" {
  description = "AWS Bedrock Bearer Token for LLM access"
  type        = string
  sensitive   = true
}

variable "bedrock_model_id" {
  description = "AWS Bedrock Model ID"
  type        = string
  default     = "amazon.nova-pro-v1:0"
}

variable "bedrock_region" {
  description = "AWS Bedrock region"
  type        = string
  default     = "ap-southeast-2"
}

