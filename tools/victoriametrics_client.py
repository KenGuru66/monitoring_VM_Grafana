"""
VictoriaMetrics Client для получения performance метрик

Модуль для запросов к VictoriaMetrics API и расчета статистик производительности.
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)


class VictoriaMetricsClient:
    """Клиент для работы с VictoriaMetrics API"""
    
    def __init__(self, vm_url: str = "http://localhost:8428"):
        """
        Инициализация клиента
        
        Args:
            vm_url: URL VictoriaMetrics сервера
        """
        self.vm_url = vm_url.rstrip('/')
        self.timeout = 30
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Выполняет HTTP запрос к VictoriaMetrics
        
        Args:
            endpoint: API endpoint (например, /api/v1/query)
            params: Query параметры
            
        Returns:
            JSON response или None если ошибка
        """
        try:
            url = f"{self.vm_url}{endpoint}"
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') != 'success':
                logger.error(f"VM query failed: {data.get('error', 'Unknown error')}")
                return None
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query VictoriaMetrics: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying VM: {e}")
            return None
    
    def _filter_by_time_of_day(self, values: List[Tuple[int, str]], time_period: str = "all") -> List[float]:
        """
        Фильтрует точки данных по времени суток
        
        Args:
            values: Список пар (timestamp, value) из VictoriaMetrics
            time_period: "day", "night" или "all"
            
        Returns:
            Список float значений, отфильтрованных по времени суток
            
        Notes:
            - Московское время = UTC+3
            - Day: 8:00-22:00 МСК = 5:00-19:00 UTC
            - Night: 22:00-08:00 МСК = 19:00-05:00 UTC (включает 19-23 и 0-4 UTC)
        """
        filtered = []
        for ts, value_str in values:
            try:
                dt = datetime.utcfromtimestamp(ts)
                utc_hour = dt.hour
                
                # Проверяем попадание в нужный период
                if time_period == "day":
                    # День: 5:00-18:59 UTC
                    if 5 <= utc_hour < 19:
                        filtered.append(float(value_str))
                elif time_period == "night":
                    # Ночь: 19:00-04:59 UTC
                    if utc_hour >= 19 or utc_hour < 5:
                        filtered.append(float(value_str))
                else:
                    # Все время
                    filtered.append(float(value_str))
            except (ValueError, TypeError):
                continue
        
        return filtered
    
    def _get_metric_stats_with_time_filter(self, metric_name: str, serial_number: str,
                                          start_time: int, end_time: int,
                                          time_period: str = "all",
                                          resource: str = "Controller") -> Dict[str, Optional[float]]:
        """
        Получает статистики (max, median) для метрики с фильтрацией по времени суток
        
        Args:
            metric_name: Имя метрики (например, huawei_read_bandwidth_mb_s)
            serial_number: Серийный номер массива
            start_time: Начало периода (Unix timestamp)
            end_time: Конец периода (Unix timestamp)
            time_period: "day", "night" или "all"
            resource: Тип ресурса (обычно "Controller")
            
        Returns:
            Dict с max и median значениями (или None если данных нет)
        """
        # Адаптивный выбор step в зависимости от периода
        period_days = (end_time - start_time) / 86400
        step = '5m' if period_days <= 45 else '10m'
        
        # Запрашиваем данные через query_range
        query = f'{metric_name}{{SN="{serial_number}",Resource="{resource}"}}'
        params = {
            'query': query,
            'start': start_time,
            'end': end_time,
            'step': step
        }
        
        result = self._make_request('/api/v1/query_range', params)
        
        if not result or not result.get('data', {}).get('result'):
            return {'max': None, 'p95': None, 'median': None}
        
        # Собираем значения со всех контроллеров
        all_values = []
        for series in result['data']['result']:
            values = series.get('values', [])
            # Фильтруем по времени суток
            filtered_values = self._filter_by_time_of_day(values, time_period)
            all_values.extend(filtered_values)
        
        if not all_values:
            return {'max': None, 'p95': None, 'median': None}
        
        # Вычисляем статистики
        max_value = max(all_values)
        sorted_values = sorted(all_values)
        median_value = sorted_values[len(sorted_values) // 2]
        
        # 95-й перцентиль: значение, ниже которого находится 95% данных
        p95_value = np.percentile(all_values, 95)
        
        return {'max': max_value, 'p95': p95_value, 'median': median_value}
    
    def find_real_data_period(self, serial_number: str, metric_name: str, 
                             ref_start: int, ref_end: int) -> Tuple[int, int, float]:
        """
        Находит реальный период данных для массива в reference диапазоне
        
        Args:
            serial_number: Серийный номер массива
            metric_name: Имя метрики (например, 'huawei_avg_cpu_usage_percent')
            ref_start: Начало reference периода (Unix timestamp)
            ref_end: Конец reference периода (Unix timestamp)
        
        Returns:
            (actual_start, actual_end, period_days) или (0, 0, 0) если нет данных
        """
        # Быстрый поиск с step=1d
        query = f'{metric_name}{{SN="{serial_number}",Resource="Controller"}}'
        params = {'query': query, 'start': ref_start, 'end': ref_end, 'step': '1d'}
        result = self._make_request('/api/v1/query_range', params)
        
        if result and result.get('data', {}).get('result'):
            values = result['data']['result'][0].get('values', [])
            if values:
                actual_start = int(values[0][0])
                actual_end = int(values[-1][0])
                period_days = (actual_end - actual_start) / 86400
                logger.info(f"SN {serial_number}: Data available from {datetime.fromtimestamp(actual_start).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(actual_end).strftime('%Y-%m-%d')}")
                return actual_start, actual_end, period_days
        
        return 0, 0, 0
    
    def check_availability(self) -> bool:
        """
        Проверяет доступность VictoriaMetrics
        
        Returns:
            True если VM доступна
        """
        try:
            response = requests.get(f"{self.vm_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_time_range_last_full_week(self, reference_date: Optional[datetime] = None) -> Tuple[int, int]:
        """
        Рассчитывает временной диапазон последней полной недели (понедельник-воскресенье)
        
        Args:
            reference_date: Референсная дата (default: сегодня)
            
        Returns:
            Tuple[start_timestamp, end_timestamp] в Unix time (секунды)
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Находим последний воскресенье перед референсной датой
        days_since_sunday = (reference_date.weekday() + 1) % 7
        if days_since_sunday == 0:
            # Сегодня воскресенье - берём предыдущую неделю
            last_sunday = reference_date - timedelta(days=7)
        else:
            last_sunday = reference_date - timedelta(days=days_since_sunday)
        
        # Последний понедельник (7 дней назад от последнего воскресенья)
        last_monday = last_sunday - timedelta(days=6)
        
        # Устанавливаем время: понедельник 00:00:00, воскресенье 23:59:59
        week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = last_sunday.replace(hour=23, minute=59, second=59, microsecond=0)
        
        return int(week_start.timestamp()), int(week_end.timestamp())
    
    def find_available_data_range(self, serial_number: str, 
                                  preferred_start: int, preferred_end: int,
                                  reference_date: datetime,
                                  lookback_days: int = 180) -> Optional[Tuple[int, int, float]]:
        """
        Ищет доступный диапазон данных для массива.
        
        Стратегия:
        1. Проверяем предпочтительный период (preferred_start - preferred_end)
        2. Если данных нет, ищем ближайший к reference_date период с данными
        3. Возвращаем до 7 дней (или сколько есть) из найденного периода
        
        Args:
            serial_number: Серийный номер массива
            preferred_start: Предпочтительное начало (Unix timestamp)
            preferred_end: Предпочтительный конец (Unix timestamp)
            reference_date: Дата генерации логов (для поиска ближайших данных)
            lookback_days: Сколько дней назад искать (default: 180 = 6 месяцев)
            
        Returns:
            Tuple[start, end, actual_days] с доступным периодом или None
            где actual_days - фактическое количество дней с данными
        """
        # 1. Проверяем предпочтительный период
        query = f'huawei_avg_cpu_usage_percent{{SN="{serial_number}",Resource="Controller"}}'
        params = {
            'query': query,
            'start': preferred_start,
            'end': preferred_end,
            'step': '1h'
        }
        
        result = self._make_request('/api/v1/query_range', params)
        if result and result.get('data', {}).get('result'):
            values = result['data']['result'][0].get('values', [])
            if values:
                # Данные есть в предпочтительном периоде
                actual_days = (preferred_end - preferred_start) / 86400
                logger.info(f"Using preferred period for SN {serial_number}: "
                           f"{datetime.fromtimestamp(preferred_start).strftime('%Y-%m-%d')} - "
                           f"{datetime.fromtimestamp(preferred_end).strftime('%Y-%m-%d')} "
                           f"({actual_days:.1f} days)")
                return (preferred_start, preferred_end, actual_days)
        
        # 2. Ищем данные в расширенном диапазоне (от reference_date назад и вперед)
        logger.info(f"No data in preferred period, searching for available data for SN {serial_number}...")
        reference_ts = int(reference_date.timestamp())
        search_start = reference_ts - (lookback_days * 86400)
        search_end = reference_ts + (30 * 86400)  # +30 дней вперед на случай если логи старые
        
        params['start'] = search_start
        params['end'] = search_end
        params['step'] = '6h'  # 6-часовой шаг для детального поиска
        
        result = self._make_request('/api/v1/query_range', params)
        if not result or not result.get('data', {}).get('result'):
            logger.warning(f"No data found for SN {serial_number} in extended range "
                          f"({datetime.fromtimestamp(search_start).strftime('%Y-%m-%d')} - "
                          f"{datetime.fromtimestamp(search_end).strftime('%Y-%m-%d')})")
            return None
        
        # 3. Находим все точки данных - берем ПОСЛЕДНЮЮ (самую свежую)
        values = result['data']['result'][0]['values']
        if not values:
            return None
        
        # Берем последнюю точку данных (values отсортированы по времени)
        last_timestamp = int(values[-1][0])
        first_timestamp = int(values[0][0])
        
        logger.info(f"Found data range: {datetime.fromtimestamp(first_timestamp).strftime('%Y-%m-%d')} - "
                   f"{datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d')}")
        
        # 4. Определяем период: берем до 7 дней назад от последней точки (или сколько есть)
        period_start = max(last_timestamp - (7 * 86400), first_timestamp)
        period_end = last_timestamp
        
        # Проверяем сколько реально данных есть в этом периоде
        params['start'] = period_start
        params['end'] = period_end
        params['step'] = '1h'
        
        result = self._make_request('/api/v1/query_range', params)
        if result and result.get('data', {}).get('result'):
            values = result['data']['result'][0].get('values', [])
            if values:
                # Корректируем диапазон по реальным данным
                actual_start = int(values[0][0])
                actual_end = int(values[-1][0])
                actual_days = (actual_end - actual_start) / 86400
                
                logger.info(f"Adjusted period for SN {serial_number}: "
                           f"{datetime.fromtimestamp(actual_start).strftime('%Y-%m-%d')} - "
                           f"{datetime.fromtimestamp(actual_end).strftime('%Y-%m-%d')} "
                           f"({actual_days:.1f} days)")
                
                return (actual_start, actual_end, actual_days)
        
        logger.warning(f"Could not determine valid data range for SN {serial_number}")
        return None
    
    def query_metric_max(self, metric_name: str, serial_number: str, 
                         resource_type: str, start_time: int, end_time: int) -> Optional[float]:
        """
        Получает максимальное значение метрики за период для всех контроллеров
        
        Args:
            metric_name: Имя метрики (например, huawei_read_bandwidth_mb_s)
            serial_number: Серийный номер массива
            resource_type: Тип ресурса (например, Controller)
            start_time: Начало периода (Unix timestamp)
            end_time: Конец периода (Unix timestamp)
            
        Returns:
            Максимальное значение или None если ошибка
        """
        # Рассчитываем диапазон для range vector (в днях)
        days_range = (end_time - start_time) // 86400 + 1
        
        # Запрос: максимум по всем контроллерам за период
        query = f'max(max_over_time({metric_name}{{SN="{serial_number}",Resource="{resource_type}"}}[{days_range}d]))'
        
        params = {
            'query': query,
            'time': end_time
        }
        
        result = self._make_request('/api/v1/query', params)
        if not result or not result.get('data', {}).get('result'):
            return None
        
        try:
            value = float(result['data']['result'][0]['value'][1])
            return value
        except (IndexError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse max value for {metric_name}: {e}")
            return None
    
    def query_metric_median(self, metric_name: str, serial_number: str,
                           resource_type: str, start_time: int, end_time: int) -> Optional[float]:
        """
        Получает медианное значение метрики за период для всех контроллеров
        
        Args:
            metric_name: Имя метрики
            serial_number: Серийный номер массива
            resource_type: Тип ресурса
            start_time: Начало периода (Unix timestamp)
            end_time: Конец периода (Unix timestamp)
            
        Returns:
            Медианное значение или None если ошибка
        """
        days_range = (end_time - start_time) // 86400 + 1
        
        # Запрос: медиана (квантиль 0.5) по всем контроллерам за период
        # Сначала получаем медиану для каждого контроллера, потом берём max из них
        query = f'max(quantile_over_time(0.5, {metric_name}{{SN="{serial_number}",Resource="{resource_type}"}}[{days_range}d]))'
        
        params = {
            'query': query,
            'time': end_time
        }
        
        result = self._make_request('/api/v1/query', params)
        if not result or not result.get('data', {}).get('result'):
            return None
        
        try:
            value = float(result['data']['result'][0]['value'][1])
            return value
        except (IndexError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse median value for {metric_name}: {e}")
            return None
    
    def get_controller_bandwidth_stats(self, serial_number: str, 
                                      start_time: int, end_time: int) -> Dict[str, Optional[float]]:
        """
        Получает статистики bandwidth для контроллеров (Max и Median)
        
        Bandwidth рассчитывается как сумма Read + Write bandwidth
        
        Args:
            serial_number: Серийный номер массива
            start_time: Начало периода (Unix timestamp)
            end_time: Конец периода (Unix timestamp)
            
        Returns:
            Dict с ключами:
                - bandwidth_max_per_controller: максимальный bandwidth (MB/s)
                - bandwidth_median_per_controller: медианный bandwidth (MB/s)
        """
        days_range = (end_time - start_time) // 86400 + 1
        
        # Bandwidth = Read + Write
        # Для Max: берём максимум суммы по всем контроллерам
        query_max = f'''max(
            max_over_time(huawei_read_bandwidth_mb_s{{SN="{serial_number}",Resource="Controller"}}[{days_range}d]) +
            max_over_time(huawei_write_bandwidth_mb_s{{SN="{serial_number}",Resource="Controller"}}[{days_range}d])
        )'''
        
        # Для Median: берём максимум из медиан каждого контроллера
        query_median = f'''max(
            quantile_over_time(0.5, huawei_read_bandwidth_mb_s{{SN="{serial_number}",Resource="Controller"}}[{days_range}d]) +
            quantile_over_time(0.5, huawei_write_bandwidth_mb_s{{SN="{serial_number}",Resource="Controller"}}[{days_range}d])
        )'''
        
        result_max = self._make_request('/api/v1/query', {'query': query_max, 'time': end_time})
        result_median = self._make_request('/api/v1/query', {'query': query_median, 'time': end_time})
        
        stats = {
            'bandwidth_max_per_controller': None,
            'bandwidth_median_per_controller': None
        }
        
        if result_max and result_max.get('data', {}).get('result'):
            try:
                stats['bandwidth_max_per_controller'] = float(result_max['data']['result'][0]['value'][1])
            except (IndexError, KeyError, ValueError):
                pass
        
        if result_median and result_median.get('data', {}).get('result'):
            try:
                stats['bandwidth_median_per_controller'] = float(result_median['data']['result'][0]['value'][1])
            except (IndexError, KeyError, ValueError):
                pass
        
        return stats
    
    def get_controller_bandwidth_stats_separated(self, serial_number: str, 
                                                start_time: int, end_time: int,
                                                time_period: str = "all") -> Dict[str, Optional[float]]:
        """
        Получает статистики bandwidth для контроллеров раздельно для Read и Write
        
        Args:
            serial_number: Серийный номер массива
            start_time: Начало периода (Unix timestamp)
            end_time: Конец периода (Unix timestamp)
            time_period: "day", "night" или "all" для фильтрации по времени суток
            
        Returns:
            Dict с ключами:
                - bandwidth_read_max: максимальный read bandwidth (MB/s)
                - bandwidth_read_median: медианный read bandwidth (MB/s)
                - bandwidth_write_max: максимальный write bandwidth (MB/s)
                - bandwidth_write_median: медианный write bandwidth (MB/s)
        """
        # Получаем статистики для Read bandwidth
        read_stats = self._get_metric_stats_with_time_filter(
            'huawei_read_bandwidth_mb_s', serial_number, start_time, end_time, time_period
        )
        
        # Получаем статистики для Write bandwidth
        write_stats = self._get_metric_stats_with_time_filter(
            'huawei_write_bandwidth_mb_s', serial_number, start_time, end_time, time_period
        )
        
        return {
            'bandwidth_read_max': read_stats['max'],
            'bandwidth_read_p95': read_stats['p95'],
            'bandwidth_read_median': read_stats['median'],
            'bandwidth_write_max': write_stats['max'],
            'bandwidth_write_p95': write_stats['p95'],
            'bandwidth_write_median': write_stats['median']
        }
    
    def get_controller_latency_stats(self, serial_number: str,
                                    start_time: int, end_time: int,
                                    time_period: str = "all") -> Dict[str, Optional[float]]:
        """
        Получает статистики latency для контроллеров (Read и Write, Max и Median)
        
        ВАЖНО: Метрики в VM хранятся в микросекундах (us), конвертируем в миллисекунды (ms)
        
        Args:
            serial_number: Серийный номер массива
            start_time: Начало периода (Unix timestamp)
            end_time: Конец периода (Unix timestamp)
            time_period: "day", "night" или "all" для фильтрации по времени суток
            
        Returns:
            Dict с ключами (все в ms):
                - latency_read_max
                - latency_read_median
                - latency_write_max
                - latency_write_median
        """
        # Получаем статистики для Read latency (в микросекундах)
        read_stats = self._get_metric_stats_with_time_filter(
            'huawei_avg_read_i_o_response_timeus', serial_number, start_time, end_time, time_period
        )
        
        # Получаем статистики для Write latency (в микросекундах)
        write_stats = self._get_metric_stats_with_time_filter(
            'huawei_avg_write_i_o_response_timeus', serial_number, start_time, end_time, time_period
        )
        
        # Конвертируем из микросекунд в миллисекунды
        return {
            'latency_read_max': read_stats['max'] / 1000 if read_stats['max'] is not None else None,
            'latency_read_p95': read_stats['p95'] / 1000 if read_stats['p95'] is not None else None,
            'latency_read_median': read_stats['median'] / 1000 if read_stats['median'] is not None else None,
            'latency_write_max': write_stats['max'] / 1000 if write_stats['max'] is not None else None,
            'latency_write_p95': write_stats['p95'] / 1000 if write_stats['p95'] is not None else None,
            'latency_write_median': write_stats['median'] / 1000 if write_stats['median'] is not None else None
        }
    
    def get_controller_cpu_stats(self, serial_number: str,
                                start_time: int, end_time: int,
                                time_period: str = "all") -> Dict[str, Optional[float]]:
        """
        Получает статистики CPU для контроллеров (Max и Median)
        
        Args:
            serial_number: Серийный номер массива
            start_time: Начало периода (Unix timestamp)
            end_time: Конец периода (Unix timestamp)
            time_period: "day", "night" или "all" для фильтрации по времени суток
            
        Returns:
            Dict с ключами:
                - cpu_max: максимальная утилизация CPU (%)
                - cpu_median: медианная утилизация CPU (%)
        """
        # Получаем статистики для CPU
        cpu_stats = self._get_metric_stats_with_time_filter(
            'huawei_avg_cpu_usage_percent', serial_number, start_time, end_time, time_period
        )
        
        return {
            'cpu_max': cpu_stats['max'],
            'cpu_p95': cpu_stats['p95'],
            'cpu_median': cpu_stats['median']
        }
    
    def get_last_datapoint_time(self, serial_number: str) -> Optional[int]:
        """
        Получает временную метку последней доступной точки данных для массива
        
        Args:
            serial_number: Серийный номер массива
            
        Returns:
            Unix timestamp последней точки данных или None если нет данных
        """
        try:
            # Используем query_range для получения последних точек данных за 6 месяцев
            import time
            end_time = int(time.time())
            start_time = end_time - (180 * 24 * 3600)  # 6 месяцев назад
            
            query = f'huawei_avg_cpu_usage_percent{{SN="{serial_number}",Resource="Controller"}}'
            
            params = {
                'query': query,
                'start': start_time,
                'end': end_time,
                'step': '1d'  # Дневной шаг для быстрого поиска
            }
            
            result = self._make_request('/api/v1/query_range', params)
            if not result or not result.get('data', {}).get('result'):
                logger.warning(f"No data found for SN {serial_number}")
                return None
            
            # Берём первую серию (любой контроллер) и последнюю точку
            values = result['data']['result'][0]['values']
            if not values:
                return None
            
            # Последняя точка данных [timestamp, value]
            last_timestamp = int(values[-1][0])
            return last_timestamp
        except Exception as e:
            logger.error(f"Failed to get last datapoint time: {e}")
            return None
    
    def get_all_performance_stats_day_night(self, serial_number: str, 
                                            reference_date: Optional[datetime] = None,
                                            start_time: Optional[int] = None,
                                            end_time: Optional[int] = None) -> Dict[str, Any]:
        """
        Получает все performance статистики для массива, разделенные на Day/Night периоды
        
        Args:
            serial_number: Серийный номер массива
            reference_date: Дата сбора логов (для определения периода анализа)
            start_time: Начало периода (Unix timestamp), если None - автоматически рассчитывается
            end_time: Конец периода (Unix timestamp), если None - автоматически рассчитывается
            
        Returns:
            Dict со структурой:
            {
                'available': True/False,
                'period_start': '2025-09-22',
                'period_end': '2025-09-28',
                'day': {
                    'bandwidth_read_max': ...,
                    'bandwidth_write_max': ...,
                    'latency_read_max': ...,
                    'cpu_max': ...,
                    ...
                },
                'night': { ... }
            }
        """
        # Проверяем доступность VM
        if not self.check_availability():
            logger.warning("VictoriaMetrics is not available")
            return {'available': False}
        
        # Если время не указано явно, рассчитываем автоматически
        if start_time is None or end_time is None:
            # Получаем последнюю доступную точку данных в VM
            last_timestamp = self.get_last_datapoint_time(serial_number)
            
            effective_date = None
            
            if reference_date and last_timestamp:
                # Основной сценарий: есть и дата логов, и данные в VM
                last_vm_date = datetime.fromtimestamp(last_timestamp)
                
                # Выбираем минимальную дату (не берем данные свежее логов)
                effective_date = min(last_vm_date, reference_date)
                
                logger.info(f"Reference date (logs): {reference_date.strftime('%Y-%m-%d')}")
                logger.info(f"Last VM data point: {last_vm_date.strftime('%Y-%m-%d')}")
                logger.info(f"Using effective date: {effective_date.strftime('%Y-%m-%d')} (min of both)")
                
            elif reference_date:
                # Есть дата логов, но нет данных в VM для этого SN
                # Используем дату логов
                effective_date = reference_date
                logger.info(f"No VM data for SN {serial_number}, using reference date: {effective_date.strftime('%Y-%m-%d')}")
                
            elif last_timestamp:
                # Нет даты логов, но есть данные в VM
                # Используем последнюю точку из VM
                effective_date = datetime.fromtimestamp(last_timestamp)
                logger.info(f"No reference date provided, using last VM data point: {effective_date.strftime('%Y-%m-%d')}")
                
            else:
                # Fallback: нет ни даты логов, ни данных в VM
                # Используем текущую дату
                effective_date = datetime.now()
                logger.warning(f"No reference date and no VM data for SN {serial_number}, using current date as fallback")
            
            # Рассчитываем последнюю полную неделю от выбранной даты
            start_time, end_time = self.get_time_range_last_full_week(effective_date)
            logger.info(f"Preferred performance metrics period: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d')} - {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d')}")
        
        # Проверяем доступность данных и адаптируем период если необходимо
        available_range = self.find_available_data_range(
            serial_number, start_time, end_time, reference_date if reference_date else datetime.now(), lookback_days=180
        )
        
        if not available_range:
            logger.warning(f"No performance data found for SN {serial_number} in last 6 months")
            return {'available': False}
        
        # Используем найденный диапазон
        start_time, end_time, actual_days = available_range
        
        # Собираем статистики для Day периода
        day_stats = {}
        
        # Bandwidth Day (separated)
        bandwidth_day = self.get_controller_bandwidth_stats_separated(serial_number, start_time, end_time, "day")
        day_stats.update(bandwidth_day)
        
        # Latency Day
        latency_day = self.get_controller_latency_stats(serial_number, start_time, end_time, "day")
        day_stats.update(latency_day)
        
        # CPU Day
        cpu_day = self.get_controller_cpu_stats(serial_number, start_time, end_time, "day")
        day_stats.update(cpu_day)
        
        # Собираем статистики для Night периода
        night_stats = {}
        
        # Bandwidth Night (separated)
        bandwidth_night = self.get_controller_bandwidth_stats_separated(serial_number, start_time, end_time, "night")
        night_stats.update(bandwidth_night)
        
        # Latency Night
        latency_night = self.get_controller_latency_stats(serial_number, start_time, end_time, "night")
        night_stats.update(latency_night)
        
        # CPU Night
        cpu_night = self.get_controller_cpu_stats(serial_number, start_time, end_time, "night")
        night_stats.update(cpu_night)
        
        # Формируем результат
        result = {
            'available': True,
            'period_start': datetime.fromtimestamp(start_time).strftime('%Y-%m-%d'),
            'period_end': datetime.fromtimestamp(end_time).strftime('%Y-%m-%d'),
            'day': day_stats,
            'night': night_stats
        }
        
        # Проверяем что хотя бы одна метрика доступна
        all_metrics = list(day_stats.values()) + list(night_stats.values())
        if all(v is None for v in all_metrics):
            logger.warning(f"No performance data found for SN {serial_number}")
            return {'available': False}
        
        return result
    
    def get_all_performance_stats(self, serial_number: str, 
                                  reference_date: Optional[datetime] = None,
                                  start_time: Optional[int] = None,
                                  end_time: Optional[int] = None) -> Dict[str, Any]:
        """
        Получает все performance статистики для массива
        
        Args:
            serial_number: Серийный номер массива
            reference_date: Дата сбора логов (для определения периода анализа)
            start_time: Начало периода (Unix timestamp), если None - автоматически рассчитывается
            end_time: Конец периода (Unix timestamp), если None - автоматически рассчитывается
            
        Returns:
            Dict со всеми метриками или {'available': False} если данных нет
        """
        # Проверяем доступность VM
        if not self.check_availability():
            logger.warning("VictoriaMetrics is not available")
            return {'available': False}
        
        # Если время не указано явно, рассчитываем автоматически
        if start_time is None or end_time is None:
            # Получаем последнюю доступную точку данных в VM
            last_timestamp = self.get_last_datapoint_time(serial_number)
            
            effective_date = None
            
            if reference_date and last_timestamp:
                # Основной сценарий: есть и дата логов, и данные в VM
                last_vm_date = datetime.fromtimestamp(last_timestamp)
                
                # Выбираем минимальную дату (не берем данные свежее логов)
                effective_date = min(last_vm_date, reference_date)
                
                logger.info(f"Reference date (logs): {reference_date.strftime('%Y-%m-%d')}")
                logger.info(f"Last VM data point: {last_vm_date.strftime('%Y-%m-%d')}")
                logger.info(f"Using effective date: {effective_date.strftime('%Y-%m-%d')} (min of both)")
                
            elif reference_date:
                # Есть дата логов, но нет данных в VM для этого SN
                # Используем дату логов
                effective_date = reference_date
                logger.info(f"No VM data for SN {serial_number}, using reference date: {effective_date.strftime('%Y-%m-%d')}")
                
            elif last_timestamp:
                # Нет даты логов, но есть данные в VM
                # Используем последнюю точку из VM
                effective_date = datetime.fromtimestamp(last_timestamp)
                logger.info(f"No reference date provided, using last VM data point: {effective_date.strftime('%Y-%m-%d')}")
                
            else:
                # Fallback: нет ни даты логов, ни данных в VM
                # Используем текущую дату
                effective_date = datetime.now()
                logger.warning(f"No reference date and no VM data for SN {serial_number}, using current date as fallback")
            
            # Рассчитываем последнюю полную неделю от выбранной даты
            start_time, end_time = self.get_time_range_last_full_week(effective_date)
            logger.info(f"Preferred performance metrics period: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d')} - {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d')}")
        
        # Проверяем доступность данных и адаптируем период если необходимо
        available_range = self.find_available_data_range(
            serial_number, start_time, end_time, reference_date if reference_date else datetime.now(), lookback_days=180
        )
        
        if not available_range:
            logger.warning(f"No performance data found for SN {serial_number} in last 6 months")
            return {'available': False}
        
        # Используем найденный диапазон
        start_time, end_time, actual_days = available_range
        
        # Собираем все статистики
        result = {
            'available': True,
            'period_start': datetime.fromtimestamp(start_time).strftime('%Y-%m-%d'),
            'period_end': datetime.fromtimestamp(end_time).strftime('%Y-%m-%d'),
        }
        
        # Bandwidth
        bandwidth_stats = self.get_controller_bandwidth_stats(serial_number, start_time, end_time)
        result.update(bandwidth_stats)
        
        # Latency
        latency_stats = self.get_controller_latency_stats(serial_number, start_time, end_time)
        result.update(latency_stats)
        
        # CPU
        cpu_stats = self.get_controller_cpu_stats(serial_number, start_time, end_time)
        result.update(cpu_stats)
        
        # Проверяем что хотя бы одна метрика доступна
        metric_values = [v for k, v in result.items() if k not in ['available', 'period_start', 'period_end']]
        if all(v is None for v in metric_values):
            logger.warning(f"No performance data found for SN {serial_number}")
            return {'available': False}
        
        return result


if __name__ == "__main__":
    # Тестирование модуля
    logging.basicConfig(level=logging.INFO)
    
    client = VictoriaMetricsClient()
    
    print("Testing VictoriaMetrics Client...")
    print(f"VM Available: {client.check_availability()}")
    
    # Тестовый запрос для массива 2102352VUV10L6000008
    test_sn = "2102352VUV10L6000008"
    
    # Используем исторический диапазон: 14 сентября - 15 октября 2025
    start_time = 1726272000  # 14 сентября 2025
    end_time = 1760572799    # 15 октября 2025
    
    print(f"\nQuerying performance stats for SN: {test_sn}")
    print(f"Period: {datetime.fromtimestamp(start_time)} - {datetime.fromtimestamp(end_time)}")
    
    stats = client.get_all_performance_stats(test_sn, start_time, end_time)
    
    print("\nResults:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

