"""
Base check class for S3 compatibility checks.

This module provides the abstract base class that all S3 compatibility checks
should inherit from. It provides common functionality like logging, cleanup,
and result tracking.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class CheckResult:
    """Represents the result of a single check operation."""
    
    def __init__(self, name: str, success: bool, message: str = "", 
                 details: Optional[Dict[str, Any]] = None, duration: float = 0.0):
        self.name = name
        self.success = success
        self.message = message
        self.details = details or {}
        self.duration = duration
        self.timestamp = time.time()


class BaseCheck(ABC):
    """
    Abstract base class for all S3 compatibility checks.
    
    All check classes should inherit from this class and implement the run_checks() method.
    This class provides common functionality like logging, cleanup, and result management.
    """
    
    def __init__(self, s3_client, config: Dict[str, Any], logger: logging.Logger):
        """
        Initialize the base check.
        
        Args:
            s3_client: Configured S3 client wrapper
            config: Configuration dictionary from INI file
            logger: Logger instance for this check
        """
        self.s3_client = s3_client
        self.config = config
        self.logger = logger
        self.results: List[CheckResult] = []
        self.cleanup_items: List[Dict[str, str]] = []
        self.check_name = self.__class__.__name__.replace('Check', '').lower()
    
    @abstractmethod
    def run_checks(self) -> List[CheckResult]:
        """
        Run all checks in this category.
        
        Returns:
            List of CheckResult objects representing the check outcomes
        """
        pass
    
    def add_result(self, name: str, success: bool, message: str = "", 
                   details: Optional[Dict[str, Any]] = None, duration: float = 0.0) -> CheckResult:
        """
        Add a check result to the results list.
        
        Args:
            name: Name of the check
            success: Whether the check passed
            message: Optional message describing the result
            details: Optional dictionary with additional details
            duration: Time taken for the check in seconds
            
        Returns:
            The created CheckResult object
        """
        result = CheckResult(name, success, message, details, duration)
        self.results.append(result)
        
        # Log the result
        if success:
            self.logger.info(f"✓ {name}: {message}")
        else:
            self.logger.error(f"✗ {name}: {message}")
            if details:
                self.logger.debug(f"  Details: {details}")
        
        return result
    
    def add_cleanup_item(self, item_type: str, identifier: str, **kwargs):
        """
        Add an item to be cleaned up after checks complete.
        
        Args:
            item_type: Type of item ('bucket', 'object', 'multipart_upload')
            identifier: Main identifier (bucket name, object key, etc.)
            **kwargs: Additional parameters needed for cleanup
        """
        cleanup_item = {
            'type': item_type,
            'identifier': identifier,
            **kwargs
        }
        self.cleanup_items.append(cleanup_item)
        self.logger.debug(f"Added cleanup item: {cleanup_item}")
    
    def cleanup(self):
        """
        Clean up all items created during checks.
        
        This method attempts to clean up all resources that were created
        during the check execution to leave the S3 storage in a clean state.
        """
        self.logger.info(f"Starting cleanup for {self.check_name} checks...")
        cleanup_errors = []
        
        # Sort cleanup items to handle dependencies (objects before buckets)
        sorted_items = sorted(self.cleanup_items, 
                            key=lambda x: {'object': 0, 'multipart_upload': 1, 'bucket': 2}.get(x['type'], 3))
        
        for item in sorted_items:
            try:
                if item['type'] == 'bucket':
                    self._cleanup_bucket(item)
                elif item['type'] == 'object':
                    self._cleanup_object(item)
                elif item['type'] == 'multipart_upload':
                    self._cleanup_multipart_upload(item)
                else:
                    self.logger.warning(f"Unknown cleanup item type: {item['type']}")
                    
            except Exception as e:
                error_msg = f"Failed to cleanup {item['type']} '{item['identifier']}': {str(e)}"
                cleanup_errors.append(error_msg)
                self.logger.error(error_msg)
        
        if cleanup_errors:
            self.logger.warning(f"Cleanup completed with {len(cleanup_errors)} errors")
        else:
            self.logger.info(f"Cleanup completed successfully for {self.check_name}")
        
        # Clear the cleanup list
        self.cleanup_items.clear()
    
    def _cleanup_bucket(self, item: Dict[str, str]):
        """Clean up a bucket."""
        bucket_name = item['identifier']
        self.logger.debug(f"Cleaning up bucket: {bucket_name}")
        
        # First, try to delete all objects in the bucket
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                for obj in response['Contents']:
                    self.s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
                    self.logger.debug(f"Deleted object: {obj['Key']}")
        except Exception as e:
            self.logger.debug(f"Error listing/deleting objects in bucket {bucket_name}: {e}")
        
        # Delete the bucket
        self.s3_client.delete_bucket(Bucket=bucket_name)
        self.logger.debug(f"Deleted bucket: {bucket_name}")
    
    def _cleanup_object(self, item: Dict[str, str]):
        """Clean up an object."""
        bucket_name = item.get('bucket')
        object_key = item['identifier']
        version_id = item.get('version_id')
        
        self.logger.debug(f"Cleaning up object: {object_key} in bucket {bucket_name}")
        
        delete_params = {'Bucket': bucket_name, 'Key': object_key}
        if version_id:
            delete_params['VersionId'] = version_id
            
        self.s3_client.delete_object(**delete_params)
        self.logger.debug(f"Deleted object: {object_key}")
    
    def _cleanup_multipart_upload(self, item: Dict[str, str]):
        """Clean up a multipart upload."""
        bucket_name = item.get('bucket')
        object_key = item['identifier']
        upload_id = item.get('upload_id')
        
        self.logger.debug(f"Cleaning up multipart upload: {object_key} in bucket {bucket_name}")
        
        self.s3_client.abort_multipart_upload(
            Bucket=bucket_name,
            Key=object_key,
            UploadId=upload_id
        )
        self.logger.debug(f"Aborted multipart upload: {object_key}")
    
    def measure_time(self, func, *args, **kwargs):
        """
        Measure execution time of a function.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Tuple of (result, duration_in_seconds)
        """
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            return result, duration
        except Exception as e:
            duration = time.time() - start_time
            raise e
    
    def generate_unique_name(self, prefix: str = "") -> str:
        """
        Generate a unique name for resources.
        
        Args:
            prefix: Optional prefix for the name
            
        Returns:
            Unique name string
        """
        timestamp = str(int(time.time() * 1000))  # milliseconds
        if prefix:
            return f"{prefix}-{timestamp}"
        return f"s3check-{timestamp}"
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of check results.
        
        Returns:
            Dictionary containing check summary statistics
        """
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed
        
        return {
            'check_category': self.check_name,
            'total_checks': total,
            'passed': passed,
            'failed': failed,
            'success_rate': (passed / total * 100) if total > 0 else 0,
            'results': self.results
        }