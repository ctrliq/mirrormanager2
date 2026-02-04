# MirrorManager2 Sequence Diagrams

This document contains Mermaid UML sequence diagrams showing how the various components of MirrorManager2 interact.

## Table of Contents

1. [UMDL: Master Mirror Scanning](#1-umdl-master-mirror-scanning)
2. [Crawler: Mirror Freshness Checking](#2-crawler-mirror-freshness-checking)
3. [Web App: Mirror Registration](#3-web-app-mirror-registration)
4. [Report Mirror: Private Mirror Check-in](#4-report-mirror-private-mirror-check-in)
5. [Cache Generation & MirrorList Request](#5-cache-generation--mirrorlist-request)
6. [End-to-End: New Content Propagation](#6-end-to-end-new-content-propagation)

---

## 1. UMDL: Master Mirror Scanning

The Update Master Directory List (UMDL) process scans the master mirror filesystem and updates the database with current file information.

```mermaid
sequenceDiagram
    autonumber
    participant Cron
    participant UMDL as mm2_update-master-directory-list
    participant NFS as Master Mirror (NFS)
    participant DB as PostgreSQL Database

    Cron->>UMDL: Execute (every 5 min)
    UMDL->>DB: Load categories & existing directories
    
    loop For each category in UMDL_MASTER_DIRECTORIES
        UMDL->>NFS: Walk directory tree
        NFS-->>UMDL: Return file/dir listing with stats
        
        loop For each directory
            UMDL->>DB: Check Directory.ctime
            
            alt Directory changed (ctime different)
                UMDL->>NFS: Read directory contents
                NFS-->>UMDL: File list with sizes, timestamps
                
                alt >10 files of same type (.rpm, .html, etc)
                    UMDL->>UMDL: short_filelist() - keep 3 newest
                end
                
                UMDL->>DB: Update Directory.files (JSON)
                UMDL->>DB: Update Directory.ctime
                
                alt Contains repodata/repomd.xml
                    UMDL->>NFS: Read repomd.xml checksums
                    UMDL->>DB: Create/Update Repository record
                    UMDL->>DB: Create FileDetail with checksums
                end
            else Directory unchanged
                UMDL->>UMDL: Skip (no update needed)
            end
        end
    end
    
    UMDL->>DB: Remove orphaned directories
    UMDL->>DB: age_file_details() - remove old FileDetail entries
    UMDL-->>Cron: Exit
```

---

## 2. Crawler: Mirror Freshness Checking

The crawler checks if public mirrors have up-to-date content by comparing their files against the database (which reflects master mirror state).

```mermaid
sequenceDiagram
    autonumber
    participant Cron
    participant CLI as mm2_crawler CLI
    participant Pool as ThreadPool
    participant Crawler as Crawler Worker
    participant Mirror as Mirror Server
    participant DB as PostgreSQL Database

    Cron->>CLI: Execute with --fraction 1:3
    CLI->>DB: Query active, public hosts
    DB-->>CLI: Host list (ordered by crawl_duration)
    CLI->>CLI: Apply fraction filter (keep 1/3)
    
    CLI->>Pool: Create ThreadPoolExecutor(max_workers=N)
    
    par Parallel for each host
        Pool->>Crawler: Spawn worker thread
        Crawler->>DB: Load host categories & URLs
        DB-->>Crawler: HostCategory, HostCategoryUrl list
        
        Crawler->>Crawler: Select preferred URL (rsync > ftp > http > https)
        
        loop For each HostCategory
            Crawler->>DB: Load expected files from Directory.files
            DB-->>Crawler: Expected file dict
            
            Crawler->>Mirror: Connect (rsync/http/ftp)
            Mirror-->>Crawler: Connection established
            
            loop For each directory in category
                Crawler->>Mirror: List directory
                Mirror-->>Crawler: Actual file listing
                
                Crawler->>Crawler: Compare actual vs expected
                
                alt Files match
                    Crawler->>DB: Set HostCategoryDir.up2date = True
                else Files don't match
                    Crawler->>DB: Set HostCategoryDir.up2date = False
                end
            end
            
            Crawler->>Mirror: Disconnect
        end
        
        alt Crawl successful
            Crawler->>DB: Update Host.last_crawled
            Crawler->>DB: Update Host.last_crawl_duration
            Crawler->>DB: Reset Host.crawl_failures = 0
        else Crawl failed
            Crawler->>DB: Increment Host.crawl_failures
            alt crawl_failures >= CRAWLER_AUTO_DISABLE
                Crawler->>DB: Set Host.admin_active = False
            end
        end
        
        Crawler-->>Pool: Return CrawlResult
    end
    
    Pool-->>CLI: All results collected
    CLI->>CLI: Generate summary report
    CLI-->>Cron: Exit
```

---

## 3. Web App: Mirror Registration

Flow for a mirror administrator registering a new mirror site and host.

```mermaid
sequenceDiagram
    autonumber
    participant User as Mirror Admin
    participant Browser
    participant Flask as Flask Web App
    participant OIDC as Fedora Accounts (OIDC)
    participant DB as PostgreSQL Database
    participant FedMsg as Fedora Messaging

    User->>Browser: Navigate to mirrormanager.fedoraproject.org
    Browser->>Flask: GET /
    Flask-->>Browser: Homepage
    
    User->>Browser: Click "Login"
    Browser->>Flask: GET /login
    Flask->>OIDC: Redirect to OIDC provider
    OIDC-->>Browser: Login form
    User->>OIDC: Enter credentials
    OIDC-->>Flask: Auth callback with token
    Flask->>Flask: Store user in session (flask.g.fas_user)
    Flask-->>Browser: Redirect to homepage (logged in)
    
    User->>Browser: Click "Register a new site"
    Browser->>Flask: GET /site/new
    Flask-->>Browser: Site registration form
    
    User->>Browser: Fill form & submit
    Browser->>Flask: POST /site/new
    Flask->>DB: Create Site record
    Flask->>DB: Create SiteAdmin record (user as admin)
    Flask->>FedMsg: Publish site.added message
    Flask-->>Browser: Redirect to /site/{id}
    
    User->>Browser: Click "Add host"
    Browser->>Flask: GET /site/{id}/host/new
    Flask-->>Browser: Host registration form
    
    User->>Browser: Fill hostname, country, bandwidth
    Browser->>Flask: POST /site/{id}/host/new
    Flask->>DB: Create Host record
    Flask->>FedMsg: Publish host.added message
    Flask-->>Browser: Redirect to /host/{id}
    
    User->>Browser: Click "Add category"
    Browser->>Flask: GET /host/{id}/category/new
    Flask->>DB: Query available Categories
    Flask-->>Browser: Category selection form
    
    User->>Browser: Select "Fedora Linux", add URLs
    Browser->>Flask: POST /host/{id}/category/new
    Flask->>DB: Create HostCategory record
    Flask->>DB: Create HostCategoryUrl records (http, rsync, etc)
    Flask-->>Browser: Redirect to /host/{id}
    
    Note over User,DB: Mirror is now registered and will be crawled
```

---

## 4. Report Mirror: Private Mirror Check-in

Private mirrors use the `report_mirror` client to report their content directly, bypassing the crawler.

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Cron (on mirror)
    participant Client as report_mirror client
    participant FS as Local Filesystem
    participant Flask as Flask Web App (XML-RPC)
    participant HostConfig as hostconfig.py
    participant DB as PostgreSQL Database

    Cron->>Client: Execute report_mirror
    Client->>Client: Load config file (report_mirror.conf)
    
    Note over Client: Config contains site name, password, host name
    
    loop For each configured category
        Client->>FS: Walk directory tree
        FS-->>Client: File listing with timestamps
        Client->>Client: Build category dict
    end
    
    Client->>Client: Serialize to JSON
    Client->>Client: bz2 compress
    Client->>Client: base64 encode
    
    Client->>Flask: POST /xmlrpc (checkin method)
    
    Flask->>Flask: base64 decode
    Flask->>Flask: bz2 decompress
    Flask->>Flask: JSON parse
    
    Flask->>HostConfig: validate_config(config)
    HostConfig->>DB: Query Site by name
    DB-->>HostConfig: Site record
    
    alt Site password matches
        HostConfig->>DB: Query Host by name + site_id
        DB-->>HostConfig: Host record
        
        HostConfig->>HostConfig: read_host_config()
        
        loop For each category in config
            HostConfig->>DB: Query/Create HostCategory
            
            loop For each directory
                HostConfig->>DB: Query Directory by path
                DB-->>HostConfig: Directory record
                
                HostConfig->>HostConfig: Compare reported files vs Directory.files
                
                alt Files match expected
                    HostConfig->>DB: Set HostCategoryDir.up2date = True
                else Files differ
                    HostConfig->>DB: Set HostCategoryDir.up2date = False
                end
            end
        end
        
        HostConfig->>DB: Update Host.last_checked_in = now()
        HostConfig-->>Flask: Success response
    else Password mismatch
        HostConfig-->>Flask: Error: Authentication failed
    end
    
    Flask-->>Client: XML-RPC response
    Client-->>Cron: Exit
```

---

## 5. Cache Generation & MirrorList Request

This shows how data flows from MirrorManager2 database to end users requesting mirror lists.

```mermaid
sequenceDiagram
    autonumber
    participant Cron
    participant GenCache as generate-mirrorlist-cache (Rust)
    participant DB as PostgreSQL Database
    participant Proto as Protobuf File
    participant Sync as File Sync (rsync)
    participant Proxy as Proxy Server
    participant MLS as mirrorlist-server (Rust)
    participant User as End User (dnf/yum)

    Note over Cron,Proto: Cache Generation (runs at :55 each hour)
    
    Cron->>GenCache: Execute
    GenCache->>DB: Query all Hosts (active, public)
    DB-->>GenCache: Host records
    GenCache->>DB: Query all HostCategories
    DB-->>GenCache: HostCategory records
    GenCache->>DB: Query all HostCategoryDirs (up2date=True)
    DB-->>GenCache: HostCategoryDir records
    GenCache->>DB: Query all HostCategoryUrls
    DB-->>GenCache: URL records
    GenCache->>DB: Query all Directories
    DB-->>GenCache: Directory records
    GenCache->>DB: Query all FileDetails
    DB-->>GenCache: FileDetail records (checksums)
    GenCache->>DB: Query all Repositories
    DB-->>GenCache: Repository records
    GenCache->>DB: Query Netblocks, Countries, ASNs
    DB-->>GenCache: Network mapping data
    
    GenCache->>GenCache: Build MirrorList protobuf structure
    GenCache->>Proto: Write mirrorlist_cache.proto
    GenCache-->>Cron: Exit
    
    Note over Sync,Proxy: File Distribution
    
    Cron->>Sync: Sync cache to proxies
    Sync->>Proxy: rsync mirrorlist_cache.proto
    Proxy-->>Sync: Transfer complete
    
    Note over Proxy,MLS: Container Restart (at :15 each hour)
    
    Proxy->>MLS: Restart container
    MLS->>Proto: Load mirrorlist_cache.proto into RAM
    Proto-->>MLS: ~600MB data structure
    MLS->>MLS: Ready to serve requests
    
    Note over User,MLS: User Request Flow
    
    User->>MLS: GET /mirrorlist?repo=fedora-40&arch=x86_64
    MLS->>MLS: Parse request parameters
    MLS->>MLS: Lookup repo → directory mapping
    MLS->>MLS: Find mirrors with up2date=True for directory
    MLS->>MLS: GeoIP lookup client IP → country
    MLS->>MLS: Filter by country, then continent
    MLS->>MLS: Check netblock/ASN for network proximity
    MLS->>MLS: Sort by preference score
    MLS-->>User: Return ordered mirror URL list
    
    User->>User: Select top mirror
    User->>User: Download packages from mirror
```

---

## 6. End-to-End: New Content Propagation

This shows the complete lifecycle when new content (e.g., a new Fedora release) is published.

```mermaid
sequenceDiagram
    autonumber
    participant RelEng as Release Engineering
    participant Master as Master Mirror (NFS)
    participant UMDL as mm2_update-master-directory-list
    participant DB as PostgreSQL Database
    participant Mirrors as Public Mirrors
    participant Crawler as mm2_crawler
    participant GenCache as generate-mirrorlist-cache
    participant MLS as mirrorlist-server
    participant User as End User

    Note over RelEng,Master: T+0: Content Published
    
    RelEng->>Master: Push new release content
    Master-->>RelEng: Files written to NFS
    
    Note over UMDL,DB: T+5min: UMDL Detects Changes
    
    UMDL->>Master: Scan directories
    Master-->>UMDL: New/changed directories found
    UMDL->>DB: Create new Directory records
    UMDL->>DB: Create Repository records (from repomd.xml)
    UMDL->>DB: Create FileDetail records (checksums)
    
    Note over Mirrors,DB: T+30min to T+24hr: Mirrors Sync
    
    Mirrors->>Master: rsync new content
    Master-->>Mirrors: Transfer files
    
    Note over Crawler,DB: T+8hr: Crawler Runs
    
    Crawler->>DB: Load expected files for new directories
    Crawler->>Mirrors: Check if mirror has new content
    
    alt Mirror has synced
        Mirrors-->>Crawler: Files match expected
        Crawler->>DB: Set HostCategoryDir.up2date = True
    else Mirror not yet synced
        Mirrors-->>Crawler: Files missing or outdated
        Crawler->>DB: Set HostCategoryDir.up2date = False
    end
    
    Note over GenCache,MLS: T+9hr: Cache Regenerated
    
    GenCache->>DB: Query all up2date mirrors for new repo
    DB-->>GenCache: List of ready mirrors
    GenCache->>GenCache: Build protobuf with new repo
    GenCache->>MLS: Sync and reload cache
    
    Note over User,MLS: T+9hr+: Users Can Access
    
    User->>MLS: GET /mirrorlist?repo=fedora-41&arch=x86_64
    MLS->>MLS: Find mirrors with up2date content
    MLS-->>User: Return mirror list (only synced mirrors)
    User->>Mirrors: Download new release
    
    Note over Crawler,MLS: T+24hr to T+72hr: More Mirrors Ready
    
    loop Crawler runs multiple times
        Crawler->>Mirrors: Check more mirrors
        Crawler->>DB: Update more HostCategoryDir.up2date = True
    end
    
    GenCache->>MLS: Cache updated with more mirrors
    
    Note over User,MLS: Users get better mirror selection as more sync
```

---

## 7. Propagation Statistics Collection

This shows how propagation statistics are collected for monitoring mirror sync progress.

```mermaid
sequenceDiagram
    autonumber
    participant Cron
    participant Crawler as mm2_crawler propagation
    participant Bodhi as Bodhi API
    participant DB as PostgreSQL Database
    participant Mirrors as Public Mirrors
    participant Web as Flask Web App
    participant Admin as MM Admin

    Cron->>Crawler: Execute propagation subcommand
    
    Crawler->>Bodhi: GET /releases (active versions)
    Bodhi-->>Crawler: List of active Fedora/EPEL versions
    
    loop For each (product, version, arch) combination
        Crawler->>DB: Get Repository for this combo
        DB-->>Crawler: Repository with directory_id
        
        Crawler->>DB: Get FileDetail for repomd.xml
        DB-->>Crawler: Expected timestamp (master's repomd.xml)
        
        Crawler->>DB: Get all mirrors for this category
        DB-->>Crawler: List of Host + HostCategoryUrl
        
        par Check all mirrors in parallel
            Crawler->>Mirrors: HEAD /repodata/repomd.xml
            Mirrors-->>Crawler: Last-Modified timestamp
        end
        
        Crawler->>Crawler: Categorize each mirror
        Note over Crawler: same_day, one_day, two_day, older, no_info
        
        Crawler->>DB: Insert PropagationStat record
    end
    
    Crawler-->>Cron: Exit
    
    Note over Web,Admin: Viewing Statistics
    
    Admin->>Web: GET /propagation
    Web->>DB: Query PropagationStat (last 7 days)
    DB-->>Web: Statistics data
    Web->>Web: Generate charts/graphs
    Web-->>Admin: Propagation dashboard
```

---

## Summary: Component Interaction Map

```mermaid
flowchart TB
    subgraph External["External Systems"]
        NFS["Master Mirror<br/>(NFS Mount)"]
        OIDC["Fedora Accounts<br/>(OIDC)"]
        Bodhi["Bodhi API"]
        FedMsg["Fedora Messaging<br/>(AMQP)"]
        Mirrors["Public Mirrors<br/>(~400 servers)"]
    end
    
    subgraph MM2["MirrorManager2 (this repo)"]
        Web["Flask Web App<br/>views.py, admin.py"]
        UMDL["UMDL<br/>update_master_directory_list.py"]
        Crawler["Crawler<br/>crawler/"]
        XMLRPC["XML-RPC<br/>xml_rpc.py"]
        DB[(PostgreSQL<br/>Database)]
    end
    
    subgraph External2["External (separate repo)"]
        GenCache["generate-mirrorlist-cache<br/>(Rust)"]
        MLS["mirrorlist-server<br/>(Rust)"]
        Proto["Protobuf Cache<br/>Files"]
    end
    
    subgraph Users["End Users"]
        Admin["Mirror Admins"]
        Private["Private Mirrors<br/>(report_mirror)"]
        EndUser["End Users<br/>(dnf/yum)"]
    end
    
    %% UMDL flow
    NFS --> UMDL
    UMDL --> DB
    
    %% Web app flows
    Admin --> Web
    Web --> OIDC
    Web --> DB
    Web --> FedMsg
    
    %% Private mirror flow
    Private --> XMLRPC
    XMLRPC --> DB
    
    %% Crawler flow
    Crawler --> DB
    Crawler --> Mirrors
    Crawler --> Bodhi
    
    %% Cache generation flow
    GenCache --> DB
    GenCache --> Proto
    Proto --> MLS
    
    %% End user flow
    EndUser --> MLS
    MLS --> EndUser
    EndUser --> Mirrors
```

---

## Data Flow Summary Table

| Flow | Trigger | Source | Destination | Data |
|------|---------|--------|-------------|------|
| UMDL Scan | Cron (5 min) | NFS Mount | Database | Directory listings, file checksums |
| Crawler Check | Cron (3x daily) | Database + Mirrors | Database | up2date status per directory |
| Report Mirror | Cron (on mirror) | Private Mirror | Database | File listings via XML-RPC |
| Cache Generation | Cron (hourly) | Database | Protobuf file | All mirror/repo/file data |
| MirrorList Request | User request | Protobuf (RAM) | User | Ordered mirror URL list |
| Web Management | User action | User | Database | Site/Host/Category config |
| Propagation Stats | Cron (hourly) | Mirrors | Database | repomd.xml freshness |

