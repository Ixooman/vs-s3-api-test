"""
S3 Client wrapper for enhanced error handling and logging.

This module provides a wrapper around boto3 S3 client with enhanced error handling,
retry logic, and detailed logging for debugging S3 compatibility issues.
"""

import logging
import time
import json
from typing import Dict, Any, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from botocore.awsrequest import AWSRequest
from botocore.endpoint import logger as endpoint_logger


class S3ClientError(Exception):
    """Custom exception for S3 client errors."""
    
    def __init__(self, message: str, error_code: str = None, status_code: int = None, 
                 operation: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.operation = operation
        self.details = details or {}


class S3Client:
    """
    Enhanced S3 client wrapper with error handling and retry logic.
    
    This wrapper provides:
    - Detailed error logging and handling
    - Automatic retry logic for transient errors
    - Request/response logging for debugging
    - Custom error types for better error analysis
    """
    
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, 
                 region: str = 'us-east-1', verify_ssl: bool = False, 
                 logger: logging.Logger = None, max_retries: int = 3,
                 enable_raw_logging: bool = False, enable_boto_debug: bool = False):
        """
        Initialize the S3 client wrapper.
        
        Args:
            endpoint_url: S3 endpoint URL
            access_key: AWS access key ID
            secret_key: AWS secret access key
            region: AWS region (default: us-east-1)
            verify_ssl: Whether to verify SSL certificates
            logger: Logger instance
            max_retries: Maximum number of retries for failed requests
        """
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.enable_raw_logging = enable_raw_logging
        self.enable_boto_debug = enable_boto_debug
        self.logger = logger or logging.getLogger(__name__)
        
        # Configure enhanced logging if requested
        self._configure_enhanced_logging()
        
        # Configure boto3 client
        config = Config(
            region_name=region,
            retries={
                'max_attempts': max_retries,
                'mode': 'adaptive'
            },
            max_pool_connections=50
        )
        
        self.client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=config,
            verify=verify_ssl
        )
        
        self.logger.info(f"S3 client initialized for endpoint: {endpoint_url}")
        
        # Add event handlers for raw request/response logging
        if self.enable_raw_logging:
            self._setup_raw_logging()
    
    def _configure_enhanced_logging(self):
        """Configure enhanced boto3/botocore logging if enabled."""
        if self.enable_boto_debug:
            # Enable full boto3 and botocore debug logging
            boto3.set_stream_logger('boto3.resources', logging.DEBUG)
            boto3.set_stream_logger('botocore', logging.DEBUG)
            boto3.set_stream_logger('botocore.credentials', logging.DEBUG)
            boto3.set_stream_logger('botocore.endpoint', logging.DEBUG)
            boto3.set_stream_logger('botocore.auth', logging.DEBUG)
            boto3.set_stream_logger('botocore.retryhandler', logging.DEBUG)
            
            self.logger.info("Enhanced boto3/botocore debug logging enabled")
    
    def _setup_raw_logging(self):
        """Setup raw HTTP request/response logging."""
        try:
            # Register event handlers for S3 operations
            self.client.meta.events.register('before-call.*.*', self._log_raw_request)
            self.client.meta.events.register('after-call.*.*', self._log_raw_response)
            self.client.meta.events.register('before-parameter-build.*.*', self._log_parameters)
            
            self.logger.info("Raw HTTP request/response logging enabled")
        except Exception as e:
            self.logger.warning(f"Failed to setup raw logging: {e}. Continuing without raw logging.")
    
    def _log_raw_request(self, event_name=None, model=None, **kwargs):
        """Log raw HTTP request details."""
        if hasattr(model, 'http') and self.enable_raw_logging:
            request_dict = model.http
            self.logger.debug(f"RAW REQUEST - Method: {request_dict.get('method', 'Unknown')}")
            self.logger.debug(f"RAW REQUEST - URI: {request_dict.get('uri', 'Unknown')}")
            
            # Log headers (mask authorization)
            headers = request_dict.get('headers', {})
            safe_headers = {k: ('***MASKED***' if 'authorization' in k.lower() else v) 
                          for k, v in headers.items()}
            self.logger.debug(f"RAW REQUEST - Headers: {safe_headers}")
            
            # Log body (truncate if too large)
            body = request_dict.get('body')
            if body:
                if isinstance(body, bytes):
                    if len(body) > 1024:
                        self.logger.debug(f"RAW REQUEST - Body: <{len(body)} bytes>")
                    else:
                        self.logger.debug(f"RAW REQUEST - Body: {body[:500]}{'...' if len(body) > 500 else ''}")
                else:
                    self.logger.debug(f"RAW REQUEST - Body: {str(body)[:500]}")
    
    def _log_raw_response(self, event_name=None, parsed=None, **kwargs):
        """Log raw HTTP response details."""
        if parsed and self.enable_raw_logging:
            # Log response metadata
            response_metadata = parsed.get('ResponseMetadata', {})
            self.logger.debug(f"RAW RESPONSE - Status: {response_metadata.get('HTTPStatusCode', 'Unknown')}")
            
            # Log response headers (mask sensitive ones)
            headers = response_metadata.get('HTTPHeaders', {})
            safe_headers = {k: ('***MASKED***' if any(sensitive in k.lower() 
                               for sensitive in ['authorization', 'signature', 'token']) else v)
                          for k, v in headers.items()}
            self.logger.debug(f"RAW RESPONSE - Headers: {safe_headers}")
            
            # Log response body structure (without sensitive data)
            response_copy = dict(parsed)
            if 'ResponseMetadata' in response_copy:
                del response_copy['ResponseMetadata']
            
            # Truncate large responses
            response_str = str(response_copy)
            if len(response_str) > 1000:
                self.logger.debug(f"RAW RESPONSE - Body: {response_str[:500]}...")
            else:
                self.logger.debug(f"RAW RESPONSE - Body: {response_str}")
    
    def _log_parameters(self, event_name=None, params=None, **kwargs):
        """Log API call parameters before they're processed."""
        if params and self.enable_raw_logging:
            # Create safe copy of parameters (mask sensitive data)
            safe_params = dict(params)
            
            # Mask body content if it's large
            if 'Body' in safe_params:
                body = safe_params['Body']
                if hasattr(body, '__len__') and len(body) > 1024:
                    safe_params['Body'] = f"<{len(body)} bytes>"
                elif isinstance(body, bytes) and len(body) > 100:
                    safe_params['Body'] = f"<{len(body)} bytes>"
            
            self.logger.debug(f"API PARAMETERS - {event_name}: {safe_params}")
    
    def _log_request(self, operation: str, **kwargs):
        """Log the request details."""
        # Create safe copy for logging (mask large bodies)
        safe_kwargs = dict(kwargs)
        if 'Body' in safe_kwargs:
            body = safe_kwargs['Body']
            if hasattr(body, '__len__') and len(body) > 1024:
                safe_kwargs['Body'] = f"<{len(body)} bytes>"
            elif isinstance(body, bytes) and len(body) > 100:
                safe_kwargs['Body'] = f"<{len(body)} bytes>"
        
        self.logger.debug(f"S3 Request: {operation} with params: {safe_kwargs}")
    
    def _log_response(self, operation: str, response: Dict[str, Any], duration: float):
        """Log the response details."""
        status_code = response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'Unknown')
        
        # Log basic response info
        self.logger.debug(f"S3 Response: {operation} completed in {duration:.3f}s with status {status_code}")
        
        # Log additional response details if raw logging is enabled
        if self.enable_raw_logging:
            response_metadata = response.get('ResponseMetadata', {})
            request_id = response_metadata.get('RequestId', 'Unknown')
            host_id = response_metadata.get('HostId', 'Unknown')
            
            self.logger.debug(f"S3 Response Details - RequestId: {request_id}, HostId: {host_id}")
            
            # Log important response fields (avoid logging large data)
            important_fields = ['ETag', 'VersionId', 'UploadId', 'ContentLength', 'ContentType', 
                              'LastModified', 'ServerSideEncryption', 'Bucket', 'Key']
            
            logged_fields = {}
            for field in important_fields:
                if field in response:
                    logged_fields[field] = response[field]
            
            if logged_fields:
                self.logger.debug(f"S3 Response Fields: {logged_fields}")
    
    def _handle_error(self, error: Exception, operation: str, **kwargs) -> S3ClientError:
        """
        Handle and transform boto3 errors into custom S3ClientError.
        
        Args:
            error: The original exception
            operation: The S3 operation that failed
            **kwargs: The parameters passed to the operation
            
        Returns:
            S3ClientError with detailed information
        """
        if isinstance(error, ClientError):
            error_code = error.response['Error']['Code']
            status_code = error.response['ResponseMetadata']['HTTPStatusCode']
            message = error.response['Error']['Message']
            
            self.logger.error(f"S3 ClientError in {operation}: {error_code} ({status_code}) - {message}")
            
            return S3ClientError(
                message=f"S3 {operation} failed: {message}",
                error_code=error_code,
                status_code=status_code,
                operation=operation,
                details={
                    'request_params': kwargs,
                    'aws_error': error.response['Error']
                }
            )
        
        elif isinstance(error, BotoCoreError):
            self.logger.error(f"S3 BotoCoreError in {operation}: {str(error)}")
            return S3ClientError(
                message=f"S3 {operation} failed: {str(error)}",
                operation=operation,
                details={'request_params': kwargs}
            )
        
        else:
            self.logger.error(f"Unexpected error in S3 {operation}: {str(error)}")
            return S3ClientError(
                message=f"S3 {operation} failed: {str(error)}",
                operation=operation,
                details={'request_params': kwargs}
            )
    
    def _execute_with_retry(self, operation: str, func, **kwargs):
        """
        Execute an S3 operation with retry logic and logging.
        
        Args:
            operation: Name of the S3 operation
            func: The boto3 client method to execute
            **kwargs: Parameters for the S3 operation
            
        Returns:
            The response from the S3 operation
            
        Raises:
            S3ClientError: If the operation fails after all retries
        """
        self._log_request(operation, **kwargs)
        start_time = time.time()
        
        try:
            response = func(**kwargs)
            duration = time.time() - start_time
            self._log_response(operation, response, duration)
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"S3 operation {operation} failed after {duration:.3f}s")
            raise self._handle_error(e, operation, **kwargs)
    
    # Bucket operations
    def create_bucket(self, **kwargs):
        """Create a bucket."""
        return self._execute_with_retry('create_bucket', self.client.create_bucket, **kwargs)
    
    def delete_bucket(self, **kwargs):
        """Delete a bucket."""
        return self._execute_with_retry('delete_bucket', self.client.delete_bucket, **kwargs)
    
    def head_bucket(self, **kwargs):
        """Check if a bucket exists."""
        return self._execute_with_retry('head_bucket', self.client.head_bucket, **kwargs)
    
    def list_buckets(self, **kwargs):
        """List all buckets."""
        return self._execute_with_retry('list_buckets', self.client.list_buckets, **kwargs)
    
    def put_bucket_versioning(self, **kwargs):
        """Set bucket versioning configuration."""
        return self._execute_with_retry('put_bucket_versioning', self.client.put_bucket_versioning, **kwargs)
    
    def get_bucket_versioning(self, **kwargs):
        """Get bucket versioning configuration."""
        return self._execute_with_retry('get_bucket_versioning', self.client.get_bucket_versioning, **kwargs)
    
    def put_bucket_tagging(self, **kwargs):
        """Set bucket tagging."""
        return self._execute_with_retry('put_bucket_tagging', self.client.put_bucket_tagging, **kwargs)
    
    def get_bucket_tagging(self, **kwargs):
        """Get bucket tagging."""
        return self._execute_with_retry('get_bucket_tagging', self.client.get_bucket_tagging, **kwargs)
    
    def delete_bucket_tagging(self, **kwargs):
        """Delete bucket tagging."""
        return self._execute_with_retry('delete_bucket_tagging', self.client.delete_bucket_tagging, **kwargs)
    
    # Object operations
    def put_object(self, **kwargs):
        """Upload an object."""
        return self._execute_with_retry('put_object', self.client.put_object, **kwargs)
    
    def get_object(self, **kwargs):
        """Download an object."""
        return self._execute_with_retry('get_object', self.client.get_object, **kwargs)
    
    def delete_object(self, **kwargs):
        """Delete an object."""
        return self._execute_with_retry('delete_object', self.client.delete_object, **kwargs)
    
    def head_object(self, **kwargs):
        """Get object metadata."""
        return self._execute_with_retry('head_object', self.client.head_object, **kwargs)
    
    def copy_object(self, **kwargs):
        """Copy an object."""
        return self._execute_with_retry('copy_object', self.client.copy_object, **kwargs)
    
    def list_objects_v2(self, **kwargs):
        """List objects in a bucket (v2)."""
        return self._execute_with_retry('list_objects_v2', self.client.list_objects_v2, **kwargs)
    
    def list_objects(self, **kwargs):
        """List objects in a bucket (v1)."""
        return self._execute_with_retry('list_objects', self.client.list_objects, **kwargs)
    
    def list_object_versions(self, **kwargs):
        """List object versions."""
        return self._execute_with_retry('list_object_versions', self.client.list_object_versions, **kwargs)
    
    def get_object_attributes(self, **kwargs):
        """Get object attributes."""
        return self._execute_with_retry('get_object_attributes', self.client.get_object_attributes, **kwargs)
    
    def put_object_tagging(self, **kwargs):
        """Set object tagging."""
        return self._execute_with_retry('put_object_tagging', self.client.put_object_tagging, **kwargs)
    
    def get_object_tagging(self, **kwargs):
        """Get object tagging."""
        return self._execute_with_retry('get_object_tagging', self.client.get_object_tagging, **kwargs)
    
    def delete_object_tagging(self, **kwargs):
        """Delete object tagging."""
        return self._execute_with_retry('delete_object_tagging', self.client.delete_object_tagging, **kwargs)
    
    # Multipart upload operations
    def create_multipart_upload(self, **kwargs):
        """Create a multipart upload."""
        return self._execute_with_retry('create_multipart_upload', self.client.create_multipart_upload, **kwargs)
    
    def upload_part(self, **kwargs):
        """Upload a part of a multipart upload."""
        return self._execute_with_retry('upload_part', self.client.upload_part, **kwargs)
    
    def complete_multipart_upload(self, **kwargs):
        """Complete a multipart upload."""
        return self._execute_with_retry('complete_multipart_upload', self.client.complete_multipart_upload, **kwargs)
    
    def abort_multipart_upload(self, **kwargs):
        """Abort a multipart upload."""
        return self._execute_with_retry('abort_multipart_upload', self.client.abort_multipart_upload, **kwargs)
    
    def list_multipart_uploads(self, **kwargs):
        """List multipart uploads."""
        return self._execute_with_retry('list_multipart_uploads', self.client.list_multipart_uploads, **kwargs)
    
    def list_parts(self, **kwargs):
        """List parts of a multipart upload."""
        return self._execute_with_retry('list_parts', self.client.list_parts, **kwargs)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information for debugging.
        
        Returns:
            Dictionary with connection details
        """
        return {
            'endpoint_url': self.endpoint_url,
            'region': self.region,
            'verify_ssl': self.verify_ssl,
            'max_retries': self.max_retries,
            'access_key': self.access_key[:8] + '...' if self.access_key else None  # Partial key for security
        }