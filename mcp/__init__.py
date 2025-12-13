# -*- coding: utf-8 -*-
"""
MCP Server для Huawei Storage VictoriaMetrics.

Предоставляет Model Context Protocol (MCP) интерфейс
для доступа к данным производительности из VictoriaMetrics.
"""

from .server import mcp

__all__ = ["mcp"]

