# MirrorManager2 Components Deep Dive

## Component Inventory

This document details each major component of MirrorManager2, what it does, and what's needed to run it.

---

## 1. Web Application (Frontend)

**Purpose:** User and admin interface for managing mirror sites, hosts, and viewing mirror lists.

### Entry Point
- [mirrormanager2/app.py](../mirrormanager2/app.py#L49-L134) - `create_app()` factory function

### Key Files
| File | Purpose |
|------|---------|
| [mirrormanager2/app.py](../mirrormanager2/app.py) | Flask app factory, initializes all components |
| [mirrormanager2/views.py](../mirrormanager2/views.py) | Main user-facing routes (1339 lines) |
| [mirrormanager2/admin.py](../mirrormanager2/admin.py) | Flask-Admin model views |
| [mirrormanager2/api.py](../mirrormanager2/api.py) | REST API endpoints |
| [mirrormanager2/xml_rpc.py](../mirrormanager2/xml_rpc.py) | XML-RPC for report_mirror client |
| [mirrormanager2/auth.py](../mirrormanager2/auth.py) | OIDC authentication handling |
| [mirrormanager2/local_auth.py](../mirrormanager2/local_auth.py) | Local authentication (non-OIDC) |
| [mirrormanager2/perms.py](../mirrormanager2/perms.py) | Permission checking utilities |
| [mirrormanager2/forms.py](../mirrormanager2/forms.py) | WTForms form definitions |
| [mirrormanager2/health_checks.py](../mirrormanager2/health_checks.py) | Health check endpoints |

### Blueprints Registered
From [app.py lines 118-131](../mirrormanager2/app.py#L118-L131):
- `auth_views` - Authentication routes
- `base_views` - Main views (routes defined in views.py)
- `api_views` - API endpoints at `/api`
- `healthz` - Health checks at `/healthz`
- `XMLRPC` - XML-RPC at `/xmlrpc`

### Key Routes (from views.py)
| Route | Function | Description |
|-------|----------|-------------|
| `/` | `index()` | Homepage with product/arch listing |
| `/mirrors` | `list_mirrors()` | Public mirror listing |
| `/site/new` | `site_new()` | Register new mirror site |
| `/site/<id>` | `site_view()` | View/edit site |
| `/host/<id>` | `host_view()` | View/edit host |
| `/statistics` | Statistics pages |
| `/maps` | Mirror maps |
| `/propagation` | Propagation stats |

### Dependencies to Run
1. Database connection (PostgreSQL or SQLite)
2. OIDC provider (Fedora Accounts or local auth)
3. Configuration file (MM2_CONFIG env var)

### How to Run (Development)
```bash
poetry install
poetry run flask -A mirrormanager2.app db sync  # Initialize DB
poetry run ./runserver.py                        # Start dev server
```

---

## 2. Crawler (`mm2_crawler`)

**Purpose:** Crawl mirror servers to check if they are up-to-date with master mirror content.

### Entry Point
- [mirrormanager2/crawler/cli.py](../mirrormanager2/crawler/cli.py#L37-L146) - `main()` Click command group

### Key Files
| File | Purpose |
|------|---------|
| [mirrormanager2/crawler/cli.py](../mirrormanager2/crawler/cli.py) | CLI interface (333 lines) |
| [mirrormanager2/crawler/crawler.py](../mirrormanager2/crawler/crawler.py) | Core crawler logic (603 lines) |
| [mirrormanager2/crawler/connector.py](../mirrormanager2/crawler/connector.py) | Protocol abstraction |
| [mirrormanager2/crawler/ftp_connector.py](../mirrormanager2/crawler/ftp_connector.py) | FTP crawler |
| [mirrormanager2/crawler/http_connector.py](../mirrormanager2/crawler/http_connector.py) | HTTP/HTTPS crawler |
| [mirrormanager2/crawler/rsync_connector.py](../mirrormanager2/crawler/rsync_connector.py) | Rsync crawler |
| [mirrormanager2/crawler/connection_pool.py](../mirrormanager2/crawler/connection_pool.py) | Connection pooling |
| [mirrormanager2/crawler/threads.py](../mirrormanager2/crawler/threads.py) | Thread pool management |
| [mirrormanager2/crawler/states.py](../mirrormanager2/crawler/states.py) | Crawl status enums |
| [mirrormanager2/crawler/reporter.py](../mirrormanager2/crawler/reporter.py) | Result storage |
| [mirrormanager2/crawler/ui.py](../mirrormanager2/crawler/ui.py) | Rich terminal UI |

### Subcommands
From [cli.py](../mirrormanager2/crawler/cli.py#L243-L280):
- `crawl` - Full mirror crawl
- `propagation` - Check repodata propagation

### CLI Options
Key options from [cli.py lines 37-96](../mirrormanager2/crawler/cli.py#L37-L96):
- `--config` - Config file path
- `--include-private` - Include private hosts
- `--category` - Filter by category
- `--threads` - Thread count (default: min(100, cpu_count * 20))
- `--global-timeout` - Total crawl timeout
- `--host-timeout` - Per-host timeout
- `--startid/--stopid` - Host ID range
- `--fraction` - Crawl a fraction of mirrors (e.g., "1:3" for first third)
- `--continent` - Filter by continent

### How to Run
```bash
mm2_crawler --config /etc/mirrormanager/mirrormanager2.cfg crawl
mm2_crawler --config /etc/mirrormanager/mirrormanager2.cfg propagation
```

### Protocol Priority
From [crawler.py lines 79-95](../mirrormanager2/crawler/crawler.py#L79-L95):
1. rsync (preferred)
2. ftp
3. http
4. https

---

## 3. Update Master Directory List (UMDL)

**Purpose:** Scan the master mirror (NFS mount) to update database with current file/directory information.

### Entry Point
- [mirrormanager2/utility/update_master_directory_list.py](../mirrormanager2/utility/update_master_directory_list.py#L1-L816)

### How It Works
From [doc/structure.rst lines 100-112](../doc/structure.rst#L100-L112):
1. Browses local copy of mirror content (NFS mount)
2. Updates database for each file/folder found
3. For directories with many files, keeps 3 most recent
4. For directories with few files, tracks all
5. Creates Repository objects for yum repos (maps repo name to directory)

### Key Classes
- `DirSynchronizer` - Base directory sync logic ([line 105](../mirrormanager2/utility/update_master_directory_list.py#L105))
- `short_filelist()` - Reduces file tracking for large directories ([line 76](../mirrormanager2/utility/update_master_directory_list.py#L76))

### How to Run
```bash
mm2_update-master-directory-list --config /etc/mirrormanager/mirrormanager2.cfg
```

---

## 4. Report Mirror Client

**Purpose:** Allows private mirrors to report their status directly to MirrorManager.

### Entry Point
- [client/report_mirror](../client/report_mirror#L1-L311)

### How It Works
From [client/report_mirror](../client/report_mirror#L57-L75):
1. Reads config file with site/host credentials
2. Walks local directory tree
3. Compresses and encodes data
4. Sends via XML-RPC to MirrorManager

### Server-Side Handler
- [mirrormanager2/xml_rpc.py](../mirrormanager2/xml_rpc.py#L44-L56) - `checkin()` function
- [mirrormanager2/lib/hostconfig.py](../mirrormanager2/lib/hostconfig.py#L1-L117) - Validates and processes config

### Config File Format
```ini
[global]
enabled = 1
server = https://mirrormanager.fedoraproject.org/xmlrpc

[site]
enabled = 1
name = My Mirror Site
password = secret

[host]
enabled = 1
name = mirror.example.com

[fedora-linux]
enabled = 1
path = /srv/mirror/fedora
```

---

## 5. MirrorList Server (EXTERNAL)

**⚠️ This is NOT in this repository!**

Lives at: https://github.com/adrianreber/mirrorlist-server

### How It Integrates
1. Backend generates `mirrorlist_cache.pkl` pickle file
2. File is synced to proxy servers
3. mirrorlist-server loads pickle and serves requests
4. Endpoints: `/mirrorlist` and `/metalink`

### Pickle Generation
A scheduled job runs `update-mirrorlist-cache` which:
1. Queries database for all mirror/directory/file data
2. Serializes to pickle format
3. Copies to proxy servers
4. Proxies restart mirrorlist containers to load new data

---

## 6. Netblocks Utilities

**Purpose:** Download BGP routing tables to match client IPs to ASNs for network-aware mirror selection.

### Entry Point
- [mirrormanager2/utility/netblocks.py](../mirrormanager2/utility/netblocks.py#L1-L165)

### Data Sources
From [netblocks.py lines 36-40](../mirrormanager2/utility/netblocks.py#L36-L40):
- Global: `http://ftp.routeviews.org/dnszones/rib.bz2`
- IPv6: `http://archive.routeviews.org/route-views6/bgpdata/`
- Internet2: `http://routes.net.internet2.edu/bgp/RIBS/`

### How to Run
```bash
mm2_get-netblocks --config /etc/mirrormanager/mirrormanager2.cfg
```

---

## 7. Release Management Utilities

### move-devel-to-release
**Purpose:** After a Fedora release, move repositories from development tree to release tree.

- [mirrormanager2/utility/move_devel_to_release.py](../mirrormanager2/utility/move_devel_to_release.py#L1-L129)
- Run ~1 week after release

```bash
mm2_move-devel-to-release --config /etc/mirrormanager/mirrormanager2.cfg --category "Fedora Linux" --version 41
```

### move-to-archive
**Purpose:** Move EOL releases to archive category.

- [mirrormanager2/utility/move_to_archive.py](../mirrormanager2/utility/move_to_archive.py#L1-L103)
- Run ~1 week after EOL

```bash
mm2_move-to-archive --config /etc/mirrormanager/mirrormanager2.cfg --product Fedora --version 39
```

---

## Component Dependencies Summary

| Component | Database | OIDC | Filesystem | Network |
|-----------|----------|------|------------|---------|
| Web App | ✅ | ✅ (or local) | Templates/Static | - |
| Crawler | ✅ | - | - | ✅ (to mirrors) |
| UMDL | ✅ | - | ✅ (NFS mount) | - |
| report_mirror | - | - | ✅ (local mirror) | ✅ (to MM) |
| MirrorList | - | - | ✅ (pickle) | - |
| Netblocks | ✅ | - | - | ✅ (BGP data) |
