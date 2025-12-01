# Huawei Storage Metric/Resource Dictionaries
#
# Содержит:
#   - METRIC_DICT: Словарь метрик (ID → Name)
#   - RESOURCE_DICT: Словарь ресурсов (ID → Name)
#   - METRIC_CONVERSION: Коэффициенты конверсии единиц измерения

from .METRIC_DICT import METRIC_NAME_DICT
from .RESOURCE_DICT import RESOURCE_NAME_DICT
from .METRIC_CONVERSION import METRIC_CONVERSION

__all__ = ['METRIC_NAME_DICT', 'RESOURCE_NAME_DICT', 'METRIC_CONVERSION']

