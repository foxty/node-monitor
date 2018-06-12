CREATE TABLE IF NOT EXISTS agent(aid UNIQUE, name, host, create_at timestamp,
    last_msg_at timestamp, last_cpu_util, last_mem_util, last_sys_load1, last_sys_cs, status);

CREATE TABLE IF NOT EXISTS node_metric_raw(aid, collect_at timestamp, category, content, recv_at timestamp);
CREATE INDEX IF NOT EXISTS `idx_nmr_aid` ON `node_metric_raw` (`aid` DESC);
CREATE INDEX IF NOT EXISTS `idx_nmr_collect_at` ON `node_metric_raw` (collect_at DESC);
CREATE INDEX IF NOT EXISTS `idx_nmr_recv_at` ON `node_metric_raw` (recv_at DESC);

CREATE TABLE IF NOT EXISTS node_memory_report(
    aid, collect_at timestamp, total_mem, used_mem, free_mem, cache_mem,
    total_swap, used_swap, free_swap, recv_at timestamp);
CREATE INDEX IF NOT EXISTS `idx_nmre_aid` ON `node_memory_report` (`aid` DESC);
CREATE INDEX IF NOT EXISTS `idx_nmre_collect_at` ON `node_memory_report` (collect_at DESC);
CREATE INDEX IF NOT EXISTS `idx_nmre_recv_at` ON `node_memory_report` (recv_at DESC);

CREATE TABLE IF NOT EXISTS node_cpu_report(aid, collect_at timestamp, us, sy, id, wa, st, recv_at timestamp);
CREATE INDEX IF NOT EXISTS `idx_ncr_aid` ON `node_cpu_report` (`aid` DESC);
CREATE INDEX IF NOT EXISTS `idx_ncr_collect_at` ON `node_cpu_report` (collect_at DESC);
CREATE INDEX IF NOT EXISTS `idx_ncr_recv_at` ON `node_cpu_report` (recv_at DESC);

CREATE TABLE IF NOT EXISTS node_system_report(aid, collect_at timestamp, uptime, users,
    load1, load5, load15, procs_r, procs_b, sys_in, sys_cs, recv_at timestamp);
CREATE INDEX IF NOT EXISTS idx_nsr_aid ON node_system_report (aid DESC);
CREATE INDEX IF NOT EXISTS idx_nsr_collect_at ON node_system_report (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_nsr_recv_at ON node_system_report (recv_at DESC);

CREATE TABLE IF NOT EXISTS node_disk_report(aid, collect_at timestamp, fs, size, used,
    available, used_util, mount_point, recv_at timestamp);
CREATE INDEX IF NOT EXISTS idx_ndr_aid ON node_disk_report (aid DESC);
CREATE INDEX IF NOT EXISTS idx_ndr_collect_at ON node_disk_report (collect_at DESC);
CREATE INDEX IF NOT EXISTS idx_ndr_recv_at ON node_disk_report (recv_at DESC);

CREATE TABLE IF NOT EXISTS service_metric_raw(aid, collect_at timestamp, name, pid,
    category, content, recv_at timestamp);
CREATE INDEX IF NOT EXISTS `idx_nsr_aid` ON `service_metric_raw` (`aid` DESC);
CREATE INDEX IF NOT EXISTS `idx_nsr_collect_at` ON `service_metric_raw` (collect_at DESC);
CREATE INDEX IF NOT EXISTS `idx_nsr_recv_at` ON `service_metric_raw` (recv_at DESC);

CREATE TABLE IF NOT EXISTS service(id PRIMARY KEY NOT NULL, aid, name, pid, type, last_report_at timestamp, status);
CREATE INDEX IF NOT EXISTS `idx_si_aid` ON `service` (aid);
CREATE INDEX IF NOT EXISTS `idx_si_report_at` ON `service` (last_report_at DESC);

CREATE TABLE IF NOT EXISTS service_history(aid, service_id, pid, collect_at timestamp, recv_at timestamp);

CREATE TABLE IF NOT EXISTS service_pidstat_report(aid, service_id, collect_at timestamp,
    tid, cpu_us, cpu_sy, cpu_gu, cpu_util, mem_minflt, mem_majflt, mem_vsz, mem_rss, mem_util,
    disk_rd, disk_wr, disk_ccwr, recv_at timestamp);
CREATE INDEX IF NOT EXISTS `idx_spr_aid` ON `service_pidstat_report` (`aid` DESC);
CREATE INDEX IF NOT EXISTS `idx_spr_collect_at` ON `service_pidstat_report` (collect_at DESC);
CREATE INDEX IF NOT EXISTS `idx_spr_recv_at` ON `service_pidstat_report` (recv_at DESC);

CREATE TABLE IF NOT EXISTS service_jstatgc_report(aid, service_id, collect_at timestamp,
    ts, s0c, s1c, s0u, s1u, ec, eu, oc, ou, mc, mu, ccsc, ccsu, ygc, ygct, fgc, fgct, gct, recv_at timestamp);
CREATE INDEX IF NOT EXISTS `idx_sjgc_aid` ON `service_jstatgc_report` (`aid` DESC);
CREATE INDEX IF NOT EXISTS `idx_sjgc_collect_at` ON `service_jstatgc_report` (collect_at DESC);
CREATE INDEX IF NOT EXISTS `idx_sjgc_recv_at` ON `service_jstatgc_report` (recv_at DESC);

CREATE TABLE IF NOT EXISTS alarm(id PRIMARY KEY, entity_id, entity_type, type, state, duration, create_at timestamp);
