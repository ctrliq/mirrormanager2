# MirrorManager2 Database Models

This document details the database schema and SQLAlchemy models.

## Model Location
- [mirrormanager2/lib/model.py](../mirrormanager2/lib/model.py) - All ORM models (1100 lines)
- [mirrormanager2/lib/database.py](../mirrormanager2/lib/database.py) - Database configuration
- [doc/database_schema.md](../doc/database_schema.md) - Auto-generated ERD diagram

## Core Entity Relationships

```
Site (organization)
  └── Host (physical/virtual server)
        └── HostCategory (what content this host mirrors)
              ├── HostCategoryDir (directory sync status)
              └── HostCategoryUrl (access URLs for this category)

Product (e.g., "Fedora")
  ├── Version (e.g., "40", "41")
  └── Category (e.g., "Fedora Linux", "Fedora Archive")
        └── Directory (filesystem paths)
              ├── FileDetail (specific files with checksums)
              └── Repository (yum repo mapping)
```

---

## Core Models

### Site
**File:** [model.py lines 40-68](../mirrormanager2/lib/model.py#L40-L68)

Represents an organization that operates mirrors.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | Text | Organization name |
| `password` | Text | For report_mirror authentication |
| `org_url` | Text | Organization website |
| `private` | Boolean | Private site (not in public lists) |
| `admin_active` | Boolean | Enabled by MM admin |
| `user_active` | Boolean | Enabled by site admin |
| `created_at` | DateTime | Creation timestamp |
| `created_by` | Text | Username who created |
| `all_sites_can_pull_from_me` | Boolean | Allow downstream syncing |
| `email_on_drop` | Boolean | Notify on mirror removal |
| `email_on_add` | Boolean | Notify on mirror addition |

**Relationships:**
- `hosts` → Host (one-to-many)
- `admins` → SiteAdmin (one-to-many)

---

### Host
**File:** [model.py lines 78-172](../mirrormanager2/lib/model.py#L78-L172)

A physical or virtual server that mirrors content.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | Text | Hostname |
| `site_id` | FK(Site) | Parent site |
| `robot_email` | Text | Contact email |
| `admin_active` | Boolean | Enabled by MM admin |
| `user_active` | Boolean | Enabled by site admin |
| `country` | Text | 2-letter country code |
| `bandwidth_int` | Integer | Bandwidth in Mbps |
| `last_checked_in` | DateTime | Last report_mirror checkin |
| `last_crawled` | DateTime | Last crawler visit |
| `last_crawl_duration` | BigInteger | Crawl time in seconds |
| `crawl_failures` | Integer | Consecutive failures |
| `disable_reason` | Text | Why disabled |
| `private` | Boolean | Private mirror |
| `internet2` | Boolean | On Internet2 network |
| `asn` | Integer | Autonomous System Number |
| `max_connections` | Integer | Max concurrent connections |
| `latitude` | Float | GeoIP latitude |
| `longitude` | Float | GeoIP longitude |

**Relationships:**
- `site` → Site (many-to-one)
- `categories` → HostCategory (one-to-many)
- `acl_ips` → HostAclIp (one-to-many)
- `netblocks` → HostNetblock (one-to-many)
- `countries_allowed` → HostCountryAllowed (one-to-many)
- `peer_asns` → HostPeerAsn (one-to-many)
- `locations` → HostLocation (one-to-many)

---

### Product
**File:** [model.py lines 370-391](../mirrormanager2/lib/model.py#L370-L391)

Top-level product (e.g., "Fedora", "EPEL").

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | Text | Product name (unique) |
| `publiclist` | Boolean | Show in public listings |

**Relationships:**
- `categories` → Category (one-to-many)
- `versions` → Version (one-to-many)

---

### Category
**File:** [model.py lines 418-472](../mirrormanager2/lib/model.py#L418-L472)

Top-level mirroring category (e.g., "Fedora Linux", "Fedora Archive").

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | Text | Category name (unique) |
| `canonicalhost` | Text | Canonical download URL |
| `publiclist` | Boolean | Show in public listings |
| `geo_dns_domain` | Text | GeoDNS domain |
| `admin_only` | Boolean | Only admins can add |
| `product_id` | FK(Product) | Parent product |
| `topdir_id` | FK(Directory) | Top-level directory |

**Relationships:**
- `product` → Product (many-to-one)
- `topdir` → Directory (many-to-one)
- `directories` → Directory (many-to-many via CategoryDirectory)
- `repositories` → Repository (one-to-many)
- `host_categories` → HostCategory (one-to-many)

---

### Directory
**File:** [model.py lines 282-366](../mirrormanager2/lib/model.py#L282-L366)

Represents a filesystem directory on the master mirror.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | Text | Full path (e.g., "pub/fedora/linux") |
| `files` | JSON/Pickle | Dict of filename → {size, stat} |
| `readable` | Boolean | Is directory accessible |
| `ctime` | BigInteger | Change time (for UMDL detection) |

**Relationships:**
- `categories` → Category (many-to-many)
- `repositories` → Repository (one-to-many)
- `fileDetails` → FileDetail (one-to-many)
- `host_category_dirs` → HostCategoryDir (one-to-many)

**Special Method:** `age_file_details()` - Removes old FileDetail entries.

---

### Repository
**File:** [model.py lines 726-787](../mirrormanager2/lib/model.py#L726-L787)

Maps a yum repository name to a directory (for mirrorlist/metalink).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | Text | Repository name (unique) |
| `prefix` | Text | Repo prefix (e.g., "fedora-40") |
| `category_id` | FK(Category) | Parent category |
| `version_id` | FK(Version) | Version this repo belongs to |
| `arch_id` | FK(Arch) | Architecture |
| `directory_id` | FK(Directory) | Physical directory |
| `disabled` | Boolean | Repository disabled |

**Relationships:**
- `category` → Category (many-to-one)
- `version` → Version (many-to-one)
- `arch` → Arch (many-to-one)
- `directory` → Directory (many-to-one)
- `propagation_stats` → PropagationStat (one-to-many)

---

### FileDetail
**File:** [model.py lines 800-825](../mirrormanager2/lib/model.py#L800-L825)

Detailed file information for freshness checking.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `filename` | Text | File name |
| `timestamp` | BigInteger | File modification time |
| `size` | BigInteger | File size in bytes |
| `sha1` | Text | SHA1 checksum |
| `md5` | Text | MD5 checksum |
| `sha256` | Text | SHA256 checksum |
| `sha512` | Text | SHA512 checksum |
| `directory_id` | FK(Directory) | Parent directory |

---

### HostCategory
**File:** [model.py lines 504-546](../mirrormanager2/lib/model.py#L504-L546)

Links a Host to a Category it mirrors.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `host_id` | FK(Host) | Host |
| `category_id` | FK(Category) | Category being mirrored |
| `always_up2date` | Boolean | Skip freshness checking |

**Relationships:**
- `host` → Host (many-to-one)
- `category` → Category (many-to-one)
- `directories` → HostCategoryDir (one-to-many)
- `urls` → HostCategoryUrl (one-to-many)

---

### HostCategoryDir
**File:** [model.py lines 549-580](../mirrormanager2/lib/model.py#L549-L580)

Tracks per-directory sync status for a host's category.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `host_category_id` | FK(HostCategory) | Parent host category |
| `path` | Text | Relative path |
| `up2date` | Boolean | Is this directory up to date? |
| `directory_id` | FK(Directory) | Reference to master directory |

This is the key table the crawler updates!

---

### HostCategoryUrl
**File:** [model.py lines 595-615](../mirrormanager2/lib/model.py#L595-L615)

Access URLs for a host category (http, https, ftp, rsync).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `host_category_id` | FK(HostCategory) | Parent |
| `url` | Text | Full URL (e.g., "https://mirror.example.com/fedora") |
| `private` | Boolean | Private URL |

---

## Supporting Models

### Version
**File:** [model.py lines 699-723](../mirrormanager2/lib/model.py#L699-L723)

Product version (e.g., "40", "41", "rawhide").

### Arch
**File:** [model.py lines 685-697](../mirrormanager2/lib/model.py#L685-L697)

Architecture (e.g., "x86_64", "aarch64").

### Country
**File:** [model.py lines 71-76](../mirrormanager2/lib/model.py#L71-L76)

Country codes.

### Location
**File:** [model.py lines 874-884](../mirrormanager2/lib/model.py#L874-L884)

Logical locations for grouping hosts (e.g., AWS regions).

### NetblockCountry
**File:** [model.py lines 930-936](../mirrormanager2/lib/model.py#L930-L936)

Maps IP netblocks to countries.

### EmbargoedCountry
**File:** [model.py lines 850-854](../mirrormanager2/lib/model.py#L850-L854)

Countries excluded from mirror service.

---

## Statistics Models

### AccessStat / AccessStatCategory
**File:** [model.py lines 1054-1084](../mirrormanager2/lib/model.py#L1054-L1084)

Mirror access statistics.

### PropagationStat
**File:** [model.py lines 1087-1100](../mirrormanager2/lib/model.py#L1087-L1100)

Repository propagation statistics.

| Column | Type | Description |
|--------|------|-------------|
| `repository_id` | FK(Repository) | Repository |
| `datetime` | DateTime | When measured |
| `same_day` | Integer | Mirrors with same-day content |
| `one_day` | Integer | 1-day old content |
| `two_day` | Integer | 2-day old content |
| `older` | Integer | Older content |
| `no_info` | Integer | Unknown freshness |

---

## Local Authentication Models

Only used with `MM_AUTHENTICATION = "local"`:

### User
**File:** [model.py lines 1006-1051](../mirrormanager2/lib/model.py#L1006-L1051)

### Group
**File:** [model.py lines 958-981](../mirrormanager2/lib/model.py#L958-L981)

### UserGroup
**File:** [model.py lines 984-1003](../mirrormanager2/lib/model.py#L984-L1003)

### UserVisit
**File:** [model.py lines 941-955](../mirrormanager2/lib/model.py#L941-L955)

---

## Database Operations

### Migrations
- Located in: [mirrormanager2/lib/migrations/](../mirrormanager2/lib/migrations/)
- Uses Alembic via sqlalchemy-helpers

### Initialize Database
```bash
poetry run flask -A mirrormanager2.app db sync
```

### Custom File Storage
The `Directory.files` column uses a custom `JsonDictTypeFilter` type ([model.py lines 243-279](../mirrormanager2/lib/model.py#L243-L279)) that:
- Stores as JSON: `[{"name": filename, "size": int, "timestamp": int}, ...]`
- Returns as dict: `{filename: {"size": int, "stat": timestamp}, ...}`
- Supports legacy pickle format for backwards compatibility
