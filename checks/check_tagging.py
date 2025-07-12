"""
Tagging operations compatibility checks.

This module contains checks for S3 tagging operations on both buckets and objects.
"""

import time
from typing import List
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class TaggingChecks(BaseCheck):
    """
    Tagging operations compatibility checks.
    
    Tests bucket and object tagging functionality including setting,
    getting, updating, and deleting tags.
    """
    
    def run_checks(self) -> List[CheckResult]:
        """
        Run all tagging related compatibility checks.
        
        Returns:
            List of CheckResult objects for each tagging check
        """
        self.logger.info("Starting tagging compatibility checks...")
        
        # Create a test bucket for tagging operations
        self.test_bucket = self.generate_unique_name("tagging-test-bucket")
        try:
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            self.add_cleanup_item('bucket', self.test_bucket)
            self.logger.info(f"Created test bucket: {self.test_bucket}")
        except S3ClientError as e:
            self.add_result(
                'tagging_test_bucket_creation',
                False,
                f"Failed to create test bucket for tagging operations: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Run individual check methods
        self._check_bucket_tagging()
        self._check_object_tagging()
        
        self.logger.info(f"Tagging checks completed: {len(self.results)} checks performed")
        return self.results
    
    def _check_bucket_tagging(self):
        """Test bucket tagging operations."""
        self.logger.info("Checking bucket tagging...")
        
        # Set bucket tags
        tag_set = {
            'TagSet': [
                {'Key': 'Environment', 'Value': 'Test'},
                {'Key': 'Purpose', 'Value': 'S3CompatibilityCheck'},
                {'Key': 'Project', 'Value': 'AutomatedTesting'}
            ]
        }
        
        try:
            start_time = time.time()
            self.s3_client.put_bucket_tagging(Bucket=self.test_bucket, Tagging=tag_set)
            duration = time.time() - start_time
            
            # Get and verify tags
            response = self.s3_client.get_bucket_tagging(Bucket=self.test_bucket)
            returned_tags = response.get('TagSet', [])
            
            if len(returned_tags) == 3:
                tag_dict = {tag['Key']: tag['Value'] for tag in returned_tags}
                expected_tags = {tag['Key']: tag['Value'] for tag in tag_set['TagSet']}
                
                if tag_dict == expected_tags:
                    self.add_result(
                        'bucket_tagging_put_get',
                        True,
                        f"Successfully set and retrieved bucket tags",
                        {'bucket': self.test_bucket, 'tags': tag_dict},
                        duration
                    )
                else:
                    self.add_result(
                        'bucket_tagging_put_get',
                        False,
                        f"Tag values don't match: expected {expected_tags}, got {tag_dict}",
                        {'bucket': self.test_bucket, 'expected': expected_tags, 'actual': tag_dict},
                        duration
                    )
            else:
                self.add_result(
                    'bucket_tagging_put_get',
                    False,
                    f"Expected 3 tags, got {len(returned_tags)}",
                    {'bucket': self.test_bucket, 'returned_tags': returned_tags},
                    duration
                )
            
            # Delete bucket tags
            start_time = time.time()
            self.s3_client.delete_bucket_tagging(Bucket=self.test_bucket)
            duration = time.time() - start_time
            
            # Verify deletion
            try:
                response = self.s3_client.get_bucket_tagging(Bucket=self.test_bucket)
                remaining_tags = response.get('TagSet', [])
                if not remaining_tags:
                    self.add_result(
                        'bucket_tagging_delete',
                        True,
                        f"Successfully deleted bucket tags",
                        {'bucket': self.test_bucket},
                        duration
                    )
                else:
                    self.add_result(
                        'bucket_tagging_delete',
                        False,
                        f"Tags still exist after deletion: {remaining_tags}",
                        {'bucket': self.test_bucket, 'remaining_tags': remaining_tags},
                        duration
                    )
            except S3ClientError as e:
                if e.status_code == 404:
                    self.add_result(
                        'bucket_tagging_delete',
                        True,
                        f"Successfully deleted bucket tags (404 response)",
                        {'bucket': self.test_bucket},
                        duration
                    )
                else:
                    self.add_result(
                        'bucket_tagging_delete',
                        False,
                        f"Unexpected error after tag deletion: {e}",
                        {'bucket': self.test_bucket, 'error_code': e.error_code}
                    )
        
        except S3ClientError as e:
            self.add_result(
                'bucket_tagging',
                False,
                f"Failed bucket tagging operations: {e}",
                {'bucket': self.test_bucket, 'error_code': e.error_code}
            )
    
    def _check_object_tagging(self):
        """Test object tagging operations."""
        self.logger.info("Checking object tagging...")
        
        # Upload a test object
        test_key = self.generate_unique_name("tagging-test-object")
        test_data = b"Test data for tagging operations"
        
        try:
            self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data
            )
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
            
            # Set object tags
            tag_set = {
                'TagSet': [
                    {'Key': 'ObjectType', 'Value': 'TestData'},
                    {'Key': 'Category', 'Value': 'TaggingTest'},
                    {'Key': 'Temporary', 'Value': 'True'}
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
            response = self.s3_client.get_object_tagging(
                Bucket=self.test_bucket,
                Key=test_key
            )
            
            returned_tags = response.get('TagSet', [])
            if len(returned_tags) == 3:
                tag_dict = {tag['Key']: tag['Value'] for tag in returned_tags}
                expected_tags = {tag['Key']: tag['Value'] for tag in tag_set['TagSet']}
                
                if tag_dict == expected_tags:
                    self.add_result(
                        'object_tagging_put_get',
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
                        'object_tagging_put_get',
                        False,
                        f"Object tag values don't match: expected {expected_tags}, got {tag_dict}",
                        {
                            'object_key': test_key,
                            'expected': expected_tags,
                            'actual': tag_dict,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'object_tagging_put_get',
                    False,
                    f"Expected 3 object tags, got {len(returned_tags)}",
                    {
                        'object_key': test_key,
                        'returned_tags': returned_tags,
                        'bucket': self.test_bucket
                    },
                    duration
                )
            
            # Update tags (replace with different tags)
            new_tag_set = {
                'TagSet': [
                    {'Key': 'Status', 'Value': 'Updated'},
                    {'Key': 'Version', 'Value': '2.0'}
                ]
            }
            
            start_time = time.time()
            self.s3_client.put_object_tagging(
                Bucket=self.test_bucket,
                Key=test_key,
                Tagging=new_tag_set
            )
            duration = time.time() - start_time
            
            # Verify update
            response = self.s3_client.get_object_tagging(
                Bucket=self.test_bucket,
                Key=test_key
            )
            
            updated_tags = response.get('TagSet', [])
            if len(updated_tags) == 2:
                updated_tag_dict = {tag['Key']: tag['Value'] for tag in updated_tags}
                expected_updated_tags = {tag['Key']: tag['Value'] for tag in new_tag_set['TagSet']}
                
                if updated_tag_dict == expected_updated_tags:
                    self.add_result(
                        'object_tagging_update',
                        True,
                        f"Successfully updated object tags",
                        {
                            'object_key': test_key,
                            'updated_tags': updated_tag_dict,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'object_tagging_update',
                        False,
                        f"Updated object tags don't match expected",
                        {
                            'object_key': test_key,
                            'expected': expected_updated_tags,
                            'actual': updated_tag_dict,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'object_tagging_update',
                    False,
                    f"Expected 2 updated tags, got {len(updated_tags)}",
                    {
                        'object_key': test_key,
                        'updated_tags': updated_tags,
                        'bucket': self.test_bucket
                    },
                    duration
                )
            
            # Delete object tags
            start_time = time.time()
            self.s3_client.delete_object_tagging(
                Bucket=self.test_bucket,
                Key=test_key
            )
            duration = time.time() - start_time
            
            # Verify deletion
            try:
                response = self.s3_client.get_object_tagging(
                    Bucket=self.test_bucket,
                    Key=test_key
                )
                remaining_tags = response.get('TagSet', [])
                if not remaining_tags:
                    self.add_result(
                        'object_tagging_delete',
                        True,
                        f"Successfully deleted object tags",
                        {'object_key': test_key, 'bucket': self.test_bucket},
                        duration
                    )
                else:
                    self.add_result(
                        'object_tagging_delete',
                        False,
                        f"Object tags still exist after deletion: {remaining_tags}",
                        {
                            'object_key': test_key,
                            'remaining_tags': remaining_tags,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            except S3ClientError as e:
                if e.status_code == 404:
                    self.add_result(
                        'object_tagging_delete',
                        True,
                        f"Successfully deleted object tags (404 response)",
                        {'object_key': test_key, 'bucket': self.test_bucket},
                        duration
                    )
                else:
                    self.add_result(
                        'object_tagging_delete',
                        False,
                        f"Unexpected error after object tag deletion: {e}",
                        {
                            'object_key': test_key,
                            'error_code': e.error_code,
                            'bucket': self.test_bucket
                        }
                    )
        
        except S3ClientError as e:
            self.add_result(
                'object_tagging',
                False,
                f"Failed object tagging operations: {e}",
                {
                    'object_key': test_key,
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )