"""
Object versioning compatibility checks.

This module contains checks for S3 object versioning operations including
enabling versioning, creating multiple versions, and version management.
"""

import time
from typing import List
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class VersioningChecks(BaseCheck):
    """
    Object versioning compatibility checks.
    
    Tests object versioning functionality including enabling versioning,
    creating multiple object versions, and version-specific operations.
    """
    
    def run_checks(self) -> List[CheckResult]:
        """
        Run all versioning related compatibility checks.
        
        Returns:
            List of CheckResult objects for each versioning check
        """
        self.logger.info("Starting versioning compatibility checks...")
        
        # Create a test bucket for versioning operations
        self.test_bucket = self.generate_unique_name("versioning-test-bucket")
        try:
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            self.add_cleanup_item('bucket', self.test_bucket)
            self.logger.info(f"Created test bucket: {self.test_bucket}")
        except S3ClientError as e:
            self.add_result(
                'versioning_test_bucket_creation',
                False,
                f"Failed to create test bucket for versioning operations: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Run individual check methods
        self._check_versioning_configuration()
        self._check_multiple_versions()
        self._check_version_listing()
        self._check_version_specific_operations()
        self._check_version_deletion()
        
        self.logger.info(f"Versioning checks completed: {len(self.results)} checks performed")
        return self.results
    
    def _check_versioning_configuration(self):
        """Test bucket versioning configuration."""
        self.logger.info("Checking versioning configuration...")
        
        try:
            # Check default versioning state
            start_time = time.time()
            response = self.s3_client.get_bucket_versioning(Bucket=self.test_bucket)
            duration = time.time() - start_time
            
            status = response.get('Status', 'Disabled')
            if status in ['Disabled', None] or 'Status' not in response:
                self.add_result(
                    'versioning_default_disabled',
                    True,
                    f"Bucket versioning correctly disabled by default",
                    {'bucket': self.test_bucket, 'status': status},
                    duration
                )
            else:
                self.add_result(
                    'versioning_default_disabled',
                    False,
                    f"Unexpected default versioning status: {status}",
                    {'bucket': self.test_bucket, 'status': status},
                    duration
                )
            
            # Enable versioning
            start_time = time.time()
            self.s3_client.put_bucket_versioning(
                Bucket=self.test_bucket,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            duration = time.time() - start_time
            
            # Verify versioning was enabled
            response = self.s3_client.get_bucket_versioning(Bucket=self.test_bucket)
            if response.get('Status') == 'Enabled':
                self.add_result(
                    'versioning_enable',
                    True,
                    f"Successfully enabled bucket versioning",
                    {'bucket': self.test_bucket},
                    duration
                )
            else:
                self.add_result(
                    'versioning_enable',
                    False,
                    f"Failed to enable versioning, status: {response.get('Status')}",
                    {'bucket': self.test_bucket, 'response': response},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'versioning_configuration',
                False,
                f"Failed versioning configuration operations: {e}",
                {'bucket': self.test_bucket, 'error_code': e.error_code}
            )
    
    def _check_multiple_versions(self):
        """Test creating multiple versions of the same object."""
        self.logger.info("Checking multiple versions creation...")
        
        test_key = self.generate_unique_name("versioned-object")
        versions = []
        
        try:
            # Create 3 versions of the same object
            for version_num in range(1, 4):
                content = f"Version {version_num} content - test data"
                
                start_time = time.time()
                response = self.s3_client.put_object(
                    Bucket=self.test_bucket,
                    Key=test_key,
                    Body=content.encode('utf-8')
                )
                duration = time.time() - start_time
                
                if 'VersionId' in response:
                    version_id = response['VersionId']
                    versions.append({
                        'version_number': version_num,
                        'version_id': version_id,
                        'content': content,
                        'etag': response.get('ETag')
                    })
                    
                    self.add_cleanup_item('object', test_key, 
                                        bucket=self.test_bucket, version_id=version_id)
                    
                    self.add_result(
                        f'versioning_create_version_{version_num}',
                        True,
                        f"Successfully created version {version_num}",
                        {
                            'object_key': test_key,
                            'version_id': version_id,
                            'version_number': version_num,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        f'versioning_create_version_{version_num}',
                        False,
                        f"Version {version_num} creation response missing VersionId",
                        {
                            'object_key': test_key,
                            'version_number': version_num,
                            'response': response,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            
            # Store versions for other tests
            if len(versions) == 3:
                self.version_test_data = {
                    'key': test_key,
                    'versions': versions
                }
        
        except S3ClientError as e:
            self.add_result(
                'versioning_multiple_versions',
                False,
                f"Failed to create multiple versions: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
    
    def _check_version_listing(self):
        """Test listing object versions."""
        self.logger.info("Checking version listing...")
        
        if not hasattr(self, 'version_test_data'):
            self.add_result(
                'versioning_list_versions',
                False,
                "No versioned object available for listing test",
                {}
            )
            return
        
        test_data = self.version_test_data
        
        try:
            start_time = time.time()
            response = self.s3_client.list_object_versions(Bucket=self.test_bucket)
            duration = time.time() - start_time
            
            if 'Versions' in response:
                versions = response['Versions']
                # Find versions for our test object
                test_versions = [v for v in versions if v['Key'] == test_data['key']]
                
                if len(test_versions) == len(test_data['versions']):
                    # Verify version IDs match
                    expected_version_ids = {v['version_id'] for v in test_data['versions']}
                    actual_version_ids = {v['VersionId'] for v in test_versions}
                    
                    if expected_version_ids == actual_version_ids:
                        self.add_result(
                            'versioning_list_versions',
                            True,
                            f"Successfully listed {len(test_versions)} versions",
                            {
                                'object_key': test_data['key'],
                                'versions_count': len(test_versions),
                                'bucket': self.test_bucket
                            },
                            duration
                        )
                    else:
                        self.add_result(
                            'versioning_list_versions',
                            False,
                            f"Version IDs don't match expected values",
                            {
                                'object_key': test_data['key'],
                                'expected_version_ids': list(expected_version_ids),
                                'actual_version_ids': list(actual_version_ids),
                                'bucket': self.test_bucket
                            },
                            duration
                        )
                else:
                    self.add_result(
                        'versioning_list_versions',
                        False,
                        f"Expected {len(test_data['versions'])} versions, found {len(test_versions)}",
                        {
                            'object_key': test_data['key'],
                            'expected_count': len(test_data['versions']),
                            'actual_count': len(test_versions),
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            else:
                self.add_result(
                    'versioning_list_versions',
                    False,
                    f"List object versions response missing 'Versions' field",
                    {'response': response, 'bucket': self.test_bucket},
                    duration
                )
        
        except S3ClientError as e:
            self.add_result(
                'versioning_list_versions',
                False,
                f"Failed to list object versions: {e}",
                {'error_code': e.error_code, 'bucket': self.test_bucket}
            )
    
    def _check_version_specific_operations(self):
        """Test operations on specific object versions."""
        self.logger.info("Checking version-specific operations...")
        
        if not hasattr(self, 'version_test_data'):
            self.add_result(
                'versioning_specific_operations',
                False,
                "No versioned object available for version-specific tests",
                {}
            )
            return
        
        test_data = self.version_test_data
        
        # Test getting specific versions
        for version_info in test_data['versions']:
            version_id = version_info['version_id']
            expected_content = version_info['content']
            
            try:
                start_time = time.time()
                response = self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=test_data['key'],
                    VersionId=version_id
                )
                duration = time.time() - start_time
                
                # Read and verify content
                actual_content = response['Body'].read().decode('utf-8')
                
                if actual_content == expected_content:
                    self.add_result(
                        f'versioning_get_version_{version_info["version_number"]}',
                        True,
                        f"Successfully retrieved version {version_info['version_number']} content",
                        {
                            'object_key': test_data['key'],
                            'version_id': version_id,
                            'version_number': version_info['version_number'],
                            'bucket': self.test_bucket
                        },
                        duration
                    )
                else:
                    self.add_result(
                        f'versioning_get_version_{version_info["version_number"]}',
                        False,
                        f"Version {version_info['version_number']} content doesn't match expected",
                        {
                            'object_key': test_data['key'],
                            'version_id': version_id,
                            'expected_content': expected_content,
                            'actual_content': actual_content,
                            'bucket': self.test_bucket
                        },
                        duration
                    )
            
            except S3ClientError as e:
                self.add_result(
                    f'versioning_get_version_{version_info["version_number"]}',
                    False,
                    f"Failed to get version {version_info['version_number']}: {e}",
                    {
                        'object_key': test_data['key'],
                        'version_id': version_id,
                        'error_code': e.error_code,
                        'bucket': self.test_bucket
                    }
                )
    
    def _check_version_deletion(self):
        """Test deleting specific object versions."""
        self.logger.info("Checking version deletion...")
        
        if not hasattr(self, 'version_test_data'):
            self.add_result(
                'versioning_delete_version',
                False,
                "No versioned object available for version deletion test",
                {}
            )
            return
        
        test_data = self.version_test_data
        
        # Delete the first version
        version_to_delete = test_data['versions'][0]
        version_id = version_to_delete['version_id']
        
        try:
            start_time = time.time()
            response = self.s3_client.delete_object(
                Bucket=self.test_bucket,
                Key=test_data['key'],
                VersionId=version_id
            )
            duration = time.time() - start_time
            
            self.add_result(
                'versioning_delete_version',
                True,
                f"Successfully deleted version {version_to_delete['version_number']}",
                {
                    'object_key': test_data['key'],
                    'version_id': version_id,
                    'version_number': version_to_delete['version_number'],
                    'bucket': self.test_bucket
                },
                duration
            )
            
            # Remove from cleanup since it's deleted
            self.cleanup_items = [item for item in self.cleanup_items 
                                if not (item['type'] == 'object' and 
                                       item['identifier'] == test_data['key'] and
                                       item.get('version_id') == version_id)]
            
            # Verify deletion by trying to get the version
            try:
                self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=test_data['key'],
                    VersionId=version_id
                )
                
                self.add_result(
                    'versioning_delete_verification',
                    False,
                    f"Deleted version still accessible",
                    {
                        'object_key': test_data['key'],
                        'version_id': version_id,
                        'bucket': self.test_bucket
                    }
                )
            
            except S3ClientError as get_error:
                if get_error.status_code == 404:
                    self.add_result(
                        'versioning_delete_verification',
                        True,
                        f"Deleted version correctly not found (404)",
                        {
                            'object_key': test_data['key'],
                            'version_id': version_id,
                            'bucket': self.test_bucket
                        }
                    )
                else:
                    self.add_result(
                        'versioning_delete_verification',
                        False,
                        f"Unexpected error accessing deleted version: {get_error}",
                        {
                            'object_key': test_data['key'],
                            'version_id': version_id,
                            'error_code': get_error.error_code,
                            'bucket': self.test_bucket
                        }
                    )
        
        except S3ClientError as e:
            self.add_result(
                'versioning_delete_version',
                False,
                f"Failed to delete version: {e}",
                {
                    'object_key': test_data['key'],
                    'version_id': version_id,
                    'error_code': e.error_code,
                    'bucket': self.test_bucket
                }
            )