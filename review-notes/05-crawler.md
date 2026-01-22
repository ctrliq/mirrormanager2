# MirrorManager2 Crawler Deep Dive

This document provides detailed information about the mirror crawler component.

## Overview

The crawler is responsible for checking if public mirrors have up-to-date content. It compares the files on mirrors against what the UMDL has recorded from the master mirror.

## Source Files

| File | Purpose | Lines |
|------|---------|-------|
| [mirrormanager2/crawler/cli.py](../mirrormanager2/crawler/cli.py) | CLI interface | 333 |
| [mirrormanager2/crawler/crawler.py](../mirrormanager2/crawler/crawler.py) | Core crawl logic | 603 |
| [mirrormanager2/crawler/connector.py](../mirrormanager2/crawler/connector.py) | Protocol abstraction | - |
| [mirrormanager2/crawler/ftp_connector.py](../mirrormanager2/crawler/ftp_connector.py) | FTP support | - |
| [mirrormanager2/crawler/http_connector.py](../mirrormanager2/crawler/http_connector.py) | HTTP/HTTPS support | - |
| [mirrormanager2/crawler/rsync_connector.py](../mirrormanager2/crawler/rsync_connector.py) | Rsync support | - |
| [mirrormanager2/crawler/connection_pool.py](../mirrormanager2/crawler/connection_pool.py) | Connection reuse | - |
| [mirrormanager2/crawler/threads.py](../mirrormanager2/crawler/threads.py) | Thread management | - |
| [mirrormanager2/crawler/states.py](../mirrormanager2/crawler/states.py) | Status enums | - |
| [mirrormanager2/crawler/reporter.py](../mirrormanager2/crawler/reporter.py) | Result storage | - |
| [mirrormanager2/crawler/continents.py](../mirrormanager2/crawler/continents.py) | Continent validation | - |
| [mirrormanager2/crawler/log.py](../mirrormanager2/crawler/log.py) | Logging setup | - |
| [mirrormanager2/crawler/ui.py](../mirrormanager2/crawler/ui.py) | Rich terminal UI | - |
| [mirrormanager2/crawler/notif.py](../mirrormanager2/crawler/notif.py) | Notifications | - |
| [mirrormanager2/crawler/utils.py](../mirrormanager2/crawler/utils.py) | Utilities | - |
| [mirrormanager2/crawler/constants.py](../mirrormanager2/crawler/constants.py) | Constants | - |

---

## CLI Interface

**Entry Point:** [mirrormanager2/crawler/cli.py](../mirrormanager2/crawler/cli.py)

### Command Group Structure
```
mm2_crawler [OPTIONS] COMMAND
  ├── crawl [OPTIONS]      # Full directory crawl
  └── propagation [OPTIONS] # Repodata freshness check
```

### Global Options (applies to all commands)
From [cli.py lines 37-142](../mirrormanager2/crawler/cli.py#L37-L142):

| Option | Default | Description |
|--------|---------|-------------|
| `--config` | `/etc/mirrormanager/mirrormanager2.cfg` | Config file |
| `--include-private` | False | Include private hosts |
| `--include-disabled` | False | Include disabled hosts |
| `--category` | All | Category to crawl (can repeat) |
| `--threads` | `min(100, cpu_count * 20)` | Thread count |
| `--global-timeout` | 4 hours | Total crawl timeout |
| `--host-timeout` | None | Per-host timeout |
| `--startid` | 0 | Start at host ID |
| `--stopid` | 0 | Stop before host ID |
| `--fraction` | "1:1" | Crawl fraction (e.g., "1:3") |
| `--disable-fedmsg` | False | Disable messaging |
| `--continent` | All | Filter by continent |
| `--debug` | False | Debug output |
| `--no-fail` | False | Always exit 0 |

### Crawl Subcommand Options
From [cli.py lines 243-259](../mirrormanager2/crawler/cli.py#L243-L259):

| Option | Description |
|--------|-------------|
| `--canary` | Only check if mirror is reachable |
| `--repodata` | Only check repodata freshness |

### Propagation Subcommand Options
From [cli.py lines 273-280](../mirrormanager2/crawler/cli.py#L273-L280):

| Option | Description |
|--------|-------------|
| `--product` | Product to check |
| `--version` | Version to check |

---

## Core Crawler Logic

**File:** [mirrormanager2/crawler/crawler.py](../mirrormanager2/crawler/crawler.py)

### Crawler Class
Located at [crawler.py lines 97-150](../mirrormanager2/crawler/crawler.py#L97-L150):

```python
class Crawler:
    def __init__(self, config, session, options, progress, host):
        self.config = config
        self.options = options
        self.session = session
        self.progress = progress
        self.host = host
        self.connection_pool = ConnectionPool(config, ...)
        self.timeout = ThreadTimeout(options["host_timeout"])
        self.host_category_dirs = {}
```

### Protocol Selection
From [crawler.py lines 79-95](../mirrormanager2/crawler/crawler.py#L79-L95):

```python
def get_preferred_urls(host_category):
    """Return which connection method to use: rsync > ftp > http > https"""
    urls = [hcurl.url for hcurl in host_category.urls if hcurl.url is not None]
    
    def _preferred_method(url):
        if url.startswith("rsync:"):
            return 1
        elif url.startswith("ftp:"):
            return 2
        elif url.startswith("http:"):
            return 3
        elif url.startswith("https:"):
            return 4
        else:
            return 5
    
    urls.sort(key=_preferred_method)
    return urls
```

**Note:** Rsync is preferred because it's more efficient for listing directories.

### Crawl Statistics
Defined at [crawler.py lines 44-60](../mirrormanager2/crawler/crawler.py#L44-L60):

```python
@dataclasses.dataclass
class CrawlStats:
    total_directories: int = 0
    up2date: int = 0
    not_up2date: int = 0
    unchanged: int = 0
    unreadable: int = 0
    unknown: int = 0
    hcds_created: int = 0
    hcds_deleted: int = 0
```

### Crawl Result
Defined at [crawler.py lines 63-73](../mirrormanager2/crawler/crawler.py#L63-L73):

```python
@dataclasses.dataclass
class CrawlResult:
    host_id: int
    host_name: str
    status: str
    details: str
    finished_at: datetime.datetime
    duration: int
    stats: CrawlStats | None = None
```

---

## Connectors (Protocol Handlers)

### Base Connector
**File:** [mirrormanager2/crawler/connector.py](../mirrormanager2/crawler/connector.py)

Abstract interface that all connectors implement:
- `connect()` - Establish connection
- `list_directory()` - Get directory listing
- `get_file()` - Download file content
- `disconnect()` - Close connection

### Rsync Connector
**File:** [mirrormanager2/crawler/rsync_connector.py](../mirrormanager2/crawler/rsync_connector.py)

Uses rsync subprocess to list directories. Most efficient for crawling.

### HTTP/HTTPS Connector  
**File:** [mirrormanager2/crawler/http_connector.py](../mirrormanager2/crawler/http_connector.py)

Parses HTML directory listings or uses HTTP HEAD requests.

### FTP Connector
**File:** [mirrormanager2/crawler/ftp_connector.py](../mirrormanager2/crawler/ftp_connector.py)

Uses Python's ftplib.

---

## Thread Pool

**File:** [mirrormanager2/crawler/threads.py](../mirrormanager2/crawler/threads.py)

### Key Functions/Classes

#### `run_in_threadpool()`
Executes crawl workers in parallel using `ThreadPoolExecutor`.

#### `GlobalTimeoutError`
Raised when the global timeout is exceeded.

#### `HostTimeoutError`
Raised when a single host takes too long.

#### `ThreadTimeout`
Context manager for per-host timeouts.

---

## Crawl States

**File:** [mirrormanager2/crawler/states.py](../mirrormanager2/crawler/states.py)

### CrawlStatus
Possible outcomes for a host crawl:
- `SUCCESS` - Crawl completed
- `FAILED` - Crawl failed
- `TIMEOUT` - Host timed out
- `SKIPPED` - Host was skipped

### SyncStatus
Directory sync status:
- `UP_TO_DATE` - Directory matches master
- `NOT_UP_TO_DATE` - Directory is stale
- `UNCHANGED` - No change since last crawl
- `UNREADABLE` - Directory not accessible

### PropagationStatus
For propagation checks:
- `SAME_DAY` - Repomd.xml is from today
- `ONE_DAY` - 1 day old
- `TWO_DAY` - 2 days old
- `OLDER` - More than 2 days old
- `NO_INFO` - Unknown

---

## Continent Validation

**File:** [mirrormanager2/crawler/continents.py](../mirrormanager2/crawler/continents.py)

The crawler validates that mirrors are actually in their claimed continent.

### Exceptions
- `WrongContinent` - Mirror's IP geolocates to different continent
- `EmbargoedCountry` - Mirror is in embargoed country
- `BrokenBaseUrl` - Cannot resolve mirror URL

---

## Crawl Flow

### 1. Host Selection
From [cli.py lines 147-192](../mirrormanager2/crawler/cli.py#L147-L192):

```python
hosts = get_mirrors(
    session,
    private=False,
    order_by_crawl_duration=True,  # Fast mirrors first
    admin_active=True,
    user_active=True,
    site_private=False,
    site_user_active=True,
    site_admin_active=True,
    category_ids=category_ids or None,
)
```

### 2. Fraction Splitting
For running multiple crawler instances:
```bash
# Instance 1
mm2_crawler --fraction 1:3 crawl
# Instance 2
mm2_crawler --fraction 2:3 crawl
# Instance 3
mm2_crawler --fraction 3:3 crawl
```

### 3. Thread Pool Execution
From [cli.py lines 204-233](../mirrormanager2/crawler/cli.py#L204-L233):

```python
with Progress(console=ctx_obj["console"], refresh_per_second=1) as progress:
    task_global = progress.add_task(f"Crawling {len(host_ids)} mirrors", ...)
    threads_results = run_in_threadpool(
        worker,
        host_ids,
        fn_args=(options, config, progress),
        timeout=options["global_timeout"],
        executor_kwargs={"max_workers": options["threads"]},
    )
    for result in threads_results:
        progress.advance(task_global)
        results.append(result)
```

### 4. Per-Host Crawl
For each host:
1. Select categories to crawl
2. Get preferred URLs (rsync > ftp > http > https)
3. Connect to mirror
4. List directories
5. Compare files against database
6. Update `HostCategoryDir.up2date`
7. Store results

### 5. Result Storage
From [cli.py lines 261-271](../mirrormanager2/crawler/cli.py#L261-L271):

Results stored via [reporter.py](../mirrormanager2/crawler/reporter.py):
- Updates `Host.last_crawled`
- Updates `Host.last_crawl_duration`
- Updates `HostCategoryDir.up2date` for each directory
- Increments `Host.crawl_failures` on failure
- Auto-disables host if failures exceed `CRAWLER_AUTO_DISABLE`

---

## Configuration Options

From [default_config.py](../mirrormanager2/default_config.py):

| Option | Default | Description |
|--------|---------|-------------|
| `CRAWLER_RSYNC_PARAMETERS` | `--no-motd --timeout 14400` | Extra rsync args |
| `CRAWLER_AUTO_DISABLE` | 4 | Failures before auto-disable |
| `MM_LOG_DIR` | `/var/log/mirrormanager` | Per-host logs |

---

## Propagation Checking

The `propagation` subcommand only checks repomd.xml freshness.

### What It Does
1. Gets list of active versions from Bodhi
2. For each (product, version, arch), checks repomd.xml
3. Compares timestamp to determine freshness
4. Stores results in `PropagationStat` table

### Statistics Generated
- `same_day` - How many mirrors have today's repomd.xml
- `one_day` - 1 day old
- `two_day` - 2 days old  
- `older` - More than 2 days old
- `no_info` - Unknown

---

## Logging

### Console Output
Uses Rich library for:
- Progress bars
- Colored output
- Table formatting

### Per-Host Logs
If `MM_LOG_DIR` is set, creates `<log_dir>/crawler/<host_id>.log` for each host.

From [crawler/log.py](../mirrormanager2/crawler/log.py).

---

## Example Commands

```bash
# Full crawl with debug output
mm2_crawler --config /etc/mm2.cfg --debug crawl

# Fast canary crawl (just check reachability)
mm2_crawler --config /etc/mm2.cfg crawl --canary

# Crawl only European mirrors
mm2_crawler --config /etc/mm2.cfg --continent EU crawl

# Crawl only Fedora Linux category
mm2_crawler --config /etc/mm2.cfg --category "Fedora Linux" crawl

# Propagation check for Fedora 41
mm2_crawler --config /etc/mm2.cfg propagation --product Fedora --version 41

# Crawl with limited threads and timeout
mm2_crawler --config /etc/mm2.cfg --threads 50 --host-timeout 10 crawl
```
