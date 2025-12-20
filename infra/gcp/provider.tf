locals {
  derived_region = join("-", slice(split("-", var.zone), 0, 2))
  region         = coalesce(var.region, local.derived_region)
}

provider "google" {
  project = var.project_id
  region  = local.region
  zone    = var.zone
}

