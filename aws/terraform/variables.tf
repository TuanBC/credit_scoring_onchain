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
}

variable "bedrock_bearer_token" {
  description = "AWS Bedrock Bearer Token (required if using bearer token authentication)"
  type        = string
  sensitive   = true
}
