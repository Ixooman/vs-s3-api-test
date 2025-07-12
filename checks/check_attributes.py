"""
Object attributes compatibility checks.

This module contains checks for S3 object attributes operations including
getting object attributes for size, storage class, and other metadata.
"""

import time
from typing import List
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class AttributeChecks(BaseCheck):
    """
    Object attributes compatibility checks.
    
    Tests object attributes functionality including getting object attributes
    for various metadata fields like size, storage class, ETag, etc.
    """
    
    def run_checks(self) -> List[CheckResult]:
        """
        Run all object attributes related compatibility checks.
        
        Returns:
            List of CheckResult objects for each attributes check
        """
        self.logger.info("Starting object attributes compatibility checks...")
        
        # Create a test bucket for attributes operations
        self.test_bucket = self.generate_unique_name("attributes-test-bucket")
        try:
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            self.add_cleanup_item('bucket', self.test_bucket)
            self.logger.info(f"Created test bucket: {self.test_bucket}")
        except S3ClientError as e:
            self.add_result(
                'attributes_test_bucket_creation',
                False,
                f"Failed to create test bucket for attributes operations: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Upload test objects for attributes testing
        self._upload_test_objects()
        
        # Run individual check methods
        self._check_basic_attributes()
        self._check_size_attributes()
        self._check_storage_class_attributes()
        self._check_multipart_attributes()
        
        self.logger.info(f"Object attributes checks completed: {len(self.results)} checks performed")
        return self.results
    
    def _upload_test_objects(self):
        """Upload test objects for attributes testing."""
        self.test_objects = {}
        
        # Upload small object
        small_key = self.generate_unique_name("small-attr-object")
        small_data = b"Small test data for attributes testing" * 10  # ~390 bytes
        
        try:
            response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=small_key,
                Body=small_data,
                ContentType='text/plain'
            )
            self.add_cleanup_item('object', small_key, bucket=self.test_bucket)
            self.test_objects['small'] = {
                'key': small_key,
                'size': len(small_data),
                'etag': response.get('ETag'),
                'content_type': 'text/plain'
            }
        except S3ClientError:
            pass
        
        # Upload medium object with metadata
        medium_key = self.generate_unique_name("medium-attr-object")
        medium_data = b"Medium test data for attributes testing " * 1000  # ~40KB
        metadata = {'test-field': 'attributes-test', 'object-type': 'medium'}
        
        try:
            response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=medium_key,
                Body=medium_data,
                ContentType='application/octet-stream',
                Metadata=metadata
            )
            self.add_cleanup_item('object', medium_key, bucket=self.test_bucket)
            self.test_objects['medium'] = {
                'key': medium_key,
                'size': len(medium_data),
                'etag': response.get('ETag'),
                'content_type': 'application/octet-stream',
                'metadata': metadata
            }
        except S3ClientError:
            pass
    
    def _check_basic_attributes(self):
        """Test basic object attributes operations."""
        self.logger.info("Checking basic object attributes...")
        
        if 'small' not in self.test_objects:
            self.add_result(
                'attributes_basic',
                False,
                "No test object available for basic attributes test",
                {}
            )
            return
        
        test_obj = self.test_objects['small']
        
        try:
            # Test getting ETag attribute
            start_time = time.time()
            response = self.s3_client.get_object_attributes(
                Bucket=self.test_bucket,
                Key=test_obj['key'],
                ObjectAttributes=['ETag']
            )
            duration = time.time() - start_time
            
            if 'ETag' in response:
                returned_etag = response['ETag']
                if returned_etag == test_obj['etag']:
                    self.add_result(
                        'attributes_etag',
                        True,
                        f"Successfully retrieved correct ETag attribute",
                        {
                            'object_key': test_obj['key'],
                            'etag': returned_etag,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'attributes_etag',
                        False,
                        f"ETag attribute doesn't match: expected {test_obj['etag']}, got {returned_etag}",
                        {
                            'object_key': test_obj['key'],
                            'expected_etag': test_obj['etag'],
                            'returned_etag': returned_etag,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'attributes_etag',
                    False,
                    f"Get object attributes response missing ETag field",
                    {
                        'object_key': test_obj['key'],
                        'response': response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'attributes_etag',
                False,
                f"Failed to get ETag attribute: {e}",
                {
                    'object_key': test_obj['key'],
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )
    
    def _check_size_attributes(self):
        """Test object size attributes."""
        self.logger.info("Checking object size attributes...")
        
        if 'medium' not in self.test_objects:
            self.add_result(
                'attributes_size',
                False,
                "No test object available for size attributes test",
                {}
            )
            return
        
        test_obj = self.test_objects['medium']
        
        try:
            # Test getting ObjectSize and StorageClass attributes
            start_time = time.time()
            response = self.s3_client.get_object_attributes(
                Bucket=self.test_bucket,
                Key=test_obj['key'],
                ObjectAttributes=['ObjectSize', 'StorageClass']
            )
            duration = time.time() - start_time
            
            checks_passed = []
            
            # Check ObjectSize
            if 'ObjectSize' in response:
                returned_size = response['ObjectSize']
                if returned_size == test_obj['size']:
                    checks_passed.append('size_correct')
                else:
                    self.add_result(
                        'attributes_size_mismatch',
                        False,
                        f"Object size mismatch: expected {test_obj['size']}, got {returned_size}",
                        {
                            'object_key': test_obj['key'],
                            'expected_size': test_obj['size'],
                            'returned_size': returned_size,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                checks_passed.append('size_missing')
            
            # Check StorageClass (optional, may not be supported)
            if 'StorageClass' in response:
                storage_class = response['StorageClass']
                checks_passed.append('storage_class_present')
            
            if 'size_correct' in checks_passed:
                self.add_result(
                    'attributes_size_and_storage',
                    True,
                    f"Successfully retrieved size attributes",
                    {
                        'object_key': test_obj['key'],
                        'object_size': response.get('ObjectSize'),
                        'storage_class': response.get('StorageClass', 'not_provided'),
                        'checks_passed': checks_passed,
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'attributes_size_and_storage',
                    False,
                    f"Size attributes validation failed",
                    {
                        'object_key': test_obj['key'],
                        'response': response,
                        'checks_passed': checks_passed,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'attributes_size_and_storage',
                False,
                f"Failed to get size attributes: {e}",
                {
                    'object_key': test_obj['key'],
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )
    
    def _check_storage_class_attributes(self):
        """Test storage class specific attributes."""
        self.logger.info("Checking storage class attributes...")
        
        if 'small' not in self.test_objects:
            return
        
        test_obj = self.test_objects['small']
        
        try:
            # Test multiple attributes at once
            start_time = time.time()
            response = self.s3_client.get_object_attributes(
                Bucket=self.test_bucket,
                Key=test_obj['key'],
                ObjectAttributes=['ETag', 'ObjectSize', 'StorageClass']
            )
            duration = time.time() - start_time
            
            # Count how many requested attributes were returned
            requested_attrs = ['ETag', 'ObjectSize', 'StorageClass']
            returned_attrs = [attr for attr in requested_attrs if attr in response]
            
            if len(returned_attrs) >= 2:  # At least ETag and ObjectSize should be supported
                self.add_result(
                    'attributes_multiple',
                    True,
                    f"Successfully retrieved multiple attributes ({len(returned_attrs)}/3)",
                    {
                        'object_key': test_obj['key'],
                        'requested_attributes': requested_attrs,
                        'returned_attributes': returned_attrs,
                        'response': response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'attributes_multiple',
                    False,
                    f"Too few attributes returned ({len(returned_attrs)}/3)",
                    {
                        'object_key': test_obj['key'],
                        'requested_attributes': requested_attrs,
                        'returned_attributes': returned_attrs,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'attributes_multiple',
                False,
                f"Failed to get multiple attributes: {e}",
                {
                    'object_key': test_obj['key'],
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )
    
    def _check_multipart_attributes(self):
        """Test attributes on multipart objects (if supported)."""
        self.logger.info("Checking multipart object attributes...")
        
        # Create a simple multipart object for testing
        multipart_key = self.generate_unique_name("multipart-attr-object")
        chunk_size = 1024 * 1024  # 1MB chunks
        
        try:
            # Create multipart upload
            create_response = self.s3_client.create_multipart_upload(
                Bucket=self.test_bucket,
                Key=multipart_key
            )
            upload_id = create_response['UploadId']
            
            # Upload 2 parts
            parts = []
            for part_num in range(1, 3):
                part_data = f"Multipart test data part {part_num} ".encode() * (chunk_size // 30)
                part_data = part_data[:chunk_size]  # Ensure exact size
                
                part_response = self.s3_client.upload_part(
                    Bucket=self.test_bucket,
                    Key=multipart_key,
                    PartNumber=part_num,
                    UploadId=upload_id,
                    Body=part_data
                )
                
                parts.append({
                    'ETag': part_response['ETag'],
                    'PartNumber': part_num
                })
            
            # Complete multipart upload
            complete_response = self.s3_client.complete_multipart_upload(
                Bucket=self.test_bucket,
                Key=multipart_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            self.add_cleanup_item('object', multipart_key, bucket=self.test_bucket)
            
            # Test getting ObjectParts attribute (if supported)
            try:
                start_time = time.time()
                response = self.s3_client.get_object_attributes(
                    Bucket=self.test_bucket,
                    Key=multipart_key,
                    ObjectAttributes=['ObjectParts']
                )
                duration = time.time() - start_time
                
                if 'ObjectParts' in response:
                    object_parts = response['ObjectParts']
                    if 'Parts' in object_parts:
                        returned_parts = object_parts['Parts']
                        if len(returned_parts) == 2:
                            self.add_result(
                                'attributes_multipart_parts',
                                True,
                                f"Successfully retrieved multipart object parts ({len(returned_parts)} parts)",
                                {
                                    'object_key': multipart_key,
                                    'parts_count': len(returned_parts),
                                    'bucket': self.test_bucket
                                },
                                duration
                            )
                        else:
                            self.add_result(
                                'attributes_multipart_parts',
                                False,
                                f"Expected 2 parts, got {len(returned_parts)}",
                                {
                                    'object_key': multipart_key,
                                    'expected_parts': 2,
                                    'actual_parts': len(returned_parts),
                                    'bucket': self.test_bucket
                                },
                                duration
                            )
                    else:
                        self.add_result(
                            'attributes_multipart_parts',
                            False,
                            f"ObjectParts response missing Parts field",
                            {
                                'object_key': multipart_key,
                                'object_parts': object_parts,
                                'bucket': self.test_bucket
                            },
                            duration
                        )
                else:
                    self.add_result(
                        'attributes_multipart_parts',
                        False,
                        f"Response missing ObjectParts field",
                        {
                            'object_key': multipart_key,
                            'response': response,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            
            except S3ClientError as attr_error:
                if attr_error.status_code in [400, 501]:
                    self.add_result(
                        'attributes_multipart_parts',
                        True,
                        f"ObjectParts attribute not supported (acceptable): {attr_error.error_code}",
                        {
                            'object_key': multipart_key,
                            'error_code': attr_error.error_code,
                            'note': 'ObjectParts is an advanced feature not required for basic S3 compatibility'
                        }
                    )
                else:
                    self.add_result(
                        'attributes_multipart_parts',
                        False,
                        f"Unexpected error getting multipart attributes: {attr_error}",
                        {
                            'object_key': multipart_key,
                            'error_code': attr_error.error_code,
                            'bucket': self.test_bucket
                        }
                    )
        
        except S3ClientError as e:
            self.add_result(
                'attributes_multipart_setup',
                False,
                f"Failed to create multipart object for attributes testing: {e}",
                {
                    'object_key': multipart_key,
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )