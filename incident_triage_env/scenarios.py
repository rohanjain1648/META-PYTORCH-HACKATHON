# Copyright (c) 2025. All rights reserved.
# Incident Triage Environment - Scenarios

"""
Incident Scenario Definitions.

Contains all pre-built incident scenarios organized by difficulty level.
Each scenario includes alerts, log data, system metrics, expected diagnosis,
expected priorities, valid remediation steps, and verification criteria.
"""

import copy
import random
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM SERVICE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

HEALTHY_SERVICES = {
    "load_balancer": {
        "status": "healthy",
        "cpu_percent": 12.3,
        "memory_percent": 34.5,
        "error_rate": 0.001,
        "latency_ms": 2.1,
        "connections_active": 1520,
        "requests_per_sec": 8500,
    },
    "app_server_1": {
        "status": "healthy",
        "cpu_percent": 45.2,
        "memory_percent": 62.1,
        "error_rate": 0.002,
        "latency_ms": 45.3,
        "active_threads": 120,
        "gc_pause_ms": 12,
    },
    "app_server_2": {
        "status": "healthy",
        "cpu_percent": 43.8,
        "memory_percent": 59.7,
        "error_rate": 0.002,
        "latency_ms": 42.1,
        "active_threads": 115,
        "gc_pause_ms": 11,
    },
    "database_primary": {
        "status": "healthy",
        "cpu_percent": 28.4,
        "memory_percent": 55.3,
        "error_rate": 0.0,
        "latency_ms": 8.2,
        "connections_active": 85,
        "connections_max": 200,
        "replication_lag_ms": 0,
        "slow_queries": 0,
    },
    "database_replica": {
        "status": "healthy",
        "cpu_percent": 22.1,
        "memory_percent": 48.9,
        "error_rate": 0.0,
        "latency_ms": 9.1,
        "connections_active": 45,
        "connections_max": 200,
        "replication_lag_ms": 12,
    },
    "cache_redis": {
        "status": "healthy",
        "cpu_percent": 8.5,
        "memory_percent": 42.0,
        "error_rate": 0.0,
        "latency_ms": 0.8,
        "hit_rate": 0.95,
        "evictions_per_sec": 2,
        "connected_clients": 60,
    },
    "message_queue": {
        "status": "healthy",
        "cpu_percent": 15.2,
        "memory_percent": 38.4,
        "error_rate": 0.0,
        "queue_depth": 120,
        "consumers_active": 8,
        "messages_per_sec": 450,
    },
    "cdn": {
        "status": "healthy",
        "hit_rate": 0.92,
        "origin_requests_per_sec": 680,
        "bandwidth_mbps": 1250,
        "error_rate": 0.001,
    },
    "dns": {
        "status": "healthy",
        "query_latency_ms": 1.2,
        "error_rate": 0.0,
        "cache_hit_rate": 0.88,
    },
    "auth_service": {
        "status": "healthy",
        "cpu_percent": 18.3,
        "memory_percent": 35.2,
        "error_rate": 0.001,
        "latency_ms": 22.5,
        "tokens_issued_per_min": 340,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# EASY SCENARIOS — Single incident, clear symptoms
# ═══════════════════════════════════════════════════════════════════════════════

EASY_SCENARIOS = {
    "db_connection_pool_exhaustion": {
        "id": "db_connection_pool_exhaustion",
        "title": "Database Connection Pool Exhaustion",
        "description": "Production database is running out of available connections, causing application timeouts.",
        "difficulty": "easy",
        "max_steps": 10,
        "expected_steps": 5,
        "initial_alerts": [
            {
                "id": "alert_001",
                "severity": "critical",
                "service": "database_primary",
                "title": "Connection Pool Near Exhaustion",
                "message": "Active connections: 195/200 (97.5%). New connection attempts are timing out. Application errors increasing.",
                "timestamp": "2025-01-15T14:23:00Z",
                "is_red_herring": False,
            }
        ],
        "system_status_override": {
            "database_primary": {
                "status": "degraded",
                "cpu_percent": 78.4,
                "memory_percent": 82.3,
                "error_rate": 0.15,
                "latency_ms": 2500.0,
                "connections_active": 195,
                "connections_max": 200,
                "replication_lag_ms": 450,
                "slow_queries": 23,
            },
            "app_server_1": {
                "status": "degraded",
                "cpu_percent": 35.2,
                "memory_percent": 58.1,
                "error_rate": 0.12,
                "latency_ms": 3200.0,
                "active_threads": 118,
                "gc_pause_ms": 15,
            },
        },
        "investigation_data": {
            "database_primary": {
                "logs": [
                    "[14:20:12] WARN: Connection pool utilization at 85%",
                    "[14:21:05] WARN: Connection pool utilization at 90%",
                    "[14:21:45] ERROR: Connection acquisition timeout after 30000ms",
                    "[14:22:03] ERROR: Too many connections - max_connections=200 reached",
                    "[14:22:15] WARN: 23 slow queries detected (>5s) in last minute",
                    "[14:22:30] ERROR: Connection acquisition timeout after 30000ms",
                    "[14:22:45] INFO: Stale connection detected: idle for 3600s from app_server_1:pid=4521",
                    "[14:22:50] INFO: Stale connection detected: idle for 2800s from app_server_1:pid=4522",
                    "[14:23:00] CRITICAL: Connection pool exhausted. 195/200 active, 47 stale connections identified",
                ],
                "metrics": "connections_active=195, connections_max=200, stale_connections=47, avg_query_time=4.2s, slow_queries_5m=23",
                "connections": "Total: 195/200 | Active queries: 148 | Idle/Stale: 47 | Waiting: 34",
                "config": "max_connections=200, connection_timeout=30s, idle_timeout=3600s, pool_size=200",
            },
            "app_server_1": {
                "logs": [
                    "[14:21:00] ERROR: Database connection timeout - retrying (attempt 1/3)",
                    "[14:21:30] ERROR: Database connection timeout - retrying (attempt 2/3)",
                    "[14:22:00] ERROR: Database connection timeout - all retries exhausted",
                    "[14:22:10] ERROR: HTTP 503 returned to client - database unavailable",
                    "[14:22:30] WARN: Request queue growing: 34 pending requests",
                ],
                "metrics": "error_rate=12%, avg_response_time=3200ms, pending_requests=34",
            },
        },
        "incidents": {
            "alert_001": {
                "expected_diagnosis": "database connection pool exhaustion due to stale connections",
                "diagnosis_keywords": ["connection pool", "exhaustion", "stale connections", "idle connections", "max connections"],
                "expected_priority": "P1",
                "expected_remediations": [
                    "kill stale connections",
                    "terminate idle connections",
                    "increase max connections",
                    "increase connection pool size",
                    "restart connection pool",
                ],
                "remediation_keywords": ["kill", "terminate", "stale", "idle", "increase", "pool", "restart"],
                "verification_check": "connections_active < connections_max * 0.8",
                "is_red_herring": False,
            },
        },
        "post_remediation_status": {
            "database_primary": {
                "status": "healthy",
                "cpu_percent": 35.2,
                "memory_percent": 58.1,
                "error_rate": 0.001,
                "latency_ms": 12.0,
                "connections_active": 92,
                "connections_max": 200,
                "replication_lag_ms": 15,
                "slow_queries": 0,
            },
        },
    },
    "disk_space_critical": {
        "id": "disk_space_critical",
        "title": "Disk Space Critical on Log Volume",
        "description": "Application log volume is nearly full, causing write failures and service degradation.",
        "difficulty": "easy",
        "max_steps": 10,
        "expected_steps": 5,
        "initial_alerts": [
            {
                "id": "alert_002",
                "severity": "high",
                "service": "app_server_1",
                "title": "Disk Space Critical - /var/log",
                "message": "Disk usage at 96% on /var/log volume. Only 2.1GB remaining of 50GB. Write failures detected.",
                "timestamp": "2025-01-15T09:15:00Z",
                "is_red_herring": False,
            }
        ],
        "system_status_override": {
            "app_server_1": {
                "status": "degraded",
                "cpu_percent": 48.2,
                "memory_percent": 65.1,
                "error_rate": 0.08,
                "latency_ms": 120.0,
                "active_threads": 110,
                "gc_pause_ms": 18,
                "disk_usage_percent": 96,
                "disk_available_gb": 2.1,
            },
        },
        "investigation_data": {
            "app_server_1": {
                "logs": [
                    "[09:10:00] WARN: Disk usage on /var/log at 90%",
                    "[09:12:00] WARN: Disk usage on /var/log at 93%",
                    "[09:13:30] ERROR: Failed to write to /var/log/app/application.log - No space left on device",
                    "[09:14:00] WARN: Log rotation has not run in 7 days",
                    "[09:14:15] INFO: Largest files: /var/log/app/application.log (18GB), /var/log/app/debug.log (15GB), /var/log/app/access.log (12GB)",
                    "[09:14:30] WARN: Debug logging is enabled in production (should be INFO level)",
                    "[09:15:00] ERROR: Disk usage critical at 96%",
                ],
                "metrics": "disk_total=50GB, disk_used=47.9GB, disk_available=2.1GB, largest_file=application.log(18GB)",
                "config": "log_level=DEBUG, log_rotation=weekly, log_retention=30d, max_log_size=unlimited",
            },
        },
        "incidents": {
            "alert_002": {
                "expected_diagnosis": "disk space exhaustion due to unrotated debug logs",
                "diagnosis_keywords": ["disk", "space", "log rotation", "debug log", "unrotated", "full"],
                "expected_priority": "P2",
                "expected_remediations": [
                    "rotate logs",
                    "compress logs",
                    "delete old logs",
                    "reduce log level",
                    "set log level to info",
                    "enable log rotation",
                ],
                "remediation_keywords": ["rotate", "compress", "delete", "clean", "truncate", "log level", "info"],
                "verification_check": "disk_usage_percent < 80",
                "is_red_herring": False,
            },
        },
        "post_remediation_status": {
            "app_server_1": {
                "status": "healthy",
                "cpu_percent": 45.2,
                "memory_percent": 62.1,
                "error_rate": 0.002,
                "latency_ms": 45.3,
                "active_threads": 120,
                "gc_pause_ms": 12,
                "disk_usage_percent": 45,
                "disk_available_gb": 27.5,
            },
        },
    },
    "ssl_certificate_expiry": {
        "id": "ssl_certificate_expiry",
        "title": "SSL/TLS Certificate Expired",
        "description": "Production SSL certificate has expired, causing HTTPS connection failures for all users.",
        "difficulty": "easy",
        "max_steps": 10,
        "expected_steps": 5,
        "initial_alerts": [
            {
                "id": "alert_003",
                "severity": "critical",
                "service": "load_balancer",
                "title": "SSL Certificate Expired",
                "message": "TLS certificate for *.production.example.com expired 2 hours ago. HTTPS handshake failures at 100%. All user traffic affected.",
                "timestamp": "2025-01-15T16:00:00Z",
                "is_red_herring": False,
            }
        ],
        "system_status_override": {
            "load_balancer": {
                "status": "critical",
                "cpu_percent": 8.5,
                "memory_percent": 22.3,
                "error_rate": 1.0,
                "latency_ms": 0,
                "connections_active": 0,
                "requests_per_sec": 0,
                "ssl_errors_per_sec": 8500,
                "cert_expiry": "EXPIRED (2h ago)",
            },
        },
        "investigation_data": {
            "load_balancer": {
                "logs": [
                    "[13:58:00] WARN: SSL certificate expires in 2 minutes",
                    "[14:00:00] ERROR: SSL certificate expired for *.production.example.com",
                    "[14:00:01] ERROR: TLS handshake failure - certificate expired",
                    "[14:00:05] ERROR: 850 TLS handshake failures in last 5 seconds",
                    "[14:00:10] CRITICAL: All HTTPS traffic failing - certificate expired",
                    "[16:00:00] ALERT: Certificate expired 2 hours ago. No auto-renewal configured.",
                ],
                "metrics": "ssl_errors_per_sec=8500, successful_connections=0, cert_valid=false, cert_expiry=2h_ago",
                "config": "cert_path=/etc/ssl/production.pem, auto_renew=false, cert_issuer=LetsEncrypt",
            },
        },
        "incidents": {
            "alert_003": {
                "expected_diagnosis": "SSL/TLS certificate expired with no auto-renewal",
                "diagnosis_keywords": ["ssl", "tls", "certificate", "expired", "renewal", "https"],
                "expected_priority": "P1",
                "expected_remediations": [
                    "renew certificate",
                    "renew ssl certificate",
                    "issue new certificate",
                    "update certificate",
                    "replace certificate",
                    "enable auto-renewal",
                ],
                "remediation_keywords": ["renew", "certificate", "ssl", "tls", "replace", "update", "issue"],
                "verification_check": "ssl_errors_per_sec == 0",
                "is_red_herring": False,
            },
        },
        "post_remediation_status": {
            "load_balancer": {
                "status": "healthy",
                "cpu_percent": 12.3,
                "memory_percent": 34.5,
                "error_rate": 0.001,
                "latency_ms": 2.1,
                "connections_active": 1520,
                "requests_per_sec": 8500,
                "ssl_errors_per_sec": 0,
                "cert_expiry": "valid (89 days remaining)",
            },
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# MEDIUM SCENARIOS — Multiple concurrent incidents, some correlation
# ═══════════════════════════════════════════════════════════════════════════════

MEDIUM_SCENARIOS = {
    "memory_leak_cascade": {
        "id": "memory_leak_cascade",
        "title": "Memory Leak Causing Cascading Timeouts",
        "description": "Application server has a memory leak. As memory fills, GC pauses increase, causing downstream service timeouts. Agent must identify root cause (memory leak) vs symptoms (timeouts).",
        "difficulty": "medium",
        "max_steps": 20,
        "expected_steps": 12,
        "initial_alerts": [
            {
                "id": "alert_101",
                "severity": "high",
                "service": "app_server_1",
                "title": "High Memory Usage",
                "message": "Memory usage at 94%. GC pause times averaging 850ms. Performance severely degraded.",
                "timestamp": "2025-01-15T11:30:00Z",
                "is_red_herring": False,
            },
            {
                "id": "alert_102",
                "severity": "high",
                "service": "cache_redis",
                "title": "Elevated Timeout Errors",
                "message": "Redis connection timeouts increased 500%. Commands timing out after 5000ms. Cache hit rate dropped to 45%.",
                "timestamp": "2025-01-15T11:32:00Z",
                "is_red_herring": False,
            },
            {
                "id": "alert_103",
                "severity": "medium",
                "service": "database_primary",
                "title": "Increased Query Latency",
                "message": "Average query latency increased from 8ms to 180ms. Connection wait times elevated.",
                "timestamp": "2025-01-15T11:33:00Z",
                "is_red_herring": False,
            },
        ],
        "system_status_override": {
            "app_server_1": {
                "status": "critical",
                "cpu_percent": 88.5,
                "memory_percent": 94.2,
                "error_rate": 0.25,
                "latency_ms": 4500.0,
                "active_threads": 200,
                "gc_pause_ms": 850,
                "heap_used_gb": 7.5,
                "heap_max_gb": 8.0,
            },
            "cache_redis": {
                "status": "degraded",
                "cpu_percent": 12.5,
                "memory_percent": 45.0,
                "error_rate": 0.08,
                "latency_ms": 5000.0,
                "hit_rate": 0.45,
                "evictions_per_sec": 150,
                "connected_clients": 60,
                "timeout_errors_per_sec": 45,
            },
            "database_primary": {
                "status": "degraded",
                "cpu_percent": 42.4,
                "memory_percent": 58.3,
                "error_rate": 0.04,
                "latency_ms": 180.0,
                "connections_active": 140,
                "connections_max": 200,
                "replication_lag_ms": 80,
                "slow_queries": 8,
            },
        },
        "investigation_data": {
            "app_server_1": {
                "logs": [
                    "[11:00:00] INFO: Application started. Heap: 2.1GB/8.0GB",
                    "[11:10:00] INFO: Heap: 3.5GB/8.0GB (+1.4GB in 10min)",
                    "[11:15:00] WARN: Heap usage growing abnormally: 4.8GB/8.0GB",
                    "[11:20:00] WARN: GC pause time: 320ms (threshold: 200ms)",
                    "[11:25:00] WARN: GC pause time: 580ms - Full GC triggered",
                    "[11:28:00] ERROR: GC pause time: 720ms - Request timeouts occurring",
                    "[11:30:00] CRITICAL: Heap: 7.5GB/8.0GB. GC pause: 850ms. Memory leak suspected.",
                    "[11:30:15] ERROR: OutOfMemoryError in UserSessionCache.addSession()",
                    "[11:30:20] INFO: Heap dump shows: UserSessionCache holding 2.1M entries (expected: ~50K)",
                    "[11:30:25] WARN: UserSessionCache not evicting expired sessions - eviction thread stuck",
                ],
                "metrics": "heap_used=7.5GB, heap_max=8.0GB, gc_pause_avg=850ms, gc_frequency=12/min, leaked_objects=UserSessionCache(2.1M entries)",
                "connections": "Outbound to Redis: 60 (45 timing out), Outbound to DB: 85 (12 waiting)",
                "config": "heap_size=8GB, gc_algorithm=G1GC, session_cache_max=100000, session_ttl=1800s",
            },
            "cache_redis": {
                "logs": [
                    "[11:28:00] WARN: Slow command detected: GET user:session:* took 4800ms",
                    "[11:29:00] WARN: Client connection from app_server_1 timing out frequently",
                    "[11:30:00] ERROR: 45 timeout errors/sec from app_server_1",
                    "[11:31:00] INFO: Redis server itself is healthy - problem is client-side",
                    "[11:32:00] WARN: Cache hit rate dropped due to expired entries not being refreshed",
                ],
                "metrics": "server_cpu=12%, server_memory=45%, server_latency=0.8ms, CLIENT_timeout_errors=45/sec",
            },
            "database_primary": {
                "logs": [
                    "[11:30:00] WARN: Connection wait time elevated: avg 150ms",
                    "[11:31:00] INFO: Query execution times normal (avg 8ms) - wait times are from connection pool contention",
                    "[11:32:00] WARN: app_server_1 holding connections longer than usual (avg 4.2s vs normal 0.05s)",
                    "[11:33:00] INFO: Database itself performing normally - upstream pressure from app_server_1",
                ],
                "metrics": "query_exec_time=8ms (normal), connection_wait=150ms (elevated), held_by_app_server_1=85 connections",
            },
        },
        "incidents": {
            "alert_101": {
                "expected_diagnosis": "memory leak in UserSessionCache causing GC pauses and cascading timeouts",
                "diagnosis_keywords": ["memory leak", "session cache", "gc pause", "heap", "out of memory", "eviction"],
                "expected_priority": "P1",
                "expected_remediations": [
                    "restart app server",
                    "restart application",
                    "clear session cache",
                    "flush session cache",
                    "increase heap size",
                    "fix eviction thread",
                    "rolling restart",
                ],
                "remediation_keywords": ["restart", "clear", "flush", "cache", "heap", "rolling"],
                "verification_check": "memory_percent < 70",
                "is_red_herring": False,
                "is_root_cause": True,
            },
            "alert_102": {
                "expected_diagnosis": "redis timeouts caused by slow app_server_1 client - symptom of memory leak",
                "diagnosis_keywords": ["symptom", "cascading", "client-side", "timeout", "upstream"],
                "expected_priority": "P2",
                "expected_remediations": [],
                "remediation_keywords": [],
                "verification_check": "resolves when root cause (alert_101) is fixed",
                "is_red_herring": False,
                "is_root_cause": False,
                "resolves_with": "alert_101",
            },
            "alert_103": {
                "expected_diagnosis": "database latency elevated due to app_server_1 holding connections - symptom of memory leak",
                "diagnosis_keywords": ["symptom", "cascading", "upstream", "connection holding"],
                "expected_priority": "P3",
                "expected_remediations": [],
                "remediation_keywords": [],
                "verification_check": "resolves when root cause (alert_101) is fixed",
                "is_red_herring": False,
                "is_root_cause": False,
                "resolves_with": "alert_101",
            },
        },
        "correlations": [
            {
                "incidents": ["alert_101", "alert_102", "alert_103"],
                "description": "All three alerts stem from the same root cause: memory leak in app_server_1. Redis and database issues are symptoms.",
                "root_cause": "alert_101",
            }
        ],
        "post_remediation_status": {
            "app_server_1": {
                "status": "healthy",
                "cpu_percent": 42.5,
                "memory_percent": 45.2,
                "error_rate": 0.002,
                "latency_ms": 48.0,
                "active_threads": 115,
                "gc_pause_ms": 15,
                "heap_used_gb": 3.2,
                "heap_max_gb": 8.0,
            },
            "cache_redis": {
                "status": "healthy",
                "cpu_percent": 8.5,
                "memory_percent": 42.0,
                "error_rate": 0.0,
                "latency_ms": 0.8,
                "hit_rate": 0.95,
                "evictions_per_sec": 2,
                "connected_clients": 60,
                "timeout_errors_per_sec": 0,
            },
            "database_primary": {
                "status": "healthy",
                "cpu_percent": 28.4,
                "memory_percent": 55.3,
                "error_rate": 0.0,
                "latency_ms": 8.2,
                "connections_active": 85,
                "connections_max": 200,
                "replication_lag_ms": 12,
                "slow_queries": 0,
            },
        },
    },
    "dns_deploy_failure": {
        "id": "dns_deploy_failure",
        "title": "DNS Misconfiguration Causing Deployment Failures",
        "description": "A DNS record was incorrectly updated during a migration, causing service discovery failures. Subsequent deployments are failing health checks because they can't reach dependencies.",
        "difficulty": "medium",
        "max_steps": 20,
        "expected_steps": 13,
        "initial_alerts": [
            {
                "id": "alert_201",
                "severity": "high",
                "service": "dns",
                "title": "DNS Resolution Failures",
                "message": "DNS resolution failures for api-internal.example.com. NXDOMAIN responses. Multiple services affected.",
                "timestamp": "2025-01-15T10:05:00Z",
                "is_red_herring": False,
            },
            {
                "id": "alert_202",
                "severity": "high",
                "service": "app_server_1",
                "title": "Deployment Health Check Failing",
                "message": "New deployment v2.4.1 health checks failing. Cannot reach auth-service via service discovery. Rolling back.",
                "timestamp": "2025-01-15T10:08:00Z",
                "is_red_herring": False,
            },
            {
                "id": "alert_203",
                "severity": "medium",
                "service": "auth_service",
                "title": "Auth Service Unreachable",
                "message": "Auth service health endpoint returning 503. Token validation requests failing from app_server_1.",
                "timestamp": "2025-01-15T10:10:00Z",
                "is_red_herring": False,
            },
        ],
        "system_status_override": {
            "dns": {
                "status": "degraded",
                "query_latency_ms": 1.2,
                "error_rate": 0.35,
                "cache_hit_rate": 0.88,
                "nxdomain_rate": 0.35,
                "failed_lookups": ["api-internal.example.com", "auth.internal.example.com"],
            },
            "app_server_1": {
                "status": "degraded",
                "cpu_percent": 38.2,
                "memory_percent": 55.1,
                "error_rate": 0.15,
                "latency_ms": 850.0,
                "active_threads": 95,
                "deployment_status": "rolling_back_v2.4.1",
            },
            "auth_service": {
                "status": "degraded",
                "cpu_percent": 5.3,
                "memory_percent": 25.2,
                "error_rate": 0.30,
                "latency_ms": 25.5,
                "tokens_issued_per_min": 12,
            },
        },
        "investigation_data": {
            "dns": {
                "logs": [
                    "[10:00:00] INFO: DNS zone update initiated by admin@example.com",
                    "[10:00:05] INFO: Record updated: api-internal.example.com A 10.0.1.50 -> DELETED",
                    "[10:00:06] INFO: Record added: api-internal-v2.example.com A 10.0.1.50",
                    "[10:00:10] WARN: Zone propagation complete. Old record api-internal.example.com no longer exists.",
                    "[10:05:00] ERROR: NXDOMAIN for api-internal.example.com - 127 queries failed in last minute",
                    "[10:05:30] INFO: Note: 14 services still reference api-internal.example.com in their configs",
                ],
                "metrics": "nxdomain_rate=35%, failed_queries=api-internal.example.com(127/min), auth.internal.example.com(45/min)",
                "config": "zone=internal.example.com, last_update=10:00:05 by admin@example.com, ttl=300s",
            },
            "app_server_1": {
                "logs": [
                    "[10:05:00] INFO: Starting deployment v2.4.1",
                    "[10:05:30] INFO: Health check: checking dependencies...",
                    "[10:05:35] ERROR: Cannot resolve api-internal.example.com - DNS NXDOMAIN",
                    "[10:05:40] ERROR: Cannot reach auth-service at auth.internal.example.com",
                    "[10:06:00] ERROR: Health check FAILED - 2 dependencies unreachable",
                    "[10:06:30] INFO: Rolling back to v2.4.0",
                    "[10:07:00] WARN: v2.4.0 also experiencing intermittent DNS failures",
                ],
                "metrics": "deployment_status=rolled_back, dns_failures=172/min, error_rate=15%",
                "config": "service_discovery=dns, auth_service_url=http://auth.internal.example.com:8080, api_url=http://api-internal.example.com:8000",
            },
            "auth_service": {
                "logs": [
                    "[10:05:00] INFO: Auth service is running normally on 10.0.2.30:8080",
                    "[10:06:00] WARN: Incoming requests dropped 95% - clients can't find us",
                    "[10:08:00] INFO: Service is healthy but unreachable via DNS name auth.internal.example.com",
                    "[10:09:00] INFO: Direct IP access (10.0.2.30:8080) works fine",
                ],
                "metrics": "service_healthy=true, reachable_by_dns=false, reachable_by_ip=true, ip=10.0.2.30",
            },
        },
        "incidents": {
            "alert_201": {
                "expected_diagnosis": "DNS record incorrectly deleted during migration - api-internal.example.com removed instead of renamed",
                "diagnosis_keywords": ["dns", "record", "deleted", "migration", "nxdomain", "misconfiguration"],
                "expected_priority": "P1",
                "expected_remediations": [
                    "restore dns record",
                    "add dns record",
                    "create dns record",
                    "fix dns record",
                    "update dns",
                    "add A record",
                ],
                "remediation_keywords": ["restore", "add", "create", "fix", "dns", "record", "A record"],
                "verification_check": "nxdomain_rate == 0",
                "is_red_herring": False,
                "is_root_cause": True,
            },
            "alert_202": {
                "expected_diagnosis": "deployment failing because of DNS resolution failure - symptom of DNS misconfiguration",
                "diagnosis_keywords": ["symptom", "dns", "deployment", "health check", "service discovery"],
                "expected_priority": "P2",
                "expected_remediations": ["retry deployment after dns fix"],
                "remediation_keywords": ["retry", "redeploy", "deploy"],
                "verification_check": "deployment_status == healthy",
                "is_red_herring": False,
                "is_root_cause": False,
                "resolves_with": "alert_201",
            },
            "alert_203": {
                "expected_diagnosis": "auth service healthy but unreachable via DNS - symptom of DNS misconfiguration",
                "diagnosis_keywords": ["symptom", "dns", "unreachable", "healthy"],
                "expected_priority": "P2",
                "expected_remediations": [],
                "remediation_keywords": [],
                "verification_check": "resolves when root cause (alert_201) is fixed",
                "is_red_herring": False,
                "is_root_cause": False,
                "resolves_with": "alert_201",
            },
        },
        "correlations": [
            {
                "incidents": ["alert_201", "alert_202", "alert_203"],
                "description": "All alerts caused by the DNS record deletion. Auth service is healthy but unreachable via DNS.",
                "root_cause": "alert_201",
            }
        ],
        "post_remediation_status": {
            "dns": {
                "status": "healthy",
                "query_latency_ms": 1.2,
                "error_rate": 0.0,
                "cache_hit_rate": 0.88,
                "nxdomain_rate": 0.0,
            },
            "app_server_1": {
                "status": "healthy",
                "cpu_percent": 45.2,
                "memory_percent": 62.1,
                "error_rate": 0.002,
                "latency_ms": 45.3,
                "active_threads": 120,
                "deployment_status": "healthy_v2.4.1",
            },
            "auth_service": {
                "status": "healthy",
                "cpu_percent": 18.3,
                "memory_percent": 35.2,
                "error_rate": 0.001,
                "latency_ms": 22.5,
                "tokens_issued_per_min": 340,
            },
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# HARD SCENARIOS — Cascading failures, red herrings, complex root cause
# ═══════════════════════════════════════════════════════════════════════════════

HARD_SCENARIOS = {
    "full_stack_cascade": {
        "id": "full_stack_cascade",
        "title": "Full Stack Cascade from Database Migration",
        "description": "A database migration locked a critical table, causing a cascade: DB slow → app servers queue up → load balancer health checks fail → cache stampede. Red herring: cache eviction spike looks alarming but is normal under load.",
        "difficulty": "hard",
        "max_steps": 30,
        "expected_steps": 20,
        "initial_alerts": [
            {
                "id": "alert_301",
                "severity": "critical",
                "service": "load_balancer",
                "title": "Backend Health Checks Failing",
                "message": "3/4 backend servers failing health checks. Traffic being routed to single healthy backend. Latency spiking.",
                "timestamp": "2025-01-15T15:45:00Z",
                "is_red_herring": False,
            },
            {
                "id": "alert_302",
                "severity": "critical",
                "service": "app_server_1",
                "title": "Request Queue Overflow",
                "message": "Request queue at 500+ (limit 200). Thread pool exhausted. 502 errors returned to clients.",
                "timestamp": "2025-01-15T15:44:00Z",
                "is_red_herring": False,
            },
            {
                "id": "alert_303",
                "severity": "critical",
                "service": "database_primary",
                "title": "Table Lock Timeout",
                "message": "Table 'users' locked for 12 minutes. 340 queries waiting on lock. Replication lag at 45 seconds.",
                "timestamp": "2025-01-15T15:35:00Z",
                "is_red_herring": False,
            },
            {
                "id": "alert_304",
                "severity": "high",
                "service": "cache_redis",
                "title": "Cache Eviction Storm",
                "message": "Cache evictions at 2000/sec (normal: 2/sec). Memory pressure at 92%. Cache hit rate dropped to 15%.",
                "timestamp": "2025-01-15T15:43:00Z",
                "is_red_herring": True,
            },
            {
                "id": "alert_305",
                "severity": "medium",
                "service": "message_queue",
                "title": "Queue Depth Growing",
                "message": "Message queue depth at 15000 (normal: 120). Consumers unable to process - dependent services slow.",
                "timestamp": "2025-01-15T15:44:00Z",
                "is_red_herring": False,
            },
        ],
        "system_status_override": {
            "load_balancer": {
                "status": "critical",
                "cpu_percent": 45.3,
                "memory_percent": 52.1,
                "error_rate": 0.75,
                "latency_ms": 12000.0,
                "connections_active": 8500,
                "requests_per_sec": 2100,
                "healthy_backends": 1,
                "total_backends": 4,
            },
            "app_server_1": {
                "status": "critical",
                "cpu_percent": 95.8,
                "memory_percent": 88.4,
                "error_rate": 0.65,
                "latency_ms": 15000.0,
                "active_threads": 200,
                "gc_pause_ms": 120,
                "request_queue": 523,
                "request_queue_max": 200,
            },
            "app_server_2": {
                "status": "critical",
                "cpu_percent": 94.2,
                "memory_percent": 86.1,
                "error_rate": 0.60,
                "latency_ms": 14500.0,
                "active_threads": 200,
                "gc_pause_ms": 115,
                "request_queue": 489,
                "request_queue_max": 200,
            },
            "database_primary": {
                "status": "critical",
                "cpu_percent": 92.4,
                "memory_percent": 78.3,
                "error_rate": 0.40,
                "latency_ms": 12000.0,
                "connections_active": 200,
                "connections_max": 200,
                "replication_lag_ms": 45000,
                "slow_queries": 340,
                "locked_tables": ["users"],
                "lock_duration_min": 12,
            },
            "cache_redis": {
                "status": "degraded",
                "cpu_percent": 78.5,
                "memory_percent": 92.0,
                "error_rate": 0.05,
                "latency_ms": 15.0,
                "hit_rate": 0.15,
                "evictions_per_sec": 2000,
                "connected_clients": 180,
            },
            "message_queue": {
                "status": "degraded",
                "cpu_percent": 55.2,
                "memory_percent": 68.4,
                "error_rate": 0.02,
                "queue_depth": 15000,
                "consumers_active": 8,
                "messages_per_sec": 45,
            },
        },
        "investigation_data": {
            "database_primary": {
                "logs": [
                    "[15:33:00] INFO: Migration started: ALTER TABLE users ADD COLUMN preferences JSONB",
                    "[15:33:01] INFO: Acquiring exclusive lock on table 'users'",
                    "[15:33:02] WARN: Table 'users' locked. 12 active transactions must complete first.",
                    "[15:33:30] WARN: Waiting for 8 long-running transactions to complete before lock acquired",
                    "[15:34:00] INFO: Lock acquired. Migration running. Table size: 45M rows.",
                    "[15:35:00] WARN: Migration in progress. 340 queries queued waiting for lock release.",
                    "[15:37:00] ERROR: Replication lag at 15 seconds and growing",
                    "[15:40:00] ERROR: Replication lag at 30 seconds",
                    "[15:42:00] ERROR: Connection pool exhausted. 200/200 connections active.",
                    "[15:45:00] CRITICAL: Migration still running after 12 minutes. Lock held on 'users' table.",
                ],
                "metrics": "lock_type=exclusive, locked_table=users, lock_duration=12min, waiting_queries=340, migration=ALTER_TABLE_ADD_COLUMN",
                "connections": "Total: 200/200 | Waiting on lock: 340 | Migration PID: 4521",
                "config": "migration_timeout=none, lock_timeout=none, statement_timeout=none",
            },
            "app_server_1": {
                "logs": [
                    "[15:34:00] WARN: Database queries to 'users' table taking >10s",
                    "[15:35:00] ERROR: Thread pool exhausted - all 200 threads waiting on DB",
                    "[15:36:00] ERROR: Request queue overflow: 200 -> 350 -> 450",
                    "[15:38:00] ERROR: HTTP 502 errors at 65%",
                    "[15:40:00] CRITICAL: All requests timing out. Server effectively down.",
                ],
                "metrics": "all_threads_blocked_on_db=true, queue_size=523, error_rate=65%",
            },
            "load_balancer": {
                "logs": [
                    "[15:40:00] WARN: app_server_1 health check failed (3 consecutive)",
                    "[15:40:30] WARN: app_server_2 health check failed (3 consecutive)",
                    "[15:41:00] WARN: app_server_3 health check failed",
                    "[15:41:30] INFO: Only app_server_4 passing health checks (not using 'users' table queries)",
                    "[15:42:00] CRITICAL: 3/4 backends DOWN. Routing all traffic to single backend.",
                ],
                "metrics": "healthy_backends=1/4, error_rate=75%, latency=12000ms",
            },
            "cache_redis": {
                "logs": [
                    "[15:35:00] INFO: Cache miss rate increasing - app servers requesting data that's normally cached",
                    "[15:38:00] WARN: Memory pressure causing evictions. This is NORMAL behavior under cache stampede.",
                    "[15:40:00] INFO: Eviction rate = 2000/sec. This is expected when backend is slow and cache entries expire.",
                    "[15:42:00] INFO: Redis itself is healthy. High eviction is a SYMPTOM of backend slowness, not a cause.",
                    "[15:43:00] INFO: Once backend recovers, cache will repopulate automatically.",
                ],
                "metrics": "redis_server_healthy=true, evictions_are_symptom=true, no_action_needed=true",
            },
            "message_queue": {
                "logs": [
                    "[15:36:00] WARN: Consumer processing slowed - consumers depend on 'users' table queries",
                    "[15:38:00] WARN: Queue depth growing: 120 -> 5000 -> 10000",
                    "[15:44:00] ERROR: Queue depth at 15000. Consumers blocked on database.",
                ],
                "metrics": "queue_depth=15000, consumer_blocked_on=database, processing_rate=45msg/sec(normal:450)",
            },
        },
        "incidents": {
            "alert_303": {
                "expected_diagnosis": "database migration locked the users table causing full stack cascade",
                "diagnosis_keywords": ["migration", "table lock", "users table", "alter table", "exclusive lock", "root cause"],
                "expected_priority": "P1",
                "expected_remediations": [
                    "kill migration",
                    "cancel migration",
                    "terminate migration",
                    "release lock",
                    "kill migration process",
                    "pg_terminate_backend",
                    "kill pid 4521",
                ],
                "remediation_keywords": ["kill", "cancel", "terminate", "migration", "lock", "release", "pid"],
                "verification_check": "locked_tables == [] and slow_queries < 5",
                "is_red_herring": False,
                "is_root_cause": True,
            },
            "alert_302": {
                "expected_diagnosis": "app server queue overflow due to database lock - symptom",
                "diagnosis_keywords": ["symptom", "database", "blocked", "queue", "overflow"],
                "expected_priority": "P1",
                "expected_remediations": [],
                "remediation_keywords": [],
                "verification_check": "resolves when root cause (alert_303) is fixed",
                "is_red_herring": False,
                "is_root_cause": False,
                "resolves_with": "alert_303",
            },
            "alert_301": {
                "expected_diagnosis": "load balancer health checks failing because backend app servers are down - symptom",
                "diagnosis_keywords": ["symptom", "health check", "backend", "down"],
                "expected_priority": "P1",
                "expected_remediations": [],
                "remediation_keywords": [],
                "verification_check": "resolves when root cause (alert_303) is fixed",
                "is_red_herring": False,
                "is_root_cause": False,
                "resolves_with": "alert_303",
            },
            "alert_304": {
                "expected_diagnosis": "cache eviction storm is normal behavior under load - red herring",
                "diagnosis_keywords": ["red herring", "normal", "expected", "symptom", "no action"],
                "expected_priority": "P4",
                "expected_remediations": [],
                "remediation_keywords": [],
                "verification_check": "no action needed - self-resolves",
                "is_red_herring": True,
                "is_root_cause": False,
            },
            "alert_305": {
                "expected_diagnosis": "message queue backlog due to consumers blocked on database - symptom",
                "diagnosis_keywords": ["symptom", "database", "blocked", "consumers", "backlog"],
                "expected_priority": "P2",
                "expected_remediations": [],
                "remediation_keywords": [],
                "verification_check": "resolves when root cause (alert_303) is fixed",
                "is_red_herring": False,
                "is_root_cause": False,
                "resolves_with": "alert_303",
            },
        },
        "correlations": [
            {
                "incidents": ["alert_301", "alert_302", "alert_303", "alert_305"],
                "description": "All alerts cascade from database migration locking the users table. Cache eviction (alert_304) is a normal side-effect, not a problem.",
                "root_cause": "alert_303",
            }
        ],
        "post_remediation_status": {
            "load_balancer": {
                "status": "healthy",
                "cpu_percent": 12.3,
                "memory_percent": 34.5,
                "error_rate": 0.001,
                "latency_ms": 2.1,
                "connections_active": 1520,
                "requests_per_sec": 8500,
                "healthy_backends": 4,
                "total_backends": 4,
            },
            "app_server_1": {
                "status": "healthy",
                "cpu_percent": 45.2,
                "memory_percent": 62.1,
                "error_rate": 0.002,
                "latency_ms": 45.3,
                "active_threads": 120,
                "gc_pause_ms": 12,
                "request_queue": 5,
                "request_queue_max": 200,
            },
            "app_server_2": {
                "status": "healthy",
                "cpu_percent": 43.8,
                "memory_percent": 59.7,
                "error_rate": 0.002,
                "latency_ms": 42.1,
                "active_threads": 115,
                "gc_pause_ms": 11,
            },
            "database_primary": {
                "status": "healthy",
                "cpu_percent": 28.4,
                "memory_percent": 55.3,
                "error_rate": 0.0,
                "latency_ms": 8.2,
                "connections_active": 85,
                "connections_max": 200,
                "replication_lag_ms": 12,
                "slow_queries": 0,
                "locked_tables": [],
                "lock_duration_min": 0,
            },
            "cache_redis": {
                "status": "healthy",
                "cpu_percent": 8.5,
                "memory_percent": 42.0,
                "error_rate": 0.0,
                "latency_ms": 0.8,
                "hit_rate": 0.95,
                "evictions_per_sec": 2,
                "connected_clients": 60,
            },
            "message_queue": {
                "status": "healthy",
                "cpu_percent": 15.2,
                "memory_percent": 38.4,
                "error_rate": 0.0,
                "queue_depth": 120,
                "consumers_active": 8,
                "messages_per_sec": 450,
            },
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

ALL_SCENARIOS = {
    **EASY_SCENARIOS,
    **MEDIUM_SCENARIOS,
    **HARD_SCENARIOS,
}

TASK_SCENARIO_MAP = {
    "single_incident": list(EASY_SCENARIOS.keys()),
    "multi_incident": list(MEDIUM_SCENARIOS.keys()),
    "cascading_failure": list(HARD_SCENARIOS.keys()),
}


def get_scenario(scenario_id: str, seed: int | None = None) -> dict:
    """Get a deep copy of a scenario by ID."""
    if scenario_id not in ALL_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_id}. Available: {list(ALL_SCENARIOS.keys())}")
    return copy.deepcopy(ALL_SCENARIOS[scenario_id])


def get_scenario_for_task(task_name: str, seed: int | None = None) -> dict:
    """Get a scenario for a given task. Uses seed for deterministic selection."""
    if task_name not in TASK_SCENARIO_MAP:
        raise ValueError(f"Unknown task: {task_name}. Available: {list(TASK_SCENARIO_MAP.keys())}")

    scenarios = TASK_SCENARIO_MAP[task_name]

    if seed is not None:
        rng = random.Random(seed)
        scenario_id = rng.choice(scenarios)
    else:
        # Default: pick first scenario for reproducibility
        scenario_id = scenarios[0]

    return get_scenario(scenario_id, seed)


def get_initial_system_status(scenario: dict) -> dict:
    """Build the full system status by overlaying scenario overrides on healthy defaults."""
    status = copy.deepcopy(HEALTHY_SERVICES)
    for service, overrides in scenario.get("system_status_override", {}).items():
        if service in status:
            status[service].update(overrides)
        else:
            status[service] = overrides
    return status
