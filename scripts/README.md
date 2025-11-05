# S3 Testing Scripts

This directory contains specialized shell-based testing scripts for S3 API compatibility validation. These scripts provide targeted testing capabilities for specific S3 features and are designed for quick diagnostic checks, performance testing, and large object upload validation.

## Overview

All scripts follow consistent design patterns:
- Color-coded output (RED for errors, GREEN for success, BLUE for info, YELLOW for warnings)
- Comprehensive error handling and validation
- Automatic resource cleanup on exit
- Support for custom S3 endpoints via `--endpoint` flag
- Optional debug mode with `--debug` flag for detailed AWS CLI output
- Size parsing with support for mb, gb, tb units

## Script Categories

### Connectivity and Basic Testing

#### `check_connection.sh`
Basic S3 endpoint connectivity test.

**Purpose**: Quickly verify that your S3 endpoint is accessible and responding to API requests.

**Usage**:
```bash
./check_connection.sh [endpoint-url]
```

**Example**:
```bash
./check_connection.sh http://192.168.10.81
```

**What it does**:
- Tests basic connectivity to S3 endpoint
- Lists all available buckets
- Verifies AWS CLI configuration

---

#### `base_check.sh`
Comprehensive compatibility test covering core S3 operations (excluding multipart uploads).

**Purpose**: Test basic S3 functionality including bucket operations, object lifecycle management, versioning, and tagging.

**Usage**:
```bash
./base_check.sh [endpoint-url]
```

**Example**:
```bash
./base_check.sh http://192.168.10.81
```

**What it tests**:
- Bucket creation, listing, and deletion
- Object upload, download, copy, and delete
- Object versioning (enable, disable, version-specific operations)
- Bucket and object tagging
- Automatic cleanup of test resources

**Note**: This script is based on the legacy S3_compatibility.txt test suite but excludes multipart upload tests.

---

#### `spec_methods_tester.sh`
Comprehensive test of specific S3 API methods.

**Purpose**: Systematically test a wide range of S3 API methods to verify API compatibility.

**Tested S3 API Methods**:

**Bucket Operations:**
- CreateBucket
- DeleteBucket
- HeadBucket
- ListBuckets

**Bucket Versioning:**
- GetBucketVersioning
- PutBucketVersioning

**Bucket Tagging:**
- DeleteBucketTagging
- GetBucketTagging
- PutBucketTagging

**Object Operations:**
- CopyObject
- DeleteObject
- DeleteObjects (bulk delete)
- GetObject
- HeadObject
- PutObject

**Object Tagging:**
- DeleteObjectTagging
- GetObjectTagging
- PutObjectTagging

**Multipart Upload Operations:**
- AbortMultipartUpload
- CompleteMultipartUpload
- CreateMultipartUpload
- ListMultipartUploads
- ListParts
- UploadPart

**Additional Features:**
- Object versioning operations
- File integrity verification
- Test timing and statistics

---

### Multipart Upload Testing

#### `test_multipart.sh`
Quick diagnostic to verify multipart upload support.

**Purpose**: Fast check to determine if the S3 endpoint supports multipart upload operations.

**Usage**:
```bash
./test_multipart.sh --bucket <bucket-name> --endpoint <endpoint-url>
```

**Example**:
```bash
./test_multipart.sh --bucket test-bucket --endpoint http://192.168.10.81
```

**What it does**:
- Creates a small test object using multipart upload
- Verifies multipart workflow (initiate → upload → complete)
- Reports success or failure
- Automatic cleanup

**When to use**: Before running comprehensive multipart tests to ensure basic support exists.

---

#### `multipart_upload_check.sh`
Single object multipart upload verification with checksum validation.

**Purpose**: Upload a single object using multipart upload and verify data integrity through MD5 checksum validation.

**Key Features**:
- Two verification modes:
  - **Hybrid (default)**: Fast verification comparing original MD5 with S3's ETag without downloading
  - **Full verification**: Downloads object and validates MD5 matches original for thorough end-to-end check
- Flexible part size configuration
- Optional automatic cleanup
- Detailed progress reporting

**Usage**:
```bash
./multipart_upload_check.sh --bucket <bucket-name> --size <object-size> --part <part-size> [options]
```

**Options**:
- `--bucket <name>`: Target bucket name (required)
- `--size <size>`: Object size (e.g., 100mb, 1gb, 5tb)
- `--part <size>`: Part size for multipart upload (e.g., 64mb, 128mb)
- `--endpoint <url>`: S3 endpoint URL (default: http://192.168.10.81)
- `--verify-full`: Enable full verification mode (download and verify)
- `--cleanup`: Automatically delete test object after verification
- `--debug`: Show detailed AWS CLI command output

**Examples**:

Upload 500MB object with 64MB parts (hybrid verification):
```bash
./multipart_upload_check.sh --bucket test-bucket --size 500mb --part 64mb
```

Full verification mode with cleanup:
```bash
./multipart_upload_check.sh --bucket test-bucket --size 1gb --part 128mb --verify-full --cleanup
```

Debug mode to see all AWS CLI commands:
```bash
./multipart_upload_check.sh --bucket test-bucket --size 100mb --part 64mb --debug
```

**Verification Modes**:

- **Hybrid Mode** (default):
  - Calculates MD5 of original data
  - Compares with S3's ETag (for single-part or AWS-calculated multipart ETags)
  - Fast: no download required
  - Best for: Quick validation, testing many objects

- **Full Verification Mode** (`--verify-full`):
  - Downloads object from S3
  - Calculates MD5 of downloaded data
  - Compares with original MD5
  - Thorough: complete end-to-end validation
  - Best for: Critical data validation, troubleshooting

---

#### `max_object_multipart_probe.sh`
Comprehensive multipart upload testing with dynamic part sizing for large objects.

**Purpose**: Test multipart uploads across a range of object sizes to find maximum reliable object size and validate dynamic part sizing.

**Key Features**:
- Tests object size ranges from 100MB to multiple terabytes
- Dynamic part sizing based on object size:
  - 64MB for objects < 1GB
  - 128MB for objects < 10GB
  - 256MB for objects < 100GB
  - 512MB for objects < 1TB
  - 1024MB for objects < 5TB
  - 2048MB for objects ≥ 5TB
- Configurable size ranges with stepping
- Full debug output and detailed progress reporting
- Automatic cleanup option

**Usage**:
```bash
./max_object_multipart_probe.sh --bucket <bucket-name> [options]
```

**Options**:
- `--bucket <name>`: Target bucket name (required)
- `--min <size>`: Minimum object size (default: 100mb)
- `--max <size>`: Maximum object size (default: 1gb)
- `--step <size>`: Size increment between tests (default: 100mb)
- `--endpoint <url>`: S3 endpoint URL (default: http://192.168.10.81)
- `--cleanup`: Delete test objects after completion
- `--debug`: Show detailed AWS CLI command output

**Examples**:

Test multipart uploads from 100MB to 1GB with 100MB steps:
```bash
./max_object_multipart_probe.sh --bucket test-bucket --min 100mb --max 1gb --step 100mb --debug
```

Test large objects with cleanup:
```bash
./max_object_multipart_probe.sh --bucket test-bucket --min 500mb --max 5gb --step 500mb --cleanup
```

Test terabyte-scale objects:
```bash
./max_object_multipart_probe.sh --bucket test-bucket --min 1tb --max 5tb --step 1tb --debug
```

**Output**: Detailed report showing success/failure for each object size tested, with timing information.

---

#### `max_object_size_probe.sh`
Tests maximum single-put object size capabilities.

**Purpose**: Determine the maximum object size that can be uploaded in a single PUT operation (non-multipart).

**Usage**:
```bash
./max_object_size_probe.sh --bucket <bucket-name> [options]
```

**What it does**:
- Tests progressively larger object sizes
- Identifies maximum supported single-put object size
- Reports size limitations

**Note**: Most S3 implementations limit single-put objects to 5GB, requiring multipart upload for larger objects.

---

### Utility Scripts

#### `cleanup_all.sh`
Removes ALL buckets and objects from the specified S3 endpoint.

**Purpose**: Complete cleanup of test resources when needed.

**Usage**:
```bash
./cleanup_all.sh [endpoint-url]
```

**Example**:
```bash
./cleanup_all.sh http://192.168.10.81
```

**WARNING**: This script will delete ALL buckets and their contents on the specified endpoint. It includes a 5-second countdown before execution to allow cancellation.

**What it does**:
- Lists all buckets on the endpoint
- Deletes all objects (including versioned objects and delete markers)
- Removes all buckets
- Handles both regular and versioned buckets

**When to use**:
- After testing is complete
- To clean up a test environment
- Before running fresh test suites

---

#### `base_check.md`
Documentation file containing additional information about the base_check.sh script.

---

## Common Usage Patterns

### Quick Connectivity Test
```bash
# Verify endpoint is accessible
./check_connection.sh http://192.168.10.81
```

### Basic Compatibility Test
```bash
# Test core S3 operations
./base_check.sh http://192.168.10.81
```

### Multipart Upload Validation
```bash
# Quick check: does multipart work?
./test_multipart.sh --bucket test-bucket --endpoint http://192.168.10.81

# Upload and verify single object with multipart
./multipart_upload_check.sh --bucket test-bucket --size 1gb --part 128mb --verify-full

# Test range of object sizes
./max_object_multipart_probe.sh --bucket test-bucket --min 100mb --max 10gb --step 1gb
```

### Complete API Method Testing
```bash
# Test all supported S3 API methods
./spec_methods_tester.sh
```

### Cleanup After Testing
```bash
# Remove all test resources
./cleanup_all.sh http://192.168.10.81
```

## Prerequisites

All scripts require:
- AWS CLI installed and configured
- Access to S3-compatible endpoint
- Valid credentials (access key and secret key)
- Network connectivity to the S3 endpoint
- Sufficient storage space for test objects

## Configuration

Scripts use the following default configuration:
- Default endpoint: `http://192.168.10.81`
- AWS CLI flags: `--no-verify-ssl` (for self-signed certificates)
- Retry count: 3 attempts for failed operations
- Timeout: Standard AWS CLI timeouts

## Error Handling

All scripts include:
- Automatic retry logic for transient failures
- Cleanup handlers to prevent resource leaks (trap on EXIT)
- Detailed error messages with context
- Graceful degradation for partial failures

## Size Format

Scripts accept size specifications in the following formats:
- `mb` or `MB`: Megabytes (e.g., 100mb = 104,857,600 bytes)
- `gb` or `GB`: Gigabytes (e.g., 1gb = 1,073,741,824 bytes)
- `tb` or `TB`: Terabytes (e.g., 5tb = 5,497,558,138,880 bytes)
- Raw bytes: Numbers without units (e.g., 1048576 = 1MB)

## Performance Considerations

- **Small objects** (< 100MB): Use regular PUT operations for better performance
- **Medium objects** (100MB - 1GB): Multipart upload with 64-128MB parts
- **Large objects** (1GB - 100GB): Multipart upload with 128-256MB parts
- **Very large objects** (> 100GB): Multipart upload with 512MB-2048MB parts
- Network bandwidth and latency significantly affect upload times
- Parallel part uploads (not implemented in these scripts) can improve performance

## Troubleshooting

### Connection Issues
- Verify endpoint URL is correct and accessible
- Check firewall settings and network connectivity
- Ensure S3 service is running

### Authentication Errors
- Verify AWS CLI is configured with valid credentials
- Check access key and secret key are correct
- Some test implementations use dummy credentials

### SSL/TLS Errors
- Scripts use `--no-verify-ssl` flag for self-signed certificates
- Use `http://` endpoints for non-SSL connections

### Multipart Upload Failures
- Verify endpoint supports multipart uploads
- Check part size meets minimum requirements (typically 5MB)
- Ensure sufficient storage space available
- Some implementations have maximum part count limits (typically 10,000 parts)

### Cleanup Failures
- May occur if objects are locked or versioned
- Try running cleanup_all.sh for comprehensive cleanup
- Manual cleanup via AWS CLI may be necessary for complex scenarios

## Best Practices

1. **Start with connectivity test**: Always run `check_connection.sh` first
2. **Test incrementally**: Begin with small objects, increase size gradually
3. **Use debug mode**: Enable `--debug` when troubleshooting issues
4. **Clean up regularly**: Run cleanup scripts to avoid storage waste
5. **Monitor resources**: Watch disk space and network usage during large uploads
6. **Test in isolation**: Use dedicated test buckets to avoid affecting production data
7. **Verify data integrity**: Use full verification mode for critical uploads
8. **Document results**: Save script output for compliance and debugging

## Integration with Python Framework

These scripts complement the main Python-based testing framework:
- Use Python framework for comprehensive automated testing
- Use shell scripts for targeted testing and quick diagnostics
- Shell scripts are ideal for performance testing and large object handling
- Python framework provides better reporting and integration capabilities

For comprehensive S3 compatibility testing, consider using both:
1. Run Python framework for full API coverage: `python main.py --scope all`
2. Use shell scripts for specific scenarios: large uploads, performance testing, quick checks

## Additional Resources

- Main project README: [../README.md](../README.md)
- Python framework documentation: See main README.md
- S3 API reference: AWS S3 API documentation
- Legacy test suite: [../S3_compatibility.txt](../S3_compatibility.txt)