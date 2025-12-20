variable "oci_profile" {
  type        = string
  description = "Profile name from ~/.oci/config"
  default     = "DEFAULT"
}

variable "region" {
  type        = string
  description = "OCI region override (e.g. ap-tokyo-1). Leave null to use ~/.oci/config."
  default     = null
}

variable "compartment_ocid" {
  type        = string
  description = "Compartment OCID where resources will be created."
}

variable "tenancy_ocid" {
  type        = string
  description = "Tenancy OCID. Leave null when deploying to the root compartment (where compartment_ocid == tenancy OCID)."
  default     = null
}

variable "availability_domain" {
  type        = string
  description = "Availability Domain name, e.g. 'RFyf:AP-SINGAPORE-2-AD-1'. Leave null to auto-pick the first AD in the region."
  default     = null
}

variable "name_prefix" {
  type        = string
  description = "Prefix for network resource names."
  default     = "mark6"
}

variable "vcn_cidr" {
  type        = string
  description = "CIDR block for the VCN."
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  type        = string
  description = "CIDR block for the public subnet."
  default     = "10.0.1.0/24"
}

variable "vcn_dns_label" {
  type        = string
  description = "DNS label for the VCN (lowercase letters/numbers, 1-15 chars)."
  default     = "mark6vcn"
}

variable "subnet_dns_label" {
  type        = string
  description = "DNS label for the subnet (lowercase letters/numbers, 1-15 chars)."
  default     = "publicsubnet"
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to the SSH public key that will be added to opc@ for login."
}

variable "ssh_ingress_cidr" {
  type        = string
  description = "Your public IP in CIDR form, e.g. '1.2.3.4/32', to allow SSH."
}

variable "ssh_private_key_path_for_command" {
  type        = string
  description = "Used only for printing an SSH command in outputs (Terraform does not read this key)."
}

variable "instance_name" {
  type        = string
  description = "Compute instance display name."
  default     = "Fortune Teller"
}

variable "fault_domain" {
  type        = string
  description = "Optional fault domain (e.g. 'FAULT-DOMAIN-1'). Leave null to let OCI choose."
  default     = null
}

variable "instance_shape" {
  type        = string
  description = "Compute shape."
  default     = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  type        = number
  description = "Number of OCPUs for Flex shape."
  default     = 1
}

variable "instance_memory_gbs" {
  type        = number
  description = "Memory (GB) for Flex shape."
  default     = 6
}

variable "preemptible" {
  type        = bool
  description = "Create the instance as preemptible (can be reclaimed by OCI at any time). Useful when on-demand capacity is exhausted."
  default     = false
}

variable "preemptible_preserve_boot_volume" {
  type        = bool
  description = "If the preemptible instance is reclaimed, preserve the boot volume so you can recreate quickly."
  default     = true
}

variable "boot_volume_size_in_gbs" {
  type        = number
  description = "Boot volume size in GB."
  default     = 50
}

variable "image_operating_system" {
  type        = string
  description = "Platform image operating system."
  default     = "Oracle Linux"
}

variable "image_operating_system_version" {
  type        = string
  description = "Platform image OS version."
  default     = "9"
}

variable "image_ocid" {
  type        = string
  description = "Optional: pin a specific image OCID. Leave empty to auto-select the latest Oracle Linux 9 image for the chosen shape."
  default     = ""
}

variable "repo_url" {
  type        = string
  description = "Repo URL to clone on the instance."
  default     = "https://github.com/girafeev1/FortuneTeller.git"
}

variable "app_dir" {
  type        = string
  description = "Directory on the instance where the repo will be cloned."
  default     = "/home/opc/mark6-generator"
}
