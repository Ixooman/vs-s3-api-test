"""
Object operations compatibility checks.

This module contains checks for S3 object operations including upload,
download, copy, delete, and object metadata operations.
"""

import time
import os
import tempfile
from typing import List
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class ObjectChecks(BaseCheck):
    """
    Object operations compatibility checks.
    
    Tests object upload, download, copy, delete, and metadata operations
    to verify S3 API compatibility for object management.
    """
    
    def run_checks(self) -> List[CheckResult]:
        """
        Run all object-related compatibility checks.
        
        Returns:
            List of CheckResult objects for each object operation check
        """
        self.logger.info("Starting object compatibility checks...")
        
        # Create a test bucket for object operations
        self.test_bucket = self.generate_unique_name("object-test-bucket")
        try:
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            self.add_cleanup_item('bucket', self.test_bucket)
            self.logger.info(f"Created test bucket: {self.test_bucket}")
        except S3ClientError as e:
            self.add_result(
                'object_test_bucket_creation',
                False,
                f"Failed to create test bucket for object operations: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Run individual check methods
        self._check_object_upload()
        self._check_object_download()
        self._check_object_head_operation()
        self._check_object_copy()
        self._check_object_listing()
        self._check_object_metadata()
        self._check_object_deletion()
        
        self.logger.info(f"Object checks completed: {len(self.results)} checks performed")
        return self.results
    
    def _generate_test_data(self, size: int, content: str = None) -> bytes:
        """
        Generate test data of specified size.
        
        Args:
            size: Size of data in bytes
            content: Base content to repeat (optional)
            
        Returns:
            Test data as bytes
        """
        if content is None:
            content = self.config.get('test_data', {}).get('test_file_content', 'S3 compatibility test data')
        
        # Repeat content to reach desired size
        content_bytes = content.encode('utf-8')
        if len(content_bytes) >= size:
            return content_bytes[:size]
        
        # Repeat content and add sequence numbers to make it unique
        data = b''
        chunk_num = 0
        while len(data) < size:
            chunk = f"{content} - chunk {chunk_num}\n".encode('utf-8')
            data += chunk
            chunk_num += 1
        
        return data[:size]
    
    def _check_object_upload(self):
        """Test object upload operations."""
        self.logger.info("Checking object upload...")
        
        # Test small file upload
        small_size = self.config.get('test_data', {}).get('small_file_size', 1024)
        small_data = self._generate_test_data(small_size)
        small_key = self.generate_unique_name("small-object")
        
        try:
            start_time = time.time()
            response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=small_key,
                Body=small_data
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', small_key, bucket=self.test_bucket)
            
            # Validate response
            if 'ETag' in response:
                self.add_result(
                    'object_upload_small',
                    True,
                    f"Successfully uploaded small object ({small_size} bytes)",
                    {
                        'object_key': small_key,
                        'size': small_size,
                        'etag': response['ETag'],
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'object_upload_small',
                    False,
                    f"Upload response missing ETag",
                    {'object_key': small_key, 'response': response},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'object_upload_small',
                False,
                f"Failed to upload small object: {e}",
                {'object_key': small_key, 'error_code': e.error_code}
            )
        
        # Test medium file upload
        medium_size = self.config.get('test_data', {}).get('medium_file_size', 1048576)
        medium_data = self._generate_test_data(medium_size)
        medium_key = self.generate_unique_name("medium-object")
        
        try:
            start_time = time.time()
            response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=medium_key,
                Body=medium_data,
                ContentType='application/octet-stream'
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', medium_key, bucket=self.test_bucket)
            
            if 'ETag' in response:
                self.add_result(
                    'object_upload_medium',
                    True,
                    f"Successfully uploaded medium object ({medium_size} bytes)",
                    {
                        'object_key': medium_key,
                        'size': medium_size,
                        'etag': response['ETag'],
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'object_upload_medium',
                    False,
                    f"Medium upload response missing ETag",
                    {'object_key': medium_key, 'response': response},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'object_upload_medium',
                False,
                f"Failed to upload medium object: {e}",
                {'object_key': medium_key, 'error_code': e.error_code}
            )
        
        # Test upload with metadata
        metadata_key = self.generate_unique_name("metadata-object")
        metadata = {
            'author': 'S3CompatibilityChecker',
            'test-type': 'object-upload',
            'custom-field': 'test-value'
        }
        
        try:
            start_time = time.time()
            response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=metadata_key,
                Body=small_data,
                Metadata=metadata,
                ContentType='text/plain'
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', metadata_key, bucket=self.test_bucket)
            
            if 'ETag' in response:
                self.add_result(
                    'object_upload_with_metadata',
                    True,
                    f"Successfully uploaded object with metadata",
                    {
                        'object_key': metadata_key,
                        'metadata': metadata,
                        'etag': response['ETag'],
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'object_upload_with_metadata',
                    False,
                    f"Metadata upload response missing ETag",
                    {'object_key': metadata_key, 'response': response},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'object_upload_with_metadata',
                False,
                f"Failed to upload object with metadata: {e}",
                {'object_key': metadata_key, 'error_code': e.error_code}
            )
    
    def _check_object_download(self):
        """Test object download operations."""
        self.logger.info("Checking object download...")
        
        # First upload a test object
        test_key = self.generate_unique_name("download-test-object")
        test_data = self._generate_test_data(2048)  # 2KB test file
        
        try:
            # Upload test object
            self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data
            )
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
            
            # Download and verify
            start_time = time.time()
            response = self.s3_client.get_object(Bucket=self.test_bucket, Key=test_key)
            duration = time.time() - start_time
            
            # Read the downloaded data
            downloaded_data = response['Body'].read()
            
            if downloaded_data == test_data:
                self.add_result(
                    'object_download',
                    True,
                    f"Successfully downloaded and verified object",
                    {
                        'object_key': test_key,
                        'size': len(downloaded_data),
                        'content_type': response.get('ContentType'),
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'object_download',
                    False,
                    f"Downloaded data doesn't match uploaded data",
                    {
                        'object_key': test_key,
                        'uploaded_size': len(test_data),
                        'downloaded_size': len(downloaded_data),
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'object_download',
                False,
                f"Failed to download object: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
        
        # Test downloading non-existent object
        nonexistent_key = self.generate_unique_name("nonexistent-object")
        try:
            start_time = time.time()
            self.s3_client.get_object(Bucket=self.test_bucket, Key=nonexistent_key)
            duration = time.time() - start_time
            
            # If this succeeds, it's unexpected
            self.add_result(
                'object_download_nonexistent',
                False,
                f"Download succeeded for non-existent object",
                {'object_key': nonexistent_key, 'bucket': self.test_bucket},
                duration
            )
        
        except S3ClientError as e:
            if e.status_code == 404:
                self.add_result(
                    'object_download_nonexistent',
                    True,
                    f"Correctly returned 404 for non-existent object",
                    {'object_key': nonexistent_key, 'error_code': e.error_code}
                )
            else:
                self.add_result(
                    'object_download_nonexistent',
                    False,
                    f"Unexpected error code for non-existent object: {e.status_code}",
                    {'object_key': nonexistent_key, 'error_code': e.error_code}
                )
    
    def _check_object_head_operation(self):
        """Test object head (metadata only) operations."""
        self.logger.info("Checking object head operations...")
        
        # Upload a test object with metadata
        test_key = self.generate_unique_name("head-test-object")
        test_data = self._generate_test_data(1024)
        metadata = {'test-field': 'head-operation-test'}
        
        try:
            # Upload with metadata
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data,
                Metadata=metadata,
                ContentType='application/json'
            )
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
            
            # Test head operation
            start_time = time.time()
            response = self.s3_client.head_object(Bucket=self.test_bucket, Key=test_key)
            duration = time.time() - start_time
            
            # Validate head response
            checks = []
            if 'ContentLength' in response and response['ContentLength'] == len(test_data):
                checks.append('content_length_correct')
            
            if 'ETag' in response and response['ETag'] == put_response.get('ETag'):
                checks.append('etag_matches')
            
            if 'ContentType' in response:
                checks.append('content_type_present')
            
            if response.get('Metadata', {}).get('test-field') == 'head-operation-test':
                checks.append('metadata_preserved')
            
            if len(checks) >= 3:  # At least 3 out of 4 checks should pass
                self.add_result(
                    'object_head_operation',
                    True,
                    f"Head operation returned correct metadata ({len(checks)}/4 checks passed)",
                    {
                        'object_key': test_key,
                        'passed_checks': checks,
                        'content_length': response.get('ContentLength'),
                        'etag': response.get('ETag'),
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'object_head_operation',
                    False,
                    f"Head operation failed validation ({len(checks)}/4 checks passed)",
                    {
                        'object_key': test_key,
                        'passed_checks': checks,
                        'response': response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'object_head_operation',
                False,
                f"Failed head operation: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
    
    def _check_object_copy(self):
        """Test object copy operations."""
        self.logger.info("Checking object copy operations...")
        
        # Upload source object
        source_key = self.generate_unique_name("copy-source-object")
        dest_key = self.generate_unique_name("copy-dest-object")
        test_data = self._generate_test_data(1024)
        
        try:
            # Upload source object
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=source_key,
                Body=test_data,
                ContentType='text/plain'
            )
            self.add_cleanup_item('object', source_key, bucket=self.test_bucket)
            source_etag = put_response.get('ETag')
            
            # Copy object
            copy_source = {'Bucket': self.test_bucket, 'Key': source_key}
            start_time = time.time()
            copy_response = self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.test_bucket,
                Key=dest_key
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', dest_key, bucket=self.test_bucket)
            
            # Verify copy was successful
            if 'CopyObjectResult' in copy_response and 'ETag' in copy_response['CopyObjectResult']:
                # Verify copied object exists and has same content
                get_response = self.s3_client.get_object(Bucket=self.test_bucket, Key=dest_key)
                copied_data = get_response['Body'].read()
                
                if copied_data == test_data:
                    self.add_result(
                        'object_copy',
                        True,
                        f"Successfully copied object and verified content",
                        {
                            'source_key': source_key,
                            'dest_key': dest_key,
                            'source_etag': source_etag,
                            'copy_etag': copy_response['CopyObjectResult']['ETag'],
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'object_copy',
                        False,
                        f"Copied object content doesn't match source",
                        {
                            'source_key': source_key,
                            'dest_key': dest_key,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'object_copy',
                    False,
                    f"Copy response missing expected fields",
                    {
                        'source_key': source_key,
                        'dest_key': dest_key,
                        'response': copy_response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'object_copy',
                False,
                f"Failed to copy object: {e}",
                {
                    'source_key': source_key,
                    'dest_key': dest_key,
                    'error_code': e.error_code
                }
            )
    
    def _check_object_listing(self):
        """Test object listing operations."""
        self.logger.info("Checking object listing...")
        
        # Upload multiple test objects
        object_keys = []
        test_prefix = self.generate_unique_name("list-test")
        
        try:
            # Upload 3 test objects
            for i in range(3):
                key = f"{test_prefix}-object-{i}"
                data = self._generate_test_data(512, f"Test object {i}")
                
                self.s3_client.put_object(
                    Bucket=self.test_bucket,
                    Key=key,
                    Body=data
                )
                object_keys.append(key)
                self.add_cleanup_item('object', key, bucket=self.test_bucket)
            
            # Test list_objects_v2
            start_time = time.time()
            response = self.s3_client.list_objects_v2(
                Bucket=self.test_bucket,
                Prefix=test_prefix
            )
            duration = time.time() - start_time
            
            if 'Contents' in response:
                listed_keys = [obj['Key'] for obj in response['Contents']]
                found_keys = [key for key in object_keys if key in listed_keys]
                
                if len(found_keys) == len(object_keys):
                    self.add_result(
                        'object_listing_v2',
                        True,
                        f"Successfully listed all {len(object_keys)} objects",
                        {
                            'prefix': test_prefix,
                            'expected_count': len(object_keys),
                            'found_count': len(found_keys),
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'object_listing_v2',
                        False,
                        f"Listed {len(found_keys)} objects, expected {len(object_keys)}",
                        {
                            'prefix': test_prefix,
                            'expected_keys': object_keys,
                            'listed_keys': listed_keys,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'object_listing_v2',
                    False,
                    f"List response missing 'Contents' field",
                    {'response': response, 'bucket': self.test_bucket},
                    duration
                )
            
            # Test list_objects (v1)
            start_time = time.time()
            response_v1 = self.s3_client.list_objects(
                Bucket=self.test_bucket,
                Prefix=test_prefix
            )
            duration = time.time() - start_time
            
            if 'Contents' in response_v1:
                listed_keys_v1 = [obj['Key'] for obj in response_v1['Contents']]
                found_keys_v1 = [key for key in object_keys if key in listed_keys_v1]
                
                if len(found_keys_v1) == len(object_keys):
                    self.add_result(
                        'object_listing_v1',
                        True,
                        f"Successfully listed all objects with v1 API",
                        {
                            'prefix': test_prefix,
                            'found_count': len(found_keys_v1),
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'object_listing_v1',
                        False,
                        f"v1 API listed {len(found_keys_v1)} objects, expected {len(object_keys)}",
                        {
                            'prefix': test_prefix,
                            'expected_keys': object_keys,
                            'listed_keys': listed_keys_v1,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'object_listing_v1',
                    False,
                    f"v1 List response missing 'Contents' field",
                    {'response': response_v1, 'bucket': self.test_bucket},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'object_listing',
                False,
                f"Failed object listing operations: {e}",
                {'prefix': test_prefix, 'error_code': e.error_code}
            )
    
    def _check_object_metadata(self):
        """Test object metadata operations (tagging and attributes)."""
        self.logger.info("Checking object metadata operations...")
        
        # Upload test object
        test_key = self.generate_unique_name("metadata-test-object")
        test_data = self._generate_test_data(2048)
        
        try:
            # Upload object
            self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data
            )
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
            
            # Test object tagging
            tag_set = {
                'TagSet': [
                    {'Key': 'Environment', 'Value': 'Test'},
                    {'Key': 'ObjectType', 'Value': 'MetadataTest'}
                ]
            }
            
            start_time = time.time()
            self.s3_client.put_object_tagging(
                Bucket=self.test_bucket,
                Key=test_key,
                Tagging=tag_set
            )
            duration = time.time() - start_time
            
            # Get and verify tags
            tag_response = self.s3_client.get_object_tagging(
                Bucket=self.test_bucket,
                Key=test_key
            )
            
            returned_tags = tag_response.get('TagSet', [])
            if len(returned_tags) == 2:
                tag_dict = {tag['Key']: tag['Value'] for tag in returned_tags}
                if (tag_dict.get('Environment') == 'Test' and 
                    tag_dict.get('ObjectType') == 'MetadataTest'):
                    self.add_result(
                        'object_tagging',
                        True,
                        f"Successfully set and retrieved object tags",
                        {
                            'object_key': test_key,
                            'tags': tag_dict,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'object_tagging',
                        False,
                        f"Object tag values don't match expected",
                        {
                            'object_key': test_key,
                            'expected': tag_set,
                            'actual': tag_dict,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'object_tagging',
                    False,
                    f"Expected 2 tags, got {len(returned_tags)}",
                    {
                        'object_key': test_key,
                        'returned_tags': returned_tags,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'object_tagging',
                False,
                f"Failed object tagging operations: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
    
    def _check_object_deletion(self):
        """Test object deletion operations."""
        self.logger.info("Checking object deletion...")
        
        # Upload test object
        test_key = self.generate_unique_name("delete-test-object")
        test_data = self._generate_test_data(1024)
        
        try:
            # Upload object
            self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data
            )
            
            # Delete object
            start_time = time.time()
            response = self.s3_client.delete_object(
                Bucket=self.test_bucket,
                Key=test_key
            )
            duration = time.time() - start_time
            
            # Verify deletion
            try:
                self.s3_client.head_object(Bucket=self.test_bucket, Key=test_key)
                # If head_object succeeds, deletion failed
                self.add_result(
                    'object_deletion',
                    False,
                    f"Object still exists after deletion",
                    {'object_key': test_key, 'bucket': self.test_bucket},
                    duration
                )
            except S3ClientError as head_error:
                if head_error.status_code == 404:
                    self.add_result(
                        'object_deletion',
                        True,
                        f"Successfully deleted object",
                        {
                            'object_key': test_key,
                            'bucket': self.test_bucket,
                            'delete_response': response
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'object_deletion',
                        False,
                        f"Unexpected error verifying deletion: {head_error}",
                        {
                            'object_key': test_key,
                            'error_code': head_error.error_code,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
        
        except S3ClientError as e:
            self.add_result(
                'object_deletion',
                False,
                f"Failed to delete object: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
        
        # Test deleting non-existent object
        nonexistent_key = self.generate_unique_name("nonexistent-delete-object")
        try:
            start_time = time.time()
            response = self.s3_client.delete_object(
                Bucket=self.test_bucket,
                Key=nonexistent_key
            )
            duration = time.time() - start_time
            
            # S3 delete is idempotent, so this should succeed
            self.add_result(
                'object_deletion_nonexistent',
                True,
                f"Delete operation on non-existent object succeeded (idempotent behavior)",
                {
                    'object_key': nonexistent_key,
                    'bucket': self.test_bucket,
                    'response': response
                },
                duration
            )
        
        except S3ClientError as e:
            # Some S3 implementations might return an error for non-existent objects
            if e.status_code == 404:
                self.add_result(
                    'object_deletion_nonexistent',
                    True,
                    f"Delete operation on non-existent object returned 404 (acceptable behavior)",
                    {
                        'object_key': nonexistent_key,
                        'error_code': e.error_code,
                        'bucket': self.test_bucket
                    }
                )
            else:
                self.add_result(
                    'object_deletion_nonexistent',
                    False,
                    f"Unexpected error deleting non-existent object: {e}",
                    {
                        'object_key': nonexistent_key,
                        'error_code': e.error_code,
                        'bucket': self.test_bucket
                    }
                )