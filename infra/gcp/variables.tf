variable "project_id" {
  type        = string
  description = "GCP project id."
}

variable "region" {
  type        = string
  description = "Optional override. If null, derived from zone."
  default     = null
}

variable "zone" {
  type        = string
  description = "GCP zone (e.g. us-west1-b)."
  default     = "us-west1-b"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names."
  default     = "mark6"
}

variable "network_cidr" {
  type        = string
  description = "CIDR block for the subnet."
  default     = "10.0.1.0/24"
}

variable "ssh_ingress_cidr" {
  type        = string
  description = "Your public IP in CIDR form, e.g. 1.2.3.4/32, to allow SSH."
}

variable "ssh_user" {
  type        = string
  description = "Linux user name to use for SSH login (created by GCE metadata)."
  default     = "mark6"
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to your SSH public key."
}

variable "ssh_private_key_path_for_command" {
  type        = string
  description = "Used only for printing an SSH command in outputs (Terraform does not read this key)."
  default     = null
}

variable "instance_name" {
  type        = string
  description = "Compute instance name (lowercase letters/digits/hyphens)."
  default     = "fortune-teller"
}

variable "machine_type" {
  type        = string
  description = "GCE machine type."
  default     = "e2-micro"
}

variable "boot_disk_size_gb" {
  type        = number
  description = "Boot disk size (GB)."
  default     = 30
}

variable "boot_disk_type" {
  type        = string
  description = "Boot disk type (pd-standard is cheapest)."
  default     = "pd-standard"
}

variable "boot_image" {
  type        = string
  description = "Boot image for the instance."
  default     = "projects/debian-cloud/global/images/family/debian-12"
}

variable "repo_url" {
  type        = string
  description = "Repo URL to clone on the instance."
  default     = "https://github.com/girafeev1/FortuneTeller.git"
}

variable "app_dir" {
  type        = string
  description = "Directory on the instance where the repo will be cloned."
  default     = "/home/mark6/mark6-generator"
}

