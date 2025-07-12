#!/usr/bin/env python3
"""
S3 Compatibility Checker - Main Application

A comprehensive testing framework for S3 API compatibility verification.
Tests bucket operations, object management, multipart uploads, versioning,
tagging, range requests, and error conditions.

Usage:
    python main.py --scope all                    # Run all checks
    python main.py --scope buckets,objects        # Run specific checks  
    python main.py --generate-config              # Generate config template
    python main.py --log-level debug              # Enable debug logging
"""

import sys
import os
import argparse
import logging
import time
from pathlib import Path
from typing import List, Optional

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework.config_manager import ConfigManager
from framework.check_runner import CheckRunner

# Import colorama for colored console output
try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init()
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Fallback - no colors
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""


class S3CompatibilityChecker:
    """
    Main application class for S3 compatibility checking.
    
    Handles CLI argument parsing, logging setup, configuration management,
    and coordinating the execution of compatibility checks.
    """
    
    def __init__(self):
        """Initialize the S3 compatibility checker application."""
        self.config_manager = ConfigManager()
        self.check_runner = None
        self.logger = None
        self.args = None
        
        # Available check scopes
        self.available_scopes = [
            'buckets', 'objects', 'multipart', 'versioning', 
            'tagging', 'attributes', 'range_requests', 
            'error_conditions', 'sync', 'all'
        ]
    
    def setup_logging(self, log_level: str = 'INFO', log_file: str = None, 
                     console_output: bool = True, scope_name: str = 's3_checker') -> logging.Logger:
        """
        Set up logging configuration.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_file: Log file path (optional)
            console_output: Whether to output to console
            scope_name: Name to use in log messages (e.g., specific check scope)
            
        Returns:
            Configured logger instance
        """
        # Create logger with scope-specific name
        logger = logging.getLogger(scope_name)
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Create formatter for console (with colors)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create formatter for file (no colors)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level.upper()))
            
            # Use colored formatter for console if available
            if COLORS_AVAILABLE:
                colored_formatter = ColoredFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(colored_formatter)
            else:
                console_handler.setFormatter(console_formatter)
            
            logger.addHandler(console_handler)
        
        # File handler (always without colors)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)  # Always debug level for file
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def parse_arguments(self) -> argparse.Namespace:
        """
        Parse command line arguments.
        
        Returns:
            Parsed arguments namespace
        """
        parser = argparse.ArgumentParser(
            description='S3 Compatibility Checker - Verify S3 API compatibility',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s --generate-config                    Generate configuration template
  %(prog)s --scope all                          Run all compatibility checks
  %(prog)s --scope buckets,objects              Run specific check categories
  %(prog)s --scope buckets --log-level debug    Run with debug logging
  %(prog)s --config custom.ini --scope all      Use custom config file
  %(prog)s --export-results results.json        Export results to JSON file
            """
        )
        
        # Configuration options
        config_group = parser.add_argument_group('Configuration')
        config_group.add_argument(
            '--config', '-c',
            default='config.ini',
            help='Configuration file path (default: config.ini)'
        )
        config_group.add_argument(
            '--generate-config',
            action='store_true',
            help='Generate configuration template and exit'
        )
        config_group.add_argument(
            '--overwrite-config',
            action='store_true',
            help='Overwrite existing configuration file when generating template'
        )
        
        # Check execution options
        execution_group = parser.add_argument_group('Check Execution')
        execution_group.add_argument(
            '--scope', '-s',
            help=f'Check scopes to run (comma-separated). Available: {", ".join(self.available_scopes)}'
        )
        execution_group.add_argument(
            '--list-scopes',
            action='store_true',
            help='List available check scopes and exit'
        )
        
        # Logging options
        logging_group = parser.add_argument_group('Logging')
        logging_group.add_argument(
            '--log-level', '-l',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='INFO',
            help='Set logging level (default: INFO)'
        )
        logging_group.add_argument(
            '--log-file',
            help='Log file path (default: from config file)'
        )
        logging_group.add_argument(
            '--no-console',
            action='store_true',
            help='Disable console output (log to file only)'
        )
        
        # Output options
        output_group = parser.add_argument_group('Output')
        output_group.add_argument(
            '--export-results',
            help='Export results to file (JSON or text based on extension)'
        )
        output_group.add_argument(
            '--export-format',
            choices=['json', 'text'],
            help='Force export format (overrides file extension detection)'
        )
        output_group.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Minimize output (only show summary)'
        )
        
        # Utility options
        parser.add_argument(
            '--version',
            action='version',
            version='S3 Compatibility Checker 1.0.0'
        )
        
        return parser.parse_args()
    
    def print_banner(self):
        """Print application banner."""
        if not self.args.quiet:
            banner = f"""
{Fore.CYAN}{Style.BRIGHT}
╔══════════════════════════════════════════════════════════════════════════════╗
║                        S3 Compatibility Checker                             ║
║                                                                              ║
║    Comprehensive S3 API compatibility testing framework                     ║
║    Tests buckets, objects, multipart uploads, versioning, and more          ║
╚══════════════════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
"""
            print(banner)
    
    def list_scopes(self):
        """List available check scopes."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Available Check Scopes:{Style.RESET_ALL}\n")
        
        scope_descriptions = {
            'buckets': 'Bucket operations (create, list, delete, versioning, tagging)',
            'objects': 'Object operations (upload, download, copy, delete, metadata)',
            'multipart': 'Multipart upload operations (create, upload parts, complete, abort)',
            'versioning': 'Object versioning (enable versioning, multiple versions)',
            'tagging': 'Bucket and object tagging (put, get, delete tags)',
            'attributes': 'Object attributes and metadata operations',
            'range_requests': 'Partial object retrieval using HTTP Range headers',
            'error_conditions': 'Error handling and invalid request scenarios',
            'sync': 'Directory synchronization operations',
            'all': 'Run all available check categories'
        }
        
        for scope in self.available_scopes:
            description = scope_descriptions.get(scope, 'No description available')
            print(f"  {Fore.GREEN}{scope:20}{Style.RESET_ALL} - {description}")
        
        print(f"\n{Fore.YELLOW}Usage examples:{Style.RESET_ALL}")
        print(f"  python main.py --scope all")
        print(f"  python main.py --scope buckets,objects")
        print(f"  python main.py --scope range_requests,error_conditions")
        print()
    
    def generate_config_template(self) -> bool:
        """
        Generate configuration template.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            config_file = self.config_manager.generate_template(
                overwrite=self.args.overwrite_config
            )
            
            print(f"{Fore.GREEN}✓ Configuration template generated: {config_file}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Next steps:{Style.RESET_ALL}")
            print(f"1. Edit {config_file} with your S3 endpoint details")
            print(f"2. Run checks: python main.py --scope all")
            print(f"3. View results and logs")
            
            return True
            
        except FileExistsError as e:
            print(f"{Fore.RED}✗ {e}{Style.RESET_ALL}")
            print(f"Use --overwrite-config to replace existing file")
            return False
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to generate config template: {e}{Style.RESET_ALL}")
            return False
    
    def initialize_application(self) -> bool:
        """
        Initialize the application with configuration and logging.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load configuration to get logging settings
            config = self.config_manager.load_config()
            
            # Setup logging
            log_level = self.args.log_level
            if self.args.quiet:
                log_level = 'WARNING'
            
            log_file = self.args.log_file
            if not log_file:
                log_file = config.get('logging', {}).get('log_file')
            
            console_output = not self.args.no_console
            if not console_output and not log_file:
                print(f"{Fore.RED}✗ Cannot disable console output without log file{Style.RESET_ALL}")
                return False
            
            # Determine scope name for logging
            scope_name = 's3_checker'
            if hasattr(self.args, 'scope') and self.args.scope:
                if self.args.scope == 'all':
                    scope_name = 's3_checker'
                else:
                    scopes = [s.strip() for s in self.args.scope.split(',')]
                    if len(scopes) == 1:
                        scope_name = f's3_checker.{scopes[0]}'
                    else:
                        scope_name = f's3_checker.multi_scope'
            
            self.logger = self.setup_logging(log_level, log_file, console_output, scope_name)
            
            # Initialize check runner
            self.check_runner = CheckRunner(self.config_manager, self.logger)
            
            if not self.check_runner.initialize(self.args.config):
                print(f"{Fore.RED}✗ Failed to initialize check runner{Style.RESET_ALL}")
                return False
            
            return True
            
        except FileNotFoundError as e:
            print(f"{Fore.RED}✗ Configuration file not found: {e}{Style.RESET_ALL}")
            print(f"Generate one using: python main.py --generate-config")
            return False
        except Exception as e:
            print(f"{Fore.RED}✗ Initialization failed: {e}{Style.RESET_ALL}")
            return False
    
    def parse_check_scopes(self) -> List[str]:
        """
        Parse and validate check scopes from arguments.
        
        Returns:
            List of valid check scopes
        """
        if not self.args.scope:
            return ['all']
        
        scopes = [scope.strip() for scope in self.args.scope.split(',')]
        valid_scopes = []
        
        for scope in scopes:
            if scope in self.available_scopes:
                valid_scopes.append(scope)
            else:
                self.logger.warning(f"Unknown check scope: {scope}")
                print(f"{Fore.YELLOW}⚠ Unknown check scope: {scope}{Style.RESET_ALL}")
        
        if not valid_scopes:
            print(f"{Fore.RED}✗ No valid check scopes specified{Style.RESET_ALL}")
            self.list_scopes()
        
        return valid_scopes
    
    def run_checks(self) -> bool:
        """
        Execute the compatibility checks.
        
        Returns:
            True if checks completed successfully, False otherwise
        """
        try:
            scopes = self.parse_check_scopes()
            if not scopes:
                return False
            
            if not self.args.quiet:
                print(f"{Fore.BLUE}Running checks: {', '.join(scopes)}{Style.RESET_ALL}")
                print()
            
            # Run checks
            start_time = time.time()
            results = self.check_runner.run_checks(scopes)
            duration = time.time() - start_time
            
            # Display summary
            if not self.args.quiet:
                print("\n" + self.check_runner.get_summary_report())
            else:
                # Quiet mode - just show overall result
                total_passed = results['total_passed']
                total_checks = results['total_checks']
                success_rate = results['overall_success_rate']
                
                if results['total_failed'] == 0:
                    print(f"{Fore.GREEN}✓ All {total_checks} checks passed ({success_rate:.1f}%){Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✗ {results['total_failed']}/{total_checks} checks failed ({success_rate:.1f}%){Style.RESET_ALL}")
            
            # Export results if requested
            if self.args.export_results:
                self.export_results(results)
            
            # Return success based on whether all checks passed
            return results['total_failed'] == 0
            
        except Exception as e:
            self.logger.error(f"Check execution failed: {e}")
            print(f"{Fore.RED}✗ Check execution failed: {e}{Style.RESET_ALL}")
            return False
    
    def export_results(self, results: dict):
        """
        Export results to file.
        
        Args:
            results: Check results dictionary
        """
        try:
            export_file = self.args.export_results
            export_format = self.args.export_format
            
            # Auto-detect format from file extension if not specified
            if not export_format:
                if export_file.lower().endswith('.json'):
                    export_format = 'json'
                elif export_file.lower().endswith('.txt'):
                    export_format = 'text'
                else:
                    export_format = 'json'  # Default to JSON
            
            output_path = self.check_runner.export_results(export_format, export_file)
            print(f"{Fore.GREEN}✓ Results exported to: {output_path}{Style.RESET_ALL}")
            
        except Exception as e:
            self.logger.error(f"Failed to export results: {e}")
            print(f"{Fore.RED}✗ Failed to export results: {e}{Style.RESET_ALL}")
    
    def run(self) -> int:
        """
        Main application entry point.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            # Parse arguments
            self.args = self.parse_arguments()
            
            # Handle special commands
            if self.args.list_scopes:
                self.list_scopes()
                return 0
            
            if self.args.generate_config:
                return 0 if self.generate_config_template() else 1
            
            # Print banner
            self.print_banner()
            
            # Initialize application
            if not self.initialize_application():
                return 1
            
            # Run checks
            success = self.run_checks()
            
            if success:
                if not self.args.quiet:
                    print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 All compatibility checks passed!{Style.RESET_ALL}")
                return 0
            else:
                if not self.args.quiet:
                    print(f"\n{Fore.RED}{Style.BRIGHT}❌ Some compatibility checks failed. Check the logs for details.{Style.RESET_ALL}")
                return 1
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⚠ Interrupted by user{Style.RESET_ALL}")
            return 1
        except Exception as e:
            print(f"{Fore.RED}✗ Unexpected error: {e}{Style.RESET_ALL}")
            if self.logger:
                self.logger.exception("Unexpected error in main application")
            return 1


class ColoredFormatter(logging.Formatter):
    """Custom log formatter with colors for console output only."""
    
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA + Style.BRIGHT
    }
    
    def format(self, record):
        # Create a copy of the record to avoid affecting other handlers
        record_copy = logging.makeLogRecord(record.__dict__)
        log_color = self.COLORS.get(record_copy.levelname, '')
        record_copy.levelname = f"{log_color}{record_copy.levelname}{Style.RESET_ALL}"
        return super().format(record_copy)


def main():
    """Main entry point."""
    app = S3CompatibilityChecker()
    sys.exit(app.run())


if __name__ == '__main__':
    main()