# GCP Compute Engine (Always‑Free) VM for the Telegram bot

This Terraform creates:
- A dedicated VPC + subnet
- SSH ingress (TCP/22) from **your IP only**
- SSH ingress (TCP/22) from **IAP** (Cloud Console / `gcloud --tunnel-through-iap`)
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

## Push-based deploy (GitHub Actions)

This repo includes `.github/workflows/deploy-bot.yml` which deploys to the VM on every push to `main` (it ignores `merged_results.csv` updates).

Prereqs:
- Enable **IAP API** in the GCP project (GCP Console → APIs & Services → enable **Cloud Identity-Aware Proxy API**).
- Apply this Terraform once to create:
  - A Workload Identity Provider for GitHub OIDC
  - A deployer service account with minimal permissions
  - An SSH firewall rule for the IAP TCP range

Then add these GitHub repo secrets:
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: Terraform output `github_actions_workload_identity_provider`
- `GCP_SERVICE_ACCOUNT_EMAIL`: Terraform output `github_actions_service_account`
- `MARK6_DEPLOY_SSH_PRIVATE_KEY`: the private key that matches a public key on the VM (see `extra_ssh_public_key_paths`)

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
