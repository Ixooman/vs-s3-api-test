# Base S3 Compatibility Check Script

This document describes the `base_check.sh` script - a simple bash script for testing basic S3 API compatibility using AWS CLI commands.

## Overview

The `base_check.sh` script is based on the original `S3_compatibility.txt` file and provides a comprehensive test of essential S3 operations. It executes AWS CLI commands sequentially to validate S3 API compatibility without the complexity of multipart upload operations.

## Features

### Tested Operations
1. **Bucket Operations**
   - Bucket creation and listing
   - Bucket deletion (empty buckets)
   - Bucket head operations

2. **Object Operations**
   - Object upload (put-object)
   - Object download (get-object)
   - Object copy operations
   - Object deletion
   - Object head operations (metadata retrieval)

3. **Directory Synchronization**
   - AWS S3 sync functionality
   - Multiple file upload

4. **Object Lifecycle Management**
   - Complete put/get/copy/delete workflow
   - Content verification

5. **Object Listing**
   - list-objects (v1 API)
   - list-objects-v2 (v2 API)

6. **Versioning**
   - Enable bucket versioning
   - Create multiple object versions
   - List object versions
   - Delete operations with versioning

7. **Tagging**
   - Bucket tagging (put/get/delete)
   - Object tagging (put/get/update/delete)

8. **Object Attributes** (Basic)
   - Get object ETag
   - Get object size and storage class (basic attributes only)

## Usage

### Basic Usage
```bash
./scripts/base_check.sh
```

### Custom Endpoint
```bash
./scripts/base_check.sh http://your-s3-endpoint:port
```

### Examples
```bash
# Test against local MinIO
./scripts/base_check.sh http://192.168.99.5:9000

# Test against default endpoint
./scripts/base_check.sh http://192.168.10.81

# Test with HTTPS endpoint
./scripts/base_check.sh https://s3.example.com
```

## Prerequisites

### Required Tools
- **AWS CLI**: Installed and accessible in PATH
- **Bash**: Version 4+ recommended
- **Standard Unix Tools**: rm, mkdir, touch, cat, echo

### AWS CLI Configuration
The script requires AWS CLI to be configured with:
- Access Key ID
- Secret Access Key
- Default region (any value works for most S3-compatible systems)

Configure using:
```bash
aws configure set aws_access_key_id YOUR_ACCESS_KEY
aws configure set aws_secret_access_key YOUR_SECRET_KEY
aws configure set default.region us-east-1
aws configure set default.output json
```

### Network Requirements
- Network connectivity to the S3 endpoint
- Appropriate firewall rules if testing against remote endpoints

## Script Behavior

### Success Indicators
- ✅ HTTP 200/204 responses for successful operations
- ✅ Proper JSON responses with expected fields (ETag, ContentLength, etc.)
- ✅ Content verification (downloaded content matches uploaded content)
- ✅ Object counts and listings match expectations

### Error Handling
- All operations use `--no-verify-ssl` flag for self-signed certificates
- Commands continue on errors during cleanup (using `|| true`)
- Detailed output shows both successful operations and error messages
- Script exits immediately on any test failure (using `set -e`)

### Automatic Cleanup
The script includes comprehensive cleanup functionality:
- Removes all created objects
- Deletes all created buckets
- Cleans up local temporary files
- Runs automatically on script exit (success or failure)

## Test Workflow

### 1. Bucket Creation and Listing
- Creates a test bucket with unique name
- Lists all buckets to verify creation
- Validates bucket appears in listing

### 2. Object Creation
- Uploads a simple text file
- Retrieves object metadata using head-object
- Verifies object exists and has correct properties

### 3. Directory Sync
- Creates local directory with multiple files
- Syncs directory to S3 using `aws s3 sync`
- Lists objects to verify all files uploaded

### 4. Object Lifecycle
- Uploads object with content
- Downloads object and verifies content
- Copies object to new key
- Downloads copy and verifies content
- Deletes original object
- Verifies deletion (head-object should fail)

### 5. Object Listing
- Tests both list-objects (v1) and list-objects-v2 APIs
- Verifies object counts and metadata

### 6. Versioning
- Creates versioned bucket
- Enables versioning
- Creates multiple versions of same object
- Lists versions to verify version creation
- Deletes current version (creates delete marker)
- Verifies version listing shows delete marker

### 7. Bucket Tagging
- Creates bucket for tagging tests
- Sets bucket tags with key-value pairs
- Retrieves and verifies tags
- Deletes tags and verifies removal

### 8. Object Tagging
- Uploads object for tagging tests
- Sets object tags
- Retrieves and verifies tags
- Updates tags with new values
- Deletes tags and verifies removal

### 9. Object Attributes (Basic)
- Creates bucket and object for attributes testing
- Tests ETag retrieval
- Tests object size and storage class retrieval

### 10. Bucket Deletion
- Creates temporary bucket
- Verifies bucket exists
- Deletes empty bucket
- Verifies deletion

## Output Format

### Console Output
The script provides real-time output showing:
- Section headers for each test category
- AWS CLI command responses (JSON format)
- Content verification results
- Success/failure messages

### Example Output Structure
```
=== S3 Basic Compatibility Test ===
Endpoint: http://192.168.99.5:9000
======================================

=== 1. Bucket Creation and Listing ===
{
    "Location": "/new-bucket"
}
{
    "Buckets": [...]
}

=== 2. Object Creation ===
{
    "ETag": "\"d8e8fca2dc0f896fd7cb4cb0031ba249\"",
    "ChecksumCRC32": "O7k1xg=="
}
...

=== Cleanup ===
=== Test Completed Successfully! ===
```

## Limitations

### 1. Multipart Upload Exclusion
- **Not Tested**: All multipart upload operations are excluded
- **Reason**: Complexity of manual ETag handling and JSON file creation
- **Impact**: Large file uploads (>5GB) and multipart-specific features not validated

### 2. Versioned Object Cleanup
- **Issue**: Version IDs are generated dynamically and change with each script run
- **Impact**: Some versioned objects may remain after script completion
- **Workaround**: Manual cleanup may be required for versioned buckets
- **Commands**: The script attempts multiple cleanup approaches but may not remove all versions

### 3. Object Attributes Limitations
- **Issue**: Advanced object attributes (ObjectParts, multipart attributes) may fail
- **Reason**: Not all S3-compatible systems support full object attributes API
- **Impact**: Some attribute tests may show errors for certain implementations

### 4. Error Handling
- **Philosophy**: Script continues on expected failures (like checking deleted objects)
- **Impact**: Some "failures" in output are actually expected behavior
- **Solution**: Review context - failures during cleanup or negative tests are normal

### 5. Endpoint-Specific Limitations
- **SSL Verification**: Disabled (`--no-verify-ssl`) for self-signed certificates
- **Authentication**: Requires pre-configured AWS CLI credentials
- **Network**: No automatic endpoint discovery or validation

### 6. Test Data Limitations
- **File Sizes**: Only tests small files (under 1MB)
- **Content Types**: Limited to text files and binary data
- **Edge Cases**: Does not test special characters in object names or extreme scenarios

### 7. Concurrency
- **Sequential Only**: All operations run sequentially, no parallel testing
- **Performance**: Does not test concurrent access or high-load scenarios

## Troubleshooting

### Common Issues

#### 1. AWS CLI Not Found
```bash
aws: command not found
```
**Solution**: Install AWS CLI using `pip install awscli`

#### 2. Authentication Errors
```bash
An error occurred (InvalidAccessKeyId)
```
**Solution**: Configure AWS credentials using `aws configure`

#### 3. Connection Refused
```bash
Could not connect to the endpoint URL
```
**Solution**: Verify endpoint URL and network connectivity

#### 4. Bucket Not Empty Errors
```bash
BucketNotEmpty: The bucket you tried to delete is not empty
```
**Solution**: This is expected for versioned buckets; manual cleanup may be needed

#### 5. Object Attributes Errors
```bash
InvalidArgument: Invalid attribute name specified
```
**Solution**: Expected behavior for S3 implementations with limited attributes support

### Debug Mode
For detailed debugging, remove output redirection:
```bash
# Remove 2>/dev/null from cleanup commands to see detailed errors
# Edit the script and remove || true to stop on cleanup errors
```

### Manual Cleanup
If script leaves orphaned resources:
```bash
# List remaining buckets
aws --no-verify-ssl s3api list-buckets --endpoint-url YOUR_ENDPOINT

# Force delete versioned bucket
aws --no-verify-ssl s3 rb s3://bucket-name --force --endpoint-url YOUR_ENDPOINT

# Delete specific object versions (get version IDs from list-object-versions)
aws --no-verify-ssl s3api delete-object --bucket BUCKET --key KEY --version-id VERSION_ID --endpoint-url YOUR_ENDPOINT
```

## Compatibility

### Tested Implementations
- ✅ **MinIO**: Full compatibility, minor object attributes limitations
- ✅ **AWS S3**: Reference implementation (when accessible)
- ⚠️ **Other S3-compatible systems**: May have varying feature support

### Expected Behavior
- **High Compatibility**: Core operations (buckets, objects, listing) should work
- **Medium Compatibility**: Versioning and tagging should work on most systems
- **Variable Compatibility**: Object attributes support varies by implementation

## Performance Considerations

- **Test Duration**: Typically 30-60 seconds depending on network latency
- **Network Usage**: Minimal data transfer (few KB total)
- **Resource Usage**: Creates 5 buckets and ~10 objects during testing
- **Cleanup Time**: Additional 10-30 seconds for cleanup operations

## Security Notes

- Uses `--no-verify-ssl` flag (suitable for testing environments only)
- Requires valid S3 credentials with full bucket/object permissions
- Creates temporary test data that is automatically cleaned up
- Does not validate or sanitize endpoint URLs

## Future Improvements

### Potential Enhancements
1. **Better Version Cleanup**: Dynamic version ID detection and cleanup
2. **Parallel Testing**: Concurrent operations for performance testing
3. **Advanced Attributes**: More comprehensive object attributes testing
4. **Error Classification**: Distinguish between expected and unexpected failures
5. **Configuration File**: External configuration for endpoints and parameters
6. **JSON Output**: Machine-readable test results
7. **Selective Testing**: Command-line options to run specific test categories

### Not Planned
- **Multipart Upload**: Intentionally excluded for simplicity
- **Complex Authentication**: OAuth, IAM roles, etc.
- **Performance Benchmarking**: Focus remains on compatibility, not performance