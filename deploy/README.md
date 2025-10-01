# Django + Podman Deployment (Rootless)

This folder helps you deploy a Django project to a Linux server using **Podman** (rootless) and **podman-compose**.

## Prerequisites (on the server)
- Linux host (Ubuntu/Debian recommended)
- Podman + podman-compose
- A non-root user, e.g. `django`, with linger enabled for systemd user units

```bash
sudo apt-get update && sudo apt-get install -y podman podman-compose
sudo useradd -m -s /bin/bash django || true
sudo -u django -H bash -lc 'loginctl enable-linger $(whoami)'
```

## Project structure
Place this `deploy/` folder at the root of your Django repository (alongside `manage.py` and `requirements.txt`).

```text
your-project/
├─ manage.py
├─ requirements.txt
├─ config/            # your Django settings module
├─ app modules ...
└─ deploy/
   ├─ Containerfile
    ├─ entrypoint.sh
    ├─ podman-compose.yml
    └─ .env.example
```

## Build & Run
On the server (as your `django` user):
```bash
cd ~/apps/your-project
cd deploy
cp .env.example .env
# edit .env (SECRET_KEY, DB_* & hosts)
podman-compose up -d --build
```

Your app should be reachable at `http://SERVER_IP:8001/`.

## First-time setup
```bash
# Inside the running web container
podman ps  # find the container name (e.g., yourproject-web-1)
podman exec -it yourproject-web-1 python manage.py createsuperuser
```

## Autostart with systemd (optional but recommended)
```bash
# Generate user systemd units for the project (from compose-created pod/containers)
podman pod ps  # get POD name, e.g. yourproject_pod
podman generate systemd --new --files --name yourproject_pod

# Move units to user dir and enable
mkdir -p ~/.config/systemd/user
mv *.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now yourproject_pod.service
```

## Notes
- If you use **mysqlclient**, the image already installs `default-libmysqlclient-dev`.
- For **ReportLab** (PDF), this image includes `libjpeg-dev`, `zlib1g-dev`, `libfreetype6-dev` to build wheels.
  If builds still fail, consider pinning a version with prebuilt wheels or switch to Python 3.11 base image.
- If you already have another web server on ports 80/443 (e.g., OpenLiteSpeed/CyberPanel),
  keep mapping to port 8001 and reverse-proxy from your existing server or Cloudflare.
- For Postgres instead of MariaDB, change the `db` service to `postgres:16` and install `libpq-dev` (already in image).

## Troubleshooting
- View logs: `podman-compose logs -f web` (or `db`)
- Rebuild after changing requirements: `podman-compose build web && podman-compose up -d`
- Ensure `*.sh` files have LF line endings on Windows (add to `.gitattributes`: `*.sh text eol=lf`)
