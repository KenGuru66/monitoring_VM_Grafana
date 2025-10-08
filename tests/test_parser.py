"""
Unit tests for perf_zip2csv.py
"""

import pytest
import zipfile
import tarfile
import io
import struct
import tempfile
from pathlib import Path
from datetime import datetime

# Import functions from perf_zip2csv
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from perf_zip2csv import (
    construct_data_header,
    construct_data_type,
    decompress_tgz,
    extract_tgz_from_zip,
    merge_resources,
)


@pytest.fixture
def sample_data_header():
    """Sample data header for testing."""
    return {
        'EndTime': '1664312940',
        'StartTime': '1664312040',
        'Archive': '60',
        'CtrlID': '1129',
        'Map': [{
            'ObjectTypes': '10',
            'IDs': ['134234114', '134234112'],
            'Names': ['DAE010.2', 'DAE010.0'],
            'DataTypes': ['5', '18', '22']
        }]
    }


@pytest.fixture
def sample_tgz_data():
    """Create a minimal .tgz file with dummy .dat content."""
    # Create dummy .dat content
    dat_content = b'dummy performance data'
    
    # Create tar.gz in memory
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        # Add .dat file to tar
        tarinfo = tarfile.TarInfo(name='test.dat')
        tarinfo.size = len(dat_content)
        tar.addfile(tarinfo, io.BytesIO(dat_content))
    
    tar_buffer.seek(0)
    return tar_buffer.read()


def test_construct_data_type(sample_data_header):
    """Test construct_data_type function."""
    list_data_type, size_collect_once = construct_data_type(sample_data_header)
    
    # Should have 2 IDs * 3 DataTypes = 6 elements
    assert len(list_data_type) == 6
    
    # Size should be 6 * 4 bytes = 24
    assert size_collect_once == 24
    
    # Check first element structure
    assert list_data_type[0][0] == '10'  # ObjectType
    assert list_data_type[0][1] == '5'   # DataType
    assert list_data_type[0][2] == 'DAE010.2'  # Name
    assert list_data_type[0][3] == []    # Data array


def test_decompress_tgz(sample_tgz_data, tmp_path):
    """Test tgz decompression."""
    result = decompress_tgz(sample_tgz_data)
    
    assert result is not None
    assert result.exists()
    assert result.suffix == '.dat'
    
    # Cleanup
    if result.exists():
        result.unlink()
        result.parent.rmdir()


def test_merge_resources():
    """Test merging resources from multiple results."""
    result1 = {
        '10': ['line1', 'line2'],
        '11': ['line3']
    }
    result2 = {
        '10': ['line4'],
        '12': ['line5']
    }
    
    merged = merge_resources([result1, result2])
    
    assert '10' in merged
    assert '11' in merged
    assert '12' in merged
    assert len(merged['10']) == 3
    assert len(merged['11']) == 1
    assert len(merged['12']) == 1


def test_extract_tgz_from_zip(tmp_path, sample_tgz_data):
    """Test extracting .tgz files from ZIP archive."""
    # Create test ZIP with one .tgz file
    zip_path = tmp_path / "test.zip"
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr('test1.tgz', sample_tgz_data)
        zf.writestr('test2.tgz', sample_tgz_data)
        zf.writestr('readme.txt', b'some text')
    
    tgz_files = extract_tgz_from_zip(str(zip_path))
    
    # Should find 2 .tgz files
    assert len(tgz_files) == 2
    assert all(name.endswith('.tgz') for name, _ in tgz_files)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



