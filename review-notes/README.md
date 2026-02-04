# MirrorManager2 Codebase Review Notes

**Created:** January 21, 2026  
**Repository:** https://github.com/fedora-infra/mirrormanager2

## Purpose

These notes document the investigation of the MirrorManager2 codebase to understand:
- The various components of the overall service
- What is needed to run each component individually
- How they work together as a whole

## Document Index

| Document | Description |
|----------|-------------|
| [00-overview.md](00-overview.md) | High-level architecture and introduction |
| [01-components.md](01-components.md) | Detailed breakdown of each component |
| [02-database-models.md](02-database-models.md) | Database schema and ORM models |
| [03-backend-utilities.md](03-backend-utilities.md) | CLI tools and cron jobs |
| [04-web-application.md](04-web-application.md) | Flask web application details |
| [05-crawler.md](05-crawler.md) | Mirror crawler deep dive |
| [06-deployment.md](06-deployment.md) | Deployment guide and requirements |
| [07-configuration.md](07-configuration.md) | Complete configuration reference |
| [08-quick-reference.md](08-quick-reference.md) | Quick reference card |
| [09-sequence-diagrams.md](09-sequence-diagrams.md) | Mermaid UML sequence diagrams |

## Key Findings Summary

### System Components

1. **Web Application** (Flask)
   - User/admin interface
   - report_mirror XML-RPC endpoint
   - REST API

2. **Crawler** (`mm2_crawler`)
   - Checks mirror freshness
   - Supports rsync, HTTP, FTP
   - Multi-threaded with timeout handling

3. **UMDL** (`mm2_update-master-directory-list`)
   - Scans master mirror (NFS mount)
   - Updates database with current files

4. **MirrorList Server** (SEPARATE REPO!)
   - **Not in this codebase**
   - https://github.com/adrianreber/mirrorlist-server
   - Serves actual `/mirrorlist` and `/metalink` endpoints

### Data Flow

```
Master Mirror (NFS)
        │
        ▼ (UMDL scans)
   Database ◄──────── Web App (user management)
        │
        ▼ (Crawler reads expected state)
   Mirrors ◄───────── Crawler (checks actual state)
        │
        ▼
   Database (stores up2date status)
        │
        ▼ (generate-cache job)
   Pickle File
        │
        ▼
   MirrorList Server → End Users
```

### Essential Services to Run

| Service | Required | Purpose |
|---------|----------|---------|
| Web App | Yes | Management UI, report_mirror |
| Database | Yes | All data storage |
| UMDL | Yes | Keep DB in sync with master |
| Crawler | Yes | Keep mirror status current |
| Cache Generator | Yes | Create mirrorlist pickle |
| MirrorList Server | Yes* | Serve mirror requests |

*Note: MirrorList Server is a separate codebase.

## External References

- **Source Repository:** https://github.com/fedora-infra/mirrormanager2
- **Production Instance:** https://mirrormanager.fedoraproject.org/
- **Fedora Infra SOP:** https://docs.fedoraproject.org/en-US/infra/sysadmin_guide/mirrormanager/
- **MirrorList Server:** https://github.com/adrianreber/mirrorlist-server
- **Fedora Messaging Schemas:** https://github.com/fedora-infra/mirrormanager-messages

## Data Handoff: MirrorManager2 → mirrorlist-server

### Overview
The `generate-mirrorlist-cache` tool (in the mirrorlist-server repo) **directly queries the MirrorManager2 database** to create the cache files that mirrorlist-server needs.

### Data Exchange Format: Protocol Buffers
The data format is defined in [mirrormanager.proto](../mirrormanager.proto) in THIS repo. Key structures:

- `MirrorList` - Top-level container with all cache data
- `MirrorListCacheType` - Per-directory mirror availability
- `FileDetailsCacheDirectoryType` - File checksums for freshness
- Various cache maps for hosts, countries, netblocks, ASNs, etc.

### How It Works
1. **`generate-mirrorlist-cache`** (Rust, in mirrorlist-server repo) connects to MM2's PostgreSQL database
2. Queries all relevant tables (hosts, directories, file_details, etc.)
3. Serializes data to protobuf format
4. Writes output files for mirrorlist-server
5. Files synced to proxy servers hourly (at :55)
6. mirrorlist-server containers restart with new data (at :15)

### Historical Note
Originally used Python Pickle format. Changed to Protobuf because:
- Pickle incompatible between Python 2/3
- Protobuf in Python used 3.5GB RAM vs 1.1GB for Pickle
- Rust implementation uses only 600MB and runs in <1 minute (vs 50 min Python)

### Key Insight
**There is NO cache generation code in THIS repository.** The [mirrormanager.proto](../mirrormanager.proto) file defines the contract, but `generate-mirrorlist-cache` lives in the mirrorlist-server repo.

---

## Questions for Further Investigation

1. ~~How is the mirrorlist cache pickle file generated?~~ **ANSWERED**: `generate-mirrorlist-cache` in mirrorlist-server repo
2. ~~What is the exact format of the pickle file?~~ **ANSWERED**: Now uses Protobuf, defined in [mirrormanager.proto](../mirrormanager.proto)
3. How are proxies coordinated for cache updates?
4. What monitoring/alerting exists for crawler failures?
5. How are database migrations handled in production?

---

*This documentation was created during codebase review and may not cover all aspects. Refer to official documentation for authoritative information.*
