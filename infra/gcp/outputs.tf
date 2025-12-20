output "public_ip" {
  value = google_compute_instance.bot.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  value = (
    var.ssh_private_key_path_for_command != null
    ? "ssh -i ${var.ssh_private_key_path_for_command} ${var.ssh_user}@${google_compute_instance.bot.network_interface[0].access_config[0].nat_ip}"
    : "ssh ${var.ssh_user}@${google_compute_instance.bot.network_interface[0].access_config[0].nat_ip}"
  )
}

output "github_actions_service_account" {
  value       = google_service_account.github_deployer.email
  description = "Service account GitHub Actions will impersonate (via OIDC)."
}

output "github_actions_workload_identity_provider" {
  value       = google_iam_workload_identity_pool_provider.github.name
  description = "Workload Identity Provider resource name for google-github-actions/auth."
}
