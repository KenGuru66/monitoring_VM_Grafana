#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom MCP Server for Huawei Storage Monitoring Project.
Provides high-level operations specific to this project.

Usage:
    python3 mcp_huawei_server.py <command> [args]

Commands:
    list_arrays              - List all storage arrays in VictoriaMetrics
    check_unknown [SN]       - Check for unknown metrics (optionally for specific array)
    metric_stats <SN>        - Get metric statistics for array
    list_jobs                - List all processing jobs
    check_grafana            - Check Grafana health
    check_vm                 - Check VictoriaMetrics health
    array_metrics <SN>       - Get all metrics for specific array
    recent_unknown           - Find recently added unknown metrics
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print(json.dumps({"error": "requests library not available"}))
    sys.exit(1)

# Configuration from environment or defaults
VM_URL = os.getenv("VM_URL", "http://localhost:8428")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
API_URL = os.getenv("API_URL", "http://localhost:8000")


class HuaweiMCPServer:
    """MCP Server with project-specific operations."""
    
    def __init__(self, vm_url: str = VM_URL, grafana_url: str = GRAFANA_URL, api_url: str = API_URL):
        """Initialize with service URLs."""
        self.vm_url = vm_url
        self.grafana_url = grafana_url
        self.api_url = api_url
    
    def list_arrays(self) -> Dict:
        """List all storage arrays in VictoriaMetrics."""
        try:
            response = requests.get(
                f"{self.vm_url}/api/v1/label/SN/values",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            arrays = data.get("data", [])
            return {
                "success": True,
                "arrays": sorted(arrays),
                "count": len(arrays),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_unknown_metrics(self, sn: Optional[str] = None) -> Dict:
        """Check for unknown metrics in VictoriaMetrics."""
        try:
            # Query for unknown metrics
            query = '{__name__=~"huawei_unknown_.*"'
            if sn:
                query += f',SN="{sn}"'
            query += '}'
            
            response = requests.get(
                f"{self.vm_url}/api/v1/query",
                params={"query": query},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("data", {}).get("result", [])
            
            # Extract unique metric names and resources
            unknown_metrics = set()
            unknown_resources = set()
            
            for result in results:
                metric_name = result.get("metric", {}).get("__name__", "")
                if metric_name.startswith("huawei_unknown_metric_"):
                    metric_id = metric_name.replace("huawei_unknown_metric_", "")
                    unknown_metrics.add(metric_id)
                
                resource = result.get("metric", {}).get("Resource", "")
                if resource.startswith("UNKNOWN_RESOURCE_"):
                    resource_id = resource.replace("UNKNOWN_RESOURCE_", "")
                    unknown_resources.add(resource_id)
            
            return {
                "success": True,
                "array": sn if sn else "all",
                "has_unknown": len(results) > 0,
                "total_series": len(results),
                "unknown_metric_ids": sorted(list(unknown_metrics)),
                "unknown_resource_ids": sorted(list(unknown_resources)),
                "unknown_metric_count": len(unknown_metrics),
                "unknown_resource_count": len(unknown_resources),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_metric_stats(self, sn: str) -> Dict:
        """Get statistics about metrics for an array."""
        try:
            # Total unique metrics
            query_total = f'count by(__name__) ({{SN="{sn}"}})'
            response = requests.get(
                f"{self.vm_url}/api/v1/query",
                params={"query": query_total},
                timeout=10
            )
            response.raise_for_status()
            total_data = response.json()
            total_metrics = len(total_data.get("data", {}).get("result", []))
            
            # Unknown metrics
            query_unknown = f'count by(__name__) ({{SN="{sn}",__name__=~"huawei_unknown_.*"}})'
            response = requests.get(
                f"{self.vm_url}/api/v1/query",
                params={"query": query_unknown},
                timeout=10
            )
            response.raise_for_status()
            unknown_data = response.json()
            unknown_metrics = len(unknown_data.get("data", {}).get("result", []))
            
            # Resources
            query_resources = f'count by(Resource) ({{SN="{sn}"}})'
            response = requests.get(
                f"{self.vm_url}/api/v1/query",
                params={"query": query_resources},
                timeout=10
            )
            response.raise_for_status()
            resources_data = response.json()
            resources = [r.get("metric", {}).get("Resource", "") for r in resources_data.get("data", {}).get("result", [])]
            
            return {
                "success": True,
                "array": sn,
                "total_metrics": total_metrics,
                "unknown_metrics": unknown_metrics,
                "known_metrics": total_metrics - unknown_metrics,
                "total_resources": len(resources),
                "resources": sorted(resources),
                "completeness_percent": round((total_metrics - unknown_metrics) / total_metrics * 100, 2) if total_metrics > 0 else 0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_jobs(self) -> Dict:
        """List all processing jobs from API."""
        try:
            response = requests.get(f"{self.api_url}/api/jobs", timeout=10)
            response.raise_for_status()
            jobs = response.json()
            
            return {
                "success": True,
                "jobs": jobs,
                "count": len(jobs),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_grafana_health(self) -> Dict:
        """Check Grafana API health."""
        try:
            response = requests.get(f"{self.grafana_url}/api/health", timeout=5)
            return {
                "success": True,
                "healthy": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else None,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "healthy": False,
                "error": str(e)
            }
    
    def check_vm_health(self) -> Dict:
        """Check VictoriaMetrics health."""
        try:
            response = requests.get(f"{self.vm_url}/health", timeout=5)
            return {
                "success": True,
                "healthy": response.status_code == 200,
                "status_code": response.status_code,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "healthy": False,
                "error": str(e)
            }
    
    def get_array_metrics(self, sn: str, limit: int = 100) -> Dict:
        """Get list of all metrics for specific array."""
        try:
            query = f'count by(__name__) ({{SN="{sn}"}})'
            response = requests.get(
                f"{self.vm_url}/api/v1/query",
                params={"query": query},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("data", {}).get("result", [])
            metrics = [r.get("metric", {}).get("__name__", "") for r in results]
            
            # Separate known and unknown
            known = [m for m in metrics if not m.startswith("huawei_unknown_")]
            unknown = [m for m in metrics if m.startswith("huawei_unknown_")]
            
            return {
                "success": True,
                "array": sn,
                "total_count": len(metrics),
                "known_count": len(known),
                "unknown_count": len(unknown),
                "known_metrics": sorted(known)[:limit],
                "unknown_metrics": sorted(unknown)[:limit],
                "truncated": len(metrics) > limit,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_recent_unknown(self, hours: int = 24) -> Dict:
        """Find recently added unknown metrics."""
        try:
            # Query for unknown metrics in recent time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            query = '{__name__=~"huawei_unknown_.*"}'
            response = requests.get(
                f"{self.vm_url}/api/v1/query",
                params={
                    "query": query,
                    "time": end_time.timestamp()
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("data", {}).get("result", [])
            
            # Group by array
            by_array = {}
            for result in results:
                metric = result.get("metric", {})
                sn = metric.get("SN", "unknown")
                metric_name = metric.get("__name__", "")
                
                if sn not in by_array:
                    by_array[sn] = set()
                by_array[sn].add(metric_name)
            
            return {
                "success": True,
                "time_range_hours": hours,
                "arrays_with_unknown": len(by_array),
                "arrays": {sn: sorted(list(metrics)) for sn, metrics in by_array.items()},
                "total_unknown_series": len(results),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def print_help():
    """Print help message."""
    help_text = """
Huawei Storage Monitoring MCP Server

Usage: python3 mcp_huawei_server.py <command> [args]

Commands:
  list_arrays              List all storage arrays in VictoriaMetrics
  check_unknown [SN]       Check for unknown metrics (optionally for specific array)
  metric_stats <SN>        Get metric statistics for array
  list_jobs                List all processing jobs from API
  check_grafana            Check Grafana health
  check_vm                 Check VictoriaMetrics health
  array_metrics <SN> [N]   Get metrics for array (limit N, default 100)
  recent_unknown [hours]   Find recently added unknown metrics (default 24h)
  help                     Show this help message

Environment Variables:
  VM_URL         VictoriaMetrics URL (default: http://localhost:8428)
  GRAFANA_URL    Grafana URL (default: http://localhost:3000)
  API_URL        API URL (default: http://localhost:8000)

Examples:
  python3 mcp_huawei_server.py list_arrays
  python3 mcp_huawei_server.py check_unknown 2102355THQFSQ
  python3 mcp_huawei_server.py metric_stats 2102355THQFSQ
  python3 mcp_huawei_server.py array_metrics 2102355THQFSQ 50
  python3 mcp_huawei_server.py recent_unknown 48
"""
    print(help_text)


def main():
    """MCP Server main entry point."""
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command in ["help", "--help", "-h"]:
        print_help()
        sys.exit(0)
    
    server = HuaweiMCPServer()
    
    try:
        if command == "list_arrays":
            result = server.list_arrays()
        
        elif command == "check_unknown":
            sn = sys.argv[2] if len(sys.argv) > 2 else None
            result = server.check_unknown_metrics(sn)
        
        elif command == "metric_stats":
            if len(sys.argv) < 3:
                result = {"success": False, "error": "Array SN required"}
            else:
                result = server.get_metric_stats(sys.argv[2])
        
        elif command == "list_jobs":
            result = server.list_jobs()
        
        elif command == "check_grafana":
            result = server.check_grafana_health()
        
        elif command == "check_vm":
            result = server.check_vm_health()
        
        elif command == "array_metrics":
            if len(sys.argv) < 3:
                result = {"success": False, "error": "Array SN required"}
            else:
                limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
                result = server.get_array_metrics(sys.argv[2], limit)
        
        elif command == "recent_unknown":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            result = server.get_recent_unknown(hours)
        
        else:
            result = {"success": False, "error": f"Unknown command: {command}"}
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result.get("success", False) else 1)
        
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()


