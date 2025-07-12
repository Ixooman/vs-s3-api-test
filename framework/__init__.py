"""
S3 Compatibility Checker Framework

Core framework components for S3 compatibility testing.
"""

from .base_check import BaseCheck, CheckResult
from .s3_client import S3Client, S3ClientError
from .config_manager import ConfigManager
from .check_runner import CheckRunner

__all__ = [
    'BaseCheck',
    'CheckResult', 
    'S3Client',
    'S3ClientError',
    'ConfigManager',
    'CheckRunner'
]