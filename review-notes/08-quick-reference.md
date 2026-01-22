# MirrorManager2 Quick Reference Card

## Service Architecture Summary

```
┌────────────────────────────────────────────────────────────────┐
│                    MirrorManager2 System                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │  Web App     │   │   Crawler    │   │    UMDL      │       │
│  │  (Flask)     │   │ (mm2_crawler)│   │ (mm2_update- │       │
│  │              │   │              │   │ master-dir..)│       │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘       │
│         │                  │                  │                │
│         └──────────────────┼──────────────────┘                │
│                            │                                    │
│                            ▼                                    │
│                   ┌────────────────┐                           │
│                   │   Database     │                           │
│                   │  (PostgreSQL)  │                           │
│                   └────────────────┘                           │
│                            ▲                                    │
│                            │                                    │
│                   ┌────────────────┐      ┌─────────────────┐  │
│                   │  Mirrorlist    │◄─────│ generate-cache  │  │
│                   │  Cache (.pkl)  │      │ (cron job)      │  │
│                   └────────────────┘      └─────────────────┘  │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │   MirrorList Server         │
              │   (SEPARATE REPO!)          │
              │   Serves /mirrorlist        │
              │   and /metalink             │
              └─────────────────────────────┘
```

---

## Key Commands

| Command | Purpose |
|---------|---------|
| `poetry run ./runserver.py` | Start dev server |
| `poetry run flask -A mirrormanager2.app db sync` | Init/migrate database |
| `mm2_crawler crawl` | Crawl all mirrors |
| `mm2_crawler propagation` | Check repodata freshness |
| `mm2_update-master-directory-list` | Scan master mirror |
| `mm2_get-netblocks` | Update BGP data |
| `mm2_move-devel-to-release` | Post-release tree switch |
| `mm2_move-to-archive` | Move EOL release |
| `mm2_expire-stats` | Clean old statistics |

---

## Key Files

| File | Purpose |
|------|---------|
| [mirrormanager2/app.py](../mirrormanager2/app.py) | Flask app factory |
| [mirrormanager2/views.py](../mirrormanager2/views.py) | Web routes |
| [mirrormanager2/lib/model.py](../mirrormanager2/lib/model.py) | Database models |
| [mirrormanager2/lib/__init__.py](../mirrormanager2/lib/__init__.py) | Core library |
| [mirrormanager2/crawler/cli.py](../mirrormanager2/crawler/cli.py) | Crawler CLI |
| [mirrormanager2/crawler/crawler.py](../mirrormanager2/crawler/crawler.py) | Crawler logic |
| [mirrormanager2/utility/update_master_directory_list.py](../mirrormanager2/utility/update_master_directory_list.py) | UMDL |
| [mirrormanager2/default_config.py](../mirrormanager2/default_config.py) | Config defaults |

---

## Key Database Tables

| Table | Purpose |
|-------|---------|
| `site` | Organizations running mirrors |
| `host` | Individual mirror servers |
| `host_category` | What content a host mirrors |
| `host_category_dir` | Per-directory sync status |
| `host_category_url` | Access URLs (http/rsync/etc) |
| `directory` | Filesystem paths on master |
| `file_detail` | File checksums for freshness |
| `repository` | Yum repo → directory mapping |
| `product` / `version` / `arch` | Metadata |

---

## Typical Cron Schedule

```cron
# UMDL - every 5 minutes
*/5 * * * * mm2_update-master-directory-list -c /etc/mm2.cfg

# Crawler - 3 times daily (fractional)
0 2 * * *   mm2_crawler -c /etc/mm2.cfg --fraction 1:3 crawl
0 10 * * *  mm2_crawler -c /etc/mm2.cfg --fraction 2:3 crawl
0 18 * * *  mm2_crawler -c /etc/mm2.cfg --fraction 3:3 crawl

# Propagation - hourly
30 * * * *  mm2_crawler -c /etc/mm2.cfg propagation

# Generate mirrorlist cache - before the hour
55 * * * *  generate-mirrorlist-cache

# Weekly netblocks update
0 3 * * 0   mm2_get-netblocks -c /etc/mm2.cfg

# Daily stats cleanup
0 4 * * *   mm2_expire-stats -c /etc/mm2.cfg
```

---

## Key Config Options

```python
# Database
SQLALCHEMY_DATABASE_URI = "postgresql://..."

# Security (CHANGE THESE!)
SECRET_KEY = "random-secret"
PASSWORD_SEED = "another-secret"

# Authentication
MM_AUTHENTICATION = "fas"  # or "local"
ADMIN_GROUP = ["sysadmin-main"]

# Crawler
CRAWLER_RSYNC_PARAMETERS = "--no-motd --timeout 14400"
CRAWLER_AUTO_DISABLE = 4

# UMDL
UMDL_MASTER_DIRECTORIES = [
    {"category": "Fedora Linux", "path": "/srv/pub/fedora/linux"},
]
MAX_STALE_DAYS = 4

# GeoIP
GEOIP_BASE = "/usr/share/GeoIP"
EMBARGOED_COUNTRIES = ["CU", "IR", "KP", "SD", "SY"]
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Homepage |
| `/mirrors` | GET | Mirror listing |
| `/api/mirroradmins` | GET | List admins |
| `/api/repositories` | GET | List repos |
| `/xmlrpc` | POST | report_mirror checkin |
| `/healthz/live` | GET | Liveness probe |
| `/healthz/ready` | GET | Readiness probe |
| `/admin/*` | GET/POST | Flask-Admin (auth required) |

---

## Development Quick Start

```bash
# Clone
git clone https://github.com/fedora-infra/mirrormanager2
cd mirrormanager2

# Install
poetry install

# Initialize database (SQLite for dev)
poetry run flask -A mirrormanager2.app db sync

# Run server
poetry run ./runserver.py
# → http://localhost:5000
```

---

## External Dependencies

| Service | Purpose | Required For |
|---------|---------|--------------|
| PostgreSQL | Database | All |
| OIDC Provider | Authentication | Web (if fas mode) |
| NFS Mount | Master mirror access | UMDL |
| SMTP Server | Error alerts | Web |
| GeoIP Database | Location lookups | Crawler |
| BGP Data | Network proximity | MirrorList |
| mirrorlist-server | Serve /mirrorlist | End users |

---

## Related Repositories

| Repo | Purpose |
|------|---------|
| [mirrorlist-server](https://github.com/adrianreber/mirrorlist-server) | Serves /mirrorlist and /metalink |
| [mirrormanager-messages](https://github.com/fedora-infra/mirrormanager-messages) | Fedora Messaging schemas |
| [tiny-stage](https://github.com/fedora-infra/tiny-stage) | OIDC dev environment |
