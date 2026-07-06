import random
import argparse
from datetime import datetime, timedelta

# ============================================================
# Challenge: Server Boot Log
# The flag is hidden in the boot sequence details:
#   IP: 10.150.44.112
#   Port: 8443
#   Crash time (server local): 2026-07-05 14:22:15 +0200
#
# The flag format is ENIGMA{IP:PORT:TIMESTAMP}
# Example: ENIGMA{10.150.44.112:8443:142215}
# ============================================================

TOTAL_PRE_TRAFFIC_LINES = 2800
OUTPUT_FILE = "server_boot.log"

# Target Solution Parameters
TARGET_SERVER_IP = "10.150.44.112"
TARGET_PORT = "8443"
CRASH_TIME_LOCAL = datetime(2026, 7, 5, 14, 22, 15)
RESTART_TIME_LOCAL = CRASH_TIME_LOCAL + timedelta(hours=3)

# Hacker activity
HACKER_IP = "198.51.100.42"

# Noise traffic pools
IP_POOL = [f"84.112.{random.randint(10, 250)}.{random.randint(1, 254)}" for _ in range(20)]
METHODS = ["GET", "POST", "HEAD"]
ENDPOINTS = [
    "/products/", "/cart/", "/static/js/bundle.js",
    "/about", "/api/v1/status", "/category/electronics",
    "/favicon.ico", "/robots.txt", "/contact",
]
STATUS_CODES = [200, 200, 200, 204, 301, 404, 302]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "curl/8.4.0",
    "Python-urllib/3.12",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Go-http-client/2.0",
]


def generate_combined_log_entry(timestamp, ip, method, endpoint, status):
    size = random.randint(120, 8500) if status not in (204, 302) else 0
    agent = random.choice(USER_AGENTS)
    return (
        f'{ip} - - [{timestamp.strftime("%d/%b/%Y:%H:%M:%S +0000")}] '
        f'"{method} {endpoint} HTTP/1.1" {status} {size} "-" "{agent}"'
    )


def generate_syslog_entry(timestamp, pid, level, message):
    return f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')} +0200] [{pid}] [{level}] {message}"


def generate_log():
    log_lines = []

    # ---- Section 1: Background traffic (well before the crash) ----
    start_time = CRASH_TIME_LOCAL - timedelta(hours=8)
    current_time = start_time
    for _ in range(TOTAL_PRE_TRAFFIC_LINES):
        current_time += timedelta(seconds=random.randint(2, 15))
        ip = random.choice(IP_POOL)
        method = random.choice(METHODS)
        endpoint = random.choice(ENDPOINTS)
        status = random.choice(STATUS_CODES)
        log_lines.append(generate_combined_log_entry(current_time, ip, method, endpoint, status))

    # ---- Section 2: Brute force attack (long before the crash) ----
    attack_start = CRASH_TIME_LOCAL - timedelta(hours=3)
    brute_force_time = attack_start

    # First probe
    log_lines.append(generate_combined_log_entry(brute_force_time, HACKER_IP, "GET", "/admin/login/", 200))

    # Realistic brute force: ~150 attempts with varying delays
    for attempt in range(148):
        brute_force_time += timedelta(seconds=random.randint(1, 6))
        log_lines.append(generate_combined_log_entry(brute_force_time, HACKER_IP, "POST", "/admin/login/", 403))

    # Two successful logins near the end
    brute_force_time += timedelta(seconds=3)
    log_lines.append(generate_combined_log_entry(brute_force_time, HACKER_IP, "POST", "/admin/login/", 302))

    brute_force_time += timedelta(seconds=2)
    log_lines.append(generate_combined_log_entry(brute_force_time, HACKER_IP, "GET", "/admin/auth/user/", 200))

    # ---- Section 3: Normal traffic continues (between attack and crash) ----
    post_attack_time = brute_force_time
    for _ in range(400):
        post_attack_time += timedelta(seconds=random.randint(3, 20))
        ip = random.choice(IP_POOL)
        method = random.choice(METHODS)
        endpoint = random.choice(ENDPOINTS)
        status = random.choice(STATUS_CODES)
        log_lines.append(generate_combined_log_entry(post_attack_time, ip, method, endpoint, status))

    # ---- Section 4: Server crash ----
    log_lines.append(generate_syslog_entry(CRASH_TIME_LOCAL, 8421, "ERROR", "Worker unexpected exit: pid 8425 (Signal 9)"))
    log_lines.append(generate_syslog_entry(CRASH_TIME_LOCAL, 11024, "WARN", "Worker timeout - no heartbeat for 30s"))
    log_lines.append(generate_syslog_entry(CRASH_TIME_LOCAL, 11024, "INFO", "Shutting down Master process"))

    # ---- Section 5: Downtime (server offline for 3 hours) ----
    MONITOR_IPS = ["10.0.0.5", "10.0.0.6"]
    downtime_time = CRASH_TIME_LOCAL + timedelta(minutes=1)
    for _ in range(60):
        ip = random.choice(MONITOR_IPS)
        log_lines.append(generate_combined_log_entry(downtime_time, ip, "GET", "/health", 503))
        downtime_time += timedelta(minutes=3)

    # Monitoring alert summaries
    alert_times = [
        CRASH_TIME_LOCAL + timedelta(minutes=5),
        CRASH_TIME_LOCAL + timedelta(hours=1),
        CRASH_TIME_LOCAL + timedelta(hours=2),
        CRASH_TIME_LOCAL + timedelta(hours=2, minutes=45),
    ]
    for t in alert_times:
        log_lines.append(generate_syslog_entry(t, 5001, "ALERT", f"Server unreachable at {TARGET_SERVER_IP}:{TARGET_PORT} - initiating auto-recovery"))

    # ---- Section 6: Server restart (3 hours after crash) ----
    boot_time = RESTART_TIME_LOCAL

    log_lines.append(generate_syslog_entry(boot_time, 12105, "INFO", "Starting gunicorn 24.0.0"))
    log_lines.append(generate_syslog_entry(boot_time, 12105, "INFO", f"Listening at: http://{TARGET_SERVER_IP}:{TARGET_PORT} (12105)"))
    log_lines.append(generate_syslog_entry(boot_time, 12108, "INFO", "Booting worker with pid: 12108"))
    log_lines.append(generate_syslog_entry(boot_time, 12108, "DEBUG", "Loaded settings: enigma.settings"))
    log_lines.append("System check identified no issues (0 silenced).")
    log_lines.append(f"{CRASH_TIME_LOCAL.strftime('%B %d, %Y')} - {CRASH_TIME_LOCAL.strftime('%H:%M:%S')}")
    log_lines.append(f"Django version 5.2, using settings 'enigma.settings'")
    log_lines.append(f"Development server is running at http://{TARGET_SERVER_IP}:{TARGET_PORT}/")
    log_lines.append("Quit the server with CONTROL-C.")
    log_lines.append("")

    # ---- Section 7: Post-restart traffic ----
    post_restart_time = boot_time
    for _ in range(250):
        post_restart_time += timedelta(seconds=random.randint(5, 30))
        ip = random.choice(IP_POOL)
        method = random.choice(METHODS)
        endpoint = random.choice(ENDPOINTS)
        status = random.choice(STATUS_CODES)
        log_lines.append(generate_combined_log_entry(post_restart_time, ip, method, endpoint, status))

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")

    print(f"[SUCCESS] Generated '{OUTPUT_FILE}' ({len(log_lines)} lines)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the server boot challenge log")
    parser.add_argument("-o", "--output", default=OUTPUT_FILE, help="Output file path")
    parser.add_argument("-n", "--noise", type=int, default=TOTAL_PRE_TRAFFIC_LINES,
                        help=f"Lines of background traffic (default: {TOTAL_PRE_TRAFFIC_LINES})")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
    OUTPUT_FILE = args.output
    TOTAL_PRE_TRAFFIC_LINES = args.noise
    generate_log()
