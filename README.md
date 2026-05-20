# node-monitor

A pure Python distributed performance monitoring tool with a Master-Agent architecture. Monitor system resources (CPU, memory, disk, network, load) and application services (process-level metrics, Java GC) across multiple nodes in real time.

- **Author**: Isaac Tian
- **License**: [Apache 2.0](LICENSE)

---

## Architecture

node-monitor has two major components:

- **Master** — The centralized controller that manages all agents, receives health metrics, stores data in PostgreSQL and OpenTSDB, and exposes a REST API + web UI.
- **Agent** — Deployed on each monitored node, collects system metrics (via `dstat`, `vmstat`, `free`, `df`, `ip`, etc.) and service-level metrics (via `pidstat`, `jstat`, `prstat`) and reports them to the Master over TCP.

```
┌─────────────────┐     TCP      ┌──────────────────┐
│   Agent (node)  │◄───────────►│  Master Server    │
│  - System stats │             │  - Agent Manager  │
│  - Service stats│             │  - Data Persister │
│  - Heartbeat    │             │  - Alarm Engine   │
└─────────────────┘             └────────┬─────────┘
                                         │
                           ┌─────────────┴─────────────┐
                           │  PostgreSQL  │  OpenTSDB   │
                           └─────────────┴─────────────┘
                                         │
                           ┌─────────────┴─────────────┐
                           │   Web UI (Vue.js + Flask) │
                           │   Grafana (optional)      │
                           └───────────────────────────┘
```

---

## Features

- **System monitoring**: CPU, memory, disk, network I/O, system load, processes
- **Service monitoring**: Process-level CPU/memory/disk via pidstat, Java GC via jstat
- **Automatic service discovery**: Find monitored processes by keyword lookup in `ps -ef`
- **Configurable collection**: Per-metric and per-service collection intervals
- **Remote agent deployment**: SSH-based agent installation from the master CLI
- **Data retention**: Configurable TTL policies per metric type
- **Dual storage**: PostgreSQL for structured data, OpenTSDB for time-series
- **Alert engine** (WIP): Rule-based alarm generation
- **Rich UI**: Vue.js + ECharts dashboard with node detail, service views, and GC analysis
- **Grafana integration**: Pre-configured Grafana dashboards for reporting
- **Cross-platform**: Linux and Solaris support
- **Deployment**: Docker, Docker Swarm, Kubernetes

---

## Tech Stack

| Layer    | Technology                                         |
| -------- | -------------------------------------------------- |
| Backend  | Python 2.7, Flask                                  |
| Frontend | Vue.js 2, ECharts, Bootstrap 3, webpack            |
| Database | PostgreSQL (RDB), OpenTSDB (Time Series)           |
| Deploy   | Docker, Docker Compose/Swarm, Kubernetes           |
| Reporting| Grafana (optional)                                 |

---

## Quickstart

### Prerequisites

- Python 2.7 on master and agent nodes
- PostgreSQL and OpenTSDB instances accessible from master
- SSH access to monitored nodes (for remote agent deployment)

### 1. Setup Master

```bash
# Install Python dependencies
pip install -r requirements.txt

# Edit configuration
vim conf/master.yaml
```

Key configuration in `conf/master.yaml`:

```yaml
master:
  server:
    host: 0.0.0.0
    port: 30079
  database:
    info:      # PostgreSQL connection
      host: ${POSTGRES_HOST:localhost}
      name: node-monitor
      user: node-monitor
      password: node-monitor
    tsd:       # OpenTSDB connection
      host: ${OPENTSDB_HOST:localhost}
      port: 4242
```

### 2. Start Master

```bash
# Start both master + UI
python nodemonitor/master_cli.py -r all

# Or start them separately:
python nodemonitor/master_cli.py -r master   # metrics receiver (port 30079)
python nodemonitor/master_cli.py -r ui       # web UI (port 30078)
```

### 3. Deploy Agent to Remote Nodes

Create a node list file (format: `host,username,password`):

```
# nodes.txt
192.168.1.10,root,password1
192.168.1.11,root,password2
```

Push and start agents:

```bash
python nodemonitor/master_cli.py -p nodes.txt master_host
```

The CLI will SSH into each node, copy agent scripts, install Python 2.7 if missing, and start the agent as a service.

### 4. Access Web UI

Open `http://<master-host>:30078` in your browser.

### 5. Stop Agents on Remote Nodes

```bash
python nodemonitor/master_cli.py --stop-agents nodes.txt
```

---

## Development Setup

### Backend

```bash
# Clone the repo
git clone <repo-url> && cd node-monitor

# (Optional) Create virtualenv
virtualenv venv && source venv/bin/activate

# Install deps
pip install -r requirements.txt
```

### Frontend

```bash
cd web

# Install JS dependencies
npm install

# Start dev server with hot-reload
npm start

# Production build
npm run build
```

The production build outputs to `web/dist/`, which is served by Flask's static file handler at runtime.

### Tests

```bash
# Run all Python tests
python -m pytest test/
```

### Run locally

```bash
# Start master + UI in development mode
python nodemonitor/master_cli.py -r all

# Or run UI with debug mode
python nodemonitor/master_ui.py
```

---

## Deploy with Docker

### Build Images

```bash
# Build all images
python build.py

# Build individual components
python build.py master   # Master image
python build.py ui       # Report UI (Grafana) image
python build.py push     # Push images to registry
```

### Run Master in Docker

```bash
docker run -d \
  --name node-monitor-master \
  -p 30078:30078 \
  -p 30079:30079 \
  -e POSTGRES_HOST=pg-host \
  -e OPENTSDB_HOST=tsdb-host \
  foxty/node-monitor-master:1.0.0-SNAPSHOT
```

### Docker Compose / Swarm

See `deploy/swam/node-monitor.yaml` for a full Docker Swarm stack with PostgreSQL and OpenTSDB.

### Kubernetes

See `deploy/k8s/` for Kubernetes manifests:

```bash
kubectl apply -f deploy/k8s/postgres.yaml
kubectl apply -f deploy/k8s/opentsdb.yaml
kubectl apply -f deploy/k8s/node-monitor.yaml
```

---

## Configuration

### Agent Configuration (`nodemonitor/agent_config.json`)

Defines what metrics to collect on each node:

- `clock_interval`: Base interval (seconds) between collection rounds
- `heartbeat_clocks`: Send heartbeat every N clocks
- `node_metrics`: System-level commands (dstat, free, vmstat, df, etc.)
- `service_metrics`: Metrics templates (pidstat, prstat, jstat-gc)
- `services`: Service definitions with lookup keywords and metric assignments

### Master Configuration (`conf/master.yaml`)

- Server host/port
- Database connections (PostgreSQL, OpenTSDB)
- Data retention policies per metric type (in days)

---

## Communication Protocol

Agents communicate with the Master over raw TCP on port `30079` using a custom binary-over-text framing protocol.

### Wire Format

```
MSG:<payload_length>\n
<base64(header_name):base64(header_value)>\n
...
<base64(pickle.dumps(body))>
```

### Headers

Each message carries base64-encoded headers: `AgentID`, `MessageType`, `CreateAt`, `CollectAt`, `SendAt`.

### Message Types

| Type | Direction | Purpose |
| ---- | --------- | ------- |
| `A_REG` | Agent → Master | Agent registration (hostname, OS) |
| `A_HEARTBEAT` | Agent → Master | Periodic heartbeat with config version |
| `A_NODE_METRIC` | Agent → Master | System metric results |
| `A_SERVICE_METRIC` | Agent → Master | Service metric results |
| `M_CONFIG_UPDATE` | Master → Agent | Push updated agent configuration |
| `M_STOP_COLLECT` | Master → Agent | Stop metric collection |

### Socket Model

Non-blocking sockets with `select.select()` I/O multiplexing on both sides. The agent uses a bounded send queue (max 8 messages, drops oldest when full). The master handles all agents in dedicated receiver and sender threads.

---

## Database Schema

The schema (defined in `conf/schema.sql`) creates **13 tables** for structured metric storage in PostgreSQL:

### Agent Registry
- **`agent`** — Registered agents with last-known metric values (CPU, memory, load, status)

### Node-Level Metrics (Raw + Parsed Reports)
- **`node_metric_raw`** — Raw command output categorized by metric type
- **`node_memory_report`** — Parsed: total/used/free memory, swap, cache
- **`node_cpu_report`** — Parsed: us/sy/id/wa/st CPU percentages
- **`node_system_report`** — Parsed: load1/5/15, uptime, users, context switches
- **`node_disk_report`** — Parsed: per-filesystem size, used, available, utilization
- **`node_network_report`** — Parsed: per-interface RX/TX bytes, packets, errors, drops

### Service-Level Metrics
- **`service`** — Discovered service instances with current PID and status
- **`service_history`** — PID change audit trail per service
- **`service_metric_raw`** — Raw service command output
- **`service_pidstat_report`** — Parsed pidstat: per-thread CPU, memory, disk I/O
- **`service_jstatgc_report`** — Parsed Java GC: heap sizes, GC counts, pause times

### Alarms
- **`alarm`** — Alarm records (table defined, alarm engine WIP)

All tables have descending indexes on `aid` and `collect_at` for efficient time-range queries.

---

## REST API

The master UI exposes the following REST endpoints:

| Method | Endpoint                                     | Description                    |
| ------ | -------------------------------------------- | ------------------------------ |
| GET    | `/api/dashboard/summary`                     | Dashboard summary counts       |
| GET    | `/api/agents`                                | List all agents                |
| POST   | `/api/agents`                                | Install agent on remote node   |
| GET    | `/api/agents/{aid}`                          | Get agent details              |
| DELETE | `/api/agents/{aid}`                          | Remove agent                   |
| GET    | `/api/agents/{aid}/report/system`            | System load reports            |
| GET    | `/api/agents/{aid}/report/cpu`               | CPU utilization reports        |
| GET    | `/api/agents/{aid}/report/memory`            | Memory usage reports           |
| GET    | `/api/agents/{aid}/report/disk`              | Disk utilization reports       |
| GET    | `/api/agents/{aid}/services`                 | Services on agent              |
| GET    | `/api/agents/{aid}/services/{sid}`           | Service details + history      |
| GET    | `/api/agents/{aid}/services/{sid}/report/pidstat` | Process-level stats     |
| GET    | `/api/agents/{aid}/services/{sid}/report/jstatgc`  | Java GC stats           |

---

## Project Structure

```
node-monitor/
├── conf/                     # Configuration files
│   ├── master.yaml           # Master server configuration
│   ├── schema.sql            # PostgreSQL table schema
│   └── grafana/              # Grafana provisioning configs
├── docker/                   # Dockerfiles
│   ├── Dockerfile.Master     # Master + UI bundled image
│   ├── Dockerfile.MasterUI   # UI-only image
│   └── Dockerfile.ReportUI   # Grafana reporting image
├── deploy/                   # Deployment manifests
│   ├── k8s/                  # Kubernetes manifests
│   └── swam/                 # Docker Swarm stack
├── nodemonitor/              # Python source
│   ├── agent.py              # Agent (metric collection, reporting)
│   ├── agent_config.json     # Default agent configuration
│   ├── agent_service.sh      # Linux init script for agent service
│   ├── agent_service_solaris.xml  # Solaris SMF manifest for agent
│   ├── common.py             # Shared: messaging (Msg), config, text parsing
│   ├── content_parser.py     # System command output parsers
│   ├── master.py             # Master server (agent mgmt, metrics processing)
│   ├── master_cli.py         # CLI: run master/ui, deploy agents via SSH
│   ├── master_ui.py          # Flask REST API server + static file serving
│   ├── model.py              # Data access: RDBModel (PostgreSQL) + TSDModel (OpenTSDB)
│   └── __init__.py
├── web/                      # Vue.js frontend
│   ├── src/
│   │   ├── components/       # 13 Vue components (Dashboard, Nodes, etc.)
│   │   ├── index.js          # App entry point with Vue Router
│   │   └── common.js         # Shared ECharts chart config
│   ├── package.json
│   └── webpack.config.js
├── test/                     # Unit tests
│   ├── agent_test.py         # AgentConfig, NodeCollector tests
│   ├── common_test.py        # YAMLConfig, Msg encode/decode, TextTable tests
│   ├── content_parser_test.py # Command output parser tests
│   ├── master_test.py        # Master message routing tests
│   ├── master_cli_test.py    # CLI argument parsing tests
│   ├── model_test.py         # RDB/TSD model tests
│   ├── agent_config_test.json
│   └── common_test_master.yaml
├── build.py                  # Build script (Docker images)
├── requirements.txt          # Python 2.7 dependencies (flask, paramiko, psycopg2, etc.)
└── LICENSE                   # Apache 2.0
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
