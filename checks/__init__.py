"""
S3 Compatibility Check Modules

Individual check categories for comprehensive S3 API testing.
"""

# Import all check classes for easy access
from .check_buckets import BucketChecks
from .check_objects import ObjectChecks
from .check_multipart import MultipartChecks
from .check_versioning import VersioningChecks
from .check_tagging import TaggingChecks
from .check_attributes import AttributeChecks
from .check_range_requests import RangeRequestChecks
from .check_error_conditions import ErrorConditionChecks
from .check_sync import SyncChecks

__all__ = [
    'BucketChecks',
    'ObjectChecks', 
    'MultipartChecks',
    'VersioningChecks',
    'TaggingChecks',
    'AttributeChecks',
    'RangeRequestChecks',
    'ErrorConditionChecks',
    'SyncChecks'
]