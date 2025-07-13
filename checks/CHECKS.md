# S3 Compatibility Checks Reference

This document provides a comprehensive list of all checks performed by the S3 Compatibility Checker, organized by scope and in execution order.

## Buckets

### bucket_creation (Positive)
- **S3 Operation**: `create_bucket`
- **Parameters**: `Bucket=<generated-unique-name>`
- **Expected**: HTTP 200, response contains bucket location
- **Validates**: Basic bucket creation functionality with valid names

### bucket_creation_invalid_name (Negative)
- **S3 Operation**: `create_bucket`
- **Parameters**: `Bucket=Invalid_Bucket_Name_With_Underscores_And_Capitals`
- **Expected**: HTTP 400, error code `InvalidBucketName` or `BucketAlreadyExists`
- **Validates**: Proper rejection of S3 naming rule violations

### bucket_listing (Positive)
- **S3 Operation**: `list_buckets`
- **Parameters**: None
- **Expected**: HTTP 200, response contains `Buckets` array with `Name` and `CreationDate` fields
- **Validates**: Bucket enumeration and response structure compliance

### bucket_listing_structure (Positive)
- **S3 Operation**: `list_buckets` (validation step)
- **Parameters**: None
- **Expected**: Each bucket object contains required `Name` and `CreationDate` fields
- **Validates**: S3 API response structure compliance

### bucket_head_existing (Positive)
- **S3 Operation**: `head_bucket`
- **Parameters**: `Bucket=<existing-test-bucket>`
- **Expected**: HTTP 200
- **Validates**: Bucket existence verification

### bucket_head_nonexistent (Negative)
- **S3 Operation**: `head_bucket`
- **Parameters**: `Bucket=<nonexistent-bucket-name>`
- **Expected**: HTTP 404
- **Validates**: Proper error response for missing buckets

### bucket_versioning_default (Positive)
- **S3 Operation**: `get_bucket_versioning`
- **Parameters**: `Bucket=<test-bucket>`
- **Expected**: HTTP 200, status `Disabled` or missing `Status` field
- **Validates**: Default versioning state for new buckets

### bucket_versioning_enable (Positive)
- **S3 Operation**: `put_bucket_versioning`
- **Parameters**: `Bucket=<test-bucket>`, `VersioningConfiguration={'Status': 'Enabled'}`
- **Expected**: HTTP 200, subsequent get_bucket_versioning returns `Status=Enabled`
- **Validates**: Bucket versioning enablement functionality

### bucket_tagging_put_get (Positive)
- **S3 Operation**: `put_bucket_tagging`, `get_bucket_tagging`
- **Parameters**: `Bucket=<test-bucket>`, `Tagging={'TagSet': [{'Key': 'Environment', 'Value': 'Test'}, ...]}`
- **Expected**: HTTP 200, retrieved tags match set tags
- **Validates**: Bucket tagging set/get operations

### bucket_tagging_delete (Positive)
- **S3 Operation**: `delete_bucket_tagging`, `get_bucket_tagging`
- **Parameters**: `Bucket=<test-bucket>`
- **Expected**: HTTP 204 for delete, HTTP 404 for subsequent get or empty TagSet
- **Validates**: Bucket tag deletion functionality

### bucket_deletion_empty (Positive)
- **S3 Operation**: `delete_bucket`
- **Parameters**: `Bucket=<empty-test-bucket>`
- **Expected**: HTTP 204
- **Validates**: Empty bucket deletion

### bucket_deletion_nonexistent (Negative)
- **S3 Operation**: `delete_bucket`
- **Parameters**: `Bucket=<nonexistent-bucket>`
- **Expected**: HTTP 404
- **Validates**: Error handling for deleting non-existent buckets

## Objects

### object_upload_small (Positive)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<unique-key>`, `Body=<1KB-data>`
- **Expected**: HTTP 200, response contains `ETag`
- **Validates**: Small object upload functionality

### object_upload_medium (Positive)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<unique-key>`, `Body=<1MB-data>`, `ContentType=application/octet-stream`
- **Expected**: HTTP 200, response contains `ETag`
- **Validates**: Medium-sized object upload with content type

### object_upload_with_metadata (Positive)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<unique-key>`, `Body=<data>`, `Metadata=<custom-metadata>`, `ContentType=text/plain`
- **Expected**: HTTP 200, response contains `ETag`
- **Validates**: Object upload with custom metadata

### object_download (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<existing-object>`
- **Expected**: HTTP 200, response body matches uploaded data
- **Validates**: Object download and data integrity

### object_download_nonexistent (Negative)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<nonexistent-object>`
- **Expected**: HTTP 404
- **Validates**: Error handling for missing objects

### object_head_operation (Positive)
- **S3 Operation**: `head_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<existing-object>`
- **Expected**: HTTP 200, correct `ContentLength`, `ETag`, `ContentType`, preserved metadata
- **Validates**: Object metadata retrieval without body

### object_copy (Positive)
- **S3 Operation**: `copy_object`
- **Parameters**: `CopySource={'Bucket': <source-bucket>, 'Key': <source-key>}`, `Bucket=<dest-bucket>`, `Key=<dest-key>`
- **Expected**: HTTP 200, `CopyObjectResult` with `ETag`, copied data matches source
- **Validates**: Object copying functionality and data integrity

### object_listing_v2 (Positive)
- **S3 Operation**: `list_objects_v2`
- **Parameters**: `Bucket=<test-bucket>`, `Prefix=<test-prefix>`
- **Expected**: HTTP 200, `Contents` array contains all uploaded objects with prefix
- **Validates**: Object listing with prefix filtering (API v2)

### object_listing_v1 (Positive)
- **S3 Operation**: `list_objects`
- **Parameters**: `Bucket=<test-bucket>`, `Prefix=<test-prefix>`
- **Expected**: HTTP 200, `Contents` array contains all uploaded objects with prefix
- **Validates**: Object listing with prefix filtering (API v1)

### object_tagging_put_get (Positive)
- **S3 Operation**: `put_object_tagging`, `get_object_tagging`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Tagging={'TagSet': [...]}`
- **Expected**: HTTP 200, retrieved tags match set tags
- **Validates**: Object tagging operations

### object_tagging_update (Positive)
- **S3 Operation**: `put_object_tagging`, `get_object_tagging`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Tagging=<new-tagset>`
- **Expected**: HTTP 200, tags replaced with new values
- **Validates**: Object tag replacement/update

### object_tagging_delete (Positive)
- **S3 Operation**: `delete_object_tagging`, `get_object_tagging`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`
- **Expected**: HTTP 204 for delete, HTTP 404 for get or empty TagSet
- **Validates**: Object tag deletion

### object_deletion (Positive)
- **S3 Operation**: `delete_object`, `head_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<existing-object>`
- **Expected**: HTTP 204 for delete, HTTP 404 for subsequent head
- **Validates**: Object deletion and verification

### object_deletion_nonexistent (Positive/Negative)
- **S3 Operation**: `delete_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<nonexistent-object>`
- **Expected**: HTTP 200/204 (idempotent) or HTTP 404 (both acceptable)
- **Validates**: Idempotent delete behavior for missing objects

## Multipart

### multipart_upload_creation (Positive)
- **S3 Operation**: `create_multipart_upload`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<unique-key>`, `ContentType=application/octet-stream`
- **Expected**: HTTP 200, response contains `UploadId`
- **Validates**: Multipart upload initiation

### multipart_part_upload_1 (Positive)
- **S3 Operation**: `upload_part`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `PartNumber=1`, `UploadId=<upload-id>`, `Body=<5MB-chunk>`
- **Expected**: HTTP 200, response contains `ETag`
- **Validates**: First part upload in multipart sequence

### multipart_part_upload_2 (Positive)
- **S3 Operation**: `upload_part`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `PartNumber=2`, `UploadId=<upload-id>`, `Body=<5MB-chunk>`
- **Expected**: HTTP 200, response contains `ETag`
- **Validates**: Second part upload in multipart sequence

### multipart_part_upload_3 (Positive)
- **S3 Operation**: `upload_part`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `PartNumber=3`, `UploadId=<upload-id>`, `Body=<5MB-chunk>`
- **Expected**: HTTP 200, response contains `ETag`
- **Validates**: Third part upload in multipart sequence

### multipart_list_parts (Positive)
- **S3 Operation**: `list_parts`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `UploadId=<upload-id>`
- **Expected**: HTTP 200, `Parts` array contains all uploaded parts with correct `PartNumber` and `ETag`
- **Validates**: Multipart upload part enumeration

### multipart_completion (Positive)
- **S3 Operation**: `complete_multipart_upload`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `UploadId=<upload-id>`, `MultipartUpload={'Parts': [...]}`
- **Expected**: HTTP 200, response contains final `ETag`
- **Validates**: Multipart upload completion

### multipart_completion_verification (Positive)
- **S3 Operation**: `head_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<completed-multipart-object>`
- **Expected**: HTTP 200, `ContentLength` matches sum of all parts
- **Validates**: Completed multipart object integrity

### multipart_abort (Positive)
- **S3 Operation**: `abort_multipart_upload`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `UploadId=<upload-id>`
- **Expected**: HTTP 204
- **Validates**: Multipart upload cancellation

### multipart_abort_verification (Positive)
- **S3 Operation**: `list_parts`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `UploadId=<aborted-upload-id>`
- **Expected**: HTTP 404
- **Validates**: Aborted upload no longer exists

### multipart_list_uploads (Positive)
- **S3 Operation**: `list_multipart_uploads`
- **Parameters**: `Bucket=<test-bucket>`
- **Expected**: HTTP 200, response contains `Uploads` array (may be empty)
- **Validates**: Active multipart upload enumeration

## Versioning

### versioning_default_disabled (Positive)
- **S3 Operation**: `get_bucket_versioning`
- **Parameters**: `Bucket=<test-bucket>`
- **Expected**: HTTP 200, `Status=Disabled` or missing `Status` field
- **Validates**: Default versioning state for new buckets

### versioning_enable (Positive)
- **S3 Operation**: `put_bucket_versioning`, `get_bucket_versioning`
- **Parameters**: `Bucket=<test-bucket>`, `VersioningConfiguration={'Status': 'Enabled'}`
- **Expected**: HTTP 200, subsequent get returns `Status=Enabled`
- **Validates**: Bucket versioning activation

### versioning_create_version_1 (Positive)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<versioned-bucket>`, `Key=<object>`, `Body=<version-1-content>`
- **Expected**: HTTP 200, response contains `VersionId`
- **Validates**: First version creation in versioned bucket

### versioning_create_version_2 (Positive)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<versioned-bucket>`, `Key=<same-object>`, `Body=<version-2-content>`
- **Expected**: HTTP 200, response contains different `VersionId`
- **Validates**: Second version creation for same object key

### versioning_create_version_3 (Positive)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<versioned-bucket>`, `Key=<same-object>`, `Body=<version-3-content>`
- **Expected**: HTTP 200, response contains different `VersionId`
- **Validates**: Third version creation for same object key

### versioning_list_versions (Positive)
- **S3 Operation**: `list_object_versions`
- **Parameters**: `Bucket=<versioned-bucket>`
- **Expected**: HTTP 200, `Versions` array contains all created versions with correct `VersionId`
- **Validates**: Object version enumeration

### versioning_get_version_1 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<versioned-bucket>`, `Key=<object>`, `VersionId=<version-1-id>`
- **Expected**: HTTP 200, body matches version 1 content
- **Validates**: Specific version retrieval by version ID

### versioning_get_version_2 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<versioned-bucket>`, `Key=<object>`, `VersionId=<version-2-id>`
- **Expected**: HTTP 200, body matches version 2 content
- **Validates**: Specific version retrieval by version ID

### versioning_get_version_3 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<versioned-bucket>`, `Key=<object>`, `VersionId=<version-3-id>`
- **Expected**: HTTP 200, body matches version 3 content
- **Validates**: Specific version retrieval by version ID

### versioning_delete_version (Positive)
- **S3 Operation**: `delete_object`
- **Parameters**: `Bucket=<versioned-bucket>`, `Key=<object>`, `VersionId=<specific-version-id>`
- **Expected**: HTTP 204
- **Validates**: Specific version deletion

### versioning_delete_verification (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<versioned-bucket>`, `Key=<object>`, `VersionId=<deleted-version-id>`
- **Expected**: HTTP 404
- **Validates**: Deleted version no longer accessible

## Tagging

### bucket_tagging_put_get (Positive)
- **S3 Operation**: `put_bucket_tagging`, `get_bucket_tagging`
- **Parameters**: `Bucket=<test-bucket>`, `Tagging={'TagSet': [{'Key': 'Environment', 'Value': 'Test'}, ...]}`
- **Expected**: HTTP 200, retrieved tags match set tags exactly
- **Validates**: Bucket tagging set and retrieval operations

### bucket_tagging_delete (Positive)
- **S3 Operation**: `delete_bucket_tagging`, `get_bucket_tagging`
- **Parameters**: `Bucket=<test-bucket>`
- **Expected**: HTTP 204 for delete, HTTP 404 for get or empty TagSet
- **Validates**: Bucket tag deletion and cleanup

### object_tagging_put_get (Positive)
- **S3 Operation**: `put_object_tagging`, `get_object_tagging`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Tagging={'TagSet': [...]}`
- **Expected**: HTTP 200, retrieved tags match set tags exactly
- **Validates**: Object tagging set and retrieval operations

### object_tagging_update (Positive)
- **S3 Operation**: `put_object_tagging`, `get_object_tagging`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Tagging=<replacement-tagset>`
- **Expected**: HTTP 200, old tags completely replaced with new tags
- **Validates**: Object tag replacement (not addition)

### object_tagging_delete (Positive)
- **S3 Operation**: `delete_object_tagging`, `get_object_tagging`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`
- **Expected**: HTTP 204 for delete, HTTP 404 for get or empty TagSet
- **Validates**: Object tag deletion and cleanup

## Attributes

### attributes_etag (Positive)
- **S3 Operation**: `get_object_attributes`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `ObjectAttributes=['ETag']`
- **Expected**: HTTP 200, returned `ETag` matches object's ETag
- **Validates**: ETag attribute retrieval via get-object-attributes

### attributes_size_and_storage (Positive)
- **S3 Operation**: `get_object_attributes`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `ObjectAttributes=['ObjectSize', 'StorageClass']`
- **Expected**: HTTP 200, `ObjectSize` matches object size, `StorageClass` present (optional)
- **Validates**: Object size and storage class attribute retrieval

### attributes_multiple (Positive)
- **S3 Operation**: `get_object_attributes`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `ObjectAttributes=['ETag', 'ObjectSize', 'StorageClass']`
- **Expected**: HTTP 200, at least 2 of 3 requested attributes returned
- **Validates**: Multiple attribute retrieval in single request

### attributes_multipart_parts (Positive/Negative)
- **S3 Operation**: `get_object_attributes`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<multipart-object>`, `ObjectAttributes=['ObjectParts']`
- **Expected**: HTTP 200 with `ObjectParts.Parts` array, or HTTP 400/501 if not supported
- **Validates**: Multipart object parts attribute retrieval (advanced feature)

## Metadata

### standard_metadata_headers (Positive)
- **S3 Operation**: `put_object`, `head_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `ContentType=application/json`, `ContentEncoding=gzip`, `ContentDisposition=attachment; filename="test.json"`, `ContentLanguage=en-US`, `CacheControl=max-age=3600, no-cache`, `Expires=Wed, 21 Oct 2025 07:28:00 GMT`
- **Expected**: HTTP 200, head_object returns ≥80% of standard metadata headers preserved
- **Validates**: Standard S3 metadata header preservation (Content-Type, Content-Encoding, etc.)

### custom_metadata_preservation (Positive)
- **S3 Operation**: `put_object`, `head_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Metadata={'author': 'S3CompatibilityChecker', 'project': 'metadata-testing', 'version': '1.0.0', 'environment': 'test', 'numeric-value': '42', 'boolean-value': 'true', 'special-chars': 'test@example.com'}`
- **Expected**: HTTP 200, head_object returns ≥90% of custom metadata fields preserved
- **Validates**: Custom metadata (x-amz-meta-*) preservation and retrieval

### metadata_encoding_handling (Positive/Negative)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Metadata={'ascii-text': 'simple-ascii-value', 'utf8-text': 'café-München-日本', 'spaces': 'value with spaces', 'url-encoded': 'test%40example.com', 'special-symbols': '!@#$%^&*()', 'numbers': '123456789', 'mixed': 'Test_123-Value@2024'}`
- **Expected**: HTTP 400 for non-ASCII characters (proper S3 spec compliance), ≥70% of valid encodings preserved
- **Validates**: Metadata encoding validation and character set compliance

### large_metadata_value_rejection (Negative)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Metadata={'large-field': '<2KB-value>'}`
- **Expected**: HTTP 400/413 (Payload Too Large) for excessive individual metadata values
- **Validates**: Individual metadata value size limits (AWS: ~2KB per field)

### total_metadata_size_check (Positive/Negative)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Metadata=<100-fields-with-large-values>`
- **Expected**: Acceptance if total size <8KB, HTTP 400/413 if exceeding limits
- **Validates**: Total metadata size limits (AWS: ~8KB total)

### metadata_case_preservation (Positive)
- **S3 Operation**: `put_object`, `head_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Metadata={'lowercase': 'value1', 'UPPERCASE': 'value2', 'MixedCase': 'value3', 'camelCase': 'value4'}`
- **Expected**: HTTP 200, ≥50% of metadata keys preserve exact case
- **Validates**: Metadata key case sensitivity behavior

### metadata_copy_preservation (Positive)
- **S3 Operation**: `put_object`, `copy_object`, `head_object`
- **Parameters**: `CopySource={'Bucket': '<bucket>', 'Key': '<source-key>'}`, no `MetadataDirective`
- **Expected**: HTTP 200, ≥80% of source metadata fields preserved in destination
- **Validates**: Default metadata preservation during copy operations

### metadata_copy_replacement (Positive)
- **S3 Operation**: `copy_object`, `head_object`
- **Parameters**: `CopySource={'Bucket': '<bucket>', 'Key': '<source-key>'}`, `Metadata=<new-metadata>`, `MetadataDirective=REPLACE`
- **Expected**: HTTP 200, new metadata set correctly, old metadata completely removed
- **Validates**: Metadata replacement during copy operations with REPLACE directive

### system_user_metadata_distinction (Positive)
- **S3 Operation**: `put_object`, `head_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Metadata=<user-metadata>`, `ContentType=application/json`, `CacheControl=no-cache`
- **Expected**: HTTP 200, system metadata (ContentType, ETag, etc.) separate from user metadata, both preserved
- **Validates**: Proper distinction between AWS system metadata and user metadata

### empty_metadata_values (Positive)
- **S3 Operation**: `put_object`, `head_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Metadata={'empty-field': '', 'normal-field': 'value'}`
- **Expected**: HTTP 200, normal field preserved, empty field handling varies by implementation
- **Validates**: Empty metadata value handling behavior

### no_metadata_baseline (Positive)
- **S3 Operation**: `put_object`, `head_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, no `Metadata` parameter
- **Expected**: HTTP 200, user metadata count = 0, only system metadata present
- **Validates**: Baseline behavior with no user metadata

## Range Requests

### range_single_byte_first_byte (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=0-0`
- **Expected**: HTTP 206, `Content-Range` header, single byte response
- **Validates**: Single byte range request (first byte)

### range_single_byte_100th_byte (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=99-99`
- **Expected**: HTTP 206, `Content-Range` header, single byte response
- **Validates**: Single byte range request (specific position)

### range_single_byte_middle_byte (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=500-500`
- **Expected**: HTTP 206, `Content-Range` header, single byte response
- **Validates**: Single byte range request (middle of object)

### range_single_byte_last_byte (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=-1`
- **Expected**: HTTP 206, `Content-Range` header, last byte of object
- **Validates**: Suffix range request for last byte

### range_partial_0_99 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=0-99`
- **Expected**: HTTP 206, 100 bytes response matching object bytes 0-99
- **Validates**: Partial range request (first 100 bytes)

### range_partial_100_299 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=100-299`
- **Expected**: HTTP 206, 200 bytes response matching object bytes 100-299
- **Validates**: Partial range request (middle section)

### range_partial_1000_1999 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=1000-1999`
- **Expected**: HTTP 206, 1000 bytes response matching object bytes 1000-1999
- **Validates**: Partial range request (1KB chunk)

### range_partial_5000_7499 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=5000-7499`
- **Expected**: HTTP 206, 2500 bytes response matching object bytes 5000-7499
- **Validates**: Partial range request (2.5KB chunk)

### range_suffix_1 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=-1`
- **Expected**: HTTP 206, last 1 byte of object
- **Validates**: Suffix range request (last N bytes)

### range_suffix_10 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=-10`
- **Expected**: HTTP 206, last 10 bytes of object
- **Validates**: Suffix range request (last N bytes)

### range_suffix_100 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=-100`
- **Expected**: HTTP 206, last 100 bytes of object
- **Validates**: Suffix range request (last N bytes)

### range_suffix_1000 (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=-1000`
- **Expected**: HTTP 206, last 1000 bytes of object
- **Validates**: Suffix range request (last N bytes)

### range_multiple_* (Positive/Negative)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=0-99,200-299`
- **Expected**: HTTP 206 with `multipart/byteranges` response, or HTTP 206 with first range only, or HTTP 400/501
- **Validates**: Multiple range request support (advanced feature)

### range_invalid_* (Negative)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=<invalid-range-header>`
- **Expected**: HTTP 400 or HTTP 416 (Range Not Satisfiable), or HTTP 200 (ignored)
- **Validates**: Invalid range header handling

### range_with_matching_etag (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=0-99`, `IfRange=<correct-etag>`
- **Expected**: HTTP 206, partial content returned
- **Validates**: Conditional range request with matching ETag

### range_with_nonmatching_etag (Positive)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Range=bytes=0-99`, `IfRange=<wrong-etag>`
- **Expected**: HTTP 200, full object returned (ignoring range)
- **Validates**: Conditional range request with non-matching ETag

## Error Conditions

### invalid_bucket_name_* (Negative)
- **S3 Operation**: `create_bucket`
- **Parameters**: `Bucket=<various-invalid-names>` (underscores, capitals, too long, too short, etc.)
- **Expected**: HTTP 400/403, error codes like `InvalidBucketName`
- **Validates**: S3 bucket naming rule enforcement

### nonexistent_bucket_* (Negative)
- **S3 Operation**: Various operations (`head_bucket`, `delete_bucket`, `put_object`, `get_object`, `list_objects_v2`)
- **Parameters**: `Bucket=<nonexistent-bucket-name>`
- **Expected**: HTTP 404
- **Validates**: Consistent 404 responses for missing buckets

### invalid_object_key_* (Negative)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<invalid-key>` (empty, too long, null characters)
- **Expected**: HTTP 400/403
- **Validates**: Object key validation and rejection

### nonexistent_object_* (Negative)
- **S3 Operation**: Various operations (`get_object`, `head_object`, `copy_object`, `get_object_tagging`)
- **Parameters**: `Bucket=<test-bucket>`, `Key=<nonexistent-object>`
- **Expected**: HTTP 404 (except `delete_object` which may be idempotent)
- **Validates**: Consistent 404 responses for missing objects

### malformed_complete_multipart (Negative)
- **S3 Operation**: `complete_multipart_upload`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `UploadId=invalid-upload-id-12345`
- **Expected**: HTTP 400/404
- **Validates**: Invalid multipart upload ID rejection

### malformed_bucket_tagging (Negative)
- **S3 Operation**: `put_bucket_tagging`
- **Parameters**: `Bucket=<test-bucket>`, `Tagging={'InvalidStructure': 'This should fail'}`
- **Expected**: HTTP 400
- **Validates**: Invalid tagging structure rejection

### malformed_versioning_config (Negative)
- **S3 Operation**: `put_bucket_versioning`
- **Parameters**: `Bucket=<test-bucket>`, `VersioningConfiguration={'Status': 'InvalidStatus'}`
- **Expected**: HTTP 400
- **Validates**: Invalid versioning configuration rejection

### bucket_policy_access (Negative)
- **S3 Operation**: `get_bucket_policy`
- **Parameters**: `Bucket=<test-bucket>`
- **Expected**: HTTP 403/501/404 (most S3-compatible storages don't support policies)
- **Validates**: Proper rejection of unsupported operations

### missing_resource_404_* (Negative)
- **S3 Operation**: Various operations on missing resources
- **Parameters**: Operations targeting non-existent buckets, objects, etc.
- **Expected**: Consistent HTTP 404 responses
- **Validates**: Standardized error responses for missing resources

### invalid_version_id (Negative)
- **S3 Operation**: `get_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `VersionId=invalid-version-id-12345`
- **Expected**: HTTP 400/404
- **Validates**: Invalid version ID rejection

### large_metadata_limit (Negative)
- **S3 Operation**: `put_object`
- **Parameters**: `Bucket=<test-bucket>`, `Key=<object>`, `Metadata=<20KB-metadata>`
- **Expected**: HTTP 400/413 (Payload Too Large) for excessive metadata
- **Validates**: Metadata size limit enforcement

### duplicate_bucket_creation (Positive/Negative)
- **S3 Operation**: `create_bucket`
- **Parameters**: `Bucket=<already-existing-bucket>`
- **Expected**: HTTP 409 with `BucketAlreadyExists` or idempotent success
- **Validates**: Duplicate bucket creation handling

### delete_bucket_with_objects (Negative)
- **S3 Operation**: `delete_bucket`
- **Parameters**: `Bucket=<bucket-containing-objects>`
- **Expected**: HTTP 409, error code `BucketNotEmpty`
- **Validates**: Non-empty bucket deletion prevention

## Sync

### sync_batch_upload (Positive)
- **S3 Operation**: Multiple `put_object` calls
- **Parameters**: 5 objects with unique keys in same bucket
- **Expected**: All uploads return HTTP 200 with ETags
- **Validates**: Batch upload capability and performance

### sync_directory_structure (Positive)
- **S3 Operation**: Multiple `put_object` calls
- **Parameters**: Objects with hierarchical key names simulating directory structure
- **Expected**: All uploads successful, objects accessible via directory-like paths
- **Validates**: Directory simulation through object key naming

### sync_batch_download (Positive)
- **S3 Operation**: Multiple `get_object` calls
- **Parameters**: Download multiple previously uploaded objects
- **Expected**: All downloads return HTTP 200 with correct content
- **Validates**: Batch download capability and data integrity

### sync_listing_prefix (Positive)
- **S3 Operation**: `list_objects_v2`
- **Parameters**: `Bucket=<test-bucket>`, `Prefix=<directory-prefix>`
- **Expected**: HTTP 200, returns only objects matching prefix
- **Validates**: Prefix-based object filtering for directory-like operations

### sync_listing_pagination (Positive)
- **S3 Operation**: `list_objects_v2`
- **Parameters**: `Bucket=<test-bucket>`, `MaxKeys=2`
- **Expected**: HTTP 200, returns limited objects with `IsTruncated` indicator
- **Validates**: Object listing pagination support

---

## Notes

- **Positive checks** verify that operations work correctly under normal conditions
- **Negative checks** verify that the system properly handles error conditions and invalid inputs
- **Positive/Negative checks** may have multiple acceptable outcomes depending on implementation choices
- Some advanced features (like `ObjectParts` attributes or multiple range requests) may not be supported by all S3-compatible implementations
- HTTP status codes and error codes follow AWS S3 API specifications
- All test resources are automatically cleaned up after check completion