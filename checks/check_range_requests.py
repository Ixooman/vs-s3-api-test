"""
Range requests (partial object retrieval) compatibility checks.

This module contains checks for S3 range request operations including
single-range requests, multi-range requests, and edge cases.
"""

import time
from typing import List
from framework.base_check import BaseCheck, CheckResult
from framework.s3_client import S3ClientError


class RangeRequestChecks(BaseCheck):
    """
    Range request operations compatibility checks.
    
    Tests partial object retrieval using HTTP Range headers to verify
    S3 API compatibility for range-based operations.
    """
    
    def run_checks(self) -> List[CheckResult]:
        """
        Run all range request related compatibility checks.
        
        Returns:
            List of CheckResult objects for each range request check
        """
        self.logger.info("Starting range request compatibility checks...")
        
        # Create a test bucket for range request operations
        self.test_bucket = self.generate_unique_name("range-test-bucket")
        try:
            self.s3_client.create_bucket(Bucket=self.test_bucket)
            self.add_cleanup_item('bucket', self.test_bucket)
            self.logger.info(f"Created test bucket: {self.test_bucket}")
        except S3ClientError as e:
            self.add_result(
                'range_test_bucket_creation',
                False,
                f"Failed to create test bucket for range operations: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Upload test object for range operations
        self.test_object_key = self.generate_unique_name("range-test-object")
        self.test_data = self._create_range_test_data()
        
        try:
            self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key=self.test_object_key,
                Body=self.test_data,
                ContentType='application/octet-stream'
            )
            self.add_cleanup_item('object', self.test_object_key, bucket=self.test_bucket)
            self.logger.info(f"Uploaded test object: {self.test_object_key} ({len(self.test_data)} bytes)")
        except S3ClientError as e:
            self.add_result(
                'range_test_object_upload',
                False,
                f"Failed to upload test object for range operations: {e}",
                {'error_code': e.error_code}
            )
            return self.results
        
        # Run individual check methods
        self._check_single_byte_range()
        self._check_partial_range_requests()
        self._check_suffix_range_requests()
        self._check_multiple_range_requests()
        self._check_invalid_range_requests()
        self._check_range_with_etag()
        
        self.logger.info(f"Range request checks completed: {len(self.results)} checks performed")
        return self.results
    
    def _create_range_test_data(self) -> bytes:
        """
        Create test data suitable for range request testing.
        
        Returns:
            Test data with predictable patterns for range verification
        """
        # Create 10KB of data with predictable patterns
        data = b''
        # Each line is exactly 100 bytes (including newline)
        for i in range(100):  # 100 lines = 10,000 bytes
            line = f"Line {i:03d}: This is line number {i:03d} with predictable content for range testing."
            # Pad to exactly 99 chars, then add newline
            line = line.ljust(99)[:99] + "\n"
            data += line.encode('utf-8')
        
        return data
    
    def _check_single_byte_range(self):
        """Test single byte range requests."""
        self.logger.info("Checking single byte range requests...")
        
        test_cases = [
            (0, 0, "First byte"),           # bytes=0-0
            (99, 99, "100th byte"),         # bytes=99-99
            (500, 500, "Middle byte"),      # bytes=500-500
            (-1, -1, "Last byte")           # bytes=-1 (suffix range for last byte)
        ]
        
        for start, end, description in test_cases:
            try:
                if start == -1:  # Suffix range
                    range_header = f"bytes=-1"
                    expected_start = len(self.test_data) - 1
                    expected_end = len(self.test_data) - 1
                else:
                    range_header = f"bytes={start}-{end}"
                    expected_start = start
                    expected_end = end
                
                start_time = time.time()
                response = self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=self.test_object_key,
                    Range=range_header
                )
                duration = time.time() - start_time
                
                # Read the response data
                range_data = response['Body'].read()
                expected_data = self.test_data[expected_start:expected_end + 1]
                
                # Validate response
                checks = []
                
                # Check status code (should be 206 for partial content)
                if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 206:
                    checks.append('status_206')
                
                # Check Content-Range header
                content_range = response.get('ContentRange', '')
                if content_range:
                    checks.append('content_range_header')
                    # Parse and validate Content-Range
                    if f"bytes {expected_start}-{expected_end}/" in content_range:
                        checks.append('content_range_correct')
                
                # Check data matches
                if range_data == expected_data:
                    checks.append('data_matches')
                
                # Check Content-Length
                if response.get('ContentLength') == len(expected_data):
                    checks.append('content_length_correct')
                
                if len(checks) >= 3:  # At least 3 checks should pass
                    self.add_result(
                        f'range_single_byte_{description.lower().replace(" ", "_")}',
                        True,
                        f"Successfully retrieved {description} using range request",
                        {
                            'range_header': range_header,
                            'expected_size': len(expected_data),
                            'actual_size': len(range_data),
                            'content_range': content_range,
                            'passed_checks': checks,
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
                else:
                    self.add_result(
                        f'range_single_byte_{description.lower().replace(" ", "_")}',
                        False,
                        f"Range request for {description} failed validation ({len(checks)}/5 checks)",
                        {
                            'range_header': range_header,
                            'passed_checks': checks,
                            'response_metadata': response.get('ResponseMetadata', {}),
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
            
            except S3ClientError as e:
                self.add_result(
                    f'range_single_byte_{description.lower().replace(" ", "_")}',
                    False,
                    f"Failed to retrieve {description} with range request: {e}",
                    {
                        'range_header': range_header if 'range_header' in locals() else 'unknown',
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
    
    def _check_partial_range_requests(self):
        """Test partial range requests for chunks of data."""
        self.logger.info("Checking partial range requests...")
        
        test_cases = [
            (0, 99, "First 100 bytes"),      # First line
            (100, 299, "Second and third lines"),  # Lines 1-2
            (1000, 1999, "1KB chunk from middle"),  # 1KB from middle
            (5000, 7499, "2.5KB chunk"),    # 2.5KB chunk
            (len(self.test_data) - 100, len(self.test_data) - 1, "Last 100 bytes")  # Last line
        ]
        
        for start, end, description in test_cases:
            try:
                range_header = f"bytes={start}-{end}"
                
                start_time = time.time()
                response = self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=self.test_object_key,
                    Range=range_header
                )
                duration = time.time() - start_time
                
                # Read and validate response
                range_data = response['Body'].read()
                expected_data = self.test_data[start:end + 1]
                expected_size = end - start + 1
                
                if (range_data == expected_data and 
                    len(range_data) == expected_size and
                    response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 206):
                    
                    self.add_result(
                        f'range_partial_{start}_{end}',
                        True,
                        f"Successfully retrieved {description} ({expected_size} bytes)",
                        {
                            'range_header': range_header,
                            'start': start,
                            'end': end,
                            'size': expected_size,
                            'content_range': response.get('ContentRange', ''),
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
                else:
                    self.add_result(
                        f'range_partial_{start}_{end}',
                        False,
                        f"Range request validation failed for {description}",
                        {
                            'range_header': range_header,
                            'expected_size': expected_size,
                            'actual_size': len(range_data),
                            'data_matches': range_data == expected_data,
                            'status_code': response.get('ResponseMetadata', {}).get('HTTPStatusCode'),
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
            
            except S3ClientError as e:
                self.add_result(
                    f'range_partial_{start}_{end}',
                    False,
                    f"Failed partial range request for {description}: {e}",
                    {
                        'range_header': range_header,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
    
    def _check_suffix_range_requests(self):
        """Test suffix range requests (last N bytes)."""
        self.logger.info("Checking suffix range requests...")
        
        test_cases = [
            (1, "Last 1 byte"),
            (10, "Last 10 bytes"),
            (100, "Last 100 bytes"),
            (1000, "Last 1000 bytes"),
            (len(self.test_data), "Entire file as suffix")
        ]
        
        for suffix_length, description in test_cases:
            try:
                range_header = f"bytes=-{suffix_length}"
                
                start_time = time.time()
                response = self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=self.test_object_key,
                    Range=range_header
                )
                duration = time.time() - start_time
                
                # Calculate expected data
                start_pos = max(0, len(self.test_data) - suffix_length)
                expected_data = self.test_data[start_pos:]
                
                # Read and validate response
                range_data = response['Body'].read()
                
                if (range_data == expected_data and 
                    response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 206):
                    
                    self.add_result(
                        f'range_suffix_{suffix_length}',
                        True,
                        f"Successfully retrieved {description}",
                        {
                            'range_header': range_header,
                            'suffix_length': suffix_length,
                            'actual_size': len(range_data),
                            'expected_size': len(expected_data),
                            'content_range': response.get('ContentRange', ''),
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
                else:
                    self.add_result(
                        f'range_suffix_{suffix_length}',
                        False,
                        f"Suffix range request failed for {description}",
                        {
                            'range_header': range_header,
                            'expected_size': len(expected_data),
                            'actual_size': len(range_data),
                            'data_matches': range_data == expected_data,
                            'status_code': response.get('ResponseMetadata', {}).get('HTTPStatusCode'),
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
            
            except S3ClientError as e:
                self.add_result(
                    f'range_suffix_{suffix_length}',
                    False,
                    f"Failed suffix range request for {description}: {e}",
                    {
                        'range_header': range_header,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
    
    def _check_multiple_range_requests(self):
        """Test multiple range requests in a single request."""
        self.logger.info("Checking multiple range requests...")
        
        # Note: Multiple range requests return multipart/byteranges response
        # This is a more advanced feature that not all S3 implementations support
        
        test_cases = [
            ("bytes=0-99,200-299", "Two 100-byte chunks"),
            ("bytes=0-49,100-149,200-249", "Three 50-byte chunks"),
            ("bytes=0-9,-10", "First 10 and last 10 bytes")
        ]
        
        for range_header, description in test_cases:
            try:
                start_time = time.time()
                response = self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=self.test_object_key,
                    Range=range_header
                )
                duration = time.time() - start_time
                
                # Read response
                response_data = response['Body'].read()
                
                # Check if we got a multipart response or a single range
                content_type = response.get('ContentType', '')
                
                if 'multipart/byteranges' in content_type:
                    # Full multipart support
                    self.add_result(
                        f'range_multiple_{hash(range_header) % 1000}',
                        True,
                        f"Successfully handled multiple ranges with multipart response: {description}",
                        {
                            'range_header': range_header,
                            'content_type': content_type,
                            'response_size': len(response_data),
                            'status_code': response.get('ResponseMetadata', {}).get('HTTPStatusCode'),
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
                elif response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 206:
                    # Single range returned (some implementations return first range only)
                    self.add_result(
                        f'range_multiple_{hash(range_header) % 1000}',
                        True,
                        f"Multiple range request returned single range (acceptable): {description}",
                        {
                            'range_header': range_header,
                            'content_type': content_type,
                            'response_size': len(response_data),
                            'status_code': 206,
                            'note': 'Single range returned instead of multipart',
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
                else:
                    self.add_result(
                        f'range_multiple_{hash(range_header) % 1000}',
                        False,
                        f"Multiple range request returned unexpected response: {description}",
                        {
                            'range_header': range_header,
                            'content_type': content_type,
                            'status_code': response.get('ResponseMetadata', {}).get('HTTPStatusCode'),
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
            
            except S3ClientError as e:
                # Some S3 implementations don't support multiple ranges
                if e.status_code in [400, 501]:  # Bad Request or Not Implemented
                    self.add_result(
                        f'range_multiple_{hash(range_header) % 1000}',
                        True,
                        f"Multiple range request correctly rejected (not supported): {description}",
                        {
                            'range_header': range_header,
                            'error_code': e.error_code,
                            'status_code': e.status_code,
                            'note': 'Multiple ranges not supported (acceptable)'
                        }
                    )
                else:
                    self.add_result(
                        f'range_multiple_{hash(range_header) % 1000}',
                        False,
                        f"Multiple range request failed unexpectedly: {description} - {e}",
                        {
                            'range_header': range_header,
                            'error_code': e.error_code,
                            'status_code': e.status_code
                        }
                    )
    
    def _check_invalid_range_requests(self):
        """Test invalid range requests to verify proper error handling."""
        self.logger.info("Checking invalid range requests...")
        
        invalid_cases = [
            ("bytes=abc-def", "Non-numeric range"),
            ("bytes=100-50", "Invalid range (end < start)"),
            ("bytes=999999-999999", "Range beyond file size"),
            ("bytes=0-999999", "End beyond file size"),
            ("invalid-range-header", "Malformed range header"),
            ("bytes=", "Empty range"),
            ("bytes=-", "Invalid suffix range")
        ]
        
        for range_header, description in invalid_cases:
            try:
                start_time = time.time()
                response = self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=self.test_object_key,
                    Range=range_header
                )
                duration = time.time() - start_time
                
                # If the request succeeds, it might indicate non-standard behavior
                status_code = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
                if status_code == 200:
                    # Some implementations might ignore invalid ranges and return full object
                    self.add_result(
                        f'range_invalid_{hash(range_header) % 1000}',
                        True,
                        f"Invalid range ignored, full object returned: {description}",
                        {
                            'range_header': range_header,
                            'status_code': status_code,
                            'note': 'Invalid range ignored (acceptable behavior)',
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
                elif status_code == 206:
                    # Partial content returned - might be too lenient
                    self.add_result(
                        f'range_invalid_{hash(range_header) % 1000}',
                        False,
                        f"Invalid range request returned partial content: {description}",
                        {
                            'range_header': range_header,
                            'status_code': status_code,
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
                else:
                    self.add_result(
                        f'range_invalid_{hash(range_header) % 1000}',
                        False,
                        f"Invalid range request succeeded unexpectedly: {description}",
                        {
                            'range_header': range_header,
                            'status_code': status_code,
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
            
            except S3ClientError as e:
                # This is expected for invalid ranges
                if e.status_code in [400, 416]:  # Bad Request or Range Not Satisfiable
                    self.add_result(
                        f'range_invalid_{hash(range_header) % 1000}',
                        True,
                        f"Invalid range correctly rejected: {description}",
                        {
                            'range_header': range_header,
                            'error_code': e.error_code,
                            'status_code': e.status_code
                        }
                    )
                else:
                    self.add_result(
                        f'range_invalid_{hash(range_header) % 1000}',
                        False,
                        f"Invalid range request returned unexpected error: {description} - {e}",
                        {
                            'range_header': range_header,
                            'error_code': e.error_code,
                            'status_code': e.status_code
                        }
                    )
    
    def _check_range_with_etag(self):
        """Test range requests with If-Range conditions."""
        self.logger.info("Checking range requests with ETag conditions...")
        
        try:
            # First get the object's ETag
            head_response = self.s3_client.head_object(
                Bucket=self.test_bucket,
                Key=self.test_object_key
            )
            etag = head_response.get('ETag', '').strip('"')
            
            if not etag:
                self.add_result(
                    'range_with_etag',
                    False,
                    "Could not retrieve ETag for range condition testing",
                    {'bucket': self.test_bucket, 'object_key': self.test_object_key}
                )
                return
            
            # Test range request with matching ETag
            try:
                start_time = time.time()
                response = self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=self.test_object_key,
                    Range="bytes=0-99",
                    IfRange=etag
                )
                duration = time.time() - start_time
                
                if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 206:
                    self.add_result(
                        'range_with_matching_etag',
                        True,
                        f"Range request with matching ETag succeeded",
                        {
                            'range_header': 'bytes=0-99',
                            'etag': etag,
                            'status_code': 206,
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'range_with_matching_etag',
                        False,
                        f"Range request with matching ETag returned unexpected status",
                        {
                            'range_header': 'bytes=0-99',
                            'etag': etag,
                            'status_code': response.get('ResponseMetadata', {}).get('HTTPStatusCode'),
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
            
            except S3ClientError as e:
                self.add_result(
                    'range_with_matching_etag',
                    False,
                    f"Range request with matching ETag failed: {e}",
                    {
                        'etag': etag,
                        'error_code': e.error_code,
                        'status_code': e.status_code
                    }
                )
            
            # Test range request with non-matching ETag
            fake_etag = "fake-etag-12345"
            try:
                start_time = time.time()
                response = self.s3_client.get_object(
                    Bucket=self.test_bucket,
                    Key=self.test_object_key,
                    Range="bytes=0-99",
                    IfRange=fake_etag
                )
                duration = time.time() - start_time
                
                # Should return full object (200) when ETag doesn't match
                if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
                    self.add_result(
                        'range_with_nonmatching_etag',
                        True,
                        f"Range request with non-matching ETag correctly returned full object",
                        {
                            'range_header': 'bytes=0-99',
                            'fake_etag': fake_etag,
                            'real_etag': etag,
                            'status_code': 200,
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
                else:
                    self.add_result(
                        'range_with_nonmatching_etag',
                        False,
                        f"Range request with non-matching ETag returned unexpected status",
                        {
                            'range_header': 'bytes=0-99',
                            'fake_etag': fake_etag,
                            'status_code': response.get('ResponseMetadata', {}).get('HTTPStatusCode'),
                            'bucket': self.test_bucket,
                            'object_key': self.test_object_key
                        },
                        duration
                    )
            
            except S3ClientError as e:
                # Some implementations might return an error for non-matching ETag
                self.add_result(
                    'range_with_nonmatching_etag',
                    True,
                    f"Range request with non-matching ETag correctly failed: {e.error_code}",
                    {
                        'fake_etag': fake_etag,
                        'error_code': e.error_code,
                        'status_code': e.status_code,
                        'note': 'Error response is acceptable for non-matching ETag'
                    }
                )
        
        except S3ClientError as e:
            self.add_result(
                'range_with_etag',
                False,
                f"Failed to perform ETag-based range tests: {e}",
                {'error_code': e.error_code}
            )