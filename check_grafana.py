#!/usr/bin/env python3
"""
Проверка метрик в Grafana - тестирование доступности через datasource
"""
import requests
import json

def check_grafana_datasource():
    """Проверка подключения к VictoriaMetrics через Grafana"""
    grafana_url = "http://localhost:3000"
    # Default admin credentials
    auth = ("admin", "admin")
    
    print("="*80)
    print("🔍 CHECKING GRAFANA")
    print("="*80)
    print()
    
    # Проверяем datasources
    print("📊 Checking datasources...")
    try:
        response = requests.get(f"{grafana_url}/api/datasources", auth=auth, timeout=10)
        response.raise_for_status()
        datasources = response.json()
        
        print(f"   Found {len(datasources)} datasource(s)")
        
        vm_datasource = None
        for ds in datasources:
            print(f"   - {ds['name']} ({ds['type']}): {ds['url']}")
            if 'victoria' in ds['name'].lower() or ds['url'] == 'http://localhost:8428':
                vm_datasource = ds
        
        if not vm_datasource:
            print("\n❌ VictoriaMetrics datasource not found!")
            return False
        
        print(f"\n✅ Found VictoriaMetrics datasource: {vm_datasource['name']}")
        print()
        
        # Проверяем доступность метрик через datasource
        print("🔍 Checking metrics availability in Grafana...")
        
        # Тестовый запрос метрик
        test_query = {
            "queries": [{
                "datasourceId": vm_datasource['id'],
                "expr": "huawei_usage_percent{SN=\"2102355THQFSQ2100014\"}",
                "refId": "A",
                "instant": False,
                "range": True,
                "start": 1760310000000,
                "end": 1760400000000
            }]
        }
        
        response = requests.post(
            f"{grafana_url}/api/ds/query",
            auth=auth,
            json=test_query,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'results' in result and result['results']:
                print("✅ Successfully queried metrics through Grafana!")
                print(f"   Query returned {len(result['results'])} result(s)")
                return True
            else:
                print("⚠️  Query succeeded but returned no data")
                print(f"   Response: {result}")
                return False
        else:
            print(f"❌ Query failed with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print()
    success = check_grafana_datasource()
    print()
    print("="*80)
    if success:
        print("✅ ALL CHECKS PASSED!")
        print("   Metrics are accessible in Grafana")
    else:
        print("⚠️  SOME CHECKS FAILED")
        print("   Please verify Grafana configuration")
    print("="*80)
    print()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())

