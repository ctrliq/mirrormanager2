# MirrorManager2 Configuration Reference

Complete reference for all configuration options.

## Configuration Loading

Configuration is loaded in order (later overrides earlier):

1. Default config: [mirrormanager2/default_config.py](../mirrormanager2/default_config.py)
2. Environment variable: `MM2_CONFIG` points to additional config file

### Config File Format
Config files are Python files executed with `exec()`:
```python
# Example: /etc/mirrormanager/mirrormanager2.cfg
SQLALCHEMY_DATABASE_URI = "postgresql://..."
SECRET_KEY = "your-secret-key"
```

---

## Core Settings

### Database

| Option | Default | Description |
|--------|---------|-------------|
| `SQLALCHEMY_DATABASE_URI` | `sqlite:////var/tmp/mirrormanager2_dev.sqlite` | Database connection URL |
| `DB_MODELS_LOCATION` | `mirrormanager2.lib.model` | ORM models module |
| `DB_ALEMBIC_LOCATION` | `<package>/lib/migrations` | Alembic migrations path |

**Source:** [default_config.py lines 34-37](../mirrormanager2/default_config.py#L34-L37)

### Security

| Option | Default | Description |
|--------|---------|-------------|
| `SECRET_KEY` | `<insert here your own key>` | Flask secret key for CSRF/sessions |
| `PASSWORD_SEED` | `You'd better change it...` | Salt for password hashing |
| `MM_COOKIE_REQUIRES_HTTPS` | `True` | Require HTTPS for cookies |
| `MM_COOKIE_NAME` | `MirrorManager` | Session cookie name |
| `CHECK_SESSION_IP` | `True` | Validate client IP in session |

**Source:** [default_config.py lines 43-47, 118-127](../mirrormanager2/default_config.py#L43-L47)

⚠️ **IMPORTANT:** Always change `SECRET_KEY` and `PASSWORD_SEED` in production!

### Session

| Option | Default | Description |
|--------|---------|-------------|
| `PERMANENT_SESSION_LIFETIME` | `timedelta(hours=1)` | Session timeout |

**Source:** [default_config.py line 31](../mirrormanager2/default_config.py#L31)

---

## Authentication

### Mode Selection

| Option | Default | Description |
|--------|---------|-------------|
| `MM_AUTHENTICATION` | `fas` | Auth method: `fas` (OIDC) or `local` |

**Source:** [default_config.py line 55](../mirrormanager2/default_config.py#L55)

### OIDC (FAS) Settings

| Option | Default | Description |
|--------|---------|-------------|
| `OIDC_CLIENT_SECRETS` | `<package>/../client_secrets.json` | OIDC client config |
| `OIDC_SCOPES` | `openid email profile groups agreements` | Requested scopes |
| `ADMIN_GROUP` | `["sysadmin-main"]` | Groups with admin access |

**Source:** [default_config.py lines 57-72](../mirrormanager2/default_config.py#L57-L72)

---

## Email & Notifications

| Option | Default | Description |
|--------|---------|-------------|
| `ADMIN_EMAIL` | `admin@fedoraproject.org` | Admin contact email |
| `EMAIL_FROM` | `nobody@fedoraproject.org` | Sender address |
| `SMTP_SERVER` | `localhost` | SMTP relay server |
| `USE_FEDORA_MESSAGING` | `True` | Enable Fedora Messaging |

**Source:** [default_config.py lines 74-83](../mirrormanager2/default_config.py#L74-L83)

### Fedora Messaging
Configure via `fedora-messaging.toml`:
```toml
amqp_url = "amqp://"
publish_exchange = "amq.topic"
```

**Source:** [fedora-messaging.toml.example](../fedora-messaging.toml.example)

---

## UI Settings

| Option | Default | Description |
|--------|---------|-------------|
| `THEME_FOLDER` | `fedora` | Template/static theme |
| `ITEMS_PER_PAGE` | `20` | Pagination items |
| `SHOW_MAPS` | `True` | Show maps tab |
| `STATIC_MAP` | `map.png` | Static map filename |
| `INTERACTIVE_MAP` | `mirrors.html` | Interactive map filename |
| `SHOW_PROPAGATION` | `True` | Show propagation tab |
| `APPLICATION_URL` | `None` | Override URL in emails |

**Source:** [default_config.py lines 40-41, 49-51, 88-97](../mirrormanager2/default_config.py#L40-L41)

---

## Geographic Settings

| Option | Default | Description |
|--------|---------|-------------|
| `EMBARGOED_COUNTRIES` | `["CU", "IR", "KP", "SD", "SY"]` | Excluded countries |
| `GEOIP_BASE` | `/usr/share/GeoIP` | GeoIP database path |

**Source:** [default_config.py lines 86, 112](../mirrormanager2/default_config.py#L86-L112)

---

## Mirror Management

| Option | Default | Description |
|--------|---------|-------------|
| `MASTER_RSYNC_ACL` | `False` | Enable master rsync ACL |
| `MM_PROTOCOL_REGEX` | `^(?!ftp)(.*)$` | Allowed URL protocols |
| `MM_IPV4_NETBLOCK_SIZE` | `/16` | Max user IPv4 netblock |
| `MM_IPV6_NETBLOCK_SIZE` | `/32` | Max user IPv6 netblock |

**Source:** [default_config.py lines 114-115, 139-148](../mirrormanager2/default_config.py#L114-L148)

---

## Logging

| Option | Default | Description |
|--------|---------|-------------|
| `MM_LOG_DIR` | `/var/log/mirrormanager` | Log directory |

**Source:** [default_config.py lines 131-134](../mirrormanager2/default_config.py#L131-L134)

When set:
- Crawler creates per-host logs: `<log_dir>/crawler/<host_id>.log`
- Other utilities may use for their logs

---

## Crawler Settings

| Option | Default | Description |
|--------|---------|-------------|
| `CRAWLER_RSYNC_PARAMETERS` | `--no-motd --timeout 14400` | Extra rsync args |
| `CRAWLER_AUTO_DISABLE` | `4` | Failures before auto-disable |

**Source:** [default_config.py lines 163-172](../mirrormanager2/default_config.py#L163-L172)

### Rsync Timeout
`--timeout 14400` = 4 hours. Adjust based on your mirror sizes.

---

## UMDL Settings

| Option | Default | Description |
|--------|---------|-------------|
| `UMDL_PREFIX` | `""` | Path prefix for master directories |
| `UMDL_MASTER_DIRECTORIES` | `[]` | List of directories to scan |
| `MAX_STALE_DAYS` | `4` | Age before file details expire |
| `SKIP_PATHS_FOR_VERSION` | `["pub/alt"]` | Paths to skip for version detection |

**Source:** [default_config.py lines 174-181, 186-187](../mirrormanager2/default_config.py#L174-L187)

### UMDL_MASTER_DIRECTORIES Format
```python
UMDL_MASTER_DIRECTORIES = [
    {
        "category": "Fedora Linux",
        "path": "/srv/pub/fedora/linux",
    },
    {
        "category": "Fedora Archive", 
        "path": "/srv/pub/archive/fedora/linux",
    },
    {
        "category": "EPEL",
        "path": "/srv/pub/epel",
    },
]
```

---

## Statistics Settings

| Option | Default | Description |
|--------|---------|-------------|
| `ACCESS_STATS_KEEP_DAYS` | `30` | Days to keep access stats |
| `PROPAGATION_KEEP_DAYS` | `7` | Days to keep propagation stats |
| `PROPAGATION_BASE` | `/var/lib/mirrormanager/statistics/data/propagation` | Propagation images path |

**Source:** [default_config.py lines 84, 99-107](../mirrormanager2/default_config.py#L84-L107)

---

## External Services

| Option | Default | Description |
|--------|---------|-------------|
| `BODHI_URL` | `https://bodhi.fedoraproject.org` | Bodhi API for version info |

**Source:** [default_config.py line 184](../mirrormanager2/default_config.py#L184)

---

## Health Checks

| Option | Default | Description |
|--------|---------|-------------|
| `HEALTHZ` | `{"live": ..., "ready": ...}` | Health check functions |

**Source:** [default_config.py lines 189-192](../mirrormanager2/default_config.py#L189-L192)

```python
HEALTHZ = {
    "live": "mirrormanager2.health_checks.liveness",
    "ready": "mirrormanager2.health_checks.readiness",
}
```

---

## Complete Example Configuration

```python
# /etc/mirrormanager/mirrormanager2.cfg

from datetime import timedelta

#################
# Core Settings #
#################

SQLALCHEMY_DATABASE_URI = "postgresql://mm2:password@localhost:5432/mirrormanager2"
SECRET_KEY = "change-me-in-production-to-random-string"
PASSWORD_SEED = "also-change-this-to-something-random"

###################
# Session/Cookies #
###################

PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
MM_COOKIE_REQUIRES_HTTPS = True
MM_COOKIE_NAME = "MirrorManager"
CHECK_SESSION_IP = True

##################
# Authentication #
##################

MM_AUTHENTICATION = "fas"
OIDC_CLIENT_SECRETS = "/etc/mirrormanager/client_secrets.json"
ADMIN_GROUP = ["sysadmin-main", "sysadmin-web"]

######################
# Email/Notifications #
######################

ADMIN_EMAIL = "admin@fedoraproject.org"
EMAIL_FROM = "mirrormanager@fedoraproject.org"
SMTP_SERVER = "smtp.fedoraproject.org"
USE_FEDORA_MESSAGING = True

###########
# GeoIP   #
###########

GEOIP_BASE = "/usr/share/GeoIP"
EMBARGOED_COUNTRIES = ["CU", "IR", "KP", "SD", "SY"]

####################
# Mirror Management #
####################

MASTER_RSYNC_ACL = False
MM_PROTOCOL_REGEX = "^(?!ftp)(.*)$"
MM_IPV4_NETBLOCK_SIZE = "/16"
MM_IPV6_NETBLOCK_SIZE = "/32"

###########
# Logging #
###########

MM_LOG_DIR = "/var/log/mirrormanager"

###########
# Crawler #
###########

CRAWLER_RSYNC_PARAMETERS = "--no-motd --timeout 14400"
CRAWLER_AUTO_DISABLE = 4

########
# UMDL #
########

UMDL_PREFIX = ""
UMDL_MASTER_DIRECTORIES = [
    {
        "category": "Fedora Linux",
        "path": "/srv/pub/fedora/linux",
    },
    {
        "category": "Fedora Archive",
        "path": "/srv/pub/archive/fedora/linux",
    },
    {
        "category": "EPEL",
        "path": "/srv/pub/epel",
    },
]
MAX_STALE_DAYS = 4
SKIP_PATHS_FOR_VERSION = ["pub/alt"]

###############
# Statistics  #
###############

ACCESS_STATS_KEEP_DAYS = 30
PROPAGATION_KEEP_DAYS = 7
PROPAGATION_BASE = "/var/lib/mirrormanager/statistics/data/propagation"

######
# UI #
######

THEME_FOLDER = "fedora"
ITEMS_PER_PAGE = 20
SHOW_MAPS = True
SHOW_PROPAGATION = True
STATIC_MAP = "map.png"
INTERACTIVE_MAP = "mirrors.html"

####################
# External Services #
####################

BODHI_URL = "https://bodhi.fedoraproject.org"
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MM2_CONFIG` | Path to configuration file |

The config file path can also be passed via `--config` to CLI tools.
