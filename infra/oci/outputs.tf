output "instance_ocid" {
  value = oci_core_instance.bot.id
}

output "public_ip" {
  value = data.oci_core_vnic.bot.public_ip_address
}

output "ssh_command" {
  value = "ssh -i ${var.ssh_private_key_path_for_command} opc@${data.oci_core_vnic.bot.public_ip_address}"
}

