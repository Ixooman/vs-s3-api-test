"""
Check runner for executing S3 compatibility checks.

This module provides the main check execution engine that coordinates
running different check categories and collecting results.
"""

import logging
import time
import importlib
from typing import Dict, List, Any, Optional
from .base_check import BaseCheck, CheckResult
from .s3_client import S3Client
from .config_manager import ConfigManager


class CheckRunner:
    """
    Main check execution engine for S3 compatibility testing.
    
    Coordinates the execution of different check categories and provides
    centralized result collection and reporting.
    """
    
    def __init__(self, config_manager: ConfigManager, logger: logging.Logger):
        """
        Initialize the check runner.
        
        Args:
            config_manager: Configuration manager instance
            logger: Logger instance for the runner
        """
        self.config_manager = config_manager
        self.logger = logger
        self.config = None
        self.s3_client = None
        self.check_classes = {}
        self.results = {}
        
        # Define available check categories
        self.available_checks = {
            'buckets': 'checks.check_buckets.BucketChecks',
            'objects': 'checks.check_objects.ObjectChecks',
            'multipart': 'checks.check_multipart.MultipartChecks',
            'versioning': 'checks.check_versioning.VersioningChecks',
            'tagging': 'checks.check_tagging.TaggingChecks',
            'attributes': 'checks.check_attributes.AttributeChecks',
            'metadata': 'checks.check_metadata.MetadataChecks',
            'range_requests': 'checks.check_range_requests.RangeRequestChecks',
            'error_conditions': 'checks.check_error_conditions.ErrorConditionChecks',
            'sync': 'checks.check_sync.SyncChecks'
        }
    
    def initialize(self, config_file: str = 'config.ini') -> bool:
        """
        Initialize the check runner with configuration.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load configuration
            self.config = self.config_manager.load_config()
            self.logger.info("Configuration loaded successfully")
            
            # Validate configuration
            warnings = self.config_manager.validate_connection_config(self.config)
            for warning in warnings:
                self.logger.warning(warning)
            
            # Initialize S3 client
            connection_config = self.config['connection']
            s3_logger = logging.getLogger('s3_checker.s3_client')
            s3_logger.setLevel(self.logger.level)
            # Copy handlers from main logger
            for handler in self.logger.handlers:
                s3_logger.addHandler(handler)
                
            # Get enhanced logging options
            logging_config = self.config.get('logging', {})
            enable_raw_logging = logging_config.get('enable_raw_logging', False)
            enable_boto_debug = logging_config.get('enable_boto_debug', False)
            
            self.s3_client = S3Client(
                endpoint_url=connection_config['endpoint_url'],
                access_key=connection_config['access_key'],
                secret_key=connection_config['secret_key'],
                region=connection_config.get('region', 'us-east-1'),
                verify_ssl=connection_config.get('verify_ssl', False),
                logger=s3_logger,
                max_retries=connection_config.get('max_retries', 3),
                enable_raw_logging=enable_raw_logging,
                enable_boto_debug=enable_boto_debug
            )
            
            self.logger.info("S3 client initialized successfully")
            
            # Test connection
            if not self._test_connection():
                return False
            
            # Load check classes
            self._load_check_classes()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize check runner: {e}")
            return False
    
    def _test_connection(self) -> bool:
        """
        Test the S3 connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info("Testing S3 connection...")
            response = self.s3_client.list_buckets()
            bucket_count = len(response.get('Buckets', []))
            self.logger.info(f"Connection successful - found {bucket_count} buckets")
            return True
            
        except Exception as e:
            self.logger.error(f"S3 connection test failed: {e}")
            return False
    
    def _load_check_classes(self):
        """Load check classes dynamically."""
        for check_name, class_path in self.available_checks.items():
            try:
                module_name, class_name = class_path.rsplit('.', 1)
                module = importlib.import_module(module_name)
                check_class = getattr(module, class_name)
                self.check_classes[check_name] = check_class
                self.logger.debug(f"Loaded check class: {check_name}")
                
            except ImportError as e:
                self.logger.warning(f"Could not load check class {check_name}: {e}")
            except AttributeError as e:
                self.logger.warning(f"Check class {class_name} not found in {module_name}: {e}")
    
    def run_checks(self, check_scopes: List[str] = None) -> Dict[str, Any]:
        """
        Run the specified checks.
        
        Args:
            check_scopes: List of check categories to run. If None, runs all enabled checks.
            
        Returns:
            Dictionary containing results from all executed checks
        """
        if not self.s3_client:
            raise RuntimeError("Check runner not initialized. Call initialize() first.")
        
        # Determine which checks to run
        if check_scopes is None or 'all' in check_scopes:
            enabled_checks = self.config_manager.get_enabled_checks(self.config)
        else:
            enabled_checks = [check for check in check_scopes if check in self.available_checks]
            # Filter by configuration
            config_enabled = self.config_manager.get_enabled_checks(self.config)
            enabled_checks = [check for check in enabled_checks if check in config_enabled]
        
        if not enabled_checks:
            self.logger.warning("No checks enabled or specified")
            return {'summary': {'total_categories': 0, 'results': {}}}
        
        self.logger.info(f"Running checks: {', '.join(enabled_checks)}")
        
        # Execute checks
        overall_start_time = time.time()
        category_results = {}
        
        for check_name in enabled_checks:
            if check_name not in self.check_classes:
                self.logger.warning(f"Check class not available: {check_name}")
                continue
            
            self.logger.info(f"Starting {check_name} checks...")
            category_start_time = time.time()
            
            try:
                # Create check instance with scope-specific logger
                check_class = self.check_classes[check_name]
                scope_logger = logging.getLogger(f's3_checker.{check_name}')
                scope_logger.setLevel(self.logger.level)
                # Copy handlers from main logger
                for handler in self.logger.handlers:
                    scope_logger.addHandler(handler)
                
                check_instance = check_class(self.s3_client, self.config, scope_logger)
                
                # Run checks
                check_results = check_instance.run_checks()
                category_duration = time.time() - category_start_time
                
                # Collect results
                category_summary = check_instance.get_summary()
                category_summary['duration'] = category_duration
                category_results[check_name] = category_summary
                
                self.logger.info(f"Completed {check_name} checks: "
                               f"{category_summary['passed']}/{category_summary['total_checks']} passed "
                               f"in {category_duration:.2f}s")
                
                # Cleanup
                if self.config.get('test_data', {}).get('cleanup_enabled', True):
                    try:
                        check_instance.cleanup()
                    except Exception as cleanup_error:
                        self.logger.warning(f"Cleanup failed for {check_name}: {cleanup_error}")
                
            except Exception as e:
                self.logger.error(f"Failed to execute {check_name} checks: {e}")
                category_results[check_name] = {
                    'check_category': check_name,
                    'total_checks': 0,
                    'passed': 0,
                    'failed': 0,
                    'success_rate': 0,
                    'duration': time.time() - category_start_time,
                    'error': str(e),
                    'results': []
                }
        
        overall_duration = time.time() - overall_start_time
        
        # Calculate overall summary
        total_checks = sum(cat['total_checks'] for cat in category_results.values())
        total_passed = sum(cat['passed'] for cat in category_results.values())
        total_failed = sum(cat['failed'] for cat in category_results.values())
        
        summary = {
            'total_categories': len(category_results),
            'total_checks': total_checks,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'overall_success_rate': (total_passed / total_checks * 100) if total_checks > 0 else 0,
            'overall_duration': overall_duration,
            'executed_checks': list(category_results.keys()),
            'results': category_results
        }
        
        self.logger.info(f"All checks completed: {total_passed}/{total_checks} passed "
                        f"({summary['overall_success_rate']:.1f}%) in {overall_duration:.2f}s")
        
        self.results = summary
        return summary
    
    def get_failed_checks(self) -> List[Dict[str, Any]]:
        """
        Get list of all failed checks with details.
        
        Returns:
            List of failed check details
        """
        failed_checks = []
        
        if not self.results:
            return failed_checks
        
        for category_name, category_data in self.results.get('results', {}).items():
            for result in category_data.get('results', []):
                if not result.success:
                    failed_checks.append({
                        'category': category_name,
                        'check_name': result.name,
                        'message': result.message,
                        'details': result.details,
                        'duration': result.duration
                    })
        
        return failed_checks
    
    def get_summary_report(self) -> str:
        """
        Generate a text summary report of check results.
        
        Returns:
            Formatted summary report string
        """
        if not self.results:
            return "No check results available"
        
        lines = []
        lines.append("=" * 60)
        lines.append("S3 COMPATIBILITY CHECK SUMMARY")
        lines.append("=" * 60)
        lines.append("")
        
        # Overall summary
        summary = self.results
        lines.append(f"Total Categories: {summary['total_categories']}")
        lines.append(f"Total Checks: {summary['total_checks']}")
        lines.append(f"Passed: {summary['total_passed']}")
        lines.append(f"Failed: {summary['total_failed']}")
        lines.append(f"Success Rate: {summary['overall_success_rate']:.1f}%")
        lines.append(f"Duration: {summary['overall_duration']:.2f}s")
        lines.append("")
        
        # Category breakdown
        lines.append("CATEGORY RESULTS:")
        lines.append("-" * 40)
        
        for category_name, category_data in summary['results'].items():
            status = "✓" if category_data['failed'] == 0 else "✗"
            lines.append(f"{status} {category_name}: "
                        f"{category_data['passed']}/{category_data['total_checks']} "
                        f"({category_data['success_rate']:.1f}%) "
                        f"[{category_data['duration']:.2f}s]")
        
        lines.append("")
        
        # Failed checks details
        failed_checks = self.get_failed_checks()
        if failed_checks:
            lines.append("FAILED CHECKS:")
            lines.append("-" * 40)
            
            for check in failed_checks:
                lines.append(f"✗ {check['category']}.{check['check_name']}")
                lines.append(f"  Message: {check['message']}")
                if check['details']:
                    lines.append(f"  Details: {check['details']}")
                lines.append("")
        else:
            lines.append("🎉 All checks passed!")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def export_results(self, format_type: str = 'json', output_file: str = None) -> str:
        """
        Export results in specified format.
        
        Args:
            format_type: Export format ('json', 'text')
            output_file: Optional output file path
            
        Returns:
            Exported data as string or file path if written to file
        """
        if not self.results:
            return "No results to export"
        
        if format_type.lower() == 'json':
            import json
            # Convert CheckResult objects to dictionaries for JSON serialization
            json_results = self._serialize_results_for_json(self.results)
            output = json.dumps(json_results, indent=2, default=str)
        elif format_type.lower() == 'text':
            output = self.get_summary_report()
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            self.logger.info(f"Results exported to {output_file}")
            return output_file
        
        return output
    
    def _serialize_results_for_json(self, data):
        """
        Serialize CheckResult objects and other complex types for JSON export.
        
        Args:
            data: Data structure to serialize
            
        Returns:
            JSON-serializable data structure
        """
        if isinstance(data, dict):
            return {k: self._serialize_results_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_results_for_json(item) for item in data]
        elif hasattr(data, '__dict__'):
            # Convert objects to dictionaries
            return {k: self._serialize_results_for_json(v) for k, v in data.__dict__.items()}
        else:
            return data
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get information about the S3 connection for debugging.
        
        Returns:
            Connection information dictionary
        """
        if self.s3_client:
            return self.s3_client.get_connection_info()
        return {}