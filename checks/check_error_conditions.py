"""
Error condition compatibility checks.

This module contains checks for S3 error handling including invalid requests,
malformed parameters, permission errors, and edge cases to verify proper
error responses and behavior.
"""

import time
from typing import List
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class ErrorConditionChecks(BaseCheck):
    """
    Error condition compatibility checks.
    
    Tests various error scenarios to verify that the S3 implementation
    properly handles invalid requests and returns appropriate error codes
    and messages.
    """
    
    def run_checks(self) -> List[CheckResult]:
        """
        Run all error condition compatibility checks.
        
        Returns:
            List of CheckResult objects for each error condition check
        """
        self.logger.info("Starting error condition compatibility checks...")
        
        # Create a test bucket for error condition tests
        self.test_bucket = self.generate_unique_name("error-test-bucket")
        try:
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            self.add_cleanup_item('bucket', self.test_bucket)
            self.logger.info(f"Created test bucket: {self.test_bucket}")
        except S3ClientError as e:
            self.add_result(
                'error_test_bucket_creation',
                False,
                f"Failed to create test bucket for error testing: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Run individual check methods
        self._check_invalid_bucket_operations()
        self._check_invalid_object_operations()
        self._check_malformed_requests()
        self._check_permission_errors()
        self._check_resource_not_found_errors()
        self._check_invalid_parameters()
        self._check_size_limit_errors()
        self._check_concurrent_access_errors()
        
        self.logger.info(f"Error condition checks completed: {len(self.results)} checks performed")
        return self.results
    
    def _check_invalid_bucket_operations(self):
        """Test invalid bucket operations and their error responses."""
        self.logger.info("Checking invalid bucket operations...")
        
        # Test invalid bucket names
        invalid_bucket_names = [
            ("bucket_with_underscores", "Bucket name with underscores"),
            ("BUCKET-WITH-CAPITALS", "Bucket name with capital letters"),
            ("bucket-", "Bucket name ending with hyphen"),
            ("-bucket", "Bucket name starting with hyphen"),
            ("a" * 64, "Bucket name too long (64 chars)"),
            ("ab", "Bucket name too short (2 chars)"),
            ("bucket..name", "Bucket name with consecutive dots"),
            ("192.168.1.1", "Bucket name looks like IP address"),
            ("bucket name", "Bucket name with space"),
            ("", "Empty bucket name")
        ]
        
        for bucket_name, description in invalid_bucket_names:
            try:
                start_time = time.time()
                self.s3_client.create_bucket(Bucket=bucket_name)
                duration = time.time() - start_time
                
                # If creation succeeds, it should fail validation
                self.add_result(
                    f'invalid_bucket_name_{hash(bucket_name) % 1000}',
                    False,
                    f"Invalid bucket name accepted: {description}",
                    {
                        'bucket_name': bucket_name,
                        'description': description,
                        'note': 'Should have been rejected'
                    },
                    duration
                )
                # Clean up if it was actually created
                try:
                    self.s3_client.delete_bucket(Bucket=bucket_name)
                except:
                    pass
            
            except S3ClientError as e:
                # This is expected - invalid bucket names should be rejected
                if e.status_code in [400, 403]:  # Bad Request or Forbidden
                    self.add_result(
                        f'invalid_bucket_name_{hash(bucket_name) % 1000}',
                        True,
                        f"Invalid bucket name correctly rejected: {description}",
                        {
                            'bucket_name': bucket_name,
                            'description': description,
                            'error_code': e.error_code,
                            'status_code': e.status_code
                        }
                    )
                else:
                    self.add_result(
                        f'invalid_bucket_name_{hash(bucket_name) % 1000}',
                        False,
                        f"Invalid bucket name rejected with unexpected error: {description} - {e}",
                        {
                            'bucket_name': bucket_name,
                            'description': description,
                            'error_code': e.error_code,
                            'status_code': e.status_code
                        }
                    )
        
        # Test operations on non-existent bucket
        nonexistent_bucket = self.generate_unique_name("nonexistent-bucket")
        operations = [
            ("head_bucket", lambda: self.s3_client.head_bucket(Bucket=nonexistent_bucket)),
            ("delete_bucket", lambda: self.s3_client.delete_bucket(Bucket=nonexistent_bucket)),
            ("put_object", lambda: self.s3_client.put_object(Bucket=nonexistent_bucket, Key="test", Body=b"data")),
            ("get_object", lambda: self.s3_client.get_object(Bucket=nonexistent_bucket, Key="test")),
            ("list_objects", lambda: self.s3_client.list_objects_v2(Bucket=nonexistent_bucket))
        ]
        
        for op_name, operation in operations:
            try:
                start_time = time.time()
                operation()
                duration = time.time() - start_time
                
                # Operations on non-existent bucket should fail
                self.add_result(
                    f'nonexistent_bucket_{op_name}',
                    False,
                    f"Operation {op_name} succeeded on non-existent bucket",
                    {
                        'bucket_name': nonexistent_bucket,
                        'operation': op_name
                    },
                    duration
                )
            
            except S3ClientError as e:
                if e.status_code == 404:
                    self.add_result(
                        f'nonexistent_bucket_{op_name}',
                        True,
                        f"Operation {op_name} correctly returned 404 for non-existent bucket",
                        {
                            'bucket_name': nonexistent_bucket,
                            'operation': op_name,
                            'error_code': e.error_code
                        }
                    )
                else:
                    self.add_result(
                        f'nonexistent_bucket_{op_name}',
                        False,
                        f"Operation {op_name} returned unexpected error for non-existent bucket: {e}",
                        {
                            'bucket_name': nonexistent_bucket,
                            'operation': op_name,
                            'error_code': e.error_code,
                            'status_code': e.status_code
                        }
                    )
    
    def _check_invalid_object_operations(self):
        """Test invalid object operations and their error responses."""
        self.logger.info("Checking invalid object operations...")
        
        # Test invalid object keys
        invalid_object_keys = [
            ("", "Empty object key"),
            ("/" + "a" * 1024, "Object key too long"),
            ("object\x00null", "Object key with null character"),
            ("object\x01control", "Object key with control character"),
        ]
        
        for object_key, description in invalid_object_keys:
            try:
                start_time = time.time()
                self.s3_client.put_object(
                    Bucket=self.test_bucket,
                    Key=object_key,
                    Body=b"test data"
                )
                duration = time.time() - start_time
                
                # Invalid keys should be rejected
                self.add_result(
                    f'invalid_object_key_{hash(object_key) % 1000}',
                    False,
                    f"Invalid object key accepted: {description}",
                    {
                        'object_key': repr(object_key),  # Use repr to show special characters
                        'description': description,
                        'bucket': self.test_bucket
                    },
                    duration
                )
                # Clean up if created
                try:
                    self.s3_client.delete_object(Bucket=self.test_bucket, Key=object_key)
                except:
                    pass
            
            except S3ClientError as e:
                if e.status_code in [400, 403]:
                    self.add_result(
                        f'invalid_object_key_{hash(object_key) % 1000}',
                        True,
                        f"Invalid object key correctly rejected: {description}",
                        {
                            'object_key': repr(object_key),
                            'description': description,
                            'error_code': e.error_code,
                            'status_code': e.status_code
                        }
                    )
                else:
                    self.add_result(
                        f'invalid_object_key_{hash(object_key) % 1000}',
                        False,
                        f"Invalid object key rejected with unexpected error: {description} - {e}",
                        {
                            'object_key': repr(object_key),
                            'description': description,
                            'error_code': e.error_code,
                            'status_code': e.status_code
                        }
                    )
        
        # Test operations on non-existent objects
        nonexistent_key = self.generate_unique_name("nonexistent-object")
        object_operations = [
            ("get_object", lambda: self.s3_client.get_object(Bucket=self.test_bucket, Key=nonexistent_key)),
            ("head_object", lambda: self.s3_client.head_object(Bucket=self.test_bucket, Key=nonexistent_key)),
            ("delete_object", lambda: self.s3_client.delete_object(Bucket=self.test_bucket, Key=nonexistent_key)),
            ("copy_object", lambda: self.s3_client.copy_object(
                CopySource={'Bucket': self.test_bucket, 'Key': nonexistent_key},
                Bucket=self.test_bucket,
                Key="copy-dest"
            )),
            ("get_object_tagging", lambda: self.s3_client.get_object_tagging(Bucket=self.test_bucket, Key=nonexistent_key))
        ]
        
        for op_name, operation in object_operations:
            try:
                start_time = time.time()
                operation()
                duration = time.time() - start_time
                
                # Some operations (like delete) might be idempotent
                if op_name == "delete_object":
                    self.add_result(
                        f'nonexistent_object_{op_name}',
                        True,
                        f"Delete operation on non-existent object succeeded (idempotent behavior)",
                        {
                            'object_key': nonexistent_key,
                            'operation': op_name,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        f'nonexistent_object_{op_name}',
                        False,
                        f"Operation {op_name} succeeded on non-existent object",
                        {
                            'object_key': nonexistent_key,
                            'operation': op_name,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            
            except S3ClientError as e:
                if e.status_code == 404:
                    self.add_result(
                        f'nonexistent_object_{op_name}',
                        True,
                        f"Operation {op_name} correctly returned 404 for non-existent object",
                        {
                            'object_key': nonexistent_key,
                            'operation': op_name,
                            'error_code': e.error_code,
                            'bucket': self.test_bucket
                        }
                    )
                else:
                    self.add_result(
                        f'nonexistent_object_{op_name}',
                        False,
                        f"Operation {op_name} returned unexpected error for non-existent object: {e}",
                        {
                            'object_key': nonexistent_key,
                            'operation': op_name,
                            'error_code': e.error_code,
                            'status_code': e.status_code,
                            'bucket': self.test_bucket
                        }
                    )
    
    def _check_malformed_requests(self):
        """Test malformed requests and parameter validation."""
        self.logger.info("Checking malformed requests...")
        
        # Test invalid multipart upload operations
        try:
            # Try to complete multipart upload with invalid upload ID
            start_time = time.time()
            self.s3_client.complete_multipart_upload(
                Bucket=self.test_bucket,
                Key="test-multipart",
                UploadId="invalid-upload-id-12345",
                MultipartUpload={'Parts': [{'ETag': 'fake-etag', 'PartNumber': 1}]}
            )
            duration = time.time() - start_time
            
            self.add_result(
                'malformed_complete_multipart',
                False,
                "Complete multipart upload with invalid ID succeeded",
                {
                    'upload_id': 'invalid-upload-id-12345',
                    'bucket': self.test_bucket
                },
                duration
            )
        
        except S3ClientError as e:
            if e.status_code in [400, 404]:
                self.add_result(
                    'malformed_complete_multipart',
                    True,
                    "Complete multipart upload correctly rejected invalid upload ID",
                    {
                        'upload_id': 'invalid-upload-id-12345',
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            else:
                self.add_result(
                    'malformed_complete_multipart',
                    False,
                    f"Complete multipart upload returned unexpected error: {e}",
                    {
                        'upload_id': 'invalid-upload-id-12345',
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
        
        # Test invalid tagging operations
        try:
            # Try to set tags with invalid structure
            start_time = time.time()
            self.s3_client.put_bucket_tagging(
                Bucket=self.test_bucket,
                Tagging={'InvalidStructure': 'This should fail'}
            )
            duration = time.time() - start_time
            
            self.add_result(
                'malformed_bucket_tagging',
                False,
                "Invalid bucket tagging structure accepted",
                {'bucket': self.test_bucket},
                duration
            )
        
        except S3ClientError as e:
            if e.status_code == 400:
                self.add_result(
                    'malformed_bucket_tagging',
                    True,
                    "Invalid bucket tagging structure correctly rejected",
                    {
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            else:
                self.add_result(
                    'malformed_bucket_tagging',
                    False,
                    f"Invalid bucket tagging returned unexpected error: {e}",
                    {
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
        
        # Test invalid versioning configuration
        try:
            start_time = time.time()
            self.s3_client.put_bucket_versioning(
                Bucket=self.test_bucket,
                VersioningConfiguration={'Status': 'InvalidStatus'}
            )
            duration = time.time() - start_time
            
            self.add_result(
                'malformed_versioning_config',
                False,
                "Invalid versioning configuration accepted",
                {'bucket': self.test_bucket},
                duration
            )
        
        except S3ClientError as e:
            if e.status_code == 400:
                self.add_result(
                    'malformed_versioning_config',
                    True,
                    "Invalid versioning configuration correctly rejected",
                    {
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            else:
                self.add_result(
                    'malformed_versioning_config',
                    False,
                    f"Invalid versioning configuration returned unexpected error: {e}",
                    {
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
    
    def _check_permission_errors(self):
        """Test permission-related error scenarios."""
        self.logger.info("Checking permission errors...")
        
        # Note: This section tests what should happen with permission errors
        # In a real scenario with proper auth, these would test actual permission denials
        
        # Test operations that might require special permissions
        # Since we're using the configured credentials, these might not fail,
        # but we can test the behavior
        
        # Try to access bucket policy (often requires special permissions)
        try:
            start_time = time.time()
            # Most S3 implementations don't support bucket policies, so this should fail
            # We'll use the raw client to try an operation that's not wrapped
            response = self.s3_client.client.get_bucket_policy(Bucket=self.test_bucket)
            duration = time.time() - start_time
            
            self.add_result(
                'bucket_policy_access',
                False,
                "Bucket policy access succeeded (unexpected for most S3-compatible storages)",
                {
                    'bucket': self.test_bucket,
                    'response': response
                },
                duration
            )
        
        except Exception as e:
            # Extract error information
            if hasattr(e, 'response'):
                status_code = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
                error_code = e.response.get('Error', {}).get('Code')
                
                if status_code in [403, 501]:  # Forbidden or Not Implemented
                    self.add_result(
                        'bucket_policy_access',
                        True,
                        f"Bucket policy access correctly denied or not implemented",
                        {
                            'bucket': self.test_bucket,
                            'error_code': error_code,
                            'status_code': status_code
                        }
                    )
                elif status_code == 404:
                    self.add_result(
                        'bucket_policy_access',
                        True,
                        f"Bucket policy not found (acceptable - no policy set)",
                        {
                            'bucket': self.test_bucket,
                            'error_code': error_code,
                            'status_code': status_code
                        }
                    )
                else:
                    self.add_result(
                        'bucket_policy_access',
                        False,
                        f"Bucket policy access returned unexpected error: {e}",
                        {
                            'bucket': self.test_bucket,
                            'error_code': error_code,
                            'status_code': status_code
                        }
                    )
            else:
                self.add_result(
                    'bucket_policy_access',
                    True,
                    f"Bucket policy access failed as expected: {e}",
                    {'bucket': self.test_bucket}
                )
    
    def _check_resource_not_found_errors(self):
        """Test 404 error responses for missing resources."""
        self.logger.info("Checking resource not found errors...")
        
        # We've already tested some of these in other methods,
        # but let's verify consistent 404 behavior
        
        missing_resources = [
            ("bucket", lambda: self.s3_client.head_bucket(Bucket="missing-bucket-12345")),
            ("object", lambda: self.s3_client.get_object(Bucket=self.test_bucket, Key="missing-object-12345")),
            ("object_metadata", lambda: self.s3_client.head_object(Bucket=self.test_bucket, Key="missing-metadata-12345")),
            ("object_tags", lambda: self.s3_client.get_object_tagging(Bucket=self.test_bucket, Key="missing-tags-12345"))
        ]
        
        for resource_type, operation in missing_resources:
            try:
                start_time = time.time()
                operation()
                duration = time.time() - start_time
                
                self.add_result(
                    f'missing_{resource_type}_404',
                    False,
                    f"Missing {resource_type} operation succeeded unexpectedly",
                    {'resource_type': resource_type},
                    duration
                )
            
            except S3ClientError as e:
                if e.status_code == 404:
                    self.add_result(
                        f'missing_{resource_type}_404',
                        True,
                        f"Missing {resource_type} correctly returned 404",
                        {
                            'resource_type': resource_type,
                            'error_code': e.error_code
                        }
                    )
                else:
                    self.add_result(
                        f'missing_{resource_type}_404',
                        False,
                        f"Missing {resource_type} returned unexpected status: {e.status_code}",
                        {
                            'resource_type': resource_type,
                            'error_code': e.error_code,
                            'status_code': e.status_code
                        }
                    )
    
    def _check_invalid_parameters(self):
        """Test invalid parameter handling."""
        self.logger.info("Checking invalid parameter handling...")
        
        # Upload a test object for parameter testing
        test_key = self.generate_unique_name("param-test-object")
        try:
            self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=b"test data for parameter validation"
            )
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
        except S3ClientError:
            # If we can't upload, skip parameter tests
            return
        
        # Test invalid version ID
        try:
            start_time = time.time()
            self.s3_client.get_object(
                Bucket=self.test_bucket,
                Key=test_key,
                VersionId="invalid-version-id-12345"
            )
            duration = time.time() - start_time
            
            self.add_result(
                'invalid_version_id',
                False,
                "Invalid version ID accepted",
                {
                    'object_key': test_key,
                    'version_id': 'invalid-version-id-12345',
                    'bucket': self.test_bucket
                },
                duration
            )
        
        except S3ClientError as e:
            if e.status_code in [400, 404]:
                self.add_result(
                    'invalid_version_id',
                    True,
                    "Invalid version ID correctly rejected",
                    {
                        'object_key': test_key,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            else:
                self.add_result(
                    'invalid_version_id',
                    False,
                    f"Invalid version ID returned unexpected error: {e}",
                    {
                        'object_key': test_key,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
    
    def _check_size_limit_errors(self):
        """Test size limit error handling."""
        self.logger.info("Checking size limit errors...")
        
        # Test extremely large metadata
        large_metadata = {f"key{i}": "x" * 1000 for i in range(20)}  # 20KB+ of metadata
        large_key = self.generate_unique_name("large-metadata-test")
        
        try:
            start_time = time.time()
            self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=large_key,
                Body=b"test",
                Metadata=large_metadata
            )
            duration = time.time() - start_time
            
            # If this succeeds, the implementation might be very lenient
            self.add_result(
                'large_metadata_limit',
                False,
                "Extremely large metadata accepted (might indicate no size limits)",
                {
                    'object_key': large_key,
                    'metadata_size': sum(len(k) + len(v) for k, v in large_metadata.items()),
                    'bucket': self.test_bucket
                },
                duration
            )
            self.add_cleanup_item('object', large_key, bucket=self.test_bucket)
        
        except S3ClientError as e:
            if e.status_code in [400, 413]:  # Bad Request or Payload Too Large
                self.add_result(
                    'large_metadata_limit',
                    True,
                    "Large metadata correctly rejected",
                    {
                        'object_key': large_key,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            else:
                self.add_result(
                    'large_metadata_limit',
                    False,
                    f"Large metadata returned unexpected error: {e}",
                    {
                        'object_key': large_key,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
    
    def _check_concurrent_access_errors(self):
        """Test concurrent access error scenarios."""
        self.logger.info("Checking concurrent access scenarios...")
        
        # Test creating bucket that already exists
        try:
            start_time = time.time()
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            duration = time.time() - start_time
            
            # Some S3 implementations might allow this (idempotent)
            self.add_result(
                'duplicate_bucket_creation',
                True,
                "Duplicate bucket creation succeeded (idempotent behavior)",
                {'bucket': self.test_bucket},
                duration
            )
        
        except S3ClientError as e:
            if e.error_code in ['BucketAlreadyExists', 'BucketAlreadyOwnedByYou']:
                self.add_result(
                    'duplicate_bucket_creation',
                    True,
                    "Duplicate bucket creation correctly rejected",
                    {
                        'bucket': self.test_bucket,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            else:
                self.add_result(
                    'duplicate_bucket_creation',
                    False,
                    f"Duplicate bucket creation returned unexpected error: {e}",
                    {
                        'bucket': self.test_bucket,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
        
        # Test deleting bucket with objects (should fail)
        object_key = self.generate_unique_name("blocking-object")
        try:
            # Upload an object
            self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=object_key,
                Body=b"blocking object"
            )
            
            # Try to delete bucket with object
            start_time = time.time()
            self.s3_client.delete_bucket(Bucket=self.test_bucket)
            duration = time.time() - start_time
            
            self.add_result(
                'delete_bucket_with_objects',
                False,
                "Bucket deletion succeeded despite containing objects",
                {
                    'bucket': self.test_bucket,
                    'object_key': object_key
                },
                duration
            )
        
        except S3ClientError as e:
            if e.error_code == 'BucketNotEmpty' or e.status_code == 409:
                self.add_result(
                    'delete_bucket_with_objects',
                    True,
                    "Bucket deletion correctly rejected (bucket not empty)",
                    {
                        'bucket': self.test_bucket,
                        'object_key': object_key,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            else:
                self.add_result(
                    'delete_bucket_with_objects',
                    False,
                    f"Bucket deletion returned unexpected error: {e}",
                    {
                        'bucket': self.test_bucket,
                        'object_key': object_key,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            
            # Clean up the object we created
            try:
                self.s3_client.delete_object(Bucket=self.test_bucket, Key=object_key)
            except:
                pass