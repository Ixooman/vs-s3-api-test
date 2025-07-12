"""
Configuration management for S3 compatibility checker.

This module handles reading configuration from INI files and generating
template configuration files with example values.
"""

import configparser
import os
import logging
from typing import Dict, Any, List


class ConfigManager:
    """
    Manages configuration for the S3 compatibility checker.
    
    Handles reading INI configuration files and generating template configurations
    with example values for easy setup.
    """
    
    def __init__(self, config_file: str = 'config.ini'):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._default_config = self._get_default_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from the INI file.
        
        Returns:
            Dictionary containing all configuration sections
            
        Raises:
            FileNotFoundError: If the config file doesn't exist
            configparser.Error: If the config file is malformed
        """
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found. "
                                  f"Generate one using --generate-config option.")
        
        self.config.read(self.config_file)
        
        # Convert to dictionary structure
        config_dict = {}
        for section in self.config.sections():
            config_dict[section] = dict(self.config[section])
        
        # Validate required sections
        self._validate_config(config_dict)
        
        # Convert string values to appropriate types
        config_dict = self._convert_types(config_dict)
        
        return config_dict
    
    def generate_template(self, overwrite: bool = False) -> str:
        """
        Generate a template configuration file with example values.
        
        Args:
            overwrite: Whether to overwrite existing config file
            
        Returns:
            Path to the generated template file
            
        Raises:
            FileExistsError: If config file exists and overwrite=False
        """
        if os.path.exists(self.config_file) and not overwrite:
            raise FileExistsError(f"Configuration file '{self.config_file}' already exists. "
                                f"Use --overwrite to replace it.")
        
        with open(self.config_file, 'w') as f:
            f.write(self._get_template_content())
        
        return self.config_file
    
    def _get_default_config(self) -> Dict[str, Dict[str, Any]]:
        """Get the default configuration structure with example values."""
        return {
            'connection': {
                'endpoint_url': 'http://192.168.10.81',
                'access_key': 'your-access-key-here',
                'secret_key': 'your-secret-key-here',
                'region': 'us-east-1',
                'verify_ssl': False,
                'max_retries': 3
            },
            'test_data': {
                'small_file_size': 1024,  # 1KB
                'medium_file_size': 1048576,  # 1MB
                'large_file_size': 10485760,  # 10MB
                'multipart_chunk_size': 5242880,  # 5MB
                'test_file_content': 'S3 compatibility test data',
                'cleanup_enabled': True
            },
            'logging': {
                'log_level': 'INFO',
                'log_file': 's3_checker.log',
                'console_output': True,
                'detailed_errors': True
            },
            'checks': {
                'buckets': True,
                'objects': True,
                'multipart': True,
                'versioning': True,
                'tagging': True,
                'attributes': True,
                'range_requests': True,
                'error_conditions': True,
                'sync': True
            },
            'timeouts': {
                'operation_timeout': 30,
                'upload_timeout': 300,
                'download_timeout': 300
            }
        }
    
    def _get_template_content(self) -> str:
        """Generate the INI template content with comments."""
        return """# S3 Compatibility Checker Configuration
# 
# This file contains configuration for the S3 compatibility testing framework.
# Modify the values below to match your S3-compatible storage system.

[connection]
# S3 endpoint URL (without trailing slash)
endpoint_url = http://192.168.10.81

# AWS-style access credentials
access_key = your-access-key-here
secret_key = your-secret-key-here

# AWS region (most S3-compatible systems accept any value)
region = us-east-1

# Whether to verify SSL certificates (set to false for self-signed certs)
verify_ssl = false

# Maximum number of retries for failed requests
max_retries = 3

[test_data]
# File sizes for testing (in bytes)
small_file_size = 1024
medium_file_size = 1048576
large_file_size = 10485760

# Chunk size for multipart uploads (minimum 5MB for real S3)
multipart_chunk_size = 5242880

# Content to use for test files
test_file_content = S3 compatibility test data

# Whether to automatically cleanup test resources after checks
cleanup_enabled = true

[logging]
# Log level: DEBUG, INFO, WARNING, ERROR
log_level = INFO

# Log file name (relative to script directory)
log_file = s3_checker.log

# Whether to show output in console
console_output = true

# Whether to show detailed error information
detailed_errors = true

[checks]
# Enable/disable specific check categories
buckets = true
objects = true
multipart = true
versioning = true
tagging = true
attributes = true
range_requests = true
error_conditions = true
sync = true

[timeouts]
# Timeouts for various operations (in seconds)
operation_timeout = 30
upload_timeout = 300
download_timeout = 300
"""
    
    def _validate_config(self, config_dict: Dict[str, Any]):
        """
        Validate that required configuration sections and keys exist.
        
        Args:
            config_dict: Configuration dictionary to validate
            
        Raises:
            ValueError: If required configuration is missing
        """
        required_sections = ['connection', 'test_data', 'logging', 'checks']
        required_keys = {
            'connection': ['endpoint_url', 'access_key', 'secret_key'],
            'test_data': ['small_file_size', 'medium_file_size', 'large_file_size'],
            'logging': ['log_level', 'log_file'],
            'checks': []  # At least one check should be enabled, validated separately
        }
        
        # Check required sections
        for section in required_sections:
            if section not in config_dict:
                raise ValueError(f"Missing required configuration section: [{section}]")
        
        # Check required keys in each section
        for section, keys in required_keys.items():
            for key in keys:
                if key not in config_dict[section]:
                    raise ValueError(f"Missing required configuration key: {key} in section [{section}]")
        
        # Check that at least one check is enabled
        checks_section = config_dict.get('checks', {})
        enabled_checks = [key for key, value in checks_section.items() 
                         if str(value).lower() in ('true', '1', 'yes', 'on')]
        if not enabled_checks:
            raise ValueError("At least one check category must be enabled in [checks] section")
        
        # Validate endpoint URL
        endpoint_url = config_dict['connection']['endpoint_url']
        if not endpoint_url.startswith(('http://', 'https://')):
            raise ValueError("endpoint_url must start with http:// or https://")
    
    def _convert_types(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert string values from INI file to appropriate Python types.
        
        Args:
            config_dict: Configuration dictionary with string values
            
        Returns:
            Configuration dictionary with properly typed values
        """
        # Define type conversions
        conversions = {
            'connection': {
                'verify_ssl': bool,
                'max_retries': int
            },
            'test_data': {
                'small_file_size': int,
                'medium_file_size': int,
                'large_file_size': int,
                'multipart_chunk_size': int,
                'cleanup_enabled': bool
            },
            'logging': {
                'console_output': bool,
                'detailed_errors': bool
            },
            'checks': {
                # All check values are boolean
                'buckets': bool,
                'objects': bool,
                'multipart': bool,
                'versioning': bool,
                'tagging': bool,
                'attributes': bool,
                'range_requests': bool,
                'error_conditions': bool,
                'sync': bool
            },
            'timeouts': {
                'operation_timeout': int,
                'upload_timeout': int,
                'download_timeout': int
            }
        }
        
        converted_config = {}
        for section, section_data in config_dict.items():
            converted_section = {}
            section_conversions = conversions.get(section, {})
            
            for key, value in section_data.items():
                if key in section_conversions:
                    target_type = section_conversions[key]
                    if target_type == bool:
                        converted_section[key] = str(value).lower() in ('true', '1', 'yes', 'on')
                    elif target_type == int:
                        converted_section[key] = int(value)
                    else:
                        converted_section[key] = target_type(value)
                else:
                    converted_section[key] = value
            
            converted_config[section] = converted_section
        
        return converted_config
    
    def get_enabled_checks(self, config_dict: Dict[str, Any]) -> List[str]:
        """
        Get list of enabled check categories from configuration.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            List of enabled check category names
        """
        checks_section = config_dict.get('checks', {})
        enabled = []
        
        for check_name, enabled_flag in checks_section.items():
            if enabled_flag:
                enabled.append(check_name)
        
        return enabled
    
    def validate_connection_config(self, config_dict: Dict[str, Any]) -> List[str]:
        """
        Validate connection configuration and return any warnings.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            List of warning messages
        """
        warnings = []
        connection = config_dict.get('connection', {})
        
        # Check for default/placeholder values
        if connection.get('access_key') == 'your-access-key-here':
            warnings.append("Access key appears to be a placeholder value")
        
        if connection.get('secret_key') == 'your-secret-key-here':
            warnings.append("Secret key appears to be a placeholder value")
        
        # Check SSL verification
        if not connection.get('verify_ssl', True):
            warnings.append("SSL verification is disabled - use only for testing")
        
        # Check endpoint URL format
        endpoint_url = connection.get('endpoint_url', '')
        if 'localhost' in endpoint_url or '127.0.0.1' in endpoint_url:
            warnings.append("Using localhost endpoint - ensure S3 service is running locally")
        
        return warnings