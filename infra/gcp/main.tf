resource "google_compute_network" "this" {
  name                    = "${var.name_prefix}-net"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "this" {
  name          = "${var.name_prefix}-subnet"
  ip_cidr_range = var.network_cidr
  region        = local.region
  network       = google_compute_network.this.id
}

resource "google_compute_firewall" "ssh" {
  name    = "${var.name_prefix}-allow-ssh"
  network = google_compute_network.this.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = [var.ssh_ingress_cidr]
  target_tags   = ["mark6-bot"]
}

resource "google_compute_firewall" "ssh_iap" {
  name    = "${var.name_prefix}-allow-ssh-iap"
  network = google_compute_network.this.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # IAP TCP forwarding range (lets you SSH from anywhere via Cloud Console / gcloud --tunnel-through-iap)
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["mark6-bot"]
}

locals {
  instance_ssh_keys = join(
    "\n",
    concat(
      ["${var.ssh_user}:${trimspace(file(var.ssh_public_key_path))}"],
      [
        for path in var.extra_ssh_public_key_paths :
        "${var.ssh_user}:${trimspace(file(path))}"
      ],
    ),
  )
}

resource "google_compute_instance" "bot" {
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["mark6-bot"]

  boot_disk {
    initialize_params {
      image = var.boot_image
      size  = var.boot_disk_size_gb
      type  = var.boot_disk_type
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.this.name

    access_config {}
  }

  metadata = {
    ssh-keys = local.instance_ssh_keys
  }

  metadata_startup_script = templatefile("${path.module}/startup.sh", {
    repo_url     = var.repo_url
    app_dir      = var.app_dir
    service_user = var.ssh_user
  })
}
