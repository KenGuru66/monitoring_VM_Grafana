#!/bin/bash
# Скрипт для запуска оригинального Parse_Perf_Files.py со ВСЕМИ метриками и ресурсами

set -e

cd /data/projects/monitoring_VM_Grafana/Data2csv

# Получаем все ресурсы и метрики из новых словарей
RESOURCES=$(python3 -c "from RESOURCE_DICT import RESOURCE_NAME_DICT; print(','.join(RESOURCE_NAME_DICT.keys()))")
METRICS=$(python3 -c "from METRIC_DICT import METRIC_NAME_DICT; print(','.join(METRIC_NAME_DICT.keys()))")

echo "=========================================="
echo "Запуск оригинального Parse_Perf_Files.py"
echo "(Python 3 портированная версия)"
echo "=========================================="
echo "Ресурсов: $(echo $RESOURCES | tr ',' '\n' | wc -l)"
echo "Метрик: $(echo $METRICS | tr ',' '\n' | wc -l)"
echo ""

# Создаем директорию для вывода
mkdir -p output_test/original_py2

# Оригинальный скрипт не поддерживает ZIP, нужно распаковать
echo "Распаковка архива..."
if [ ! -d "logs/extracted_tgz" ]; then
    mkdir -p logs/extracted_tgz
    unzip -q logs/Storage_History_Performance_Files.zip -d logs/extracted_tgz
    echo "Архив распакован в logs/extracted_tgz/"
else
    echo "Архив уже распакован в logs/extracted_tgz/"
fi

# Запускаем оригинальный скрипт (Python 3 версия)
echo "Запуск парсера..."
python3 Hu_vers/Parse_Perf_Files_py3.py \
    -i logs/extracted_tgz \
    -o output_test/original_py2 \
    -r "$RESOURCES" \
    -m "$METRICS"

echo ""
echo "✅ Готово!"
echo "Результат: output_test/original_py2/"
ls -lh output_test/original_py2/

