
-- Table agent
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

-- Table node_metric_raw
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

-- Table service_metric_raw
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
