# MirrorManager2 Web Application Details

This document provides detailed information about the Flask web application.

## Application Factory

**File:** [mirrormanager2/app.py](../mirrormanager2/app.py)

### `create_app()` Function
Located at [app.py lines 49-134](../mirrormanager2/app.py#L49-L134)

```python
def create_app(config=None):
    app = flask.Flask(__name__)
    
    # 1. Load configuration
    app.config.from_object("mirrormanager2.default_config")
    if "MM2_CONFIG" in os.environ:
        app.config.from_envvar("MM2_CONFIG")
    app.config.update(config or {})
    
    # 2. Configure template/static paths for theming
    app.template_folder = os.path.join(app.template_folder, app.config["THEME_FOLDER"])
    app.static_folder = os.path.join(app.static_folder, app.config["THEME_FOLDER"])
    
    # 3. Set up logging (email errors to admins)
    # 4. Initialize database
    DB.init_app(app)
    
    # 5. Initialize authentication (OIDC or local)
    # 6. Initialize Flask-Admin
    # 7. Register blueprints
    # 8. Return configured app
```

---

## Authentication

### OpenID Connect (FAS)
- Default mode: `MM_AUTHENTICATION = "fas"`
- Uses Flask-OIDC with Fedora Accounts
- Configuration in [default_config.py lines 56-69](../mirrormanager2/default_config.py#L56-L69)

### Local Authentication
- Alternative mode: `MM_AUTHENTICATION = "local"`
- Blueprint: [mirrormanager2/local_auth.py](../mirrormanager2/local_auth.py)
- Uses local User/Group tables in database

### Auth Views
**File:** [mirrormanager2/auth.py](../mirrormanager2/auth.py)

Handles:
- Login/logout flow
- Session management
- User info injection via `flask.g.fas_user`

---

## Main Views (User Interface)

**File:** [mirrormanager2/views.py](../mirrormanager2/views.py) (1339 lines)

### Public Routes

| Route | Function | Description |
|-------|----------|-------------|
| `/` | `index()` | Homepage with products/architectures |
| `/mirrors` | `list_mirrors()` | List all public mirrors |
| `/mirrors/<product>` | `list_mirrors()` | Filter by product |
| `/mirrors/<product>/<version>` | `list_mirrors()` | Filter by product/version |
| `/mirrors/<product>/<version>/<arch>` | `list_mirrors()` | Filter by product/version/arch |
| `/statistics` | | Access statistics |
| `/maps` | | Mirror world maps |
| `/propagation` | | Propagation statistics |

### Authenticated User Routes

| Route | Function | Description |
|-------|----------|-------------|
| `/site/new` | `site_new()` | Register new mirror site |
| `/site/<id>` | `site_view()` | View/edit site details |
| `/site/<id>/host/new` | `host_new()` | Add host to site |
| `/host/<id>` | `host_view()` | View/edit host |
| `/host/<id>/category/<cat_id>` | `host_category()` | Configure host category |
| `/host/<id>/category/<cat_id>/url/new` | | Add category URL |
| `/host/<id>/netblock/new` | | Add netblock |

### Admin Routes
Require `is_mirrormanager_admin()` from [perms.py](../mirrormanager2/perms.py):

- `/admin/*` - Flask-Admin interface

---

## Admin Interface

**File:** [mirrormanager2/admin.py](../mirrormanager2/admin.py)

Uses Flask-Admin to provide CRUD interfaces for all database models.

### Model Views Registered
From [admin.py lines 53-91](../mirrormanager2/admin.py#L53-L91):

```python
views = [
    MMModelView(model.Arch, db_session),
    MMModelView(model.Category, db_session),
    MMModelView(model.Country, db_session, category="Country"),
    MMModelView(model.CountryContinentRedirect, db_session, category="Country"),
    MMModelView(model.EmbargoedCountry, db_session, category="Country"),
    DirectoryView(model.Directory, db_session, category="Directory"),
    # ... and many more
]
```

### Access Control
`MMModelView.is_accessible()` checks if user is in `ADMIN_GROUP`:
```python
def is_accessible(self):
    admin = False
    if hasattr(flask.g, "fas_user") and flask.g.fas_user:
        admin = is_mirrormanager_admin(flask.g.fas_user)
    return admin
```

---

## REST API

**File:** [mirrormanager2/api.py](../mirrormanager2/api.py)

### Endpoints

#### `/api/mirroradmins`
**Lines:** [31-88](../mirrormanager2/api.py#L31-L88)

Returns list of mirror administrators.

```
GET /api/mirroradmins/
GET /api/mirroradmins/?name=<mirror url or site name>
```

Response:
```json
{
  "admins": ["user1", "user2"],
  "total": 2
}
```

#### `/api/repositories`
**Lines:** [91-150](../mirrormanager2/api.py#L91-L150)

Returns list of repositories.

```
GET /api/repositories
```

Response:
```json
{
  "repositories": [
    {
      "fedora-install-40": {
        "directory": "pub/fedora/linux/releases/40/Fedora/x86_64/os",
        "name": "..."
      }
    }
  ],
  "total": 42
}
```

---

## XML-RPC Interface

**File:** [mirrormanager2/xml_rpc.py](../mirrormanager2/xml_rpc.py)

### `checkin()` Method
**Lines:** [44-56](../mirrormanager2/xml_rpc.py#L44-L56)

Handles `report_mirror` client check-ins.

```python
@XMLRPC.register
def checkin(pickledata):
    # Decompress and decode data
    uncompressed = bz2.decompress(base64.urlsafe_b64decode(pickledata))
    # Parse JSON or pickle
    config = json.loads(uncompressed)
    # Validate and process
    r, host, message = read_host_config(DB.session, config)
```

### Host Config Validation
**File:** [mirrormanager2/lib/hostconfig.py](../mirrormanager2/lib/hostconfig.py)

`validate_config()` checks ([lines 32-75](../mirrormanager2/lib/hostconfig.py#L32-L75)):
- Config is a dict with version field
- Has required sections: global, site, host
- Site name and password match database
- Host name matches site

---

## Health Checks

**File:** [mirrormanager2/health_checks.py](../mirrormanager2/health_checks.py)

### Endpoints
- `/healthz/live` - Liveness probe (always passes)
- `/healthz/ready` - Readiness probe (checks database)

### Readiness Check
```python
def readiness():
    status = DB.manager.get_status()
    if status is DatabaseStatus.NO_INFO:
        raise HealthError("Can't connect to the database")
    if status is DatabaseStatus.UPGRADE_AVAILABLE:
        raise HealthError("The database schema needs to be updated")
```

---

## Templates & Static Files

### Template Structure
Located in [mirrormanager2/templates/fedora/](../mirrormanager2/templates/fedora/):
- Base templates
- Site management forms
- Host management forms
- Mirror listings
- Statistics pages

### Static Files
Located in [mirrormanager2/static/fedora/](../mirrormanager2/static/fedora/):
- CSS
- JavaScript
- Images

### Theming
Theme folder configured via `THEME_FOLDER` (default: "fedora").
From [app.py lines 58-60](../mirrormanager2/app.py#L58-L60).

---

## Forms

**File:** [mirrormanager2/forms.py](../mirrormanager2/forms.py)

Uses WTForms for:
- Site registration/editing
- Host configuration
- Category URLs
- Netblocks
- etc.

---

## Session & Security

From [default_config.py](../mirrormanager2/default_config.py):

| Setting | Default | Description |
|---------|---------|-------------|
| `PERMANENT_SESSION_LIFETIME` | 1 hour | Session timeout |
| `MM_COOKIE_REQUIRES_HTTPS` | True | HTTPS-only cookies |
| `MM_COOKIE_NAME` | "MirrorManager" | Session cookie name |
| `CHECK_SESSION_IP` | True | Validate client IP |
| `SECRET_KEY` | Must change! | CSRF/session key |

---

## Error Handling & Logging

### Email Alerts
From [app.py lines 63-81](../mirrormanager2/app.py#L63-L81):

Errors are emailed to `MAIL_ADMIN` via `SMTP_SERVER`:
```python
MAIL_HANDLER = logging.handlers.SMTPHandler(
    app.config.get("SMTP_SERVER", "127.0.0.1"),
    "nobody@fedoraproject.org",
    app.config.get("MAIL_ADMIN", "admin@fedoraproject.org"),
    "MirrorManager2 error",
)
MAIL_HANDLER.setLevel(logging.ERROR)
```

### Stderr Logging
All INFO+ messages go to stderr.

---

## Fedora Messaging Integration

**File:** [mirrormanager2/lib/notifications.py](../mirrormanager2/lib/notifications.py)

Events published:
- Host added/updated/deleted
- Site deleted

Messages use `mirrormanager-messages` package schemas.

### Configuration
From [fedora-messaging.toml.example](../fedora-messaging.toml.example):
- AMQP connection settings
- TLS certificates
- Exchange configuration

### Usage in Views
```python
from mirrormanager2.lib.notifications import fedmsg_publish
from mirrormanager_messages.host import HostAddedV2

fedmsg_publish(HostAddedV2(body=host_to_message_body(host)))
```

---

## Running the Web Application

### Development
```bash
poetry install
export MM2_CONFIG=/path/to/config.cfg
poetry run ./runserver.py --debug
```

### Production (Gunicorn)
```bash
poetry install --extras deploy
gunicorn -w 4 "mirrormanager2.app:create_app()"
```

### Production (OpenShift/Kubernetes)
Uses `gunicorn` with configuration from environment.
