"""
Sync operations compatibility checks.

This module contains checks for S3 sync-like operations including
batch uploads, downloads, and directory synchronization patterns.
"""

import time
import tempfile
import os
from typing import List
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class SyncChecks(BaseCheck):
    """
    Sync operations compatibility checks.
    
    Tests sync-like operations including batch uploads, downloads,
    and operations that simulate directory synchronization.
    """
    
    def run_checks(self) -> List[CheckResult]:
        """
        Run all sync related compatibility checks.
        
        Returns:
            List of CheckResult objects for each sync check
        """
        self.logger.info("Starting sync compatibility checks...")
        
        # Create a test bucket for sync operations
        self.test_bucket = self.generate_unique_name("sync-test-bucket")
        try:
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            self.add_cleanup_item('bucket', self.test_bucket)
            self.logger.info(f"Created test bucket: {self.test_bucket}")
        except S3ClientError as e:
            self.add_result(
                'sync_test_bucket_creation',
                False,
                f"Failed to create test bucket for sync operations: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Run individual check methods
        self._check_batch_upload()
        self._check_directory_structure_upload()
        self._check_batch_download()
        self._check_object_listing_patterns()
        
        self.logger.info(f"Sync checks completed: {len(self.results)} checks performed")
        return self.results
    
    def _check_batch_upload(self):
        """Test batch upload operations (multiple files)."""
        self.logger.info("Checking batch upload operations...")
        
        # Create multiple test objects to upload
        test_objects = []
        for i in range(5):
            key = self.generate_unique_name(f"batch-upload-{i}")
            data = f"Batch upload test data for object {i}\n".encode() * 10
            test_objects.append({'key': key, 'data': data, 'size': len(data)})
        
        successful_uploads = 0
        total_duration = 0
        
        for obj in test_objects:
            try:
                start_time = time.time()
                response = self.s3_client.put_object(
                    Bucket=self.test_bucket,
                    Key=obj['key'],
                    Body=obj['data']
                )
                duration = time.time() - start_time
                total_duration += duration
                
                if 'ETag' in response:
                    successful_uploads += 1
                    self.add_cleanup_item('object', obj['key'], bucket=self.test_bucket)
            
            except S3ClientError as e:
                self.logger.debug(f"Failed to upload {obj['key']}: {e}")
        
        # Evaluate batch upload results
        if successful_uploads == len(test_objects):
            self.add_result(
                'sync_batch_upload',
                True,
                f"Successfully uploaded {successful_uploads} objects in batch",
                {
                    'objects_count': len(test_objects),
                    'successful_uploads': successful_uploads,
                    'total_duration': total_duration,
                    'average_duration': total_duration / len(test_objects),
                    'bucket': self.test_bucket
                },
                total_duration
            )
        elif successful_uploads > 0:
            self.add_result(
                'sync_batch_upload',
                False,
                f"Partial batch upload success: {successful_uploads}/{len(test_objects)} objects uploaded",
                {
                    'objects_count': len(test_objects),
                    'successful_uploads': successful_uploads,
                    'failed_uploads': len(test_objects) - successful_uploads,
                    'bucket': self.test_bucket
                },
                total_duration
            )
        else:
            self.add_result(
                'sync_batch_upload',
                False,
                f"Batch upload completely failed: 0/{len(test_objects)} objects uploaded",
                {
                    'objects_count': len(test_objects),
                    'bucket': self.test_bucket
                },
                total_duration
            )
    
    def _check_directory_structure_upload(self):
        """Test uploading objects that simulate a directory structure."""
        self.logger.info("Checking directory structure upload...")
        
        # Create objects that simulate a directory tree
        directory_structure = [
            'docs/readme.txt',
            'docs/api/overview.txt',
            'docs/api/reference.txt',
            'src/main.py',
            'src/utils/helper.py',
            'src/utils/config.py',
            'tests/test_main.py',
            'tests/integration/test_api.py'
        ]
        
        successful_uploads = 0
        total_duration = 0
        
        for file_path in directory_structure:
            key = self.generate_unique_name(f"dir-sync/{file_path}")
            content = f"Content of {file_path}\nGenerated for sync testing\n"
            data = content.encode()
            
            try:
                start_time = time.time()
                response = self.s3_client.put_object(
                    Bucket=self.test_bucket,
                    Key=key,
                    Body=data,
                    ContentType='text/plain'
                )
                duration = time.time() - start_time
                total_duration += duration
                
                if 'ETag' in response:
                    successful_uploads += 1
                    self.add_cleanup_item('object', key, bucket=self.test_bucket)
            
            except S3ClientError as e:
                self.logger.debug(f"Failed to upload {key}: {e}")
        
        if successful_uploads == len(directory_structure):
            self.add_result(
                'sync_directory_structure',
                True,
                f"Successfully uploaded directory structure ({successful_uploads} files)",
                {
                    'files_count': len(directory_structure),
                    'successful_uploads': successful_uploads,
                    'total_duration': total_duration,
                    'bucket': self.test_bucket
                },
                total_duration
            )
            
            # Store structure info for listing test
            self.directory_prefix = self.generate_unique_name("dir-sync")
            
        else:
            self.add_result(
                'sync_directory_structure',
                False,
                f"Directory structure upload failed: {successful_uploads}/{len(directory_structure)} files",
                {
                    'files_count': len(directory_structure),
                    'successful_uploads': successful_uploads,
                    'bucket': self.test_bucket
                },
                total_duration
            )
    
    def _check_batch_download(self):
        """Test batch download operations."""
        self.logger.info("Checking batch download operations...")
        
        # First, upload some test objects to download
        download_objects = []
        for i in range(3):
            key = self.generate_unique_name(f"download-test-{i}")
            content = f"Download test content for object {i}\n" * 50
            data = content.encode()
            
            try:
                self.s3_client.put_object(
                    Bucket=self.test_bucket,
                    Key=key,
                    Body=data
                )
                download_objects.append({
                    'key': key,
                    'expected_data': data,
                    'size': len(data)
                })
                self.add_cleanup_item('object', key, bucket=self.test_bucket)
            except S3ClientError:
                continue
        
        if not download_objects:
            self.add_result(
                'sync_batch_download',
                False,
                "No objects available for batch download test",
                {'bucket': self.test_bucket}
            )
            return
        
        # Download all objects
        successful_downloads = 0
        total_duration = 0
        data_matches = 0
        
        for obj in download_objects:
            try:
                start_time = time.time()
                response = self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=obj['key']
                )
                downloaded_data = response['Body'].read()
                duration = time.time() - start_time
                total_duration += duration
                
                successful_downloads += 1
                
                if downloaded_data == obj['expected_data']:
                    data_matches += 1
            
            except S3ClientError as e:
                self.logger.debug(f"Failed to download {obj['key']}: {e}")
        
        if successful_downloads == len(download_objects) and data_matches == len(download_objects):
            self.add_result(
                'sync_batch_download',
                True,
                f"Successfully downloaded and verified {successful_downloads} objects",
                {
                    'objects_count': len(download_objects),
                    'successful_downloads': successful_downloads,
                    'data_matches': data_matches,
                    'total_duration': total_duration,
                    'average_duration': total_duration / len(download_objects),
                    'bucket': self.test_bucket
                },
                total_duration
            )
        else:
            self.add_result(
                'sync_batch_download',
                False,
                f"Batch download issues: {successful_downloads}/{len(download_objects)} downloaded, "
                f"{data_matches}/{len(download_objects)} data matches",
                {
                    'objects_count': len(download_objects),
                    'successful_downloads': successful_downloads,
                    'data_matches': data_matches,
                    'bucket': self.test_bucket
                },
                total_duration
            )
    
    def _check_object_listing_patterns(self):
        """Test object listing patterns used in sync operations."""
        self.logger.info("Checking object listing patterns...")
        
        if not hasattr(self, 'directory_prefix'):
            self.add_result(
                'sync_listing_patterns',
                False,
                "No directory structure available for listing patterns test",
                {}
            )
            return
        
        prefix = self.directory_prefix
        
        try:
            # Test listing with prefix (directory-like listing)
            start_time = time.time()
            response = self.s3_client.list_objects_v2(
                Bucket=self.test_bucket,
                Prefix=prefix
            )
            duration = time.time() - start_time
            
            if 'Contents' in response:
                objects = response['Contents']
                prefix_objects = [obj for obj in objects if obj['Key'].startswith(prefix)]
                
                if len(prefix_objects) > 0:
                    self.add_result(
                        'sync_listing_prefix',
                        True,
                        f"Successfully listed {len(prefix_objects)} objects with prefix",
                        {
                            'prefix': prefix,
                            'objects_found': len(prefix_objects),
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'sync_listing_prefix',
                        False,
                        f"No objects found with prefix {prefix}",
                        {
                            'prefix': prefix,
                            'total_objects': len(objects),
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'sync_listing_prefix',
                    False,
                    f"List objects response missing Contents field",
                    {
                        'prefix': prefix,
                        'response': response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
            
            # Test pagination for large object sets
            start_time = time.time()
            response = self.s3_client.list_objects_v2(
                Bucket=self.test_bucket,
                MaxKeys=2  # Force pagination
            )
            duration = time.time() - start_time
            
            if 'Contents' in response:
                objects = response['Contents']
                is_truncated = response.get('IsTruncated', False)
                
                self.add_result(
                    'sync_listing_pagination',
                    True,
                    f"Successfully tested pagination: {len(objects)} objects, truncated={is_truncated}",
                    {
                        'objects_returned': len(objects),
                        'is_truncated': is_truncated,
                        'max_keys': 2,
                        'bucket': self.test_bucket
                    },
                    duration
                )
            else:
                self.add_result(
                    'sync_listing_pagination',
                    False,
                    f"Pagination test failed - no contents returned",
                    {
                        'response': response,
                        'bucket': self.test_bucket
                    },
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'sync_listing_patterns',
                False,
                f"Failed object listing patterns test: {e}",
                {
                    'prefix': prefix,
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )