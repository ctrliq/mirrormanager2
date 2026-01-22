# MirrorManager2 Backend Utilities

This document details all CLI utilities (cron jobs/backend scripts) that run alongside the web application.

## Utility Location

All utilities are in [mirrormanager2/utility/](../mirrormanager2/utility/) directory.

---

## Critical Path Utilities

These are essential for MirrorManager to function properly.

### 1. `mm2_update-master-directory-list` (UMDL)

**File:** [mirrormanager2/utility/update_master_directory_list.py](../mirrormanager2/utility/update_master_directory_list.py)  
**Lines:** 816 total  
**Typical Schedule:** Cron, runs frequently (every few minutes in production)

#### Purpose
Scans the master mirror (NFS mount at `/srv`) to update the database with current file/directory information.

#### What It Does
1. Walks the master mirror filesystem
2. Detects changed directories by comparing `ctime` to database value
3. Updates `Directory.files` with current file listings
4. Creates `FileDetail` entries with checksums for key files
5. Creates `Repository` entries when it finds yum repos (repodata/repomd.xml)
6. Removes directories that no longer exist

#### Key Classes
- `DirSynchronizer` ([line 105](../mirrormanager2/utility/update_master_directory_list.py#L105)) - Base sync logic
- `short_filelist()` ([line 76](../mirrormanager2/utility/update_master_directory_list.py#L76)) - Limits tracked files

#### Usage
```bash
mm2_update-master-directory-list \
  --config /etc/mirrormanager/mirrormanager2.cfg \
  --category "Fedora Linux"
```

#### Config Options Used
- `UMDL_PREFIX` - Prefix for master directory
- `UMDL_MASTER_DIRECTORIES` - List of directories to scan
- `MAX_STALE_DAYS` - How long to keep old FileDetail entries

---

### 2. `mm2_crawler`

**File:** [mirrormanager2/crawler/cli.py](../mirrormanager2/crawler/cli.py)  
**Lines:** 333 total (CLI), 603 (crawler.py)  
**Typical Schedule:** Cron, multiple times daily with different fractions

#### Purpose
Crawls public mirrors to check if they have up-to-date content compared to master mirror.

#### What It Does
1. Queries database for active, public mirrors
2. For each mirror, connects via rsync/http/ftp
3. Compares file listings against `Directory.files` in database
4. Updates `HostCategoryDir.up2date` status
5. Records crawl results and duration
6. Auto-disables mirrors after repeated failures

#### Subcommands
- `crawl` - Full crawl checking all directories
- `propagation` - Only checks repomd.xml freshness

#### Key Options
From [cli.py lines 37-142](../mirrormanager2/crawler/cli.py#L37-L142):

| Option | Description |
|--------|-------------|
| `--threads N` | Parallel threads (default: min(100, cpu*20)) |
| `--global-timeout M` | Total timeout in minutes |
| `--host-timeout M` | Per-host timeout in minutes |
| `--fraction 1:3` | Crawl first third of mirrors |
| `--continent EU` | Only crawl European mirrors |
| `--include-private` | Include private mirrors |
| `--canary` | Only check if mirror is reachable |
| `--repodata` | Only check repodata freshness |

#### Usage
```bash
# Full crawl
mm2_crawler --config /etc/mirrormanager/mm2.cfg crawl

# Crawl first half of mirrors
mm2_crawler --config /etc/mirrormanager/mm2.cfg --fraction 1:2 crawl

# Propagation check
mm2_crawler --config /etc/mirrormanager/mm2.cfg propagation
```

---

### 3. `mm2_get-netblocks`

**File:** [mirrormanager2/utility/netblocks.py](../mirrormanager2/utility/netblocks.py)  
**Lines:** 165 total  
**Typical Schedule:** Daily or weekly

#### Purpose
Downloads BGP routing tables to map client IPs to ASNs for network-aware mirror selection.

#### What It Does
1. Downloads compressed BGP RIB data from routeviews.org
2. Parses MRT format routing tables
3. Outputs netblock → ASN mappings
4. Used by mirrorlist-server for network proximity matching

#### Data Sources
From [netblocks.py lines 36-41](../mirrormanager2/utility/netblocks.py#L36-L41):
- Global IPv4: `http://ftp.routeviews.org/dnszones/rib.bz2`
- IPv6: `http://archive.routeviews.org/route-views6/bgpdata/`
- Internet2: `http://routes.net.internet2.edu/bgp/RIBS/`

#### Usage
```bash
mm2_get-netblocks --config /etc/mirrormanager/mm2.cfg
mm2_get-netblocks --config /etc/mirrormanager/mm2.cfg --internet2
```

---

## Release Management Utilities

### 4. `mm2_move-devel-to-release`

**File:** [mirrormanager2/utility/move_devel_to_release.py](../mirrormanager2/utility/move_devel_to_release.py)  
**Lines:** 129 total  
**When:** ~1 week after Fedora release

#### Purpose
Redirects repository paths from development tree to release tree.

#### Why It's Needed
At release time, more mirrors have synced the development tree than the release tree. By pointing to development first, traffic is spread over more mirrors. After a week, most mirrors have the release tree, so we switch.

#### What It Changes
```
pub/fedora/linux/development/40/... → pub/fedora/linux/releases/40/...
```

#### Usage
```bash
mm2_move-devel-to-release \
  --config /etc/mirrormanager/mm2.cfg \
  --category "Fedora Linux" \
  --version 41
```

---

### 5. `mm2_move-to-archive`

**File:** [mirrormanager2/utility/move_to_archive.py](../mirrormanager2/utility/move_to_archive.py)  
**Lines:** 103 total  
**When:** After release reaches End-of-Life (EOL)

#### Purpose
Moves EOL release repositories to the archive category.

#### What It Does
1. Finds all repositories for specified product/version
2. Updates `Repository.directory` to point to archive location
3. Updates `Repository.category` to archive category

#### Usage
```bash
mm2_move-to-archive \
  --config /etc/mirrormanager/mm2.cfg \
  --product Fedora \
  --version 39 \
  --dry-run  # Preview changes first

mm2_move-to-archive \
  --config /etc/mirrormanager/mm2.cfg \
  --repository fedora-39-updates
```

---

## Statistics Utilities

### 6. `mm2_expire-stats`

**File:** [mirrormanager2/utility/expire_statistics.py](../mirrormanager2/utility/expire_statistics.py)  
**Typical Schedule:** Daily

#### Purpose
Removes old access statistics and propagation statistics from database.

#### Config Options
- `ACCESS_STATS_KEEP_DAYS` (default: 30)
- `PROPAGATION_KEEP_DAYS` (default: 7)

---

### 7. `mm2_mirrorlist-statistics`

**File:** [mirrormanager2/utility/mirrorlist_statistics.py](../mirrormanager2/utility/mirrorlist_statistics.py)  

#### Purpose
Generates statistics about mirrorlist usage.

---

### 8. `mm2_generate-worldmap`

**File:** [mirrormanager2/utility/generate_worldmap.py](../mirrormanager2/utility/generate_worldmap.py)  

#### Purpose
Generates world map visualizations of mirror locations.

#### Output
- Static map image (`map.png`)
- Interactive map (`mirrors.html`)

---

## Other Utilities

### 9. `mm2_add-product`

**File:** [mirrormanager2/utility/add_product.py](../mirrormanager2/utility/add_product.py)  

#### Purpose
Adds a new product to the database.

---

### 10. `mm2_create_install_repo`

**File:** [mirrormanager2/utility/create_install_repo.py](../mirrormanager2/utility/create_install_repo.py)  

#### Purpose
Creates install repository entries.

---

### 11. `mm2_upgrade-install-repo`

**File:** [mirrormanager2/utility/upgrade_install_repo.py](../mirrormanager2/utility/upgrade_install_repo.py)  

#### Purpose
Upgrades install repository entries for new versions.

---

### 12. `mm2_emergency-expire-repo`

**File:** [mirrormanager2/utility/emergency_expire_repo.py](../mirrormanager2/utility/emergency_expire_repo.py)  

#### Purpose
Emergency tool to expire old file details for a repository, forcing mirrors to be marked as not up-to-date until they have the newest files.

**Warning:** Use sparingly! This will temporarily make many mirrors appear outdated.

---

### 13. `mm2_last-sync`

**File:** [mirrormanager2/utility/last_sync.py](../mirrormanager2/utility/last_sync.py)  

#### Purpose
Reports when mirrors last synced.

---

### 14. `mm2_update-EC2-netblocks`

**File:** [mirrormanager2/utility/update_ec2_netblocks.py](../mirrormanager2/utility/update_ec2_netblocks.py)  

#### Purpose
Downloads and updates Amazon EC2 IP ranges to direct EC2 instances to Amazon-hosted mirrors.

---

## Cron Job Schedule Example

Based on Fedora Infrastructure SOP, a typical schedule might be:

```cron
# UMDL - scan master mirror
*/5 * * * * mm2_update-master-directory-list --config /etc/mm2.cfg

# Crawler - split into 3 parts throughout the day
0 1 * * * mm2_crawler --config /etc/mm2.cfg --fraction 1:3 crawl
0 9 * * * mm2_crawler --config /etc/mm2.cfg --fraction 2:3 crawl  
0 17 * * * mm2_crawler --config /etc/mm2.cfg --fraction 3:3 crawl

# Propagation check
0 * * * * mm2_crawler --config /etc/mm2.cfg propagation

# Netblocks
0 3 * * 0 mm2_get-netblocks --config /etc/mm2.cfg

# Statistics cleanup
0 4 * * * mm2_expire-stats --config /etc/mm2.cfg

# Generate mirrorlist cache (for mirrorlist-server)
55 * * * * generate-mirrorlist-cache
```

---

## Common Options

Most utilities share these common options via [mirrormanager2/utility/common.py](../mirrormanager2/utility/common.py):

| Option | Description |
|--------|-------------|
| `--config` / `-c` | Path to configuration file |
| `--debug` / `-d` | Enable debug output |
| `--dry-run` | Preview without making changes |
