variable "subscription_id" {
  description = "Azure subscription ID used for the deployment."
  type        = string
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "westeurope"
}

variable "resource_group_name" {
  description = "Resource group containing the churn application resources."
  type        = string
  default     = "rg-customer-churn"
}

variable "registry_name" {
  description = "Globally unique Azure Container Registry name."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{5,50}$", var.registry_name))
    error_message = "registry_name must contain 5-50 lowercase letters and digits."
  }
}

variable "environment_name" {
  description = "Container Apps environment name."
  type        = string
  default     = "env-customer-churn"
}

variable "app_name" {
  description = "Container App name."
  type        = string
  default     = "customer-churn"
}

variable "identity_name" {
  description = "User-assigned identity used to pull the private image."
  type        = string
  default     = "customer-churn-pull"
}

variable "container_image" {
  description = "Optional complete image reference. Leave empty to use the image in this ACR."
  type        = string
  default     = ""
}

variable "image_tag" {
  description = "Image tag used when container_image is empty."
  type        = string
  default     = "latest"
}

variable "container_cpu" {
  description = "Container CPU allocation in vCPU."
  type        = number
  default     = 0.5
}

variable "container_memory" {
  description = "Container memory allocation."
  type        = string
  default     = "1Gi"
}

variable "min_replicas" {
  description = "Minimum number of Container App replicas."
  type        = number
  default     = 0
}

variable "max_replicas" {
  description = "Maximum number of Container App replicas."
  type        = number
  default     = 1
}

variable "app_environment_variables" {
  description = "Non-sensitive environment variables passed to the container."
  type        = map(string)
  default = {
    MODEL_PATH     = "/app/models/churn_pipeline.joblib"
    OMP_NUM_THREADS = "1"
  }
}

variable "app_secrets" {
  description = "Sensitive Container App secrets. Values are stored in Terraform state; use an encrypted remote backend."
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "secret_environment_variables" {
  description = "Maps container environment variable names to keys in app_secrets."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default = {
    application = "customer-churn"
    managed_by  = "terraform"
  }
}
