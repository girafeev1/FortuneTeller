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

