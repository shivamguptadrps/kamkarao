# Deploy KamKarao on Oracle Cloud Always Free (₹0)

Total time: about 45 minutes. You only need a browser and the terminal (PowerShell) on your laptop.

---

## 1. Create the Oracle Cloud account (10 min)

1. Go to <https://www.oracle.com/cloud/free/> → **Start for free**.
2. **Home region:** pick **India South (Hyderabad)** or **India West (Mumbai)**. This cannot be changed later.
3. Oracle asks for a card to verify you are a real person. Always Free resources are not charged.
   Do **not** upgrade to "Pay As You Go" unless you choose to later.

## 2. Create the server (10 min)

1. Console → **Compute → Instances → Create instance**.
2. **Name:** `kamkarao`
3. **Image:** click *Change image* → **Canonical Ubuntu 24.04** (or 22.04).
4. **Shape:** click *Change shape* → **Ampere** → `VM.Standard.A1.Flex` → **2 OCPU, 12 GB memory**
   (it should say *Always Free-eligible*).
   - If you see **“Out of capacity”**, try again after some time or another *Availability domain*.
5. **Networking:** keep the defaults (new VCN, public subnet) and make sure
   **Assign a public IPv4 address** is ON.
6. **SSH keys:** choose **Generate a key pair for me** → **Save private key**. Keep this file safe,
   e.g. `C:\Users\shiva\.ssh\kamkarao.key`. Without it you cannot log in.
7. **Boot volume:** 50 GB default is fine (up to 200 GB is free).
8. Click **Create**. When it shows *Running*, copy the **Public IP address**.

## 3. Open the web ports in Oracle's firewall (3 min)

Oracle blocks web traffic by default.

1. On the instance page → **Primary VNIC → Subnet** → **Security Lists** → *Default Security List*.
2. **Add Ingress Rules** – add two rules:

   | Source CIDR | IP Protocol | Destination Port |
   |---|---|---|
   | `0.0.0.0/0` | TCP | `80` |
   | `0.0.0.0/0` | TCP | `443` |

(The setup script opens the same ports inside the server.)

## 4. Copy the project to the server (5 min)

In **PowerShell** on your laptop:

```powershell
# allow the key file to be used (once)
icacls C:\Users\shiva\.ssh\kamkarao.key /inheritance:r /grant:r "$($env:USERNAME):R"

# go to the folder that contains the kamkarao project folder
cd C:\Users\shiva\OneDrive\Desktop\project

# make a clean zip (without your laptop's database, photos and virtualenv)
tar -a -c -f kamkarao_upload.zip --exclude=kamkarao/.venv --exclude=kamkarao/db.sqlite3 --exclude=kamkarao/media --exclude=kamkarao/.env --exclude=*/__pycache__ kamkarao

# send it to the server (replace 1.2.3.4 with your Public IP)
scp -i C:\Users\shiva\.ssh\kamkarao.key kamkarao_upload.zip ubuntu@1.2.3.4:~
```

Better long-term: put the project in a **private GitHub repo** and `git clone` it on the server.
Updates then become `git pull`.

## 5. Run the setup script (10 min)

```powershell
ssh -i C:\Users\shiva\.ssh\kamkarao.key ubuntu@1.2.3.4
```

Then on the server:

```bash
sudo apt-get update && sudo apt-get install -y unzip
unzip -o kamkarao_upload.zip && cd kamkarao
bash deploy/oracle_setup.sh
```

It installs Docker, opens ports 80/443, writes a `.env` with strong passwords, starts the site
(database + Django + automatic HTTPS) and schedules nightly backups.

Then create your admin login:

```bash
sudo docker compose exec web python manage.py createsuperuser
```

## 6. Open the site

The script prints the address, e.g. **https://1-2-3-4.sslip.io** (a free name that points to your IP,
with a real HTTPS certificate). Admin: the same address + `/admin/`.

The live site starts **empty of providers** (only mohallas and services). Add real providers in the
admin. To show demo providers privately for testing only:
`sudo docker compose exec web python manage.py seed_demo` – and remove them with `seed_demo --clear`
before you share the link, because the demo numbers are fake.

---

## Later

**Use kamkarao.com:** at your domain registrar add **A records** for `@` and `www` → your Public IP.
Wait until `ping kamkarao.com` shows your IP, then on the server:

```bash
cd ~/kamkarao
sed -i 's/^DOMAIN=.*/DOMAIN=kamkarao.com/; s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=kamkarao.com,www.kamkarao.com/; s#^CSRF_TRUSTED_ORIGINS=.*#CSRF_TRUSTED_ORIGINS=https://kamkarao.com,https://www.kamkarao.com#; s#^SITE_URL=.*#SITE_URL=https://kamkarao.com#' .env
sudo docker compose up -d
```

**Update the code:** copy the new files (or `git pull`), then `sudo docker compose up -d --build`.

**See errors:** `sudo docker compose logs -f web`

**Backups:** saved every night in `~/kamkarao/backups/` (database + photos, 14 days). Download them
to your laptop now and then:
`scp -i C:\Users\shiva\.ssh\kamkarao.key -r ubuntu@1.2.3.4:~/kamkarao/backups .`

**Login verification:** the site starts with `OTP_PROVIDER=none` (customers just enter their number).
Switch to WhatsApp or SMS OTP later by changing `.env` and running `sudo docker compose up -d`.

**Keep it free:** Oracle may reclaim Always Free servers that stay almost completely idle for a long
time. A live website with visitors normally isn't idle, but check Oracle's current policy.
