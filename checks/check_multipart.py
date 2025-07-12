"""
Multipart upload compatibility checks.

This module contains checks for S3 multipart upload operations including
creation, part uploads, completion, and abort operations.
"""

import time
import hashlib
from typing import List
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class MultipartChecks(BaseCheck):
    """
    Multipart upload compatibility checks.
    
    Tests multipart upload workflow including creation, part uploads,
    listing parts, completion, and abort operations.
    """
    
    def run_checks(self) -> List[CheckResult]:
        """
        Run all multipart upload related compatibility checks.
        
        Returns:
            List of CheckResult objects for each multipart operation check
        """
        self.logger.info("Starting multipart upload compatibility checks...")
        
        # Create a test bucket for multipart operations
        self.test_bucket = self.generate_unique_name("multipart-test-bucket")
        try:
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            self.add_cleanup_item('bucket', self.test_bucket)
            self.logger.info(f"Created test bucket: {self.test_bucket}")
        except S3ClientError as e:
            self.add_result(
                'multipart_test_bucket_creation',
                False,
                f"Failed to create test bucket for multipart operations: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Run individual check methods
        self._check_multipart_upload_creation()
        self._check_multipart_part_upload()
        self._check_multipart_list_parts()
        self._check_multipart_completion()
        self._check_multipart_abort()
        self._check_multipart_list_uploads()
        
        self.logger.info(f"Multipart upload checks completed: {len(self.results)} checks performed")
        return self.results
    
    def _generate_test_part_data(self, part_number: int, size: int) -> bytes:
        """Generate test data for a multipart upload part."""
        content = f"Multipart upload test data - Part {part_number}\n"
        content_bytes = content.encode('utf-8')
        
        # Repeat content to reach desired size
        data = b''
        while len(data) < size:
            data += content_bytes
        
        return data[:size]
    
    def _check_multipart_upload_creation(self):
        """Test multipart upload creation."""
        self.logger.info("Checking multipart upload creation...")
        
        test_key = self.generate_unique_name("multipart-creation-test")
        
        try:
            start_time = time.time()
            response = self.s3_client.create_multipart_upload(
                Bucket=self.test_bucket,
                Key=test_key,
                ContentType='application/octet-stream'
            )
            duration = time.time() - start_time
            
            # Validate response
            if 'UploadId' in response:
                upload_id = response['UploadId']
                self.add_cleanup_item('multipart_upload', test_key, 
                                    bucket=self.test_bucket, upload_id=upload_id)
                
                self.add_result(
                    'multipart_upload_creation',
                    True,
                    f"Successfully created multipart upload",
                    {
                        'object_key': test_key,
                        'upload_id': upload_id,
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'multipart_upload_creation',
                    False,
                    f"Multipart upload response missing UploadId",
                    {
                        'object_key': test_key,
                        'response': response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'multipart_upload_creation',
                False,
                f"Failed to create multipart upload: {e}",
                {
                    'object_key': test_key,
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )
    
    def _check_multipart_part_upload(self):
        """Test uploading parts to multipart upload."""
        self.logger.info("Checking multipart part upload...")
        
        test_key = self.generate_unique_name("multipart-parts-test")
        chunk_size = self.config.get('test_data', {}).get('multipart_chunk_size', 5242880)  # 5MB
        
        try:
            # Create multipart upload
            create_response = self.s3_client.create_multipart_upload(
                Bucket=self.test_bucket,
                Key=test_key
            )
            upload_id = create_response['UploadId']
            self.add_cleanup_item('multipart_upload', test_key, 
                                bucket=self.test_bucket, upload_id=upload_id)
            
            # Upload 3 parts
            parts = []
            for part_num in range(1, 4):  # Parts 1, 2, 3
                part_data = self._generate_test_part_data(part_num, chunk_size)
                
                start_time = time.time()
                part_response = self.s3_client.upload_part(
                    Bucket=self.test_bucket,
                    Key=test_key,
                    PartNumber=part_num,
                    UploadId=upload_id,
                    Body=part_data
                )
                duration = time.time() - start_time
                
                if 'ETag' in part_response:
                    parts.append({
                        'PartNumber': part_num,
                        'ETag': part_response['ETag'],
                        'Size': len(part_data)
                    })
                    
                    self.add_result(
                        f'multipart_part_upload_{part_num}',
                        True,
                        f"Successfully uploaded part {part_num} ({len(part_data)} bytes)",
                        {
                            'object_key': test_key,
                            'part_number': part_num,
                            'part_size': len(part_data),
                            'etag': part_response['ETag'],
                            'upload_id': upload_id,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        f'multipart_part_upload_{part_num}',
                        False,
                        f"Part {part_num} upload response missing ETag",
                        {
                            'object_key': test_key,
                            'part_number': part_num,
                            'response': part_response,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            
            # Store parts list for completion test
            if len(parts) == 3:
                self.multipart_test_data = {
                    'key': test_key,
                    'upload_id': upload_id,
                    'parts': parts
                }
        
        except S3ClientError as e:
            self.add_result(
                'multipart_part_upload',
                False,
                f"Failed to upload multipart parts: {e}",
                {
                    'object_key': test_key,
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )
    
    def _check_multipart_list_parts(self):
        """Test listing parts of a multipart upload."""
        self.logger.info("Checking multipart list parts...")
        
        if not hasattr(self, 'multipart_test_data'):
            self.add_result(
                'multipart_list_parts',
                False,
                "No multipart upload available for list parts test",
                {}
            )
            return
        
        test_data = self.multipart_test_data
        
        try:
            start_time = time.time()
            response = self.s3_client.list_parts(
                Bucket=self.test_bucket,
                Key=test_data['key'],
                UploadId=test_data['upload_id']
            )
            duration = time.time() - start_time
            
            # Validate response
            if 'Parts' in response:
                listed_parts = response['Parts']
                expected_parts = test_data['parts']
                
                if len(listed_parts) == len(expected_parts):
                    # Verify part details
                    parts_match = True
                    for i, listed_part in enumerate(listed_parts):
                        expected_part = expected_parts[i]
                        if (listed_part['PartNumber'] != expected_part['PartNumber'] or
                            listed_part['ETag'] != expected_part['ETag']):
                            parts_match = False
                            break
                    
                    if parts_match:
                        self.add_result(
                            'multipart_list_parts',
                            True,
                            f"Successfully listed {len(listed_parts)} parts",
                            {
                                'object_key': test_data['key'],
                                'upload_id': test_data['upload_id'],
                                'parts_count': len(listed_parts),
                                'bucket': self.test_bucket
                            },
                            duration
                        )
                    else:
                        self.add_result(
                            'multipart_list_parts',
                            False,
                            f"Listed parts don't match uploaded parts",
                            {
                                'object_key': test_data['key'],
                                'expected_parts': expected_parts,
                                'listed_parts': listed_parts,
                                'bucket': self.test_bucket
                            },
                            duration
                        )
                else:
                    self.add_result(
                        'multipart_list_parts',
                        False,
                        f"Expected {len(expected_parts)} parts, got {len(listed_parts)}",
                        {
                            'object_key': test_data['key'],
                            'expected_count': len(expected_parts),
                            'actual_count': len(listed_parts),
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'multipart_list_parts',
                    False,
                    f"List parts response missing 'Parts' field",
                    {
                        'object_key': test_data['key'],
                        'response': response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'multipart_list_parts',
                False,
                f"Failed to list multipart parts: {e}",
                {
                    'object_key': test_data['key'],
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )
    
    def _check_multipart_completion(self):
        """Test completing a multipart upload."""
        self.logger.info("Checking multipart completion...")
        
        if not hasattr(self, 'multipart_test_data'):
            self.add_result(
                'multipart_completion',
                False,
                "No multipart upload available for completion test",
                {}
            )
            return
        
        test_data = self.multipart_test_data
        
        try:
            # Prepare parts list for completion
            parts_list = [
                {
                    'ETag': part['ETag'],
                    'PartNumber': part['PartNumber']
                }
                for part in test_data['parts']
            ]
            
            start_time = time.time()
            response = self.s3_client.complete_multipart_upload(
                Bucket=self.test_bucket,
                Key=test_data['key'],
                UploadId=test_data['upload_id'],
                MultipartUpload={'Parts': parts_list}
            )
            duration = time.time() - start_time
            
            # Validate completion
            if 'ETag' in response:
                self.add_result(
                    'multipart_completion',
                    True,
                    f"Successfully completed multipart upload",
                    {
                        'object_key': test_data['key'],
                        'upload_id': test_data['upload_id'],
                        'final_etag': response['ETag'],
                        'parts_count': len(parts_list),
                        'bucket': self.test_bucket
                    },
                    duration
                )
                
                # Add object to cleanup (remove multipart upload cleanup)
                self.cleanup_items = [item for item in self.cleanup_items 
                                    if not (item['type'] == 'multipart_upload' and 
                                           item['identifier'] == test_data['key'])]
                self.add_cleanup_item('object', test_data['key'], bucket=self.test_bucket)
                
                # Verify object exists and has correct size
                try:
                    head_response = self.s3_client.head_object(
                        Bucket=self.test_bucket,
                        Key=test_data['key']
                    )
                    
                    expected_size = sum(part['Size'] for part in test_data['parts'])
                    actual_size = head_response.get('ContentLength', 0)
                    
                    if actual_size == expected_size:
                        self.add_result(
                            'multipart_completion_verification',
                            True,
                            f"Completed object has correct size ({actual_size} bytes)",
                            {
                                'object_key': test_data['key'],
                                'expected_size': expected_size,
                                'actual_size': actual_size,
                                'bucket': self.test_bucket
                            }
                        )
                    else:
                        self.add_result(
                            'multipart_completion_verification',
                            False,
                            f"Completed object size mismatch: expected {expected_size}, got {actual_size}",
                            {
                                'object_key': test_data['key'],
                                'expected_size': expected_size,
                                'actual_size': actual_size,
                                'bucket': self.test_bucket
                            }
                        )
                
                except S3ClientError as verify_error:
                    self.add_result(
                        'multipart_completion_verification',
                        False,
                        f"Failed to verify completed object: {verify_error}",
                        {
                            'object_key': test_data['key'],
                            'error_code': verify_error.error_code,
                            'bucket': self.test_bucket
                        }
                    )
            else:
                self.add_result(
                    'multipart_completion',
                    False,
                    f"Multipart completion response missing ETag",
                    {
                        'object_key': test_data['key'],
                        'response': response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'multipart_completion',
                False,
                f"Failed to complete multipart upload: {e}",
                {
                    'object_key': test_data['key'],
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )
    
    def _check_multipart_abort(self):
        """Test aborting a multipart upload."""
        self.logger.info("Checking multipart abort...")
        
        test_key = self.generate_unique_name("multipart-abort-test")
        
        try:
            # Create multipart upload
            create_response = self.s3_client.create_multipart_upload(
                Bucket=self.test_bucket,
                Key=test_key
            )
            upload_id = create_response['UploadId']
            
            # Upload one part
            part_data = self._generate_test_part_data(1, 1024)
            self.s3_client.upload_part(
                Bucket=self.test_bucket,
                Key=test_key,
                PartNumber=1,
                UploadId=upload_id,
                Body=part_data
            )
            
            # Abort the multipart upload
            start_time = time.time()
            self.s3_client.abort_multipart_upload(
                Bucket=self.test_bucket,
                Key=test_key,
                UploadId=upload_id
            )
            duration = time.time() - start_time
            
            self.add_result(
                'multipart_abort',
                True,
                f"Successfully aborted multipart upload",
                {
                    'object_key': test_key,
                    'upload_id': upload_id,
                    'bucket': self.test_bucket
                },
                duration
            )
            
            # Verify abort by trying to list parts (should fail)
            try:
                self.s3_client.list_parts(
                    Bucket=self.test_bucket,
                    Key=test_key,
                    UploadId=upload_id
                )
                
                self.add_result(
                    'multipart_abort_verification',
                    False,
                    f"List parts succeeded after abort (upload should not exist)",
                    {
                        'object_key': test_key,
                        'upload_id': upload_id,
                        'bucket': self.test_bucket
                    }
                )
            
            except S3ClientError as list_error:
                if list_error.status_code == 404:
                    self.add_result(
                        'multipart_abort_verification',
                        True,
                        f"Aborted upload correctly not found (404)",
                        {
                            'object_key': test_key,
                            'upload_id': upload_id,
                            'bucket': self.test_bucket
                        }
                    )
                else:
                    self.add_result(
                        'multipart_abort_verification',
                        False,
                        f"Unexpected error verifying abort: {list_error}",
                        {
                            'object_key': test_key,
                            'upload_id': upload_id,
                            'error_code': list_error.error_code,
                            'bucket': self.test_bucket
                        }
                    )
        
        except S3ClientError as e:
            self.add_result(
                'multipart_abort',
                False,
                f"Failed to abort multipart upload: {e}",
                {
                    'object_key': test_key,
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )
    
    def _check_multipart_list_uploads(self):
        """Test listing multipart uploads."""
        self.logger.info("Checking multipart list uploads...")
        
        try:
            start_time = time.time()
            response = self.s3_client.list_multipart_uploads(Bucket=self.test_bucket)
            duration = time.time() - start_time
            
            # Should return a valid response (may be empty)
            if 'Uploads' in response:
                uploads_count = len(response['Uploads'])
                self.add_result(
                    'multipart_list_uploads',
                    True,
                    f"Successfully listed multipart uploads ({uploads_count} found)",
                    {
                        'uploads_count': uploads_count,
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'multipart_list_uploads',
                    False,
                    f"List multipart uploads response missing 'Uploads' field",
                    {
                        'response': response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'multipart_list_uploads',
                False,
                f"Failed to list multipart uploads: {e}",
                {
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )