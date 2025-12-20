# OCI Terraform (Always‑Free VM for the Telegram bot)

This Terraform creates:
- A new VCN + public subnet
- An ingress rule for SSH (TCP/22) from **your IP only**
- A `VM.Standard.A1.Flex` instance (Ampere ARM)
- A cloud-init bootstrap that clones this repo and installs Python deps (it does **not** store your Telegram token)

## Prereqs

1) Install Terraform
- macOS: `brew install terraform`

2) Create an OCI API key (for Terraform)
- OCI Console → **Profile (top right)** → **My profile**
- **API Keys** → **Add API Key** → generate/download
- Download the private key to `~/.oci/oci_api_key.pem` (example path)
- OCI will show you a suggested `~/.oci/config` stanza — add it to `~/.oci/config`

Your local OCI config file (`~/.oci/config`) should look like:
```
[DEFAULT]
user=ocid1.user.oc1..xxxxx
fingerprint=aa:bb:cc:...
tenancy=ocid1.tenancy.oc1..xxxxx
region=ap-singapore-2
key_file=/Users/<you>/.oci/oci_api_key.pem
```

## Values you must provide (where to find them)

- `compartment_ocid`
  - OCI Console → **Identity & Security** → **Compartments** → click your compartment → **OCID**
- `availability_domain`
  - OCI Console → your instance create page shows it (example: `RFyf:AP-SINGAPORE-2-AD-1`)
  - Or: **Compute** → **Instances** → Create → **Placement**
- `ssh_public_key_path`
  - The public key file on your Mac, e.g. `~/.ssh/oci_mark6.pub`
  - Create one if you don’t have it: `ssh-keygen -t ed25519 -f ~/.ssh/oci_mark6 -C mark6-bot`
- `ssh_ingress_cidr`
  - Your current public IP in CIDR form, e.g. `1.2.3.4/32`
  - Get your IP: `curl -s https://ifconfig.me`

## Quick start

From the repo root:
```
cd infra/oci
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

After apply, Terraform prints `public_ip` and an `ssh_command`.

## Common issue: “Out of host capacity” (Always Free ARM)

In some regions (including `ap-singapore-2`), Always Free `VM.Standard.A1.Flex` capacity is often exhausted.

Options:
- Retry later (capacity opens up randomly).
- Use the retry script: `bash retry_apply.sh` (writes logs to `retry-apply.log`, default 5-minute backoff).
- Try a different region (requires subscribing to that region in OCI first).
- Try **preemptible** (often has capacity, but can be reclaimed): set `preemptible = true` in `terraform.tfvars`.
- Use a paid shape if you must stay in a specific region.

## Finish bot setup on the VM

1) SSH to the instance (Terraform output shows the command)

2) Put your Telegram token on the VM (don’t paste it into Terraform)
```
sudo bash -lc 'cat > /etc/mark6-bot.env <<EOF
TELEGRAM_BOT_TOKEN=PASTE_YOUR_TOKEN_HERE
EOF
chmod 600 /etc/mark6-bot.env'
```

3) Enable and start the service
```
sudo systemctl enable --now mark6-bot
sudo systemctl status mark6-bot --no-pager
```

4) Tail logs
```
journalctl -u mark6-bot -f
```

## Tear down

To delete everything created by this Terraform (recommended if you’re done testing):
```
terraform destroy
```
