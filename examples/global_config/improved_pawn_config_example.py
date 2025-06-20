"""
Usage Examples for Improved Global Configuration

This file demonstrates how to use the improved configuration system
and how to migrate from the legacy system.
"""
import common
from pawnlib.config.improved_globalconfig import (
    create_improved_config,
    ImprovedPawnlibConfig,
    improved_pawnlib_config,
    ConfigState,
    PawnlibConfigSchema
)
from pathlib import Path
import tempfile
import json


def basic_usage_example():
    """Basic usage of the improved configuration system"""
    print("=== Basic Usage Example ===")

    # Create a new configuration instance
    config = create_improved_config(
        app_name="my_app",
        env_prefix="MYAPP",
        debug=True
    )

    # Set configuration values
    config.set(
        database_url="postgresql://localhost/mydb",
        redis_host="localhost",
        redis_port=6379,
        api_timeout=30
    )

    # Get configuration values
    db_url = config.get("database_url")
    timeout = config.get("api_timeout", 60)  # with default

    print(f"Database URL: {db_url}")
    print(f"API Timeout: {timeout}")
    print(f"Configuration: {config.to_dict()}")


def environment_variables_example():
    """Example using environment variables"""
    print("\n=== Environment Variables Example ===")

    import os

    # Set environment variables
    os.environ["PAWN_DEBUG"] = "true"
    os.environ["PAWN_APP_NAME"] = "env_app"
    os.environ["PAWN_TIMEOUT"] = "5000"
    os.environ["PAWN_MAX_WORKERS"] = "8"

    # Create config that will automatically load from environment
    config = create_improved_config()

    print(f"Debug from env: {config.get('debug')}")
    print(f"App name from env: {config.get('app_name')}")
    print(f"Timeout from env: {config.get('timeout')}")
    print(f"Max workers from env: {config.get('max_workers')}")


def config_file_example():
    """Example using configuration files"""
    print("\n=== Configuration File Example ===")

    # Create a temporary config file
    config_data = {
        "app_name": "file_app",
        "debug": False,
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "mydb"
        },
        "features": {
            "cache_enabled": True,
            "max_connections": 100
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_file_path = f.name

    try:
        # Create config with file
        config = create_improved_config(config_file=config_file_path)

        print(f"App name from file: {config.get('app_name')}")
        print(f"Debug from file: {config.get('debug')}")
        print(f"Full config: {config.to_dict()}")

    finally:
        # Clean up
        Path(config_file_path).unlink(missing_ok=True)


def advanced_operations_example():
    """Example of advanced configuration operations"""
    print("\n=== Advanced Operations Example ===")

    config = create_improved_config()

    # Initialize some counters
    config.set(
        request_count=0,
        error_count=0,
        success_rate=0.0,
        active_connections=[]
    )

    # Increment counters
    config.increase(request_count=1, error_count=0)
    print(f"After first request: {config.get('request_count')}")

    config.increase(request_count=5, error_count=2)
    print(f"After more requests: {config.get('request_count')}, errors: {config.get('error_count')}")

    # Decrease counters
    config.decrease(error_count=1)
    print(f"After error fix: {config.get('error_count')}")

    # List operations
    config.append_list(active_connections="conn_1")
    config.append_list(active_connections="conn_2")
    config.append_list(active_connections="conn_3")
    print(f"Active connections: {config.get('active_connections')}")

    config.remove_list(active_connections="conn_2")
    print(f"After removing conn_2: {config.get('active_connections')}")


def context_manager_example():
    """Example using context manager for temporary configuration"""
    print("\n=== Context Manager Example ===")

    config = create_improved_config()
    config.set(debug=False, timeout=1000)

    print(f"Original debug: {config.get('debug')}")
    print(f"Original timeout: {config.get('timeout')}")

    # Temporarily override configuration
    with config.temporary_config(debug=True, timeout=5000) as temp_config:
        print(f"Temporary debug: {temp_config.get('debug')}")
        print(f"Temporary timeout: {temp_config.get('timeout')}")

    # Configuration is restored
    print(f"Restored debug: {config.get('debug')}")
    print(f"Restored timeout: {config.get('timeout')}")


def type_safety_example():
    """Example demonstrating type safety and validation"""
    print("\n=== Type Safety Example ===")

    config = create_improved_config()

    try:
        # Valid values
        config.set(debug=True, timeout=5000, log_level="DEBUG")
        print("Valid configuration set successfully")

        # Invalid log level (will raise error if pydantic is available)
        try:
            config.set(log_level="INVALID_LEVEL")
        except ValueError as e:
            print(f"Validation error caught: {e}")

        # Invalid timeout (negative value)
        try:
            config.set(timeout=-100)
        except ValueError as e:
            print(f"Validation error caught: {e}")

    except Exception as e:
        print(f"Configuration error: {e}")


def legacy_compatibility_example():
    """Example showing backward compatibility with legacy code"""
    print("\n=== Legacy Compatibility Example ===")

    # Use the global improved config instance (backward compatible)
    from pawnlib.config.improved_globalconfig import improved_pawnlib_config as config

    # Legacy-style usage still works
    config.set(hello="world", debug=True)
    print(f"Hello: {config.get('hello')}")
    print(f"Debug: {config.get('debug')}")

    # Legacy conf() method
    all_config = config.conf()
    print(f"All config: {all_config}")

    # Legacy make_config method
    config.make_config(new_feature=True, version="1.0.0")
    print(f"After make_config: {config.get('new_feature')}")


def custom_schema_example():
    """Example using custom configuration schema"""
    print("\n=== Custom Schema Example ===")

    try:
        from pydantic import BaseModel, Field

        class MyAppConfigSchema(BaseModel):
            app_name: str = Field(default="my_app")
            database_url: str = Field(default="sqlite:///app.db")
            redis_url: str = Field(default="redis://localhost:6379")
            max_connections: int = Field(default=10, ge=1, le=1000)
            enable_cache: bool = Field(default=True)
            log_level: str = Field(default="INFO")

            class Config:
                extra = "allow"

        # Create config with custom schema
        config = create_improved_config(schema_class=MyAppConfigSchema)

        # Set values according to schema
        config.set(
            app_name="custom_app",
            database_url="postgresql://localhost/mydb",
            max_connections=50
        )

        print(f"Custom config: {config.to_dict()}")

    except ImportError:
        print("Pydantic not available, using default schema")
        config = create_improved_config()
        config.set(app_name="fallback_app")
        print(f"Fallback config: {config.to_dict()}")


def monitoring_and_inspection_example():
    """Example of configuration monitoring and inspection"""
    print("\n=== Monitoring and Inspection Example ===")

    config = create_improved_config()

    # Check configuration state
    print(f"Configuration state: {config.get_state()}")
    print(f"Is ready: {config.is_ready()}")

    # Set some configuration
    config.set(
        app_name="monitored_app",
        debug=True,
        features={"feature1": True, "feature2": False}
    )

    # Inspect configuration (uses rich if available)
    print("\nInspecting configuration:")
    try:
        config.inspect()
    except Exception:
        # Fallback if rich is not available
        import pprint
        pprint.pprint(config.to_dict())


def migration_from_legacy_example():
    """Example showing how to migrate from legacy globalconfig"""
    print("\n=== Migration from Legacy Example ===")

    # OLD WAY (legacy globalconfig)
    print("Legacy style (still supported):")
    from pawnlib.config.improved_globalconfig import improved_pawnlib_config as pwn

    pwn.set(
        PAWN_LOGGER={"app_name": "legacy_app"},
        PAWN_DEBUG=True,
        app_name="legacy_style",
        data={}
    )

    print(f"Legacy get: {pwn.get('PAWN_DEBUG')}")
    print(f"Legacy conf: {pwn.conf()}")

    # NEW WAY (improved)
    print("\nImproved style:")
    new_config = create_improved_config(app_name="new_style")

    new_config.set(
        debug=True,
        logger_config={"app_name": "new_app"},
        timeout=5000
    )

    print(f"Improved get: {new_config.get('debug')}")
    print(f"Improved config: {new_config.to_dict()}")


def performance_example():
    """Example demonstrating thread safety and performance"""
    print("\n=== Performance and Thread Safety Example ===")

    import threading
    import time

    config = create_improved_config()
    config.set(counter=0, results=[])

    def worker_thread(thread_id: int):
        """Worker thread that modifies configuration"""
        for i in range(100):
            # Thread-safe increment
            config.increase(counter=1)

            # Thread-safe list append
            config.append_list(results=f"thread_{thread_id}_item_{i}")

            time.sleep(0.001)  # Small delay

    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker_thread, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    final_counter = config.get("counter")
    final_results_count = len(config.get("results", []))

    print(f"Final counter (should be 500): {final_counter}")
    print(f"Final results count (should be 500): {final_results_count}")
    print("Thread safety test completed successfully!")


def run_all_examples():
    """Run all examples"""
    print("🚀 Running Improved Pawnlib Configuration Examples\n")

    basic_usage_example()
    environment_variables_example()
    config_file_example()
    advanced_operations_example()
    context_manager_example()
    type_safety_example()
    legacy_compatibility_example()
    custom_schema_example()
    monitoring_and_inspection_example()
    migration_from_legacy_example()
    performance_example()

    print("\n✅ All examples completed successfully!")


if __name__ == "__main__":
    run_all_examples()
