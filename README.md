# S3 Compatibility Checker

A comprehensive testing framework for verifying S3 API compatibility in custom storage systems. This tool helps developers and system administrators validate that their S3-compatible storage implementations correctly handle the full range of S3 operations.

The framework includes both a modern Python-based testing framework and legacy AWS CLI test scripts for comprehensive S3 API validation.

## Features

- **Comprehensive Testing**: Tests all major S3 operations including buckets, objects, multipart uploads, versioning, tagging, and more
- **Range Request Testing**: Validates partial object retrieval using HTTP Range headers
- **Error Condition Testing**: Verifies proper error handling for invalid requests and edge cases
- **Extensible Framework**: Easy to add new test categories and customize for specific needs
- **Detailed Reporting**: Console output and file logging with configurable detail levels
- **Enhanced Protocol Logging**: Raw HTTP request/response logging for maximum S3 API validation
- **boto3 Debug Logging**: Full AWS SDK debug logging for protocol-level analysis
- **Configuration Driven**: INI-based configuration for easy setup and customization
- **Automated Cleanup**: Automatically cleans up test resources to avoid storage pollution

## Quick Start

### 1. Installation

```bash
# Clone or download the S3 compatibility checker
cd /path/to/s3-compatibility-checker

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Generate Configuration

```bash
# Generate a configuration template
python main.py --generate-config

# Edit the generated config.ini file with your S3 endpoint details
nano config.ini
```

### 3. Configure Your S3 Endpoint

Edit `config.ini` and update the connection settings:

```ini
[connection]
endpoint_url = http://your-s3-endpoint:port
access_key = your-access-key
secret_key = your-secret-key
region = us-east-1
verify_ssl = false
```

### 4. Run Compatibility Checks

```bash
# Run all compatibility checks
python main.py --scope all

# Run specific check categories
python main.py --scope buckets,objects,multipart

# Run with debug logging
python main.py --scope all --log-level debug

# Export results to JSON
python main.py --scope all --export-results results.json
```

## Check Categories

The framework includes the following test categories:

### Core Operations
- **buckets**: Bucket creation, listing, deletion, configuration (versioning, tagging)
- **objects**: Object upload, download, copy, delete, metadata operations
- **multipart**: Multipart upload workflow (create, upload parts, complete, abort)

### Advanced Features
- **versioning**: Object versioning (enable/disable, multiple versions, version-specific operations)
- **tagging**: Bucket and object tagging (put, get, delete tags)
- **attributes**: Object attributes and metadata (get-object-attributes, storage class)
- **metadata**: Comprehensive metadata testing (standard headers, custom metadata, encoding, size limits)

### Specialized Testing
- **range_requests**: Partial object retrieval using HTTP Range headers
- **error_conditions**: Error handling for invalid requests and edge cases
- **sync**: Batch operations and directory synchronization patterns

## Configuration

The framework uses INI configuration files for easy setup. Key configuration sections:

### Connection Settings
```ini
[connection]
endpoint_url = http://192.168.10.81    # Your S3 endpoint
access_key = your-access-key           # Access credentials
secret_key = your-secret-key
region = us-east-1                     # AWS region
verify_ssl = false                     # SSL verification
max_retries = 3                        # Request retry count
```

### Test Data Configuration
```ini
[test_data]
small_file_size = 1024                 # Small file size (bytes)
medium_file_size = 1048576             # Medium file size (bytes)
large_file_size = 10485760             # Large file size (bytes)
multipart_chunk_size = 5242880         # Multipart chunk size (bytes)
test_file_content = S3 test data       # Base content for test files
cleanup_enabled = true                 # Auto-cleanup test resources
```

### Logging Configuration
```ini
[logging]
log_level = INFO                       # Log level (DEBUG, INFO, WARNING, ERROR)
log_file = s3_checker.log             # Log file name
console_output = true                  # Show console output
detailed_errors = true                 # Show detailed error info

# Enhanced logging for maximum S3 API validation confidence
enable_raw_logging = false             # Raw HTTP request/response logging
enable_boto_debug = false              # Full boto3/botocore debug logging
```

### Check Selection
```ini
[checks]
buckets = true                         # Enable/disable specific checks
objects = true
multipart = true
versioning = true
tagging = true
attributes = true
metadata = true
range_requests = true
error_conditions = true
sync = true
```

## AWS CLI Testing Scripts

In addition to the Python framework, the project includes several specialized AWS CLI-based testing scripts for specific S3 testing scenarios:

### Legacy AWS CLI Test Suite
- **S3_compatibility.txt**: Original comprehensive AWS CLI test script with sequential operations covering bucket operations, object lifecycle management, multipart uploads, versioning, tagging, and object attributes

### Advanced Multipart Upload Testing

#### `scripts/max_object_multipart_probe.sh`
Comprehensive multipart upload testing for large objects with dynamic part sizing:
- Tests objects from 100MB up to multiple terabytes
- Dynamic part sizing: 64MB (< 1GB), 128MB (< 10GB), 256MB (< 100GB), 512MB (< 1TB), 1024MB (< 5TB), 2048MB (≥ 5TB)
- Support for object size ranges with stepping
- Full debug output and detailed progress reporting
- Automatic cleanup of test objects

```bash
# Test multipart uploads for objects ranging from 100MB to 1GB with 100MB steps
scripts/max_object_multipart_probe.sh --bucket test-bucket --min 100mb --max 1gb --step 100mb --debug

# Test with cleanup
scripts/max_object_multipart_probe.sh --bucket test-bucket --min 500mb --max 5gb --step 500mb --cleanup
```

#### `scripts/multipart_upload_check.sh`
Single object multipart upload verification with checksum validation:
- Creates and uploads a single object using multipart upload
- Verifies upload correctness through two verification modes:
  - **Hybrid (default)**: Fast verification comparing original MD5 with S3's ETag (no download)
  - **Full verification**: Downloads object and validates MD5 matches original (thorough end-to-end check)
- Optional automatic cleanup
- Flexible part sizing configuration

```bash
# Upload 500MB object with 64MB parts (hybrid verification)
scripts/multipart_upload_check.sh --bucket test-bucket --size 500mb --part 64mb

# Full verification mode with cleanup
scripts/multipart_upload_check.sh --bucket test-bucket --size 1gb --part 128mb --verify-full --cleanup

# Debug mode to see all AWS CLI commands
scripts/multipart_upload_check.sh --bucket test-bucket --size 100mb --part 64mb --debug
```

### Script Prerequisites
- AWS CLI installed and configured
- S3-compatible endpoint access with valid credentials
- Sufficient storage space for test objects
- Network connectivity to the S3 endpoint

## Python Framework: Command Line Options

### Basic Usage
```bash
python main.py [options]
```

### Configuration Options
- `--config FILE`: Specify configuration file (default: config.ini)
- `--generate-config`: Generate configuration template
- `--overwrite-config`: Overwrite existing configuration when generating template

### Check Execution
- `--scope SCOPES`: Comma-separated list of check scopes to run
- `--list-scopes`: List available check scopes

### Logging Options
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `--log-file FILE`: Specify log file path
- `--no-console`: Disable console output (log to file only)
- `--quiet`: Minimize output (show only summary)

### Output Options
- `--export-results FILE`: Export results to file (JSON or text)
- `--export-format FORMAT`: Force export format (json, text)

## Example Usage

### Basic Compatibility Check
```bash
# Run all checks with standard output
python main.py --scope all
```

### Focused Testing
```bash
# Test only bucket and object operations
python main.py --scope buckets,objects

# Test advanced features
python main.py --scope versioning,tagging,attributes

# Test error handling
python main.py --scope error_conditions
```

### Debugging and Analysis
```bash
# Enable debug logging for detailed information
python main.py --scope all --log-level debug

# Export detailed results for analysis
python main.py --scope all --export-results detailed_results.json

# Quiet mode for automated testing
python main.py --scope all --quiet --export-results results.json
```

### Enhanced Protocol Validation
For maximum S3 API validation confidence, enable enhanced logging modes:

```bash
# Enable raw HTTP request/response logging for protocol-level debugging
# Edit config.ini: enable_raw_logging = true
python main.py --scope buckets --log-level debug

# Enable full boto3/botocore debug logging (very verbose)
# Edit config.ini: enable_boto_debug = true
python main.py --scope objects --log-level debug

# Maximum logging for protocol compliance verification
# Edit config.ini: enable_raw_logging = true, enable_boto_debug = true
python main.py --scope all --log-level debug --log-file protocol_debug.log
```

**Enhanced Logging Output Examples:**

Raw HTTP Request/Response Logging:
```
RAW REQUEST - Method: PUT
RAW REQUEST - URI: /test-bucket/test-object
RAW REQUEST - Headers: {'Content-Type': 'application/octet-stream', 'Authorization': '***MASKED***'}
RAW RESPONSE - Status: 200
RAW RESPONSE - Headers: {'etag': '"d41d8cd98f00b204e9800998ecf8427e"', 'server': 'MinIO'}
S3 Response Fields: {'ETag': '"d41d8cd98f00b204e9800998ecf8427e"', 'ContentLength': 1024}
```

boto3 Debug Logging:
```
botocore.auth [DEBUG] Calculating signature using v4 auth.
botocore.endpoint [DEBUG] Making request for OperationModel(name=PutObject)
botocore.parsers [DEBUG] Response headers: {'ETag': '"..."', 'Content-Length': '1024'}
```

## Understanding Results

### Console Output
The framework provides real-time feedback during test execution:

```
✓ bucket_creation: Successfully created bucket 'test-bucket-1234567890'
✓ bucket_listing: Successfully listed 1 buckets
✗ bucket_versioning: Failed to enable versioning, status: None
```

### Summary Report
After completion, a comprehensive summary is displayed:

```
==========================================
S3 COMPATIBILITY CHECK SUMMARY
==========================================

Total Categories: 5
Total Checks: 45
Passed: 42
Failed: 3
Success Rate: 93.3%
Duration: 12.34s

CATEGORY RESULTS:
✓ buckets: 8/8 (100.0%) [2.1s]
✓ objects: 12/12 (100.0%) [3.2s]
✗ versioning: 3/5 (60.0%) [1.8s]
✓ tagging: 6/6 (100.0%) [2.1s]
✓ range_requests: 13/14 (92.9%) [3.1s]
```

### Log Files
Detailed logs are written to the specified log file with timestamps and full error details. Log files contain plain text without color codes, while console output includes colors for better readability:

```
2024-01-15 10:30:15 - s3_checker.buckets - INFO - Starting bucket compatibility checks...
2024-01-15 10:30:15 - s3_checker.buckets - INFO - ✓ bucket_creation: Successfully created bucket
2024-01-15 10:30:16 - s3_checker.versioning - ERROR - ✗ bucket_versioning: Failed versioning operations: InvalidRequest
2024-01-15 10:30:17 - s3_checker.s3_client - DEBUG - S3 Request: put_object with params: {'Bucket': 'test-bucket', 'Key': 'test-object'}
```

**Logging Features:**
- **Scope-specific loggers**: Each check category has its own logger name (e.g., `s3_checker.buckets`, `s3_checker.objects`)
- **Clean file output**: Log files contain no ANSI color codes, ensuring compatibility with log analysis tools
- **Colored console**: Console output includes colors for improved readability during interactive use
- **Two detail levels**: Standard (INFO) shows test results, Debug (DEBUG) includes detailed request/response information

## S3 API Compatibility Extension Options

The framework can be extended to test additional S3 API features and edge cases for comprehensive compatibility validation:

### Advanced S3 API Features
- **S3 Select**: SQL query execution on objects (CSV, JSON, Parquet)
- **Object Lock**: Write-once-read-many (WORM) functionality and retention policies
- **Cross-Origin Resource Sharing (CORS)**: Browser-based access configuration
- **Website Hosting**: Static website configuration and error documents
- **Notification Events**: Bucket event notifications and webhooks
- **Inventory Reports**: Automated bucket inventory generation
- **Metrics and Analytics**: CloudWatch-style metrics collection

### Storage Classes and Lifecycle
- **Storage Class Transitions**: Standard, IA, Glacier, Deep Archive
- **Lifecycle Policies**: Automated object transitions and expiration
- **Intelligent Tiering**: Automatic cost optimization features
- **Restoration Operations**: Object retrieval from archival storage

### Advanced Security Features
- **Server-Side Encryption**: SSE-S3, SSE-KMS, SSE-C encryption modes
- **Bucket Policies**: Complex access control policy validation
- **Access Control Lists (ACLs)**: Fine-grained permission testing
- **Pre-signed URLs**: Temporary access URL generation and validation
- **Request Payment**: Requester-pays bucket configuration

### Multi-Region and Replication
- **Cross-Region Replication (CRR)**: Automatic object replication
- **Same-Region Replication (SRR)**: In-region redundancy
- **Transfer Acceleration**: CloudFront-accelerated uploads
- **Multi-Region Access Points**: Global endpoint management

### Enterprise Features
- **Access Points**: VPC-specific access control
- **S3 Batch Operations**: Large-scale object processing
- **Directory Buckets**: Hierarchical namespace support
- **Express One Zone**: High-performance storage class

### API Edge Cases and Compliance
- **HTTP/2 Protocol Support**: Modern protocol compatibility
- **IPv6 Connectivity**: Dual-stack network support
- **Large Object Handling**: >5TB objects and extreme multipart scenarios
- **Rate Limiting**: Throttling behavior and retry mechanisms
- **Error Code Compliance**: Complete AWS error response validation
- **Header Validation**: S3-specific HTTP headers and metadata limits

## Extending the Framework

### Adding New Check Categories

1. Create a new check module (e.g., `check_custom.py`):

```python
from base_check import BaseCheck, CheckResult
from s3_client import S3ClientError

class CustomChecks(BaseCheck):
    def run_checks(self):
        # Implement your custom checks
        self._check_custom_operation()
        return self.results
    
    def _check_custom_operation(self):
        # Your test implementation
        pass
```

2. Register the new check in `check_runner.py`:

```python
self.available_checks = {
    # ... existing checks ...
    'custom': 'check_custom.CustomChecks'
}
```

3. Enable in configuration:

```ini
[checks]
custom = true
```

### Customizing Test Data

Modify the `[test_data]` section in your configuration file to adjust:
- File sizes for testing
- Test content patterns
- Multipart upload chunk sizes
- Cleanup behavior

### Adding Custom Validation

Extend the base check class to add custom validation logic:

```python
class MyCustomChecks(BaseCheck):
    def _validate_custom_response(self, response):
        # Custom validation logic
        if self._my_custom_condition(response):
            return True, "Custom validation passed"
        return False, "Custom validation failed"
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Verify your S3 endpoint URL is correct and accessible
   - Check firewall settings and network connectivity
   - Ensure the S3 service is running

2. **Authentication Errors**
   - Verify access key and secret key are correct
   - Check if your S3 implementation requires authentication
   - Some test implementations use dummy credentials

3. **SSL/TLS Errors**
   - Set `verify_ssl = false` for self-signed certificates
   - Use `http://` instead of `https://` for non-SSL endpoints

4. **Permission Errors**
   - Ensure your credentials have sufficient permissions
   - Some S3 implementations may not support all operations

5. **Test Failures**
   - Review the detailed logs for specific error messages
   - Some advanced features may not be implemented in your S3 storage
   - Check if your implementation follows S3 API specifications exactly

### Debug Mode

Enable debug logging for maximum detail:

```bash
python main.py --scope all --log-level debug --log-file debug.log
```

This will provide:
- Detailed HTTP request/response information
- Timing data for each operation
- Full error stack traces
- Configuration validation details

### Cleanup Issues

If automatic cleanup fails:

```bash
# Manually clean up test resources using AWS CLI
aws --endpoint-url http://your-endpoint s3 ls
aws --endpoint-url http://your-endpoint s3 rm s3://test-bucket --recursive
aws --endpoint-url http://your-endpoint s3 rb s3://test-bucket
```

## Performance Considerations

- Tests are designed to be run sequentially for reliability
- Large file tests may take significant time depending on your storage performance
- Network latency affects test duration, especially for many small operations
- Consider adjusting timeouts in configuration for slow storage systems

## Security Notes

- This tool is designed for testing environments, not production systems
- Test credentials should be limited to test environments only
- The framework generates temporary test data that is automatically cleaned up
- Logs may contain sensitive information; protect log files appropriately

## Contributing

To contribute new test categories or improvements:

1. Follow the existing code structure and naming conventions
2. Add comprehensive error handling and logging
3. Include both positive and negative test cases
4. Update documentation for new features
5. Test thoroughly against multiple S3 implementations

## Support

For issues, questions, or contributions:
- Review the troubleshooting section above
- Check log files for detailed error information
- Ensure your S3 implementation follows standard S3 API conventions
- Consider that some advanced features may not be supported by all S3-compatible storage systems