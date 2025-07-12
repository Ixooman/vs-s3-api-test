"""
Bucket operations compatibility checks.

This module contains checks for S3 bucket operations including creation,
listing, deletion, and bucket-level configuration like versioning and tagging.
"""

import time
from typing import List
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class BucketChecks(BaseCheck):
    """
    Bucket operations compatibility checks.
    
    Tests bucket creation, deletion, listing, and configuration operations
    to verify S3 API compatibility for bucket management.
    """
    
    def run_checks(self) -> List[CheckResult]:
        """
        Run all bucket-related compatibility checks.
        
        Returns:
            List of CheckResult objects for each bucket operation check
        """
        self.logger.info("Starting bucket compatibility checks...")
        
        # Run individual check methods
        self._check_bucket_creation()
        self._check_bucket_listing()
        self._check_bucket_head_operation()
        self._check_bucket_versioning()
        self._check_bucket_tagging()
        self._check_bucket_deletion()
        
        self.logger.info(f"Bucket checks completed: {len(self.results)} checks performed")
        return self.results
    
    def _check_bucket_creation(self):
        """Test bucket creation operations."""
        self.logger.info("Checking bucket creation...")
        
        bucket_name = self.generate_unique_name("test-bucket")
        
        try:
            # Test bucket creation
            start_time = time.time()
            response = self.s3_client.create_bucket(Bucket=bucket_name)
            duration = time.time() - start_time
            
            # Add bucket to cleanup list
            self.add_cleanup_item('bucket', bucket_name)
            
            # Validate response
            if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
                self.add_result(
                    'bucket_creation',
                    True,
                    f"Successfully created bucket '{bucket_name}'",
                    {'bucket_name': bucket_name, 'response': response},
                    duration
                )
            else:
                self.add_result(
                    'bucket_creation',
                    False,
                    f"Unexpected response code: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}",
                    {'bucket_name': bucket_name, 'response': response},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'bucket_creation',
                False,
                f"Failed to create bucket: {e}",
                {'bucket_name': bucket_name, 'error': str(e), 'error_code': e.error_code}
            )
        
        # Test bucket creation with invalid name
        try:
            invalid_bucket_name = "Invalid_Bucket_Name_With_Underscores_And_Capitals"
            start_time = time.time()
            self.s3_client.create_bucket(Bucket=invalid_bucket_name)
            duration = time.time() - start_time
            
            # If this succeeds, it might indicate non-standard S3 behavior
            self.add_result(
                'bucket_creation_invalid_name',
                False,
                f"Created bucket with invalid name '{invalid_bucket_name}' - this violates S3 naming rules",
                {'bucket_name': invalid_bucket_name},
                duration
            )
            # Add to cleanup if it was actually created
            self.add_cleanup_item('bucket', invalid_bucket_name)
            
        except S3ClientError as e:
            # This is expected behavior for invalid bucket names
            if e.error_code in ['InvalidBucketName', 'BucketAlreadyExists']:
                self.add_result(
                    'bucket_creation_invalid_name',
                    True,
                    f"Correctly rejected invalid bucket name: {e.error_code}",
                    {'error_code': e.error_code}
                )
            else:
                self.add_result(
                    'bucket_creation_invalid_name',
                    False,
                    f"Unexpected error for invalid bucket name: {e}",
                    {'error_code': e.error_code}
                )
    
    def _check_bucket_listing(self):
        """Test bucket listing operations."""
        self.logger.info("Checking bucket listing...")
        
        try:
            start_time = time.time()
            response = self.s3_client.list_buckets()
            duration = time.time() - start_time
            
            # Validate response structure
            if 'Buckets' in response:
                bucket_count = len(response['Buckets'])
                self.add_result(
                    'bucket_listing',
                    True,
                    f"Successfully listed {bucket_count} buckets",
                    {'bucket_count': bucket_count, 'buckets': [b['Name'] for b in response['Buckets']]},
                    duration
                )
                
                # Validate bucket list structure
                for bucket in response['Buckets']:
                    if 'Name' not in bucket or 'CreationDate' not in bucket:
                        self.add_result(
                            'bucket_listing_structure',
                            False,
                            "Bucket list contains invalid bucket structure",
                            {'invalid_bucket': bucket}
                        )
                        return
                
                self.add_result(
                    'bucket_listing_structure',
                    True,
                    "Bucket listing has correct structure",
                    {'sample_bucket': response['Buckets'][0] if response['Buckets'] else None}
                )
            else:
                self.add_result(
                    'bucket_listing',
                    False,
                    "Response missing 'Buckets' field",
                    {'response': response},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'bucket_listing',
                False,
                f"Failed to list buckets: {e}",
                {'error_code': e.error_code}
            )
    
    def _check_bucket_head_operation(self):
        """Test bucket head (existence check) operations."""
        self.logger.info("Checking bucket head operations...")
        
        # Create a bucket to test head operation
        bucket_name = self.generate_unique_name("head-test-bucket")
        
        try:
            # Create bucket first
            self.s3_client.create_bucket(Bucket=bucket_name)
            self.add_cleanup_item('bucket', bucket_name)
            
            # Test head operation on existing bucket
            start_time = time.time()
            response = self.s3_client.head_bucket(Bucket=bucket_name)
            duration = time.time() - start_time
            
            if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
                self.add_result(
                    'bucket_head_existing',
                    True,
                    f"Successfully performed head operation on existing bucket '{bucket_name}'",
                    {'bucket_name': bucket_name},
                    duration
                )
            else:
                self.add_result(
                    'bucket_head_existing',
                    False,
                    f"Unexpected response code for head operation: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}",
                    {'bucket_name': bucket_name, 'response': response},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'bucket_head_existing',
                False,
                f"Failed head operation on existing bucket: {e}",
                {'bucket_name': bucket_name, 'error_code': e.error_code}
            )
        
        # Test head operation on non-existing bucket
        nonexistent_bucket = self.generate_unique_name("nonexistent-bucket")
        try:
            start_time = time.time()
            self.s3_client.head_bucket(Bucket=nonexistent_bucket)
            duration = time.time() - start_time
            
            # If this succeeds, it's unexpected
            self.add_result(
                'bucket_head_nonexistent',
                False,
                f"Head operation succeeded on non-existent bucket '{nonexistent_bucket}'",
                {'bucket_name': nonexistent_bucket},
                duration
            )
        
        except S3ClientError as e:
            if e.status_code == 404:
                self.add_result(
                    'bucket_head_nonexistent',
                    True,
                    f"Correctly returned 404 for non-existent bucket",
                    {'bucket_name': nonexistent_bucket, 'error_code': e.error_code}
                )
            else:
                self.add_result(
                    'bucket_head_nonexistent',
                    False,
                    f"Unexpected error code for non-existent bucket: {e.status_code}",
                    {'bucket_name': nonexistent_bucket, 'error_code': e.error_code}
                )
    
    def _check_bucket_versioning(self):
        """Test bucket versioning configuration."""
        self.logger.info("Checking bucket versioning...")
        
        bucket_name = self.generate_unique_name("versioning-test-bucket")
        
        try:
            # Create bucket
            self.s3_client.create_bucket(Bucket=bucket_name)
            self.add_cleanup_item('bucket', bucket_name)
            
            # Test getting versioning (should be disabled by default)
            start_time = time.time()
            response = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
            duration = time.time() - start_time
            
            # Check default versioning state
            status = response.get('Status', 'Disabled')  # Default is typically no Status field or 'Disabled'
            if status in ['Disabled', None] or 'Status' not in response:
                self.add_result(
                    'bucket_versioning_default',
                    True,
                    f"Bucket versioning correctly disabled by default",
                    {'bucket_name': bucket_name, 'status': status},
                    duration
                )
            else:
                self.add_result(
                    'bucket_versioning_default',
                    False,
                    f"Unexpected default versioning status: {status}",
                    {'bucket_name': bucket_name, 'status': status},
                    duration
                )
            
            # Test enabling versioning
            start_time = time.time()
            self.s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            duration = time.time() - start_time
            
            # Verify versioning was enabled
            response = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
            if response.get('Status') == 'Enabled':
                self.add_result(
                    'bucket_versioning_enable',
                    True,
                    f"Successfully enabled bucket versioning",
                    {'bucket_name': bucket_name},
                    duration
                )
            else:
                self.add_result(
                    'bucket_versioning_enable',
                    False,
                    f"Failed to enable versioning, status: {response.get('Status')}",
                    {'bucket_name': bucket_name, 'response': response},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'bucket_versioning',
                False,
                f"Failed versioning operations: {e}",
                {'bucket_name': bucket_name, 'error_code': e.error_code}
            )
    
    def _check_bucket_tagging(self):
        """Test bucket tagging operations."""
        self.logger.info("Checking bucket tagging...")
        
        bucket_name = self.generate_unique_name("tagging-test-bucket")
        
        try:
            # Create bucket
            self.s3_client.create_bucket(Bucket=bucket_name)
            self.add_cleanup_item('bucket', bucket_name)
            
            # Test putting bucket tags
            tag_set = {
                'TagSet': [
                    {'Key': 'Environment', 'Value': 'Test'},
                    {'Key': 'Purpose', 'Value': 'S3CompatibilityCheck'}
                ]
            }
            
            start_time = time.time()
            self.s3_client.put_bucket_tagging(Bucket=bucket_name, Tagging=tag_set)
            duration = time.time() - start_time
            
            # Get tags to verify
            response = self.s3_client.get_bucket_tagging(Bucket=bucket_name)
            returned_tags = response.get('TagSet', [])
            
            if len(returned_tags) == 2:
                # Verify tag contents
                tag_dict = {tag['Key']: tag['Value'] for tag in returned_tags}
                if (tag_dict.get('Environment') == 'Test' and 
                    tag_dict.get('Purpose') == 'S3CompatibilityCheck'):
                    self.add_result(
                        'bucket_tagging_put_get',
                        True,
                        f"Successfully set and retrieved bucket tags",
                        {'bucket_name': bucket_name, 'tags': tag_dict},
                        duration
                    )
                else:
                    self.add_result(
                        'bucket_tagging_put_get',
                        False,
                        f"Tag values don't match: {tag_dict}",
                        {'bucket_name': bucket_name, 'expected': tag_set, 'actual': tag_dict},
                        duration
                    )
            else:
                self.add_result(
                    'bucket_tagging_put_get',
                    False,
                    f"Expected 2 tags, got {len(returned_tags)}",
                    {'bucket_name': bucket_name, 'returned_tags': returned_tags},
                    duration
                )
            
            # Test deleting bucket tags
            start_time = time.time()
            self.s3_client.delete_bucket_tagging(Bucket=bucket_name)
            duration = time.time() - start_time
            
            # Verify tags were deleted
            try:
                response = self.s3_client.get_bucket_tagging(Bucket=bucket_name)
                # If we get here, tags might still exist
                remaining_tags = response.get('TagSet', [])
                if not remaining_tags:
                    self.add_result(
                        'bucket_tagging_delete',
                        True,
                        f"Successfully deleted bucket tags",
                        {'bucket_name': bucket_name},
                        duration
                    )
                else:
                    self.add_result(
                        'bucket_tagging_delete',
                        False,
                        f"Tags still exist after deletion: {remaining_tags}",
                        {'bucket_name': bucket_name, 'remaining_tags': remaining_tags},
                        duration
                    )
            except S3ClientError as e:
                if e.status_code == 404:
                    # This is expected when no tags exist
                    self.add_result(
                        'bucket_tagging_delete',
                        True,
                        f"Successfully deleted bucket tags (404 response)",
                        {'bucket_name': bucket_name},
                        duration
                    )
                else:
                    self.add_result(
                        'bucket_tagging_delete',
                        False,
                        f"Unexpected error after tag deletion: {e}",
                        {'bucket_name': bucket_name, 'error_code': e.error_code}
                    )
        
        except S3ClientError as e:
            self.add_result(
                'bucket_tagging',
                False,
                f"Failed bucket tagging operations: {e}",
                {'bucket_name': bucket_name, 'error_code': e.error_code}
            )
    
    def _check_bucket_deletion(self):
        """Test bucket deletion operations."""
        self.logger.info("Checking bucket deletion...")
        
        # Test deleting an empty bucket
        bucket_name = self.generate_unique_name("delete-test-bucket")
        
        try:
            # Create bucket
            self.s3_client.create_bucket(Bucket=bucket_name)
            
            # Delete empty bucket
            start_time = time.time()
            response = self.s3_client.delete_bucket(Bucket=bucket_name)
            duration = time.time() - start_time
            
            if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 204:
                self.add_result(
                    'bucket_deletion_empty',
                    True,
                    f"Successfully deleted empty bucket '{bucket_name}'",
                    {'bucket_name': bucket_name},
                    duration
                )
                # Remove from cleanup since it's already deleted
                self.cleanup_items = [item for item in self.cleanup_items 
                                    if not (item['type'] == 'bucket' and item['identifier'] == bucket_name)]
            else:
                self.add_result(
                    'bucket_deletion_empty',
                    False,
                    f"Unexpected response code for bucket deletion: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}",
                    {'bucket_name': bucket_name, 'response': response},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'bucket_deletion_empty',
                False,
                f"Failed to delete empty bucket: {e}",
                {'bucket_name': bucket_name, 'error_code': e.error_code}
            )
        
        # Test deleting non-existent bucket
        nonexistent_bucket = self.generate_unique_name("nonexistent-delete-bucket")
        try:
            start_time = time.time()
            self.s3_client.delete_bucket(Bucket=nonexistent_bucket)
            duration = time.time() - start_time
            
            # If this succeeds, it's unexpected
            self.add_result(
                'bucket_deletion_nonexistent',
                False,
                f"Delete succeeded on non-existent bucket '{nonexistent_bucket}'",
                {'bucket_name': nonexistent_bucket},
                duration
            )
        
        except S3ClientError as e:
            if e.status_code == 404:
                self.add_result(
                    'bucket_deletion_nonexistent',
                    True,
                    f"Correctly returned 404 for non-existent bucket deletion",
                    {'bucket_name': nonexistent_bucket, 'error_code': e.error_code}
                )
            else:
                self.add_result(
                    'bucket_deletion_nonexistent',
                    False,
                    f"Unexpected error code for non-existent bucket deletion: {e.status_code}",
                    {'bucket_name': nonexistent_bucket, 'error_code': e.error_code}
                )