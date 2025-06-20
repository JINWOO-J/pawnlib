"""
Migration Guide: From Legacy GlobalConfig to Improved GlobalConfig

This guide helps you migrate from the original globalconfig.py to the improved version.
"""

from typing import Dict, Any, List
from pathlib import Path


class MigrationGuide:
    """Interactive migration guide for upgrading to improved configuration"""

    def __init__(self):
        self.legacy_patterns = []
        self.improved_alternatives = []
        self._setup_migration_patterns()

    def _setup_migration_patterns(self):
        """Setup common migration patterns"""

        # Pattern 1: Basic import and usage
        self.legacy_patterns.append({
            'name': 'Basic Import',
            'legacy': '''
from pawnlib.config.globalconfig import pawnlib_config as pwn

pwn.set(debug=True, app_name="my_app")
value = pwn.get("debug")
config_dict = pwn.conf()
            ''',
            'improved': '''
from pawnlib.config.improved_globalconfig import improved_pawnlib_config as pwn

pwn.set(debug=True, app_name="my_app")
value = pwn.get("debug")
config_dict = pwn.conf()
            ''',
            'notes': 'Drop-in replacement with same API'
        })

        # Pattern 2: Creating custom config instance
        self.legacy_patterns.append({
            'name': 'Custom Config Instance',
            'legacy': '''
from pawnlib.config.globalconfig import PawnlibConfig

config = PawnlibConfig(
    global_name="my_app_config",
    debug=True,
    use_global_namespace=False
)
config.init_with_env()
            ''',
            'improved': '''
from pawnlib.config.improved_globalconfig import create_improved_config

config = create_improved_config(
    app_name="my_app_config",
    debug=True,
    env_prefix="MYAPP"
)
            ''',
            'notes': 'Simplified creation with automatic initialization'
        })

        # Pattern 3: Environment variable handling
        self.legacy_patterns.append({
            'name': 'Environment Variables',
            'legacy': '''
config.fill_config_from_environment()
config.set(PAWN_DEBUG=True)
debug = config.get("PAWN_DEBUG")
            ''',
            'improved': '''
# Automatic environment loading with PAWN_ prefix
config.set(debug=True)
debug = config.get("debug")
            ''',
            'notes': 'Environment variables automatically loaded and converted'
        })

        # Pattern 4: Logger configuration
        self.legacy_patterns.append({
            'name': 'Logger Setup',
            'legacy': '''
from pawnlib.utils.log import AppLogger

app_logger, error_logger = AppLogger(
    app_name="my_app",
    log_path="./logs"
).get_logger()

pwn.set(
    PAWN_APP_LOGGER=app_logger,
    PAWN_ERROR_LOGGER=error_logger
)
            ''',
            'improved': '''
from pawnlib.utils.log import AppLogger

app_logger, error_logger = AppLogger(
    app_name="my_app",
    log_path="./logs"
).get_logger()

config.set(
    app_logger=app_logger,
    error_logger=error_logger,
    log_level="INFO"
)
            ''',
            'notes': 'Cleaner naming without PAWN_ prefix for internal use'
        })

        # Pattern 5: Config file handling
        self.legacy_patterns.append({
            'name': 'Configuration Files',
            'legacy': '''
config._config_file = "config.ini"
config._load_config_file()
            ''',
            'improved': '''
config = create_improved_config(
    config_file="config.json"  # or config.ini
)
# Automatic loading on creation
            ''',
            'notes': 'Supports both JSON and INI files with automatic loading'
        })

        # Pattern 6: Testing and isolation
        self.legacy_patterns.append({
            'name': 'Testing Configuration',
            'legacy': '''
# Difficult to isolate for testing
old_debug = pwn.get("debug")
pwn.set(debug=True)
# ... test code ...
pwn.set(debug=old_debug)  # Manual restore
            ''',
            'improved': '''
# Easy testing with context manager
with config.temporary_config(debug=True) as test_config:
    # ... test code ...
    pass
# Automatic restore
            ''',
            'notes': 'Built-in context manager for test isolation'
        })

    def print_migration_guide(self):
        """Print the complete migration guide"""
        print("=" * 80)
        print("🔄 PAWNLIB CONFIG MIGRATION GUIDE")
        print("=" * 80)
        print()

        print("📋 OVERVIEW")
        print("-" * 40)
        print("This guide helps you migrate from the legacy globalconfig.py")
        print("to the improved version with better type safety, performance,")
        print("and testing capabilities.")
        print()

        print("🎯 KEY BENEFITS OF IMPROVED VERSION")
        print("-" * 40)
        print("✅ Type safety with Pydantic validation")
        print("✅ Thread-safe operations")
        print("✅ Better error handling")
        print("✅ Context managers for testing")
        print("✅ Automatic environment variable loading")
        print("✅ Support for JSON and INI config files")
        print("✅ Backward compatibility")
        print()

        print("📝 MIGRATION PATTERNS")
        print("-" * 40)

        for i, pattern in enumerate(self.legacy_patterns, 1):
            print(f"\n{i}. {pattern['name']}")
            print("   " + "─" * (len(pattern['name']) + 3))

            print("\n   BEFORE (Legacy):")
            print("   " + "─" * 20)
            for line in pattern['legacy'].strip().split('\n'):
                print(f"   {line}")

            print("\n   AFTER (Improved):")
            print("   " + "─" * 21)
            for line in pattern['improved'].strip().split('\n'):
                print(f"   {line}")

            print(f"\n   📌 {pattern['notes']}")
            print()

    def check_compatibility_issues(self, code_content: str) -> List[Dict[str, Any]]:
        """Check code for potential compatibility issues"""
        issues = []

        compatibility_checks = [
            {
                'pattern': 'use_global_namespace=True',
                'issue': 'Global namespace usage',
                'suggestion': 'Use improved config manager instead',
                'severity': 'medium'
            },
            {
                'pattern': 'fill_config_from_environment()',
                'issue': 'Manual environment loading',
                'suggestion': 'Environment variables loaded automatically',
                'severity': 'low'
            },
            {
                'pattern': 'PAWN_LOGGER',
                'issue': 'Legacy logger configuration',
                'suggestion': 'Use simplified logger config',
                'severity': 'low'
            },
            {
                'pattern': 'globals()[',
                'issue': 'Direct global variable manipulation',
                'suggestion': 'Use configuration manager methods',
                'severity': 'high'
            },
            {
                'pattern': '_load_config_file()',
                'issue': 'Manual config file loading',
                'suggestion': 'Pass config_file to create_improved_config()',
                'severity': 'medium'
            }
        ]

        for check in compatibility_checks:
            if check['pattern'] in code_content:
                issues.append({
                    'pattern': check['pattern'],
                    'issue': check['issue'],
                    'suggestion': check['suggestion'],
                    'severity': check['severity'],
                    'line_numbers': self._find_line_numbers(code_content, check['pattern'])
                })

        return issues

    def _find_line_numbers(self, content: str, pattern: str) -> List[int]:
        """Find line numbers where pattern occurs"""
        lines = content.split('\n')
        line_numbers = []

        for i, line in enumerate(lines, 1):
            if pattern in line:
                line_numbers.append(i)

        return line_numbers

    def generate_migration_report(self, file_path: Path) -> Dict[str, Any]:
        """Generate migration report for a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            issues = self.check_compatibility_issues(content)

            return {
                'file_path': str(file_path),
                'total_issues': len(issues),
                'issues': issues,
                'severity_counts': self._count_severities(issues),
                'migration_required': len(issues) > 0
            }

        except Exception as e:
            return {
                'file_path': str(file_path),
                'error': str(e),
                'migration_required': False
            }

    def _count_severities(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {'high': 0, 'medium': 0, 'low': 0}
        for issue in issues:
            severity = issue.get('severity', 'low')
            counts[severity] = counts.get(severity, 0) + 1
        return counts


def create_migration_checklist():
    """Create a migration checklist"""
    checklist = """
📋 MIGRATION CHECKLIST

□ 1. Install dependencies
   □ pip install pydantic (optional, for type validation)

□ 2. Update imports
   □ Replace globalconfig imports with improved_globalconfig

□ 3. Update configuration creation
   □ Replace PawnlibConfig() with create_improved_config()

□ 4. Update environment variable handling
   □ Remove manual fill_config_from_environment() calls

□ 5. Update configuration file handling
   □ Pass config_file parameter to create_improved_config()

□ 6. Update logger configuration
   □ Use simplified logger config without PAWN_ prefixes

□ 7. Add type validation (optional)
   □ Create custom schema classes for validation

□ 8. Update tests
   □ Use context managers for test isolation

□ 9. Performance optimization
   □ Remove unnecessary global variable access

□ 10. Documentation
    □ Update documentation with new patterns

□ 11. Testing
    □ Run comprehensive tests with new configuration

□ 12. Deployment
    □ Deploy with backward compatibility enabled
    """

    return checklist


def run_migration_assistant():
    """Run interactive migration assistant"""
    guide = MigrationGuide()

    print("🚀 Pawnlib Configuration Migration Assistant")
    print("=" * 50)

    while True:
        print("\nWhat would you like to do?")
        print("1. View migration guide")
        print("2. Check file for compatibility issues")
        print("3. Show migration checklist")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == "1":
            guide.print_migration_guide()

        elif choice == "2":
            file_path = input("Enter file path to check: ").strip()
            try:
                path = Path(file_path)
                if path.exists():
                    report = guide.generate_migration_report(path)
                    print(f"\n📊 Migration Report for {file_path}")
                    print("-" * 50)
                    print(f"Total issues found: {report['total_issues']}")

                    if report['total_issues'] > 0:
                        print("\nIssues by severity:")
                        for severity, count in report['severity_counts'].items():
                            if count > 0:
                                print(f"  {severity.upper()}: {count}")

                        print("\nDetailed issues:")
                        for issue in report['issues']:
                            print(f"\n  ⚠️  {issue['issue']}")
                            print(f"      Pattern: {issue['pattern']}")
                            print(f"      Lines: {', '.join(map(str, issue['line_numbers']))}")
                            print(f"      Suggestion: {issue['suggestion']}")
                    else:
                        print("✅ No compatibility issues found!")

                else:
                    print("❌ File not found!")

            except Exception as e:
                print(f"❌ Error checking file: {e}")

        elif choice == "3":
            print(create_migration_checklist())

        elif choice == "4":
            print("👋 Migration assistant closed. Good luck with your migration!")
            break

        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    run_migration_assistant()
