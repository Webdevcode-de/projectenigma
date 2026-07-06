import sqlite3, random, hashlib, string
from datetime import datetime, timezone, timedelta

DB_PATH = "users.db"
NUM_USERS = random.randint(4800, 5200)
NUM_ADMINS = 5

FIRST_NAMES = [
    "James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda","David","Barbara",
    "William","Elizabeth","Richard","Susan","Joseph","Jessica","Thomas","Sarah","Christopher","Karen",
    "Charles","Lisa","Daniel","Nancy","Matthew","Betty","Anthony","Margaret","Mark","Sandra",
    "Donald","Ashley","Steven","Kimberly","Paul","Emily","Andrew","Donna","Joshua","Michelle",
    "Kenneth","Carol","Kevin","Amanda","Brian","Dorothy","George","Melissa","Timothy","Deborah",
    "Ronald","Stephanie","Edward","Rebecca","Jason","Sharon","Jeffrey","Laura","Ryan","Cynthia",
    "Jacob","Kathleen","Gary","Amy","Nicholas","Angela","Eric","Shirley","Jonathan","Anna",
    "Stephen","Brenda","Larry","Pamela","Justin","Emma","Scott","Nicole","Brandon","Helen",
    "Benjamin","Samantha","Samuel","Katherine","Raymond","Christine","Gregory","Debra","Frank","Rachel",
    "Alexander","Carolyn","Patrick","Janet","Jack","Catherine","Dennis","Maria","Jerry","Heather",
    "Tyler","Diane","Aaron","Ruth","Jose","Olivia","Nathan","Julie","Henry","Joyce",
    "Adrian","Aria","Kai","Nova","Eden","Sage","Rowan","Elara","Orion","Lyra",
    "Zara","Kael","Rhea","Liam","Zoe","Miles","Ivy","Finn","Aurora","Ezra",
    "Lena","Otis","Vera","Theo","Wren","Jasper","Clara","Felix","Iris","Silas",
    "Hazel","Arlo","Ruby","Oscar","Pearl","Hugo","June","Tobias","Luna","Beckett",
]

LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
    "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
    "Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson",
    "Walker","Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores",
    "Green","Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell","Carter","Roberts",
    "Gomez","Phillips","Evans","Turner","Diaz","Parker","Cruz","Edwards","Collins","Reyes",
    "Stewart","Morris","Morales","Murphy","Cook","Rogers","Gutierrez","Ortiz","Morgan","Cooper",
    "Peterson","Bailey","Reed","Kelly","Howard","Ramos","Kim","Cox","Ward","Richardson",
    "Watson","Brooks","Chavez","Wood","James","Bennett","Gray","Mendoza","Ruiz","Hughes",
    "Price","Alvarez","Castillo","Sanders","Patel","Myers","Long","Ross","Foster","Jimenez",
    "Blackwood","Stern","Vance","Monroe","Pitts","Graham","Fox","Stone","Cole","Hayes",
]

DOMAINS = [
    "mail.com","email.com","inbox.com","webmail.org","outlook.com","hotmail.com","gmail.com",
    "yahoo.com","protonmail.com","icloud.com","zoho.com","fastmail.com","tutanota.com",
    "corp.net","company.org","startup.io","tech.co","devmail.io","sysadmin.net",
]

ADJECTIVES = [
    "admin","root","super","power","main","primary","chief","lead","master","head",
    "sys","sec","ops","dev","net","cloud","core","ultra","meta","prime",
]

PASSWORD_HASHES = [
    hashlib.sha1(b"password").hexdigest(),
    hashlib.sha1(b"123456").hexdigest(),
    hashlib.sha1(b"12345678").hexdigest(),
    hashlib.sha1(b"qwerty").hexdigest(),
    hashlib.sha1(b"letmein").hexdigest(),
    hashlib.sha1(b"welcome").hexdigest(),
    hashlib.sha1(b"monkey").hexdigest(),
    hashlib.sha1(b"dragon").hexdigest(),
    hashlib.sha1(b"passw0rd").hexdigest(),
    hashlib.sha1(b"sunshine").hexdigest(),
    hashlib.sha1(b"princess").hexdigest(),
    hashlib.sha1(b"football").hexdigest(),
    hashlib.sha1(b"iloveyou").hexdigest(),
    hashlib.sha1(b"trustno1").hexdigest(),
    hashlib.sha1(b"abc123").hexdigest(),
]

OFFLINE_TIME = datetime(2026, 7, 5, 3, 22, 27, tzinfo=timezone.utc)

def random_username():
    style = random.randint(0, 4)
    if style == 0:
        return random.choice(FIRST_NAMES).lower() + "." + random.choice(LAST_NAMES).lower()
    elif style == 1:
        return random.choice(FIRST_NAMES).lower() + str(random.randint(1, 9999))
    elif style == 2:
        return random.choice(ADJECTIVES) + "." + random.choice(LAST_NAMES).lower()
    elif style == 3:
        return random.choice(LAST_NAMES).lower() + random.choice(FIRST_NAMES).lower()[:3] + str(random.randint(10, 99))
    else:
        return random.choice(ADJECTIVES) + str(random.randint(100, 9999))

def random_email(username):
    domain = random.choice(DOMAINS)
    if random.random() < 0.3:
        return f"{username}.{random.randint(1, 999)}@{domain}"
    return f"{username}@{domain}"

def random_password_hash():
    if random.random() < 0.7:
        return random.choice(PASSWORD_HASHES)
    length = random.randint(6, 16)
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    plain = ''.join(random.choices(chars, k=length))
    return hashlib.sha1(plain.encode()).hexdigest()

def random_last_login(is_admin_before):
    if is_admin_before:
        days_ago = random.randint(1, 60)
        hours = random.randint(0, 23)
        minutes = random.randint(0, 59)
        dt = OFFLINE_TIME - timedelta(days=days_ago, hours=hours, minutes=minutes)
    else:
        days_ago = random.randint(0, 30)
        hours = random.randint(0, 23)
        minutes = random.randint(0, 59)
        dt = OFFLINE_TIME - timedelta(days=days_ago, hours=hours, minutes=minutes)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("DROP TABLE IF EXISTS users")
c.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT NOT NULL,
        admin INTEGER NOT NULL DEFAULT 0,
        first_name TEXT NOT NULL DEFAULT '',
        last_name TEXT NOT NULL DEFAULT '',
        last_login TEXT
    )
""")

usernames = set()
users = []

admin_indices = set(random.sample(range(NUM_USERS), NUM_ADMINS))
admin123_index = random.choice(list(admin_indices))

for i in range(NUM_USERS):
    while True:
        u = random_username()
        if u not in usernames:
            usernames.add(u)
            break

    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    is_admin = i in admin_indices

    if i == admin123_index:
        pw_hash = "f865b53623b121fd34ee5426c792e5c33af8c227"
        last_login = OFFLINE_TIME.strftime("%Y-%m-%d %H:%M:%S")
    elif is_admin:
        plain = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        pw_hash = hashlib.sha1(plain.encode()).hexdigest()
        last_login = random_last_login(is_admin_before=True)
    else:
        pw_hash = random_password_hash()
        last_login = random_last_login(is_admin_before=False)

    email = random_email(u)
    users.append((u, pw_hash, email, 1 if is_admin else 0, fn, ln, last_login))

c.executemany(
    "INSERT INTO users (username, password_hash, email, admin, first_name, last_name, last_login) VALUES (?, ?, ?, ?, ?, ?, ?)",
    users
)

conn.commit()
conn.close()

print(f"Created {DB_PATH} with {len(users)} users ({NUM_ADMINS} admins, one with admin123)")

admins = [u for u in users if u[3] == 1]
print("\nAdmin accounts:")
for u in admins:
    print(f"  {u[4]} {u[5]:15} ({u[0]:20}) last_login={u[6]}  admin123={'***' if u[1] == 'f865b53623b121fd34ee5426c792e5c33af8c227' else ''}")
