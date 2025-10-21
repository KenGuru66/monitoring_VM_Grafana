# 🔌 MCP Server Recommendations для Huawei Storage Monitoring Project

## 📊 Рекомендуемые MCP серверы

### 1. 🐳 **Docker MCP Server** (Обязательно!)

**Почему нужен:**
- Ваш проект полностью построен на Docker Compose
- 4 сервиса: VictoriaMetrics, Grafana, API, Web
- Частые операции с контейнерами

**Возможности:**
- Просмотр статуса контейнеров
- Чтение логов в реальном времени
- Управление контейнерами (start/stop/restart)
- Просмотр использования ресурсов
- Exec команды в контейнерах

**Установка:**
```bash
npm install -g @modelcontextprotocol/server-docker
```

**Настройка в Cursor:**
```json
{
  "mcpServers": {
    "docker": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-docker"]
    }
  }
}
```

**Примеры использования:**
- "Покажи логи API контейнера за последние 100 строк"
- "Какие контейнеры сейчас запущены?"
- "Перезапусти VictoriaMetrics контейнер"
- "Сколько памяти использует Grafana?"

---

### 2. 📊 **Prometheus/VictoriaMetrics MCP Server**

**Почему нужен:**
- Прямой доступ к метрикам в VictoriaMetrics
- Проверка данных без открытия браузера
- Отладка запросов PromQL

**Возможности:**
- Выполнение PromQL запросов
- Просмотр labels и series
- Проверка метрик после загрузки
- Анализ производительности запросов

**Установка:**
```bash
# Custom MCP server - нужно создать
npm install -g @prometheus/prometheus-mcp-server
```

**Альтернатива** (пока нет официального):
Создайте простой скрипт-обертку:

```python
# mcp_victoria_wrapper.py
#!/usr/bin/env python3
"""MCP wrapper for VictoriaMetrics queries."""
import sys
import json
import requests

VM_URL = "http://localhost:8428"

def query_vm(promql: str):
    """Execute PromQL query."""
    response = requests.get(f"{VM_URL}/api/v1/query", params={"query": promql})
    return response.json()

def list_labels():
    """Get all label names."""
    response = requests.get(f"{VM_URL}/api/v1/labels")
    return response.json()

def label_values(label: str):
    """Get values for specific label."""
    response = requests.get(f"{VM_URL}/api/v1/label/{label}/values")
    return response.json()

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if command == "query":
        result = query_vm(sys.argv[2])
        print(json.dumps(result, indent=2))
    elif command == "labels":
        result = list_labels()
        print(json.dumps(result, indent=2))
    elif command == "label_values":
        result = label_values(sys.argv[2])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: mcp_victoria_wrapper.py [query|labels|label_values] [args]")
```

**Примеры использования:**
- "Покажи все массивы (SN) в VictoriaMetrics"
- "Выполни запрос: huawei_read_bandwidth_mb_s{SN='2102355THQFSQ'}"
- "Какие метрики доступны для массива 2102355THQFSQ?"
- "Есть ли unknown метрики в базе?"

---

### 3. 📁 **Filesystem MCP Server** (Встроенный в Cursor)

**Почему нужен:**
- Анализ больших файлов (CSV, logs)
- Поиск по файловой системе
- Мониторинг размеров директорий

**Возможности:**
- Рекурсивный поиск файлов
- Чтение больших файлов порциями
- Подсчет размеров директорий
- Поиск по содержимому

**Уже доступен в Cursor!**

**Примеры использования:**
- "Найди все .tgz файлы в директории uploads"
- "Какой размер директории /data/vmdata?"
- "Покажи последние 50 строк streaming_pipeline.log"
- "Сколько CSV файлов в /app/jobs?"

---

### 4. 🗄️ **SQLite/Database MCP Server**

**Почему может быть полезен:**
- Если добавите job tracking в SQLite
- Для анализа структурированных метаданных
- История обработанных файлов

**Возможности:**
- Выполнение SQL запросов
- Просмотр схемы БД
- Экспорт данных

**Установка:**
```bash
npm install -g @modelcontextprotocol/server-sqlite
```

**Настройка:**
```json
{
  "mcpServers": {
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "/app/jobs/jobs.db"]
    }
  }
}
```

**Примеры использования:**
- "Покажи все завершенные jobs за последнюю неделю"
- "Какой average processing time для CSV jobs?"
- "Какие массивы обрабатывались чаще всего?"

---

### 5. 📦 **Git MCP Server** (Опционально)

**Почему может быть полезен:**
- Анализ истории изменений
- Сравнение версий парсеров
- Отслеживание изменений в словарях

**Возможности:**
- Git log, diff, blame
- Поиск по коммитам
- Анализ изменений в файлах

**Установка:**
```bash
npm install -g @modelcontextprotocol/server-git
```

**Примеры использования:**
- "Когда последний раз обновлялся METRIC_DICT.py?"
- "Покажи diff между текущей и предыдущей версией streaming_pipeline.py"
- "Кто добавил metric ID 1633?"

---

### 6. 🌐 **HTTP/Fetch MCP Server** (Для внешних API)

**Почему может быть полезен:**
- Проверка Grafana API
- Тестирование FastAPI endpoints
- Интеграция с внешними системами

**Возможности:**
- HTTP GET/POST/DELETE запросы
- Работа с JSON responses
- Headers и authentication

**Встроен в некоторые версии Cursor**

**Примеры использования:**
- "Проверь здоровье Grafana API: GET http://localhost:3000/api/health"
- "Отправь POST запрос на /api/upload с файлом test.zip"
- "Получи список dashboards из Grafana"

---

### 7. 🐍 **Python Execution MCP Server** (Осторожно!)

**Почему может быть полезен:**
- Быстрое тестирование кода
- Анализ данных в pandas
- Проверка алгоритмов

**⚠️ ОСТОРОЖНО:**
- Может выполнять произвольный код
- Используйте только в dev окружении
- Не давайте доступ к production данным

**Установка:**
```bash
# Custom implementation
npm install -g @experimental/python-mcp-server
```

**Примеры использования:**
- "Посчитай среднее значение метрики в этом CSV файле"
- "Проверь, валиден ли этот Prometheus metric line"
- "Сколько уникальных Element в этом датасете?"

---

## 🎯 Приоритетная конфигурация для вашего проекта

### Минимальная (обязательная) конфигурация:

```json
{
  "mcpServers": {
    "docker": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-docker"]
    }
  }
}
```

### Рекомендуемая конфигурация:

```json
{
  "mcpServers": {
    "docker": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-docker"]
    },
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "/app/jobs/jobs.db"]
    }
  }
}
```

### Полная конфигурация (для продвинутых):

```json
{
  "mcpServers": {
    "docker": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-docker"]
    },
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "/app/jobs/jobs.db"]
    },
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git", "/data/projects/monitoring_VM_Grafana"]
    },
    "victoria": {
      "command": "python3",
      "args": ["/data/projects/monitoring_VM_Grafana/mcp_victoria_wrapper.py"]
    }
  }
}
```

---

## 📋 Где находится конфигурация MCP?

### Для Cursor:

**Linux/macOS:**
```bash
~/.cursor/config/settings.json
# или
~/.config/cursor/User/settings.json
```

**Windows:**
```
C:\Users\YourUsername\AppData\Roaming\Cursor\User\settings.json
```

### Как добавить:

1. Откройте Cursor Settings (Ctrl+,)
2. Найдите "MCP Servers" или "Model Context Protocol"
3. Или напрямую отредактируйте `settings.json`

---

## 🚀 Примеры реальных сценариев использования

### Сценарий 1: Отладка после загрузки данных

```
Вы: Загрузил новый архив через веб-интерфейс, но не вижу данных в Grafana

AI (с Docker MCP):
1. "Проверяю логи API контейнера..."
   → Нашел job_id: abc123
2. "Смотрю логи streaming pipeline..."
   → WARNING: Found 15 unknown metric IDs
3. "Проверяю VictoriaMetrics..."
   → Метрики есть, но с UNKNOWN_ префиксом
4. Решение: Нужно обновить METRIC_DICT.py
```

### Сценарий 2: Проверка производительности

```
Вы: Парсинг стал медленным

AI (с Docker + Filesystem MCP):
1. "Проверяю использование ресурсов контейнерами..."
   → API контейнер использует 95% CPU
2. "Смотрю размер temp директорий..."
   → /app/uploads: 45GB (не очищается!)
3. "Читаю логи api.log..."
   → Множество failed cleanup operations
4. Решение: Добавить periodic cleanup task
```

### Сценарий 3: Анализ метрик

```
Вы: Нужно понять, какие метрики самые популярные

AI (с Victoria + SQLite MCP):
1. "Запрашиваю все метрики из VM..."
   → 1247 уникальных метрик
2. "Группирую по Resource типу..."
   → LUN: 450, Controller: 380, Disk: 250, ...
3. "Смотрю job history в SQLite..."
   → 85% jobs используют только 20 метрик
4. Рекомендация: Оптимизировать DEFAULT_METRICS
```

---

## 🛠️ Custom MCP Server для VictoriaMetrics

Создайте специализированный MCP server для вашего проекта:

```python
#!/usr/bin/env python3
# mcp_huawei_server.py
"""
Custom MCP Server for Huawei Storage Monitoring Project.
Provides high-level operations specific to this project.
"""

import json
import sys
import requests
from pathlib import Path
from typing import Optional

VM_URL = "http://localhost:8428"
GRAFANA_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"

class HuaweiMCPServer:
    """MCP Server with project-specific operations."""
    
    def list_arrays(self) -> dict:
        """List all storage arrays in VictoriaMetrics."""
        response = requests.get(f"{VM_URL}/api/v1/label/SN/values")
        data = response.json()
        return {
            "arrays": data.get("data", []),
            "count": len(data.get("data", []))
        }
    
    def check_unknown_metrics(self, sn: Optional[str] = None) -> dict:
        """Check for unknown metrics in VM."""
        query = '{__name__=~"huawei_unknown_.*"'
        if sn:
            query += f',SN="{sn}"'
        query += '}'
        
        response = requests.get(f"{VM_URL}/api/v1/query", params={"query": query})
        data = response.json()
        
        return {
            "has_unknown": len(data.get("data", {}).get("result", [])) > 0,
            "count": len(data.get("data", {}).get("result", []))
        }
    
    def get_metric_stats(self, sn: str) -> dict:
        """Get statistics about metrics for an array."""
        # Total metrics
        response = requests.get(
            f"{VM_URL}/api/v1/query",
            params={"query": f'count({{SN="{sn}"}})'}
        )
        total = response.json()
        
        # Unknown metrics
        response = requests.get(
            f"{VM_URL}/api/v1/query",
            params={"query": f'count({{SN="{sn}",__name__=~"huawei_unknown_.*"}})'}
        )
        unknown = response.json()
        
        return {
            "array": sn,
            "total_metrics": total.get("data", {}).get("result", [{}])[0].get("value", [0, 0])[1],
            "unknown_metrics": unknown.get("data", {}).get("result", [{}])[0].get("value", [0, 0])[1]
        }
    
    def list_jobs(self) -> dict:
        """List all processing jobs from API."""
        response = requests.get(f"{API_URL}/api/jobs")
        return response.json()
    
    def check_grafana_health(self) -> dict:
        """Check Grafana API health."""
        try:
            response = requests.get(f"{GRAFANA_URL}/api/health", timeout=5)
            return {
                "healthy": response.status_code == 200,
                "status": response.json()
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }

def main():
    """MCP Server main entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command specified"}))
        sys.exit(1)
    
    server = HuaweiMCPServer()
    command = sys.argv[1]
    
    try:
        if command == "list_arrays":
            result = server.list_arrays()
        elif command == "check_unknown":
            sn = sys.argv[2] if len(sys.argv) > 2 else None
            result = server.check_unknown_metrics(sn)
        elif command == "metric_stats":
            result = server.get_metric_stats(sys.argv[2])
        elif command == "list_jobs":
            result = server.list_jobs()
        elif command == "check_grafana":
            result = server.check_grafana_health()
        else:
            result = {"error": f"Unknown command: {command}"}
        
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Настройка:**
```json
{
  "mcpServers": {
    "huawei": {
      "command": "python3",
      "args": ["/data/projects/monitoring_VM_Grafana/mcp_huawei_server.py"]
    }
  }
}
```

**Использование:**
- "Покажи все массивы в системе"
- "Есть ли unknown метрики для массива 2102355THQFSQ?"
- "Покажи статистику по метрикам для всех массивов"
- "Список активных jobs"
- "Grafana работает?"

---

## 📚 Дополнительные ресурсы

- **MCP Protocol Spec**: https://modelcontextprotocol.io/
- **Официальные MCP серверы**: https://github.com/modelcontextprotocol/servers
- **Cursor MCP документация**: https://docs.cursor.com/context/model-context-protocol

---

## ✅ Рекомендации по использованию

### DO:
- ✅ Начните с Docker MCP (самый полезный для проекта)
- ✅ Протестируйте каждый MCP на dev окружении
- ✅ Создайте custom MCP для проект-специфичных операций
- ✅ Документируйте команды и примеры

### DON'T:
- ❌ Не давайте MCP доступ к production данным без авторизации
- ❌ Не используйте Python execution MCP в prod
- ❌ Не храните credentials в MCP конфигурации
- ❌ Не забывайте про timeouts для HTTP запросов

---

**Обновлено**: October 2025
**Версия проекта**: 2.1.0


