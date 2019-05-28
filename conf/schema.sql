
--  agnet & node tables
CREATE TABLE IF NOT EXISTS agent (
    aid VARCHAR(256) NOT NULL,
    name VARCHAR(256) ,
    host VARCHAR(256),
    create_at TIMESTAMP,
    last_msg_at TIMESTAMP,
    last_cpu_util REAL,
    last_mem_util REAL,
    last_sys_load1 REAL,
    last_sys_cs INTEGER,
    status VARCHAR(10),
    CONSTRAINT agent_pkey PRIMARY KEY (aid)
);

CREATE TABLE IF NOT EXISTS node_metric_raw (
  aid VARCHAR(256),
  collect_at TIMESTAMP,
  category VARCHAR(20),
  content TEXT,
  recv_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_nmr_aid ON node_metric_raw (aid DESC);
CREATE INDEX IF NOT EXISTS idx_nmr_collect_at ON node_metric_raw (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_nmr_recv_at ON node_metric_raw (recv_at DESC);


CREATE TABLE IF NOT EXISTS node_memory_report(
    aid VARCHAR(256),
    collect_at timestamp,
    total_mem INTEGER,
    used_mem INTEGER,
    free_mem INTEGER,
    cache_mem INTEGER,
    total_swap INTEGER ,
    used_swap INTEGER ,
    free_swap INTEGER ,
    recv_at timestamp);
CREATE INDEX IF NOT EXISTS idx_nmre_aid ON node_memory_report (aid DESC);
CREATE INDEX IF NOT EXISTS idx_nmre_collect_at ON node_memory_report (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_nmre_recv_at ON node_memory_report (recv_at DESC);

CREATE TABLE IF NOT EXISTS node_cpu_report(
    aid VARCHAR(256),
    collect_at timestamp,
    us INTEGER,
    sy INTEGER,
    id INTEGER,
    wa INTEGER,
    st INTEGER,
    recv_at timestamp);
CREATE INDEX IF NOT EXISTS idx_ncr_aid ON node_cpu_report (aid DESC);
CREATE INDEX IF NOT EXISTS idx_ncr_collect_at ON node_cpu_report (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_ncr_recv_at ON node_cpu_report (recv_at DESC);

CREATE TABLE IF NOT EXISTS node_system_report(
    aid VARCHAR(256),
    collect_at timestamp,
    uptime INTEGER,
    users INTEGER,
    load1 REAL,
    load5 REAL,
    load15 REAL,
    procs_r INTEGER,
    procs_b INTEGER,
    sys_in INTEGER,
    sys_cs INTEGER,
    recv_at timestamp);
CREATE INDEX IF NOT EXISTS idx_nsr_aid ON node_system_report (aid DESC);
CREATE INDEX IF NOT EXISTS idx_nsr_collect_at ON node_system_report (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_nsr_recv_at ON node_system_report (recv_at DESC);

CREATE TABLE IF NOT EXISTS node_disk_report(
    aid VARCHAR(256),
    collect_at timestamp,
    fs VARCHAR(1024),
    size INTEGER,
    used INTEGER,
    available INTEGER,
    used_util REAL,
    mount_point VARCHAR(1024),
    recv_at timestamp);
CREATE INDEX IF NOT EXISTS idx_ndr_aid ON node_disk_report (aid DESC);
CREATE INDEX IF NOT EXISTS idx_ndr_collect_at ON node_disk_report (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_ndr_recv_at ON node_disk_report (recv_at DESC);


CREATE TABLE IF NOT EXISTS node_network_report(
    aid VARCHAR(256),
    collect_at timestamp,
    interface VARCHAR(256),
    rx_bytes INTEGER,
    rx_packets INTEGER,
    rx_errors INTEGER,
    rx_dropped INTEGER,
    rx_overrun INTEGER,
    rx_mcast INTEGER,
    tx_bytes INTEGER,
    tx_packets INTEGER,
    tx_errors INTEGER,
    tx_dropped INTEGER,
    tx_carrier INTEGER,
    tx_collsns INTEGER,
    recv_at timestamp);
CREATE INDEX IF NOT EXISTS idx_nnr_aid ON node_network_report (aid DESC);
CREATE INDEX IF NOT EXISTS idx_nnr_collect_at ON node_network_report (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_nnr_recv_at ON node_network_report (recv_at DESC);

-- service tables
CREATE TABLE IF NOT EXISTS service_metric_raw (
  aid VARCHAR(256),
  collect_at TIMESTAMP,
  name VARCHAR(256),
  pid INTEGER,
  category VARCHAR(20),
  content TEXT,
  recv_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_nsr_aid ON service_metric_raw (aid DESC);
CREATE INDEX IF NOT EXISTS idx_nsr_collect_at ON service_metric_raw (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_nsr_recv_at ON service_metric_raw (recv_at DESC);

-- Table service
CREATE TABLE IF NOT EXISTS service (
  id CHAR(32),
  aid VARCHAR(256),
  name VARCHAR(64),
  pid INTEGER ,
  type CHAR(10),
  last_report_at TIMESTAMP,
  status CHAR(10),
  CONSTRAINT service_pkey PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_si_aid ON service (aid);
CREATE INDEX IF NOT EXISTS idx_si_report_at ON service (last_report_at DESC);

-- Table service_history
CREATE TABLE IF NOT EXISTS service_history (
  aid VARCHAR(256),
  service_id CHAR(32),
  pid INTEGER ,
  collect_at TIMESTAMP,
  recv_at TIMESTAMP
);


CREATE TABLE IF NOT EXISTS service_pidstat_report(
    aid VARCHAR(256),
    service_id CHAR(32),
    collect_at timestamp,
    tid INTEGER,
    cpu_us REAL,
    cpu_sy REAL,
    cpu_gu REAL,
    cpu_util REAL,
    mem_minflt INTEGER,
    mem_majflt INTEGER,
    mem_vsz INTEGER,
    mem_rss INTEGER,
    mem_util REAL,
    disk_rd INTEGER,
    disk_wr INTEGER,
    disk_ccwr INTEGER,
    recv_at timestamp);
CREATE INDEX IF NOT EXISTS idx_spr_aid ON service_pidstat_report (aid DESC);
CREATE INDEX IF NOT EXISTS idx_spr_collect_at ON service_pidstat_report (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_spr_recv_at ON service_pidstat_report (recv_at DESC);


CREATE TABLE IF NOT EXISTS service_jstatgc_report(
    aid VARCHAR(256),
    service_id CHAR(32),
    collect_at timestamp,
    ts INTEGER,
    s0c INTEGER,
    s1c INTEGER,
    s0u INTEGER,
    s1u INTEGER,
    ec INTEGER,
    eu INTEGER,
    oc INTEGER,
    ou INTEGER,
    mc INTEGER,
    mu INTEGER,
    ccsc INTEGER,
    ccsu INTEGER,
    ygc INTEGER,
    ygct REAL,
    fgc INTEGER,
    fgct REAL,
    gct REAL,
    recv_at timestamp);
CREATE INDEX IF NOT EXISTS idx_sjgc_aid ON service_jstatgc_report (aid DESC);
CREATE INDEX IF NOT EXISTS idx_sjgc_collect_at ON service_jstatgc_report (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_sjgc_recv_at ON service_jstatgc_report (recv_at DESC);

-- Table alarm
CREATE TABLE IF NOT EXISTS alarm (
  id CHAR(32),
  entity_id CHAR(32),
  entity_type CHAR(1),
  type CHAR(10),
  state SMALLINT,
  duration INTEGER, -- in seconds
  create_at TIMESTAMP,
  CONSTRAINT alarm_pkey PRIMARY KEY (id)
);
