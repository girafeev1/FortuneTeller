# GCP Compute Engine (Always‑Free) VM for the Telegram bot

This Terraform creates:
- A dedicated VPC + subnet
- SSH ingress (TCP/22) from **your IP only**
- A Compute Engine VM (default `e2-micro`)
- A startup script that installs Python, clones this repo, sets up a venv, and writes a `systemd` unit (it does **not** store your Telegram token)

## Prereqs (you may need to do this)

1) Ensure the project has billing enabled (even for Always Free)

2) Ensure Compute Engine API is enabled
- GCP Console → APIs & Services → Enabled APIs → enable **Compute Engine API**

3) Terraform auth options

Option A (recommended): Use your Google account credentials (no key file)
- Install `gcloud` and run:
  - `gcloud auth login`
  - `gcloud auth application-default login`

Option B: Use a dedicated service account key JSON (recommended for servers)
- Create a new service account, e.g. `mark6-terraform`, in:
  - GCP Console → IAM & Admin → Service Accounts → Create service account
- Grant it roles on the project:
  - `roles/compute.admin`
  - `roles/iam.serviceAccountUser` (needed to create a VM using the project’s default Compute Engine service account)
- Create a JSON key for it:
  - Service Accounts → click it → Keys → Add key → Create new key → JSON
- Save it locally and set:
  - `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`

## Quick start

From the repo root:
```
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

After apply, Terraform prints `public_ip` and an `ssh_command`.

## Finish bot setup on the VM

1) SSH to the instance (use the Terraform output)

2) Put your Telegram token on the VM (don’t commit it anywhere)
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

To delete everything created by this Terraform:
```
terraform destroy
```
