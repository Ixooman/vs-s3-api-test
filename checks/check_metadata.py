"""
S3 Metadata Compatibility Checks

This module provides comprehensive testing for S3 metadata functionality including
standard headers, custom metadata, encoding, size limits, and copy behavior.
"""

import time
import json
import urllib.parse
from typing import Dict, Any
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class MetadataChecks(BaseCheck):
    """
    Comprehensive S3 metadata compatibility testing.
    
    Tests all aspects of S3 metadata handling including:
    - Standard S3 metadata headers (Content-Type, Content-Encoding, etc.)
    - Custom metadata (x-amz-meta-* headers)
    - Metadata encoding and special characters
    - Metadata size limits and validation
    - Metadata case sensitivity
    - Metadata behavior during copy operations
    - System vs user metadata distinction
    """
    
    def run_checks(self):
        """Run all metadata compatibility checks."""
        self.logger.info("Starting comprehensive S3 metadata compatibility checks...")
        
        # Create a test bucket for metadata operations
        self.test_bucket = self.generate_unique_name("metadata-test-bucket")
        try:
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            self.add_cleanup_item('bucket', self.test_bucket)
            self.logger.info(f"Created test bucket: {self.test_bucket}")
        except S3ClientError as e:
            self.add_result(
                'metadata_test_bucket_creation',
                False,
                f"Failed to create test bucket for metadata operations: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Run metadata tests
        self._check_standard_metadata_headers()
        self._check_custom_metadata()
        self._check_metadata_encoding()
        self._check_metadata_size_limits()
        self._check_metadata_case_sensitivity()
        self._check_metadata_copy_behavior()
        self._check_system_vs_user_metadata()
        self._check_metadata_edge_cases()
        
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
            content = self.config.get('test_data', {}).get('test_file_content', 'S3 metadata test data')
        
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
    
    def _check_standard_metadata_headers(self):
        """Test standard S3 metadata headers."""
        self.logger.info("Checking standard S3 metadata headers...")
        
        test_key = self.generate_unique_name("standard-metadata-test")
        test_data = self._generate_test_data(1024)
        
        # Standard metadata to test
        standard_metadata = {
            'ContentType': 'application/json',
            'ContentEncoding': 'gzip',
            'ContentDisposition': 'attachment; filename="test.json"',
            'ContentLanguage': 'en-US',
            'CacheControl': 'max-age=3600, no-cache',
            'Expires': 'Wed, 21 Oct 2025 07:28:00 GMT'
        }
        
        try:
            # Upload with standard metadata
            start_time = time.time()
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data,
                **standard_metadata
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
            
            # Verify upload succeeded
            if 'ETag' not in put_response:
                self.add_result(
                    'standard_metadata_upload',
                    False,
                    "Upload with standard metadata failed - no ETag returned",
                    {'object_key': test_key, 'response': put_response}
                )
                return
            
            # Retrieve and verify metadata
            head_response = self.s3_client.head_object(Bucket=self.test_bucket, Key=test_key)
            
            verified_headers = []
            for header, expected_value in standard_metadata.items():
                actual_value = head_response.get(header)
                if actual_value == expected_value:
                    verified_headers.append(header)
                else:
                    self.logger.debug(f"Standard metadata mismatch - {header}: expected '{expected_value}', got '{actual_value}'")
            
            success_rate = len(verified_headers) / len(standard_metadata)
            
            self.add_result(
                'standard_metadata_headers',
                success_rate >= 0.8,  # At least 80% of headers should be preserved
                f"Standard metadata headers: {len(verified_headers)}/{len(standard_metadata)} preserved correctly",
                {
                    'object_key': test_key,
                    'verified_headers': verified_headers,
                    'expected_headers': list(standard_metadata.keys()),
                    'success_rate': success_rate,
                    'head_response': dict(head_response)
                },
                duration
            )
            
        except S3ClientError as e:
            self.add_result(
                'standard_metadata_headers',
                False,
                f"Failed to test standard metadata headers: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
    
    def _check_custom_metadata(self):
        """Test custom metadata (x-amz-meta-* headers)."""
        self.logger.info("Checking custom metadata handling...")
        
        test_key = self.generate_unique_name("custom-metadata-test")
        test_data = self._generate_test_data(512)
        
        # Custom metadata to test
        custom_metadata = {
            'author': 'S3CompatibilityChecker',
            'project': 'metadata-testing',
            'version': '1.0.0',
            'environment': 'test',
            'numeric-value': '42',
            'boolean-value': 'true',
            'special-chars': 'test@example.com'
        }
        
        try:
            # Upload with custom metadata
            start_time = time.time()
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data,
                Metadata=custom_metadata,
                ContentType='text/plain'
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
            
            if 'ETag' not in put_response:
                self.add_result(
                    'custom_metadata_upload',
                    False,
                    "Upload with custom metadata failed - no ETag returned",
                    {'object_key': test_key, 'metadata': custom_metadata}
                )
                return
            
            # Retrieve and verify custom metadata
            head_response = self.s3_client.head_object(Bucket=self.test_bucket, Key=test_key)
            returned_metadata = head_response.get('Metadata', {})
            
            verified_metadata = []
            for key, expected_value in custom_metadata.items():
                actual_value = returned_metadata.get(key)
                if actual_value == expected_value:
                    verified_metadata.append(key)
                else:
                    self.logger.debug(f"Custom metadata mismatch - {key}: expected '{expected_value}', got '{actual_value}'")
            
            success_rate = len(verified_metadata) / len(custom_metadata)
            
            self.add_result(
                'custom_metadata_preservation',
                success_rate >= 0.9,  # At least 90% should be preserved
                f"Custom metadata: {len(verified_metadata)}/{len(custom_metadata)} fields preserved correctly",
                {
                    'object_key': test_key,
                    'verified_fields': verified_metadata,
                    'expected_metadata': custom_metadata,
                    'returned_metadata': returned_metadata,
                    'success_rate': success_rate
                },
                duration
            )
            
        except S3ClientError as e:
            self.add_result(
                'custom_metadata_preservation',
                False,
                f"Failed to test custom metadata: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
    
    def _check_metadata_encoding(self):
        """Test metadata encoding and special characters."""
        self.logger.info("Checking metadata encoding and special characters...")
        
        test_key = self.generate_unique_name("encoding-metadata-test")
        test_data = self._generate_test_data(256)
        
        # Metadata with various encodings and special characters
        encoding_metadata = {
            'ascii-text': 'simple-ascii-value',
            'utf8-text': 'café-München-日本',
            'spaces': 'value with spaces',
            'url-encoded': urllib.parse.quote('test@example.com'),
            'special-symbols': '!@#$%^&*()',
            'numbers': '123456789',
            'mixed': 'Test_123-Value@2024'
        }
        
        try:
            # Upload with encoding test metadata
            start_time = time.time()
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data,
                Metadata=encoding_metadata,
                ContentType='application/octet-stream'
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
            
            if 'ETag' not in put_response:
                self.add_result(
                    'metadata_encoding',
                    False,
                    "Upload with encoded metadata failed - no ETag returned",
                    {'object_key': test_key, 'metadata': encoding_metadata}
                )
                return
            
            # Retrieve and verify encoded metadata
            head_response = self.s3_client.head_object(Bucket=self.test_bucket, Key=test_key)
            returned_metadata = head_response.get('Metadata', {})
            
            encoding_results = []
            for key, expected_value in encoding_metadata.items():
                actual_value = returned_metadata.get(key)
                if actual_value == expected_value:
                    encoding_results.append(f"{key}:preserved")
                elif actual_value:
                    encoding_results.append(f"{key}:modified")
                else:
                    encoding_results.append(f"{key}:missing")
            
            preserved_count = len([r for r in encoding_results if r.endswith(':preserved')])
            success_rate = preserved_count / len(encoding_metadata)
            
            self.add_result(
                'metadata_encoding_handling',
                success_rate >= 0.7,  # At least 70% should handle encoding correctly
                f"Metadata encoding: {preserved_count}/{len(encoding_metadata)} values preserved correctly",
                {
                    'object_key': test_key,
                    'encoding_results': encoding_results,
                    'expected_metadata': encoding_metadata,
                    'returned_metadata': returned_metadata,
                    'success_rate': success_rate
                },
                duration
            )
            
        except S3ClientError as e:
            self.add_result(
                'metadata_encoding_handling',
                False,
                f"Failed to test metadata encoding: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
    
    def _check_metadata_size_limits(self):
        """Test metadata size limits and validation."""
        self.logger.info("Checking metadata size limits...")
        
        # Test 1: Individual metadata value size limit (2KB)
        large_value_key = self.generate_unique_name("large-value-metadata")
        large_value = 'x' * 2048  # 2KB value
        
        try:
            start_time = time.time()
            response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=large_value_key,
                Body=b"test data",
                Metadata={'large-field': large_value}
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', large_value_key, bucket=self.test_bucket)
            
            if 'ETag' in response:
                self.add_result(
                    'large_metadata_value_acceptance',
                    False,  # This should ideally be rejected
                    "Large metadata value (2KB) was accepted - may indicate no size validation",
                    {
                        'object_key': large_value_key,
                        'value_size': len(large_value),
                        'response': response
                    },
                    duration
                )
            
        except S3ClientError as e:
            if e.status_code in [400, 413]:  # Bad Request or Payload Too Large
                self.add_result(
                    'large_metadata_value_rejection',
                    True,
                    f"Large metadata value correctly rejected: {e.error_code}",
                    {
                        'object_key': large_value_key,
                        'value_size': len(large_value),
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            else:
                self.add_result(
                    'large_metadata_value_rejection',
                    False,
                    f"Unexpected error for large metadata value: {e}",
                    {'object_key': large_value_key, 'error_code': e.error_code}
                )
        
        # Test 2: Total metadata size limit
        many_fields_key = self.generate_unique_name("many-fields-metadata")
        many_fields_metadata = {f"field{i}": f"value{i}" * 50 for i in range(100)}  # Many fields
        
        try:
            start_time = time.time()
            response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=many_fields_key,
                Body=b"test data",
                Metadata=many_fields_metadata
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', many_fields_key, bucket=self.test_bucket)
            
            total_size = sum(len(k) + len(v) for k, v in many_fields_metadata.items())
            
            if 'ETag' in response:
                self.add_result(
                    'total_metadata_size_check',
                    total_size < 8192,  # AWS limit is ~8KB total
                    f"Total metadata size {total_size} bytes accepted",
                    {
                        'object_key': many_fields_key,
                        'field_count': len(many_fields_metadata),
                        'total_size': total_size,
                        'response': response
                    },
                    duration
                )
            
        except S3ClientError as e:
            if e.status_code in [400, 413]:
                total_size = sum(len(k) + len(v) for k, v in many_fields_metadata.items())
                self.add_result(
                    'total_metadata_size_rejection',
                    True,
                    f"Large total metadata size ({total_size} bytes) correctly rejected",
                    {
                        'object_key': many_fields_key,
                        'field_count': len(many_fields_metadata),
                        'total_size': total_size,
                        'error_code': e.error_code
                    }
                )
            else:
                self.add_result(
                    'total_metadata_size_rejection',
                    False,
                    f"Unexpected error for large total metadata: {e}",
                    {'object_key': many_fields_key, 'error_code': e.error_code}
                )
    
    def _check_metadata_case_sensitivity(self):
        """Test metadata case sensitivity behavior."""
        self.logger.info("Checking metadata case sensitivity...")
        
        test_key = self.generate_unique_name("case-sensitivity-test")
        test_data = self._generate_test_data(256)
        
        # Metadata with different cases
        case_metadata = {
            'lowercase': 'value1',
            'UPPERCASE': 'value2',
            'MixedCase': 'value3',
            'camelCase': 'value4'
        }
        
        try:
            # Upload with case-varied metadata
            start_time = time.time()
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data,
                Metadata=case_metadata
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
            
            if 'ETag' not in put_response:
                self.add_result(
                    'metadata_case_sensitivity',
                    False,
                    "Upload with case-varied metadata failed",
                    {'object_key': test_key}
                )
                return
            
            # Retrieve and check case preservation
            head_response = self.s3_client.head_object(Bucket=self.test_bucket, Key=test_key)
            returned_metadata = head_response.get('Metadata', {})
            
            case_results = {}
            for original_key, expected_value in case_metadata.items():
                # Check if key is preserved exactly
                if original_key in returned_metadata:
                    case_results[original_key] = 'exact_match'
                else:
                    # Check if key exists in different case
                    found_key = None
                    for ret_key in returned_metadata:
                        if ret_key.lower() == original_key.lower():
                            found_key = ret_key
                            break
                    
                    if found_key:
                        case_results[original_key] = f'case_changed_to_{found_key}'
                    else:
                        case_results[original_key] = 'missing'
            
            exact_matches = len([r for r in case_results.values() if r == 'exact_match'])
            total_found = len([r for r in case_results.values() if r != 'missing'])
            
            self.add_result(
                'metadata_case_preservation',
                exact_matches >= len(case_metadata) * 0.5,  # At least 50% should preserve case
                f"Case sensitivity: {exact_matches}/{len(case_metadata)} keys preserved exactly, {total_found} found total",
                {
                    'object_key': test_key,
                    'case_results': case_results,
                    'expected_metadata': case_metadata,
                    'returned_metadata': returned_metadata,
                    'exact_matches': exact_matches,
                    'total_found': total_found
                },
                duration
            )
            
        except S3ClientError as e:
            self.add_result(
                'metadata_case_preservation',
                False,
                f"Failed to test metadata case sensitivity: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
    
    def _check_metadata_copy_behavior(self):
        """Test metadata behavior during copy operations."""
        self.logger.info("Checking metadata behavior during copy operations...")
        
        source_key = self.generate_unique_name("copy-source-metadata")
        dest_key = self.generate_unique_name("copy-dest-metadata")
        test_data = self._generate_test_data(512)
        
        source_metadata = {
            'original-author': 'source-creator',
            'creation-time': '2024-01-01',
            'category': 'original'
        }
        
        try:
            # Upload source object with metadata
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=source_key,
                Body=test_data,
                Metadata=source_metadata,
                ContentType='text/plain'
            )
            
            self.add_cleanup_item('object', source_key, bucket=self.test_bucket)
            self.add_cleanup_item('object', dest_key, bucket=self.test_bucket)
            
            if 'ETag' not in put_response:
                self.add_result(
                    'metadata_copy_behavior',
                    False,
                    "Failed to create source object for copy test",
                    {'source_key': source_key}
                )
                return
            
            # Test 1: Copy with metadata preservation (default behavior)
            start_time = time.time()
            copy_response = self.s3_client.copy_object(
                Bucket=self.test_bucket,
                Key=dest_key,
                CopySource={'Bucket': self.test_bucket, 'Key': source_key}
            )
            copy_duration = time.time() - start_time
            
            # Check if metadata was preserved
            dest_head = self.s3_client.head_object(Bucket=self.test_bucket, Key=dest_key)
            dest_metadata = dest_head.get('Metadata', {})
            
            preserved_fields = []
            for key, value in source_metadata.items():
                if dest_metadata.get(key) == value:
                    preserved_fields.append(key)
            
            preservation_rate = len(preserved_fields) / len(source_metadata)
            
            self.add_result(
                'metadata_copy_preservation',
                preservation_rate >= 0.8,  # At least 80% should be preserved
                f"Copy operation metadata preservation: {len(preserved_fields)}/{len(source_metadata)} fields preserved",
                {
                    'source_key': source_key,
                    'dest_key': dest_key,
                    'source_metadata': source_metadata,
                    'dest_metadata': dest_metadata,
                    'preserved_fields': preserved_fields,
                    'preservation_rate': preservation_rate
                },
                copy_duration
            )
            
            # Test 2: Copy with metadata replacement
            replacement_key = self.generate_unique_name("copy-replacement-metadata")
            self.add_cleanup_item('object', replacement_key, bucket=self.test_bucket)
            
            new_metadata = {
                'new-author': 'copy-creator',
                'modified-time': '2024-12-01',
                'category': 'modified'
            }
            
            start_time = time.time()
            replace_response = self.s3_client.copy_object(
                Bucket=self.test_bucket,
                Key=replacement_key,
                CopySource={'Bucket': self.test_bucket, 'Key': source_key},
                Metadata=new_metadata,
                MetadataDirective='REPLACE'
            )
            replace_duration = time.time() - start_time
            
            # Verify metadata replacement
            replace_head = self.s3_client.head_object(Bucket=self.test_bucket, Key=replacement_key)
            replace_metadata = replace_head.get('Metadata', {})
            
            replaced_correctly = all(
                replace_metadata.get(key) == value 
                for key, value in new_metadata.items()
            )
            
            old_metadata_absent = all(
                key not in replace_metadata 
                for key in source_metadata.keys()
            )
            
            self.add_result(
                'metadata_copy_replacement',
                replaced_correctly and old_metadata_absent,
                f"Copy with metadata replacement: new metadata set={replaced_correctly}, old metadata removed={old_metadata_absent}",
                {
                    'source_key': source_key,
                    'replacement_key': replacement_key,
                    'new_metadata': new_metadata,
                    'replace_metadata': replace_metadata,
                    'source_metadata': source_metadata,
                    'replaced_correctly': replaced_correctly,
                    'old_metadata_absent': old_metadata_absent
                },
                replace_duration
            )
            
        except S3ClientError as e:
            self.add_result(
                'metadata_copy_operations',
                False,
                f"Failed to test metadata copy behavior: {e}",
                {'source_key': source_key, 'error_code': e.error_code}
            )
    
    def _check_system_vs_user_metadata(self):
        """Test distinction between system and user metadata."""
        self.logger.info("Checking system vs user metadata handling...")
        
        test_key = self.generate_unique_name("system-user-metadata-test")
        test_data = self._generate_test_data(1024)
        
        user_metadata = {
            'user-field': 'user-value',
            'application': 'test-app'
        }
        
        try:
            # Upload with user metadata and system metadata
            start_time = time.time()
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=test_key,
                Body=test_data,
                Metadata=user_metadata,
                ContentType='application/json',
                CacheControl='no-cache',
                ContentEncoding='identity'
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', test_key, bucket=self.test_bucket)
            
            if 'ETag' not in put_response:
                self.add_result(
                    'system_user_metadata',
                    False,
                    "Upload with system and user metadata failed",
                    {'object_key': test_key}
                )
                return
            
            # Retrieve and analyze metadata types
            head_response = self.s3_client.head_object(Bucket=self.test_bucket, Key=test_key)
            
            # Check system metadata
            system_metadata_present = []
            expected_system = ['ContentType', 'ContentLength', 'ETag', 'LastModified']
            for field in expected_system:
                if field in head_response:
                    system_metadata_present.append(field)
            
            # Check user metadata
            returned_user_metadata = head_response.get('Metadata', {})
            user_metadata_preserved = all(
                returned_user_metadata.get(key) == value 
                for key, value in user_metadata.items()
            )
            
            # Check that system metadata is separate from user metadata
            metadata_separation = not any(
                key in returned_user_metadata 
                for key in expected_system
            )
            
            self.add_result(
                'system_user_metadata_distinction',
                user_metadata_preserved and len(system_metadata_present) >= 3 and metadata_separation,
                f"System/User metadata distinction: system fields={len(system_metadata_present)}, user preserved={user_metadata_preserved}, separated={metadata_separation}",
                {
                    'object_key': test_key,
                    'system_metadata_present': system_metadata_present,
                    'user_metadata_preserved': user_metadata_preserved,
                    'metadata_separation': metadata_separation,
                    'returned_user_metadata': returned_user_metadata,
                    'head_response_keys': list(head_response.keys())
                },
                duration
            )
            
        except S3ClientError as e:
            self.add_result(
                'system_user_metadata_distinction',
                False,
                f"Failed to test system vs user metadata: {e}",
                {'object_key': test_key, 'error_code': e.error_code}
            )
    
    def _check_metadata_edge_cases(self):
        """Test metadata edge cases and boundary conditions."""
        self.logger.info("Checking metadata edge cases...")
        
        # Test 1: Empty metadata values
        empty_test_key = self.generate_unique_name("empty-metadata-test")
        
        try:
            start_time = time.time()
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=empty_test_key,
                Body=b"test",
                Metadata={'empty-field': '', 'normal-field': 'value'}
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', empty_test_key, bucket=self.test_bucket)
            
            if 'ETag' in put_response:
                head_response = self.s3_client.head_object(Bucket=self.test_bucket, Key=empty_test_key)
                returned_metadata = head_response.get('Metadata', {})
                
                empty_field_handling = 'empty-field' in returned_metadata
                normal_field_preserved = returned_metadata.get('normal-field') == 'value'
                
                self.add_result(
                    'empty_metadata_values',
                    normal_field_preserved,  # Normal field should be preserved
                    f"Empty metadata values: empty field present={empty_field_handling}, normal field preserved={normal_field_preserved}",
                    {
                        'object_key': empty_test_key,
                        'empty_field_handling': empty_field_handling,
                        'normal_field_preserved': normal_field_preserved,
                        'returned_metadata': returned_metadata
                    },
                    duration
                )
            
        except S3ClientError as e:
            self.add_result(
                'empty_metadata_values',
                False,
                f"Failed to test empty metadata values: {e}",
                {'object_key': empty_test_key, 'error_code': e.error_code}
            )
        
        # Test 2: No metadata (baseline)
        no_metadata_key = self.generate_unique_name("no-metadata-test")
        
        try:
            start_time = time.time()
            put_response = self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=no_metadata_key,
                Body=b"test without metadata"
            )
            duration = time.time() - start_time
            
            self.add_cleanup_item('object', no_metadata_key, bucket=self.test_bucket)
            
            if 'ETag' in put_response:
                head_response = self.s3_client.head_object(Bucket=self.test_bucket, Key=no_metadata_key)
                user_metadata = head_response.get('Metadata', {})
                
                self.add_result(
                    'no_metadata_baseline',
                    len(user_metadata) == 0,
                    f"No metadata baseline: user metadata count={len(user_metadata)}",
                    {
                        'object_key': no_metadata_key,
                        'user_metadata_count': len(user_metadata),
                        'user_metadata': user_metadata
                    },
                    duration
                )
            
        except S3ClientError as e:
            self.add_result(
                'no_metadata_baseline',
                False,
                f"Failed to test no metadata baseline: {e}",
                {'object_key': no_metadata_key, 'error_code': e.error_code}
            )