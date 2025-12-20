locals {
  image_id = (
    var.image_ocid != ""
    ? var.image_ocid
    : data.oci_core_images.oracle_linux_9_arm.images[0].id
  )

  is_flex_shape = length(regexall("\\.Flex$", var.instance_shape)) > 0

  tenancy_id_for_identity = (
    try(trimspace(var.tenancy_ocid), "") != ""
    ? var.tenancy_ocid
    : var.compartment_ocid
  )
}

data "oci_identity_availability_domains" "this" {
  compartment_id = local.tenancy_id_for_identity
}

locals {
  resolved_availability_domain = (
    try(trimspace(var.availability_domain), "") != ""
    ? var.availability_domain
    : data.oci_identity_availability_domains.this.availability_domains[0].name
  )

  resolved_fault_domain = (
    try(trimspace(var.fault_domain), "") != ""
    ? var.fault_domain
    : null
  )
}

data "oci_core_images" "oracle_linux_9_arm" {
  compartment_id           = var.compartment_ocid
  operating_system         = var.image_operating_system
  operating_system_version = var.image_operating_system_version
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_ocid
  cidr_block     = var.vcn_cidr
  display_name   = "${var.name_prefix}-vcn"
  dns_label      = var.vcn_dns_label
}

resource "oci_core_internet_gateway" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-igw"
  enabled        = true
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-public-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.this.id
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-public-sl"

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }

  ingress_security_rules {
    protocol = "6"
    source   = var.ssh_ingress_cidr

    tcp_options {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_subnet" "public" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.this.id
  cidr_block                 = var.subnet_cidr
  display_name               = "${var.name_prefix}-public-subnet"
  dns_label                  = var.subnet_dns_label
  route_table_id             = oci_core_route_table.public.id
  security_list_ids          = [oci_core_security_list.public.id]
  prohibit_public_ip_on_vnic = false
}

resource "oci_core_instance" "bot" {
  availability_domain = local.resolved_availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = var.instance_name
  shape               = var.instance_shape

  fault_domain = local.resolved_fault_domain

  dynamic "preemptible_instance_config" {
    for_each = var.preemptible ? [1] : []
    content {
      preemption_action {
        type                 = "TERMINATE"
        preserve_boot_volume = var.preemptible_preserve_boot_volume
      }
    }
  }

  dynamic "shape_config" {
    for_each = local.is_flex_shape ? [1] : []
    content {
      ocpus         = var.instance_ocpus
      memory_in_gbs = var.instance_memory_gbs
    }
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
  }

  source_details {
    source_type             = "image"
    source_id               = local.image_id
    boot_volume_size_in_gbs = var.boot_volume_size_in_gbs
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data = base64encode(
      templatefile("${path.module}/cloud-init.yaml", {
        repo_url = var.repo_url
        app_dir  = var.app_dir
      })
    )
  }
}

data "oci_core_vnic_attachments" "bot" {
  compartment_id = var.compartment_ocid
  instance_id    = oci_core_instance.bot.id
}

data "oci_core_vnic" "bot" {
  vnic_id = data.oci_core_vnic_attachments.bot.vnic_attachments[0].vnic_id
}
