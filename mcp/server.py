#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Server для доступа к данным Huawei Storage в VictoriaMetrics.

Предоставляет tools для:
- Получения списка массивов, ресурсов, метрик, элементов
- Запросов текущих значений и данных за период
- Сводной информации по массивам
- Аналитики: сравнение массивов, поиск аномалий, топ по нагрузке

Использование:
    python mcp_server.py

Конфигурация через переменные окружения:
    VM_URL - Primary URL VictoriaMetrics (по умолчанию http://10.5.10.163:8428)
    VM_URL_FALLBACK - Fallback URL если primary недоступен (по умолчанию http://localhost:8428)

Логика подключения:
    1. Проверяет доступность primary (лаборатория через VPN)
    2. Если недоступен — переключается на fallback (локальный)
    3. Кеширует результат на 60 секунд
"""

import os
import logging
from typing import Optional, List
from datetime import datetime, timedelta

import httpx
from mcp.server.fastmcp import FastMCP

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp-huawei-vm")

# Конфигурация
# Список URL для попыток подключения (в порядке приоритета)
VM_URLS = [
    os.getenv("VM_URL", "http://10.5.10.163:8428"),  # Лаборатория (primary)
    os.getenv("VM_URL_FALLBACK", "http://localhost:8428"),  # Локальный (fallback)
]

# Кеш активного URL (чтобы не проверять каждый раз)
_active_vm_url: Optional[str] = None
_active_vm_url_checked_at: Optional[float] = None
HEALTH_CHECK_INTERVAL = 60  # Перепроверять доступность каждые 60 секунд

# Временной диапазон по умолчанию (6 месяцев назад - сейчас)
DEFAULT_START = 1571875200  # Достаточно старая дата для захвата всех данных
DEFAULT_END = int((datetime.now() + timedelta(days=1)).timestamp())

# =============================================================================
# Конфигурация метрик
# =============================================================================

METRICS_CONFIG = {
    "cpu": {
        "name": "huawei_avg_cpu_usage_percent",
        "display": "CPU Usage",
        "unit": "%",
        "divisor": 1,
        "resource": "Controller"
    },
    "bandwidth_read": {
        "name": "huawei_read_bandwidth_mb_s",
        "display": "Bandwidth Read",
        "unit": "MB/s",
        "divisor": 1,
        "resource": "Controller"
    },
    "bandwidth_write": {
        "name": "huawei_write_bandwidth_mb_s",
        "display": "Bandwidth Write",
        "unit": "MB/s",
        "divisor": 1,
        "resource": "Controller"
    },
    "latency_read": {
        "name": "huawei_avg_read_i_o_response_timeus",
        "display": "Latency Read",
        "unit": "ms",
        "divisor": 1000,  # us -> ms
        "resource": "Controller"
    },
    "latency_write": {
        "name": "huawei_avg_write_i_o_response_timeus",
        "display": "Latency Write",
        "unit": "ms",
        "divisor": 1000,
        "resource": "Controller"
    },
    "iops_read": {
        "name": "huawei_read_i_o_s",
        "display": "IOPS Read",
        "unit": "IOPS",
        "divisor": 1,
        "resource": "Controller"
    },
    "iops_write": {
        "name": "huawei_write_i_o_s",
        "display": "IOPS Write",
        "unit": "IOPS",
        "divisor": 1,
        "resource": "Controller"
    },
    "rw_ratio": {
        "name": "huawei_ratio_of_read_i_os_to_total_i_os_percent",
        "display": "Read:Write Ratio",
        "unit": "%",
        "divisor": 1,
        "resource": "Controller"
    },
    "cache": {
        "name": "huawei_avg_cache_usage_percent",
        "display": "Cache Usage",
        "unit": "%",
        "divisor": 1,
        "resource": "Controller"
    }
}

# =============================================================================
# Конфигурация Health метрик (ECC, SMART, BBU)
# =============================================================================

HEALTH_METRICS_CONFIG = {
    # ECC Memory Metrics - лейблы: SN, controller, dimm
    "ecc_total": {
        "name": "huawei_ecc_total",
        "display": "Total ECC Errors",
        "unit": "count",
        "label_key": "controller",
        "description": "Total ECC error count per controller"
    },
    "ecc_dimm": {
        "name": "huawei_ecc_dimm",
        "display": "ECC Errors per DIMM",
        "unit": "count",
        "label_key": "dimm",
        "description": "ECC correctable errors per memory module"
    },
    "mce_dimm": {
        "name": "huawei_mce_dimm",
        "display": "MCE Errors per DIMM",
        "unit": "count",
        "label_key": "dimm",
        "description": "MCE uncorrectable errors per memory module (critical)"
    },
    # SMART Disk Metrics - лейблы: SN, disk_id
    "smart_disk_health": {
        "name": "huawei_smart_disk_health",
        "display": "Disk Health Score",
        "unit": "%",
        "label_key": "disk_id",
        "description": "Overall disk health score (0-100)"
    },
    "smart_reallocated_sectors": {
        "name": "huawei_smart_reallocated_sectors",
        "display": "Reallocated Sectors (ID_5)",
        "unit": "count",
        "label_key": "disk_id",
        "description": "SMART ID_5 - count of reallocated sectors"
    },
    "smart_reallocated_events": {
        "name": "huawei_smart_reallocated_events",
        "display": "Reallocated Events (ID_196)",
        "unit": "count",
        "label_key": "disk_id",
        "description": "SMART ID_196 - count of reallocation events"
    },
    "smart_pending_sectors": {
        "name": "huawei_smart_pending_sectors",
        "display": "Pending Sectors (ID_197)",
        "unit": "count",
        "label_key": "disk_id",
        "description": "SMART ID_197 - sectors waiting to be remapped"
    },
    "smart_offline_uncorrectable": {
        "name": "huawei_smart_offline_uncorrectable",
        "display": "Offline Uncorrectable (ID_198)",
        "unit": "count",
        "label_key": "disk_id",
        "description": "SMART ID_198 - uncorrectable errors during offline scan"
    },
    "smart_available_spare": {
        "name": "huawei_smart_available_spare",
        "display": "Available Spare (ID_232)",
        "unit": "%",
        "label_key": "disk_id",
        "description": "SMART ID_232 - available spare capacity for NVMe/SSD"
    },
    "smart_temperature": {
        "name": "huawei_smart_temperature",
        "display": "Disk Temperature",
        "unit": "°C",
        "label_key": "disk_id",
        "description": "Disk temperature in Celsius"
    },
    # BBU Metrics - лейблы: SN, bbu_id
    "bbu_temperature": {
        "name": "huawei_bbu_temperature",
        "display": "BBU Temperature",
        "unit": "°C",
        "label_key": "bbu_id",
        "description": "Battery Backup Unit temperature"
    },
    "bbu_capacity": {
        "name": "huawei_bbu_capacity_percent",
        "display": "BBU Capacity",
        "unit": "%",
        "label_key": "bbu_id",
        "description": "BBU remaining capacity percentage"
    },
    "bbu_voltage": {
        "name": "huawei_bbu_voltage",
        "display": "BBU Voltage",
        "unit": "V",
        "label_key": "bbu_id",
        "description": "BBU current voltage"
    },
}

# Инициализация MCP сервера
mcp = FastMCP(
    "huawei-storage-vm",
    instructions="Доступ к данным производительности Huawei Storage в VictoriaMetrics"
)


# =============================================================================
# Вспомогательные функции
# =============================================================================

async def get_active_vm_url() -> str:
    """
    Возвращает активный URL VictoriaMetrics с fallback логикой.
    
    Проверяет доступность серверов в порядке приоритета:
    1. Лаборатория (VM_URL) - если доступен VPN
    2. Локальный (VM_URL_FALLBACK) - fallback
    
    Кеширует результат на HEALTH_CHECK_INTERVAL секунд.
    """
    global _active_vm_url, _active_vm_url_checked_at
    
    import time
    now = time.time()
    
    # Используем кешированный URL если он ещё валиден
    if (_active_vm_url is not None and 
        _active_vm_url_checked_at is not None and
        now - _active_vm_url_checked_at < HEALTH_CHECK_INTERVAL):
        return _active_vm_url
    
    # Проверяем доступность серверов
    async with httpx.AsyncClient(timeout=5.0) as client:
        for vm_url in VM_URLS:
            try:
                response = await client.get(f"{vm_url}/health")
                if response.status_code == 200:
                    if _active_vm_url != vm_url:
                        logger.info(f"Активный VictoriaMetrics: {vm_url}")
                    _active_vm_url = vm_url
                    _active_vm_url_checked_at = now
                    return vm_url
            except Exception as e:
                logger.debug(f"VictoriaMetrics {vm_url} недоступен: {e}")
                continue
    
    # Если ничего не доступно, используем первый URL (ошибка будет позже)
    logger.warning(f"Ни один VictoriaMetrics не доступен, используем {VM_URLS[0]}")
    _active_vm_url = VM_URLS[0]
    _active_vm_url_checked_at = now
    return VM_URLS[0]


async def vm_request(
    endpoint: str,
    params: Optional[dict] = None,
    method: str = "GET",
    add_default_time: bool = True
) -> dict:
    """
    Выполняет HTTP запрос к VictoriaMetrics API.
    
    Автоматически выбирает доступный сервер (лаборатория или локальный).
    
    Args:
        endpoint: Путь API (например, /api/v1/label/SN/values)
        params: Query параметры
        method: HTTP метод (GET или POST)
        add_default_time: Добавлять ли дефолтный временной диапазон
    
    Returns:
        dict: JSON ответ от VictoriaMetrics
    
    Raises:
        Exception: При ошибке запроса
    """
    vm_url = await get_active_vm_url()
    url = f"{vm_url}{endpoint}"
    
    # Добавляем временной диапазон по умолчанию только для endpoints где это нужно
    if params is None:
        params = {}
    
    if add_default_time:
        if "start" not in params:
            params["start"] = DEFAULT_START
        if "end" not in params:
            params["end"] = DEFAULT_END
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        if method == "GET":
            response = await client.get(url, params=params)
        else:
            response = await client.post(url, data=params)
        
        response.raise_for_status()
        return response.json()


def build_selector(
    sn: Optional[str] = None,
    resource: Optional[str] = None,
    element: Optional[str] = None
) -> str:
    """
    Строит PromQL селектор из параметров.
    
    Args:
        sn: Серийный номер массива
        resource: Тип ресурса (Controller, Disk, FC Port и т.д.)
        element: Конкретный элемент (CTE0.A, 0.1 и т.д.)
    
    Returns:
        str: PromQL селектор вида {SN="...",Resource="..."}
    """
    parts = []
    if sn:
        parts.append(f'SN="{sn}"')
    if resource:
        parts.append(f'Resource="{resource}"')
    if element:
        parts.append(f'Element="{element}"')
    
    return "{" + ",".join(parts) + "}" if parts else "{}"


def _parse_relative_time(relative: str) -> int:
    """
    Парсит относительное время вида 'now-7d' в Unix timestamp.
    
    Поддерживаемые форматы:
        - now
        - now-1h, now-7d, now-30d
        - now-1w (неделя)
    """
    now = datetime.now()
    
    if relative == "now":
        return int(now.timestamp())
    
    if relative.startswith("now-"):
        offset_str = relative[4:]
        
        # Парсим число и единицу
        unit = offset_str[-1]
        try:
            amount = int(offset_str[:-1])
        except ValueError:
            return int(now.timestamp())
        
        if unit == "m":
            delta = timedelta(minutes=amount)
        elif unit == "h":
            delta = timedelta(hours=amount)
        elif unit == "d":
            delta = timedelta(days=amount)
        elif unit == "w":
            delta = timedelta(weeks=amount)
        else:
            delta = timedelta()
        
        return int((now - delta).timestamp())
    
    return int(now.timestamp())


def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    Вычисляет перцентиль для списка значений.
    
    Args:
        values: Список числовых значений
        percentile: Перцентиль (0-100)
    
    Returns:
        float: Значение перцентиля
    """
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    # Интерполяция для точного значения
    k = (n - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < n else f
    
    if f == c:
        return sorted_values[f]
    
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def calculate_stats(values: List[float], divisor: float = 1.0) -> dict:
    """
    Вычисляет полную статистику для списка значений.
    
    Args:
        values: Список числовых значений
        divisor: Делитель для конвертации единиц (например, 1000 для us -> ms)
    
    Returns:
        dict: {max, avg, median, p95}
    """
    if not values:
        return {"max": None, "avg": None, "median": None, "p95": None}
    
    # Применяем делитель
    converted = [v / divisor for v in values]
    
    return {
        "max": round(max(converted), 2),
        "avg": round(sum(converted) / len(converted), 2),
        "median": round(calculate_percentile(converted, 50), 2),
        "p95": round(calculate_percentile(converted, 95), 2)
    }


def filter_by_time_of_day(values: List[tuple], time_period: str = "all") -> List[float]:
    """
    Фильтрует точки данных по времени суток.
    
    Args:
        values: Список пар (timestamp, value) из VictoriaMetrics
        time_period: "day", "night" или "all"
        
    Returns:
        Список float значений, отфильтрованных по времени суток
        
    Notes:
        - Московское время = UTC+3
        - Day: 8:00-22:00 МСК = 5:00-19:00 UTC
        - Night: 22:00-08:00 МСК = 19:00-05:00 UTC
    """
    filtered = []
    for ts, value_str in values:
        try:
            dt = datetime.utcfromtimestamp(ts)
            utc_hour = dt.hour
            value = float(value_str) if value_str != "NaN" else None
            
            if value is None:
                continue
            
            if time_period == "day":
                # День: 5:00-18:59 UTC (8:00-21:59 МСК)
                if 5 <= utc_hour < 19:
                    filtered.append(value)
            elif time_period == "night":
                # Ночь: 19:00-04:59 UTC (22:00-07:59 МСК)
                if utc_hour >= 19 or utc_hour < 5:
                    filtered.append(value)
            else:
                # Все время
                filtered.append(value)
        except (ValueError, TypeError):
            continue
    
    return filtered


# =============================================================================
# Базовые tools (метаданные)
# =============================================================================

@mcp.tool()
async def list_arrays() -> list[str]:
    """
    Возвращает список серийных номеров (SN) всех массивов в VictoriaMetrics.
    
    Returns:
        list[str]: Список серийных номеров массивов
    
    Пример:
        ["2102352VUV10L6000008", "2102352VUV10L6000009", ...]
    """
    logger.info("Запрос списка массивов")
    result = await vm_request("/api/v1/label/SN/values")
    arrays = result.get("data", [])
    logger.info(f"Найдено {len(arrays)} массивов")
    return arrays


@mcp.tool()
async def list_resources(sn: Optional[str] = None) -> list[str]:
    """
    Возвращает список типов ресурсов (Resource) в VictoriaMetrics.
    
    Args:
        sn: Опционально - серийный номер массива для фильтрации
    
    Returns:
        list[str]: Список типов ресурсов (Controller, Disk, FC Port и т.д.)
    
    Пример:
        ["Controller", "Disk", "FC Port", "LUN", "Storage Pool", ...]
    """
    logger.info(f"Запрос списка ресурсов (SN={sn})")
    
    params = {}
    if sn:
        params["match[]"] = build_selector(sn=sn)
    
    result = await vm_request("/api/v1/label/Resource/values", params)
    resources = result.get("data", [])
    logger.info(f"Найдено {len(resources)} типов ресурсов")
    return resources


@mcp.tool()
async def list_metrics(
    sn: Optional[str] = None,
    resource: Optional[str] = None
) -> list[str]:
    """
    Возвращает список метрик в VictoriaMetrics.
    
    Args:
        sn: Опционально - серийный номер массива
        resource: Опционально - тип ресурса (Controller, Disk и т.д.)
    
    Returns:
        list[str]: Список имён метрик (huawei_read_bandwidth_mb_s и т.д.)
    
    Пример:
        ["huawei_avg_cpu_usage_percent", "huawei_read_bandwidth_mb_s", ...]
    """
    logger.info(f"Запрос списка метрик (SN={sn}, Resource={resource})")
    
    selector = build_selector(sn=sn, resource=resource)
    params = {"match[]": selector} if selector != "{}" else {}
    
    result = await vm_request("/api/v1/series", params)
    
    # Извлекаем уникальные имена метрик
    metrics = set()
    for series in result.get("data", []):
        if "__name__" in series:
            metrics.add(series["__name__"])
    
    metrics_list = sorted(metrics)
    logger.info(f"Найдено {len(metrics_list)} метрик")
    return metrics_list


@mcp.tool()
async def list_elements(
    sn: str,
    resource: str
) -> list[str]:
    """
    Возвращает список элементов (Element) для указанного массива и ресурса.
    
    Args:
        sn: Серийный номер массива
        resource: Тип ресурса (Controller, Disk, FC Port и т.д.)
    
    Returns:
        list[str]: Список элементов (CTE0.A, 0.1, CTE0.A.IOM0.P0 и т.д.)
    
    Пример для FC Port:
        ["CTE0.A.IOM0.P0", "CTE0.A.IOM0.P1", "CTE0.B.IOM1.P0", ...]
    """
    logger.info(f"Запрос списка элементов (SN={sn}, Resource={resource})")
    
    selector = build_selector(sn=sn, resource=resource)
    params = {"match[]": selector}
    
    result = await vm_request("/api/v1/label/Element/values", params)
    elements = result.get("data", [])
    logger.info(f"Найдено {len(elements)} элементов")
    return elements


# =============================================================================
# Расширенные tools (запросы данных)
# =============================================================================

@mcp.tool()
async def query_metric(
    sn: str,
    resource: str,
    metric: str,
    element: Optional[str] = None
) -> dict:
    """
    Запрашивает текущее (последнее известное) значение метрики.
    
    Args:
        sn: Серийный номер массива
        resource: Тип ресурса (Controller, Disk, FC Port и т.д.)
        metric: Имя метрики (huawei_avg_cpu_usage_percent и т.д.)
        element: Опционально - конкретный элемент (CTE0.A и т.д.)
    
    Returns:
        dict: Результат запроса с метрикой и значениями
            {
                "metric": "huawei_avg_cpu_usage_percent",
                "results": [
                    {"element": "CTE0.A", "value": 45.2, "timestamp": "2025-01-15T10:30:00Z"},
                    {"element": "CTE0.B", "value": 38.1, "timestamp": "2025-01-15T10:30:00Z"}
                ]
            }
    """
    logger.info(f"Запрос метрики {metric} (SN={sn}, Resource={resource}, Element={element})")
    
    selector = build_selector(sn=sn, resource=resource, element=element)
    query = f"{metric}{selector}"
    
    result = await vm_request("/api/v1/query", {"query": query})
    
    # Форматируем результат
    formatted_results = []
    for item in result.get("data", {}).get("result", []):
        metric_labels = item.get("metric", {})
        value_data = item.get("value", [])
        
        if len(value_data) >= 2:
            timestamp = datetime.fromtimestamp(value_data[0]).isoformat()
            value = float(value_data[1]) if value_data[1] != "NaN" else None
            
            formatted_results.append({
                "element": metric_labels.get("Element", "unknown"),
                "value": value,
                "timestamp": timestamp
            })
    
    return {
        "metric": metric,
        "sn": sn,
        "resource": resource,
        "results": formatted_results
    }


@mcp.tool()
async def query_range(
    sn: str,
    resource: str,
    metric: str,
    element: Optional[str] = None,
    start: str = "now-7d",
    end: str = "now",
    step: str = "1h"
) -> dict:
    """
    Запрашивает значения метрики за указанный период времени.
    
    Args:
        sn: Серийный номер массива
        resource: Тип ресурса (Controller, Disk, FC Port и т.д.)
        metric: Имя метрики (huawei_avg_cpu_usage_percent и т.д.)
        element: Опционально - конкретный элемент (CTE0.A и т.д.)
        start: Начало периода (Unix timestamp, RFC3339 или относительное: now-7d)
        end: Конец периода (Unix timestamp, RFC3339 или относительное: now)
        step: Шаг между точками (5m, 1h, 1d и т.д.)
    
    Returns:
        dict: Результат запроса с временным рядом
            {
                "metric": "huawei_avg_cpu_usage_percent",
                "results": [
                    {
                        "element": "CTE0.A",
                        "values_count": 168,
                        "first_value": {"timestamp": "...", "value": 45.2},
                        "last_value": {"timestamp": "...", "value": 38.1},
                        "stats": {"min": 10.5, "max": 85.3, "avg": 42.1, "median": 40.0, "p95": 75.2}
                    }
                ]
            }
    """
    logger.info(f"Запрос range для {metric} (SN={sn}, Resource={resource}, start={start}, end={end}, step={step})")
    
    selector = build_selector(sn=sn, resource=resource, element=element)
    query = f"{metric}{selector}"
    
    # Определяем делитель для конвертации единиц
    divisor = 1.0
    for cfg in METRICS_CONFIG.values():
        if cfg["name"] == metric:
            divisor = cfg.get("divisor", 1.0)
            break
    
    # Для относительных времён преобразуем в Unix timestamp
    params = {
        "query": query,
        "step": step
    }
    
    # Обработка start/end
    if start.startswith("now"):
        params["start"] = _parse_relative_time(start)
    else:
        params["start"] = start
    
    if end.startswith("now"):
        params["end"] = _parse_relative_time(end)
    else:
        params["end"] = end
    
    result = await vm_request("/api/v1/query_range", params)
    
    # Форматируем результат с вычислением полной статистики
    formatted_results = []
    for item in result.get("data", {}).get("result", []):
        metric_labels = item.get("metric", {})
        values = item.get("values", [])
        
        if values:
            # Извлекаем числовые значения
            numeric_values = [float(v[1]) for v in values if v[1] != "NaN"]
            
            # Вычисляем полную статистику с учётом делителя
            stats = calculate_stats(numeric_values, divisor)
            stats["min"] = round(min(numeric_values) / divisor, 2) if numeric_values else None
            
            first_ts = datetime.fromtimestamp(values[0][0]).isoformat()
            last_ts = datetime.fromtimestamp(values[-1][0]).isoformat()
            
            formatted_results.append({
                "element": metric_labels.get("Element", "unknown"),
                "values_count": len(values),
                "first_value": {
                    "timestamp": first_ts,
                    "value": round(float(values[0][1]) / divisor, 2) if values[0][1] != "NaN" else None
                },
                "last_value": {
                    "timestamp": last_ts,
                    "value": round(float(values[-1][1]) / divisor, 2) if values[-1][1] != "NaN" else None
                },
                "stats": stats
            })
    
    return {
        "metric": metric,
        "sn": sn,
        "resource": resource,
        "period": {"start": start, "end": end, "step": step},
        "results": formatted_results
    }


@mcp.tool()
async def get_array_summary(sn: str) -> dict:
    """
    Возвращает сводную информацию о массиве.
    
    Args:
        sn: Серийный номер массива
    
    Returns:
        dict: Сводка по массиву
            {
                "sn": "2102352VUV10L6000008",
                "resources": ["Controller", "Disk", "FC Port", ...],
                "metrics_count": 150,
                "data_range": {
                    "first_data": "2025-08-22T00:00:00Z",
                    "last_data": "2025-12-11T10:00:00Z"
                },
                "key_metrics": {
                    "cpu": {"max": 85.3, "avg": 42.1, "median": 40.0, "p95": 75.2, "unit": "%"},
                    "bandwidth_read": {"max": 1200.5, "avg": 450.2, ...},
                    ...
                }
            }
    """
    logger.info(f"Запрос сводки по массиву SN={sn}")
    
    # Получаем список ресурсов
    resources = await list_resources(sn)
    
    # Получаем список метрик
    metrics = await list_metrics(sn)
    
    # Получаем временной диапазон данных (по метрике CPU)
    data_range = {}
    try:
        cpu_result = await vm_request("/api/v1/query_range", {
            "query": f'huawei_avg_cpu_usage_percent{{SN="{sn}",Resource="Controller"}}',
            "step": "1d"
        })
        
        for item in cpu_result.get("data", {}).get("result", []):
            values = item.get("values", [])
            if values:
                data_range = {
                    "first_data": datetime.fromtimestamp(values[0][0]).isoformat(),
                    "last_data": datetime.fromtimestamp(values[-1][0]).isoformat()
                }
                break
    except Exception as e:
        logger.warning(f"Не удалось получить временной диапазон: {e}")
    
    # Получаем ключевые метрики с полной статистикой
    key_metrics = {}
    
    # Определяем период для статистик (последние 7 дней данных)
    start_ts = _parse_relative_time("now-180d")  # Ищем за 6 месяцев
    end_ts = _parse_relative_time("now")
    
    metrics_to_query = ["cpu", "bandwidth_read", "bandwidth_write", 
                        "latency_read", "latency_write", "iops_read", "iops_write", "rw_ratio"]
    
    for metric_key in metrics_to_query:
        if metric_key not in METRICS_CONFIG:
            continue
            
        cfg = METRICS_CONFIG[metric_key]
        metric_name = cfg["name"]
        resource = cfg.get("resource", "Controller")
        divisor = cfg.get("divisor", 1.0)
        unit = cfg.get("unit", "")
        
        try:
            # Запрашиваем данные
            query = f'{metric_name}{{SN="{sn}",Resource="{resource}"}}'
            params = {
                "query": query,
                "start": start_ts,
                "end": end_ts,
                "step": "1h"
            }
            
            result = await vm_request("/api/v1/query_range", params)
            
            # Собираем все значения со всех контроллеров
            all_values = []
            for item in result.get("data", {}).get("result", []):
                values = item.get("values", [])
                for ts, val in values:
                    if val != "NaN":
                        all_values.append(float(val))
            
            if all_values:
                stats = calculate_stats(all_values, divisor)
                stats["unit"] = unit
                key_metrics[metric_key] = stats
                
        except Exception as e:
            logger.debug(f"Не удалось получить метрику {metric_key}: {e}")
    
    return {
        "sn": sn,
        "resources": resources,
        "resources_count": len(resources),
        "metrics_count": len(metrics),
        "data_range": data_range,
        "key_metrics": key_metrics
    }


# =============================================================================
# Аналитические tools
# =============================================================================

@mcp.tool()
async def get_performance_stats(
    sn: str,
    start: str = "now-7d",
    end: str = "now",
    time_period: str = "all"
) -> dict:
    """
    Получает полные статистики производительности для массива.
    
    Args:
        sn: Серийный номер массива
        start: Начало периода (now-7d, now-30d и т.д.)
        end: Конец периода (now)
        time_period: Фильтр по времени суток: "day" (8:00-22:00 МСК), 
                     "night" (22:00-8:00 МСК), "all" (всё время)
    
    Returns:
        dict: Статистики производительности
            {
                "sn": "...",
                "period": {"start": "...", "end": "...", "time_filter": "day"},
                "cpu": {"max": 85.3, "avg": 42.1, "median": 40.0, "p95": 75.2},
                "bandwidth_read": {...},
                "bandwidth_write": {...},
                "latency_read": {...},
                "latency_write": {...},
                "iops_read": {...},
                "iops_write": {...}
            }
    """
    logger.info(f"Запрос performance stats для SN={sn} (period={time_period})")
    
    start_ts = _parse_relative_time(start)
    end_ts = _parse_relative_time(end)
    
    # Адаптивный выбор step в зависимости от периода
    period_days = (end_ts - start_ts) / 86400
    step = "5m" if period_days <= 14 else "10m" if period_days <= 45 else "1h"
    
    result = {
        "sn": sn,
        "period": {
            "start": datetime.fromtimestamp(start_ts).isoformat(),
            "end": datetime.fromtimestamp(end_ts).isoformat(),
            "time_filter": time_period
        }
    }
    
    metrics_to_query = ["cpu", "bandwidth_read", "bandwidth_write", 
                        "latency_read", "latency_write", "iops_read", "iops_write"]
    
    for metric_key in metrics_to_query:
        if metric_key not in METRICS_CONFIG:
            continue
            
        cfg = METRICS_CONFIG[metric_key]
        metric_name = cfg["name"]
        resource = cfg.get("resource", "Controller")
        divisor = cfg.get("divisor", 1.0)
        unit = cfg.get("unit", "")
        
        try:
            # Запрашиваем данные
            query = f'{metric_name}{{SN="{sn}",Resource="{resource}"}}'
            params = {
                "query": query,
                "start": start_ts,
                "end": end_ts,
                "step": step
            }
            
            vm_result = await vm_request("/api/v1/query_range", params)
            
            # Собираем значения с фильтрацией по времени суток
            all_values = []
            for item in vm_result.get("data", {}).get("result", []):
                values = item.get("values", [])
                filtered = filter_by_time_of_day(values, time_period)
                all_values.extend(filtered)
            
            if all_values:
                stats = calculate_stats(all_values, divisor)
                stats["unit"] = unit
                stats["data_points"] = len(all_values)
                result[metric_key] = stats
            else:
                result[metric_key] = {"max": None, "avg": None, "median": None, "p95": None, "unit": unit}
                
        except Exception as e:
            logger.debug(f"Не удалось получить метрику {metric_key}: {e}")
            result[metric_key] = {"error": str(e)}
    
    return result


@mcp.tool()
async def compare_arrays(
    sn1: str,
    sn2: str,
    start: str = "now-7d",
    end: str = "now"
) -> dict:
    """
    Сравнивает производительность двух массивов.
    
    Args:
        sn1: Серийный номер первого массива
        sn2: Серийный номер второго массива
        start: Начало периода
        end: Конец периода
    
    Returns:
        dict: Сравнение метрик
            {
                "period": {...},
                "comparison": {
                    "cpu": {
                        "sn1": {"max": 85, "avg": 42, ...},
                        "sn2": {"max": 65, "avg": 35, ...},
                        "diff_percent": {"max": -23.5, "avg": -16.7, ...}
                    },
                    ...
                }
            }
    """
    logger.info(f"Сравнение массивов {sn1} и {sn2}")
    
    # Получаем статистики для обоих массивов
    stats1 = await get_performance_stats(sn1, start, end, "all")
    stats2 = await get_performance_stats(sn2, start, end, "all")
    
    # Формируем сравнение
    comparison = {}
    metrics_to_compare = ["cpu", "bandwidth_read", "bandwidth_write", 
                          "latency_read", "latency_write", "iops_read", "iops_write"]
    
    for metric_key in metrics_to_compare:
        m1 = stats1.get(metric_key, {})
        m2 = stats2.get(metric_key, {})
        
        diff = {}
        for stat_name in ["max", "avg", "median", "p95"]:
            v1 = m1.get(stat_name)
            v2 = m2.get(stat_name)
            
            if v1 is not None and v2 is not None and v1 != 0:
                diff[stat_name] = round(((v2 - v1) / v1) * 100, 1)
            else:
                diff[stat_name] = None
        
        comparison[metric_key] = {
            "sn1": {k: v for k, v in m1.items() if k in ["max", "avg", "median", "p95", "unit"]},
            "sn2": {k: v for k, v in m2.items() if k in ["max", "avg", "median", "p95", "unit"]},
            "diff_percent": diff
        }
    
    return {
        "sn1": sn1,
        "sn2": sn2,
        "period": stats1.get("period", {}),
        "comparison": comparison
    }


@mcp.tool()
async def get_top_loaded(
    metric: str = "cpu",
    limit: int = 10,
    start: str = "now-7d"
) -> list:
    """
    Возвращает топ массивов по указанной метрике.
    
    Args:
        metric: Метрика для сортировки (cpu, bandwidth_read, bandwidth_write, 
                latency_read, latency_write, iops_read, iops_write)
        limit: Количество массивов в топе
        start: Начало периода для анализа
    
    Returns:
        list: Топ массивов с метриками
            [
                {"sn": "...", "max": 95.2, "avg": 75.3, "p95": 88.1, "unit": "%"},
                ...
            ]
    """
    logger.info(f"Запрос топ-{limit} массивов по метрике {metric}")
    
    if metric not in METRICS_CONFIG:
        return [{"error": f"Неизвестная метрика: {metric}. Доступные: {list(METRICS_CONFIG.keys())}"}]
    
    cfg = METRICS_CONFIG[metric]
    metric_name = cfg["name"]
    resource = cfg.get("resource", "Controller")
    divisor = cfg.get("divisor", 1.0)
    unit = cfg.get("unit", "")
    
    # Получаем список всех массивов
    arrays = await list_arrays()
    
    start_ts = _parse_relative_time(start)
    end_ts = _parse_relative_time("now")
    
    # Собираем статистики для каждого массива
    results = []
    
    for sn in arrays:
        try:
            query = f'{metric_name}{{SN="{sn}",Resource="{resource}"}}'
            params = {
                "query": query,
                "start": start_ts,
                "end": end_ts,
                "step": "1h"
            }
            
            vm_result = await vm_request("/api/v1/query_range", params)
            
            # Собираем все значения
            all_values = []
            for item in vm_result.get("data", {}).get("result", []):
                values = item.get("values", [])
                for ts, val in values:
                    if val != "NaN":
                        all_values.append(float(val))
            
            if all_values:
                stats = calculate_stats(all_values, divisor)
                results.append({
                    "sn": sn,
                    "max": stats["max"],
                    "avg": stats["avg"],
                    "median": stats["median"],
                    "p95": stats["p95"],
                    "unit": unit
                })
                
        except Exception as e:
            logger.debug(f"Пропущен массив {sn}: {e}")
    
    # Сортируем по p95 (или max если p95 недоступен)
    results.sort(key=lambda x: x.get("p95") or x.get("max") or 0, reverse=True)
    
    return results[:limit]


@mcp.tool()
async def find_anomalies(
    sn: str,
    metric: str = "cpu",
    start: str = "now-7d",
    threshold_multiplier: float = 1.5
) -> dict:
    """
    Находит аномальные значения метрики (выбросы).
    
    Args:
        sn: Серийный номер массива
        metric: Метрика для анализа (cpu, bandwidth_read, latency_read и т.д.)
        start: Начало периода для анализа
        threshold_multiplier: Множитель для P95 (значения > P95 * multiplier считаются аномалиями)
    
    Returns:
        dict: Информация об аномалиях
            {
                "sn": "...",
                "metric": "cpu",
                "threshold": 82.5,
                "p95": 55.0,
                "anomalies_count": 12,
                "anomalies": [
                    {"timestamp": "...", "value": 95.2, "element": "0A"},
                    ...
                ]
            }
    """
    logger.info(f"Поиск аномалий для SN={sn}, metric={metric}")
    
    if metric not in METRICS_CONFIG:
        return {"error": f"Неизвестная метрика: {metric}. Доступные: {list(METRICS_CONFIG.keys())}"}
    
    cfg = METRICS_CONFIG[metric]
    metric_name = cfg["name"]
    resource = cfg.get("resource", "Controller")
    divisor = cfg.get("divisor", 1.0)
    unit = cfg.get("unit", "")
    
    start_ts = _parse_relative_time(start)
    end_ts = _parse_relative_time("now")
    
    # Адаптивный выбор step чтобы не превысить лимит точек (30000)
    period_days = (end_ts - start_ts) / 86400
    if period_days <= 7:
        step = "5m"
    elif period_days <= 30:
        step = "15m"
    elif period_days <= 90:
        step = "1h"
    else:
        step = "6h"
    
    query = f'{metric_name}{{SN="{sn}",Resource="{resource}"}}'
    params = {
        "query": query,
        "start": start_ts,
        "end": end_ts,
        "step": step
    }
    
    result = await vm_request("/api/v1/query_range", params, add_default_time=False)
    
    # Собираем все значения для расчёта P95
    all_values = []
    all_points = []  # (timestamp, value, element)
    
    for item in result.get("data", {}).get("result", []):
        element = item.get("metric", {}).get("Element", "unknown")
        values = item.get("values", [])
        
        for ts, val in values:
            if val != "NaN":
                value = float(val) / divisor
                all_values.append(value)
                all_points.append((ts, value, element))
    
    if not all_values:
        return {
            "sn": sn,
            "metric": metric,
            "error": "Нет данных"
        }
    
    # Вычисляем P95 и порог
    p95 = calculate_percentile(all_values, 95)
    threshold = p95 * threshold_multiplier
    
    # Находим аномалии
    anomalies = []
    for ts, value, element in all_points:
        if value > threshold:
            anomalies.append({
                "timestamp": datetime.fromtimestamp(ts).isoformat(),
                "value": round(value, 2),
                "element": element
            })
    
    # Сортируем по значению (самые большие выбросы первыми)
    anomalies.sort(key=lambda x: x["value"], reverse=True)
    
    return {
        "sn": sn,
        "metric": metric,
        "unit": unit,
        "p95": round(p95, 2),
        "threshold": round(threshold, 2),
        "threshold_multiplier": threshold_multiplier,
        "anomalies_count": len(anomalies),
        "anomalies": anomalies[:50]  # Ограничиваем 50 аномалиями
    }


# =============================================================================
# Health Metrics Tools (ECC, SMART, BBU)
# =============================================================================

def build_health_selector(
    sn: str,
    controller: Optional[str] = None,
    dimm: Optional[str] = None,
    disk_id: Optional[str] = None,
    bbu_id: Optional[str] = None
) -> str:
    """
    Строит PromQL селектор для Health метрик.
    
    Args:
        sn: Серийный номер массива
        controller: Контроллер (CTE0.0A, CTE0.0B и т.д.)
        dimm: Имя DIMM модуля (DIMM000, DIMM120 и т.д.)
        disk_id: ID диска (CTE0.A_ROOT.0 и т.д.)
        bbu_id: ID BBU (CTE0.BBU0 и т.д.)
    
    Returns:
        str: PromQL селектор
    """
    parts = [f'SN="{sn}"']
    if controller:
        parts.append(f'controller="{controller}"')
    if dimm:
        parts.append(f'dimm="{dimm}"')
    if disk_id:
        parts.append(f'disk_id="{disk_id}"')
    if bbu_id:
        parts.append(f'bbu_id="{bbu_id}"')
    
    return "{" + ",".join(parts) + "}"


@mcp.tool()
async def get_ecc_errors(
    sn: str,
    start: str = "now-180d",
    end: str = "now"
) -> dict:
    """
    Получает ECC/MCE ошибки памяти для массива.
    
    ECC (Error Correcting Code) — исправляемые ошибки памяти.
    MCE (Machine Check Exception) — критические неисправляемые ошибки.
    
    Args:
        sn: Серийный номер массива
        start: Начало периода (now-180d для поиска исторических данных)
        end: Конец периода
    
    Returns:
        dict: ECC статистика по контроллерам и DIMM модулям
            {
                "sn": "...",
                "controllers": [
                    {
                        "controller": "CTE0.0A",
                        "total_ecc": 29728,
                        "timestamp": "2025-10-02T12:37:00"
                    }
                ],
                "dimms": [
                    {
                        "controller": "CTE0.0A",
                        "dimm": "DIMM000",
                        "ecc_errors": 410,
                        "timestamp": "2025-10-02T12:37:00"
                    }
                ],
                "mce_errors": [...],  # Критические ошибки (если есть)
                "has_critical": false
            }
    """
    logger.info(f"Запрос ECC ошибок для SN={sn}")
    
    start_ts = _parse_relative_time(start)
    end_ts = _parse_relative_time(end)
    
    result = {
        "sn": sn,
        "controllers": [],
        "dimms": [],
        "mce_errors": [],
        "has_critical": False
    }
    
    # Запрашиваем huawei_ecc_total по контроллерам
    try:
        selector = build_health_selector(sn)
        query = f"huawei_ecc_total{selector}"
        params = {
            "query": query,
            "start": start_ts,
            "end": end_ts,
            "step": "1d"
        }
        
        vm_result = await vm_request("/api/v1/query_range", params, add_default_time=False)
        
        for item in vm_result.get("data", {}).get("result", []):
            labels = item.get("metric", {})
            values = item.get("values", [])
            
            if values:
                # Берём последнее значение
                last_ts, last_val = values[-1]
                result["controllers"].append({
                    "controller": labels.get("controller", "unknown"),
                    "total_ecc": int(float(last_val)) if last_val != "NaN" else 0,
                    "timestamp": datetime.fromtimestamp(last_ts).isoformat()
                })
    except Exception as e:
        logger.warning(f"Ошибка запроса ECC total: {e}")
    
    # Запрашиваем huawei_ecc_dimm по DIMM модулям
    try:
        selector = build_health_selector(sn)
        query = f"huawei_ecc_dimm{selector}"
        params = {
            "query": query,
            "start": start_ts,
            "end": end_ts,
            "step": "1d"
        }
        
        vm_result = await vm_request("/api/v1/query_range", params, add_default_time=False)
        
        for item in vm_result.get("data", {}).get("result", []):
            labels = item.get("metric", {})
            values = item.get("values", [])
            
            if values:
                last_ts, last_val = values[-1]
                ecc_count = int(float(last_val)) if last_val != "NaN" else 0
                
                # Добавляем только DIMM с ошибками или все для полноты картины
                result["dimms"].append({
                    "controller": labels.get("controller", "unknown"),
                    "dimm": labels.get("dimm", "unknown"),
                    "ecc_errors": ecc_count,
                    "timestamp": datetime.fromtimestamp(last_ts).isoformat()
                })
    except Exception as e:
        logger.warning(f"Ошибка запроса ECC DIMM: {e}")
    
    # Запрашиваем huawei_mce_dimm (критические ошибки)
    try:
        selector = build_health_selector(sn)
        query = f"huawei_mce_dimm{selector}"
        params = {
            "query": query,
            "start": start_ts,
            "end": end_ts,
            "step": "1d"
        }
        
        vm_result = await vm_request("/api/v1/query_range", params, add_default_time=False)
        
        for item in vm_result.get("data", {}).get("result", []):
            labels = item.get("metric", {})
            values = item.get("values", [])
            
            if values:
                last_ts, last_val = values[-1]
                mce_count = int(float(last_val)) if last_val != "NaN" else 0
                
                if mce_count > 0:
                    result["has_critical"] = True
                    result["mce_errors"].append({
                        "controller": labels.get("controller", "unknown"),
                        "dimm": labels.get("dimm", "unknown"),
                        "mce_errors": mce_count,
                        "timestamp": datetime.fromtimestamp(last_ts).isoformat()
                    })
    except Exception as e:
        logger.warning(f"Ошибка запроса MCE: {e}")
    
    # Сортируем DIMM по количеству ошибок (больше — первыми)
    result["dimms"].sort(key=lambda x: x.get("ecc_errors", 0), reverse=True)
    
    logger.info(f"Найдено {len(result['controllers'])} контроллеров, {len(result['dimms'])} DIMM с ECC")
    return result


@mcp.tool()
async def get_smart_status(
    sn: str,
    start: str = "now-180d",
    end: str = "now"
) -> dict:
    """
    Получает SMART статус дисков массива.
    
    SMART атрибуты указывают на состояние здоровья дисков.
    Критические атрибуты: ID_5, ID_196, ID_197, ID_198.
    
    Args:
        sn: Серийный номер массива
        start: Начало периода (now-180d для исторических данных)
        end: Конец периода
    
    Returns:
        dict: SMART статистика по дискам
            {
                "sn": "...",
                "disks": [
                    {
                        "disk_id": "CTE0.A_ROOT.0",
                        "health": 100,
                        "reallocated_sectors": 0,
                        "reallocated_events": 0,
                        "pending_sectors": 0,
                        "offline_uncorrectable": 0,
                        "available_spare": 100,
                        "temperature": 35,
                        "timestamp": "2025-10-02T12:37:00",
                        "status": "healthy"  # healthy, warning, critical
                    }
                ],
                "summary": {
                    "total_disks": 4,
                    "healthy": 3,
                    "warning": 1,
                    "critical": 0
                }
            }
    """
    logger.info(f"Запрос SMART статуса для SN={sn}")
    
    start_ts = _parse_relative_time(start)
    end_ts = _parse_relative_time(end)
    
    # Собираем данные по всем SMART метрикам
    disk_data = {}  # disk_id -> {метрики}
    
    smart_metrics = [
        ("huawei_smart_disk_health", "health"),
        ("huawei_smart_reallocated_sectors", "reallocated_sectors"),
        ("huawei_smart_reallocated_events", "reallocated_events"),
        ("huawei_smart_pending_sectors", "pending_sectors"),
        ("huawei_smart_offline_uncorrectable", "offline_uncorrectable"),
        ("huawei_smart_available_spare", "available_spare"),
        ("huawei_smart_temperature", "temperature"),
    ]
    
    for metric_name, field_name in smart_metrics:
        try:
            selector = build_health_selector(sn)
            query = f"{metric_name}{selector}"
            params = {
                "query": query,
                "start": start_ts,
                "end": end_ts,
                "step": "1d"
            }
            
            vm_result = await vm_request("/api/v1/query_range", params, add_default_time=False)
            
            for item in vm_result.get("data", {}).get("result", []):
                labels = item.get("metric", {})
                values = item.get("values", [])
                disk_id = labels.get("disk_id", "unknown")
                
                if values:
                    last_ts, last_val = values[-1]
                    value = float(last_val) if last_val != "NaN" else None
                    
                    if disk_id not in disk_data:
                        disk_data[disk_id] = {
                            "disk_id": disk_id,
                            "timestamp": datetime.fromtimestamp(last_ts).isoformat()
                        }
                    
                    disk_data[disk_id][field_name] = value
                    
        except Exception as e:
            logger.debug(f"Ошибка запроса {metric_name}: {e}")
    
    # Определяем статус каждого диска
    disks = []
    summary = {"total_disks": 0, "healthy": 0, "warning": 0, "critical": 0}
    
    for disk_id, data in disk_data.items():
        # Определяем статус на основе критических атрибутов
        status = "healthy"
        
        reallocated = data.get("reallocated_sectors", 0) or 0
        reallocated_events = data.get("reallocated_events", 0) or 0
        pending = data.get("pending_sectors", 0) or 0
        offline_unc = data.get("offline_uncorrectable", 0) or 0
        health = data.get("health", 100)
        
        # Критические условия
        if offline_unc > 0 or pending > 10 or (health is not None and health < 50):
            status = "critical"
        elif reallocated > 100 or reallocated_events > 50 or pending > 0 or (health is not None and health < 80):
            status = "warning"
        
        data["status"] = status
        disks.append(data)
        
        summary["total_disks"] += 1
        summary[status] += 1
    
    # Сортируем: critical первыми, потом warning, потом healthy
    status_order = {"critical": 0, "warning": 1, "healthy": 2}
    disks.sort(key=lambda x: status_order.get(x.get("status", "healthy"), 3))
    
    logger.info(f"Найдено {len(disks)} дисков: {summary['healthy']} healthy, {summary['warning']} warning, {summary['critical']} critical")
    
    return {
        "sn": sn,
        "disks": disks,
        "summary": summary
    }


@mcp.tool()
async def get_bbu_status(
    sn: str,
    start: str = "now-180d",
    end: str = "now"
) -> dict:
    """
    Получает статус BBU (Battery Backup Unit) массива.
    
    BBU обеспечивает защиту данных при отключении питания.
    Критические параметры: температура, ёмкость, напряжение.
    
    Args:
        sn: Серийный номер массива
        start: Начало периода
        end: Конец периода
    
    Returns:
        dict: BBU статистика
            {
                "sn": "...",
                "bbus": [
                    {
                        "bbu_id": "CTE0.BBU0",
                        "temperature": 25.5,
                        "capacity_percent": 95,
                        "voltage": 12.1,
                        "timestamp": "2025-10-02T12:37:00",
                        "status": "healthy"
                    }
                ],
                "summary": {
                    "total_bbus": 2,
                    "healthy": 2,
                    "warning": 0,
                    "critical": 0
                }
            }
    """
    logger.info(f"Запрос BBU статуса для SN={sn}")
    
    start_ts = _parse_relative_time(start)
    end_ts = _parse_relative_time(end)
    
    bbu_data = {}  # bbu_id -> {метрики}
    
    bbu_metrics = [
        ("huawei_bbu_temperature", "temperature"),
        ("huawei_bbu_capacity_percent", "capacity_percent"),
        ("huawei_bbu_voltage", "voltage"),
    ]
    
    for metric_name, field_name in bbu_metrics:
        try:
            selector = build_health_selector(sn)
            query = f"{metric_name}{selector}"
            params = {
                "query": query,
                "start": start_ts,
                "end": end_ts,
                "step": "1d"
            }
            
            vm_result = await vm_request("/api/v1/query_range", params, add_default_time=False)
            
            for item in vm_result.get("data", {}).get("result", []):
                labels = item.get("metric", {})
                values = item.get("values", [])
                bbu_id = labels.get("bbu_id", "unknown")
                
                if values:
                    last_ts, last_val = values[-1]
                    value = float(last_val) if last_val != "NaN" else None
                    
                    if bbu_id not in bbu_data:
                        bbu_data[bbu_id] = {
                            "bbu_id": bbu_id,
                            "timestamp": datetime.fromtimestamp(last_ts).isoformat()
                        }
                    
                    bbu_data[bbu_id][field_name] = value
                    
        except Exception as e:
            logger.debug(f"Ошибка запроса {metric_name}: {e}")
    
    # Определяем статус BBU
    bbus = []
    summary = {"total_bbus": 0, "healthy": 0, "warning": 0, "critical": 0}
    
    for bbu_id, data in bbu_data.items():
        status = "healthy"
        
        temp = data.get("temperature")
        capacity = data.get("capacity_percent")
        voltage = data.get("voltage")
        
        # Критические условия для BBU
        if temp is not None and temp > 45:
            status = "critical"
        elif capacity is not None and capacity < 50:
            status = "critical"
        elif temp is not None and temp > 40:
            status = "warning"
        elif capacity is not None and capacity < 80:
            status = "warning"
        
        data["status"] = status
        bbus.append(data)
        
        summary["total_bbus"] += 1
        summary[status] += 1
    
    logger.info(f"Найдено {len(bbus)} BBU")
    
    return {
        "sn": sn,
        "bbus": bbus,
        "summary": summary
    }


@mcp.tool()
async def get_health_summary(
    sn: str,
    start: str = "now-180d",
    end: str = "now"
) -> dict:
    """
    Получает полную сводку здоровья массива: ECC, SMART, BBU.
    
    Объединяет данные из get_ecc_errors, get_smart_status, get_bbu_status
    в единый отчёт с общей оценкой состояния.
    
    Args:
        sn: Серийный номер массива
        start: Начало периода для поиска данных
        end: Конец периода
    
    Returns:
        dict: Полная сводка здоровья
            {
                "sn": "...",
                "overall_status": "warning",  # healthy, warning, critical
                "ecc": {
                    "total_errors": 29728,
                    "controllers_count": 2,
                    "dimms_with_errors": 6,
                    "has_mce": false
                },
                "smart": {
                    "total_disks": 4,
                    "healthy": 3,
                    "warning": 1,
                    "critical": 0
                },
                "bbu": {
                    "total_bbus": 2,
                    "healthy": 2,
                    "warning": 0,
                    "critical": 0
                },
                "recommendations": [
                    "DIMM DIMM120 на контроллере CTE0.0A имеет 14465 ECC ошибок - рекомендуется замена",
                    ...
                ]
            }
    """
    logger.info(f"Запрос полной сводки здоровья для SN={sn}")
    
    # Получаем все данные параллельно
    ecc_data = await get_ecc_errors(sn, start, end)
    smart_data = await get_smart_status(sn, start, end)
    bbu_data = await get_bbu_status(sn, start, end)
    
    # Формируем сводку
    recommendations = []
    overall_status = "healthy"
    
    # Анализ ECC
    total_ecc = sum(c.get("total_ecc", 0) for c in ecc_data.get("controllers", []))
    dimms_with_errors = len([d for d in ecc_data.get("dimms", []) if d.get("ecc_errors", 0) > 0])
    
    if ecc_data.get("has_critical"):
        overall_status = "critical"
        for mce in ecc_data.get("mce_errors", []):
            recommendations.append(
                f"CRITICAL: MCE ошибка на DIMM {mce['dimm']} контроллера {mce['controller']} - требуется немедленная замена!"
            )
    
    # Рекомендации по DIMM с высоким количеством ECC
    for dimm in ecc_data.get("dimms", []):
        ecc_count = dimm.get("ecc_errors", 0)
        if ecc_count > 10000:
            if overall_status == "healthy":
                overall_status = "warning"
            recommendations.append(
                f"DIMM {dimm['dimm']} на {dimm['controller']} имеет {ecc_count:,} ECC ошибок - рекомендуется замена"
            )
        elif ecc_count > 1000:
            recommendations.append(
                f"DIMM {dimm['dimm']} на {dimm['controller']} имеет {ecc_count:,} ECC ошибок - требуется мониторинг"
            )
    
    # Анализ SMART
    smart_summary = smart_data.get("summary", {})
    if smart_summary.get("critical", 0) > 0:
        overall_status = "critical"
        for disk in smart_data.get("disks", []):
            if disk.get("status") == "critical":
                recommendations.append(
                    f"CRITICAL: Диск {disk['disk_id']} в критическом состоянии - требуется замена!"
                )
    elif smart_summary.get("warning", 0) > 0:
        if overall_status == "healthy":
            overall_status = "warning"
        for disk in smart_data.get("disks", []):
            if disk.get("status") == "warning":
                recommendations.append(
                    f"Диск {disk['disk_id']} требует внимания (reallocated: {disk.get('reallocated_sectors', 0)})"
                )
    
    # Анализ BBU
    bbu_summary = bbu_data.get("summary", {})
    if bbu_summary.get("critical", 0) > 0:
        overall_status = "critical"
        for bbu in bbu_data.get("bbus", []):
            if bbu.get("status") == "critical":
                recommendations.append(
                    f"CRITICAL: BBU {bbu['bbu_id']} в критическом состоянии!"
                )
    elif bbu_summary.get("warning", 0) > 0:
        if overall_status == "healthy":
            overall_status = "warning"
    
    return {
        "sn": sn,
        "overall_status": overall_status,
        "ecc": {
            "total_errors": total_ecc,
            "controllers_count": len(ecc_data.get("controllers", [])),
            "dimms_with_errors": dimms_with_errors,
            "has_mce": ecc_data.get("has_critical", False)
        },
        "smart": smart_summary,
        "bbu": bbu_summary,
        "recommendations": recommendations[:10]  # Ограничиваем 10 рекомендациями
    }


# =============================================================================
# Точка входа
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Логируем количество зарегистрированных инструментов перед запуском
    try:
        # Пытаемся получить список инструментов (может не работать до запуска)
        logger.info(f"Инициализация MCP сервера huawei-storage-vm")
        logger.info(f"  Primary: {VM_URLS[0]}")
        logger.info(f"  Fallback: {VM_URLS[1] if len(VM_URLS) > 1 else 'не настроен'}")
        logger.info("Все инструменты должны быть зарегистрированы через декораторы @mcp.tool()")
    except Exception as e:
        logger.warning(f"Не удалось проверить инструменты до запуска: {e}")
    
    # Проверяем аргументы командной строки для выбора транспорта
    transport = "stdio"  # По умолчанию stdio для совместимости с Cursor
    port = 8000
    
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        transport = "http"
        if len(sys.argv) > 2:
            port = int(sys.argv[2])
        logger.info(f"Запуск MCP сервера в режиме HTTP (порт {port})")
        mcp.run(transport="http", host="127.0.0.1", port=port)
    else:
        logger.info(f"Запуск MCP сервера в режиме stdio")
        logger.info("Примечание: если инструменты не находятся при повторном подключении,")
        logger.info("попробуйте перезапустить Cursor или отключить/включить сервер в настройках")
        mcp.run(transport="stdio")
