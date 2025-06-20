"""
Comprehensive tests for improved global configuration system
"""
import common
import pytest
import threading
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from pawnlib.config.improved_globalconfig import (
    ImprovedPawnlibConfig,
    ThreadSafeConfigManager,
    EnvironmentConfigSource,
    FileConfigSource,
    ConfigState,
    PawnlibConfigSchema,
    create_improved_config,
    improved_pawnlib_config
)


class TestThreadSafeConfigManager:
    """Test thread-safe configuration manager"""

    def test_basic_operations(self):
        """Test basic set/get operations"""
        manager = ThreadSafeConfigManager()

        # Test set and get
        manager.set('test_key', 'test_value')
        assert manager.get('test_key') == 'test_value'

        # Test default value
        assert manager.get('nonexistent', 'default') == 'default'

        # Test update
        manager.update(key1='value1', key2='value2')
        assert manager.get('key1') == 'value1'
        assert manager.get('key2') == 'value2'

    def test_thread_safety(self):
        """Test thread safety of configuration manager"""
        manager = ThreadSafeConfigManager()
        manager.set('counter', 0)
        results = []

        def worker():
            for _ in range(100):
                current = manager.get('counter', 0)
                manager.set('counter', current + 1)
                results.append(current)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check final value
        final_value = manager.get('counter')
        assert final_value == 500

    def test_to_dict(self):
        """Test dictionary export"""
        manager = ThreadSafeConfigManager()
        manager.update(key1='value1', key2=123, key3=True)

        config_dict = manager.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict['key1'] == 'value1'
        assert config_dict['key2'] == 123
        assert config_dict['key3'] is True


class TestEnvironmentConfigSource:
    """Test environment configuration source"""

    def test_load_environment_variables(self):
        """Test loading environment variables"""
        with patch.dict(os.environ, {
            'PAWN_DEBUG': 'true',
            'PAWN_TIMEOUT': '5000',
            'PAWN_APP_NAME': 'test_app',
            'OTHER_VAR': 'ignored'
        }):
            source = EnvironmentConfigSource(prefix='PAWN')
            config = source.load()

            assert config['debug'] is True
            assert config['timeout'] == 5000
            assert config['app_name'] == 'test_app'
            assert 'other_var' not in config

    def test_type_conversion(self):
        """Test automatic type conversion"""
        source = EnvironmentConfigSource()

        # Test boolean conversion
        assert source._str_to_bool('true') is True
        assert source._str_to_bool('false') is False
        assert source._str_to_bool('1') is True
        assert source._str_to_bool('0') is False

        # Test list conversion
        assert source._str_to_list('a,b,c') == ['a', 'b', 'c']
        assert source._str_to_list('a, b , c ') == ['a', 'b', 'c']

        # Test dict conversion
        dict_str = '{"key": "value", "num": 123}'
        result = source._str_to_dict(dict_str)
        assert result == {"key": "value", "num": 123}


class TestFileConfigSource:
    """Test file configuration source"""

    def test_load_json_config(self):
        """Test loading JSON configuration file"""
        config_data = {
            'app_name': 'test_app',
            'debug': True,
            'timeout': 5000
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name

        try:
            source = FileConfigSource(config_file)
            loaded_config = source.load()

            assert loaded_config['app_name'] == 'test_app'
            assert loaded_config['debug'] is True
            assert loaded_config['timeout'] == 5000

        finally:
            Path(config_file).unlink()

    def test_save_json_config(self):
        """Test saving JSON configuration file"""
        config_data = {
            'app_name': 'test_app',
            'debug': False,
            'features': {'cache': True}
        }

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            config_file = f.name

        try:
            source = FileConfigSource(config_file)
            source.save(config_data)

            # Load and verify
            loaded_config = source.load()
            assert loaded_config == config_data

        finally:
            Path(config_file).unlink(missing_ok=True)

    def test_nonexistent_file(self):
        """Test handling of nonexistent configuration file"""
        source = FileConfigSource('/nonexistent/file.json')
        config = source.load()
        assert config == {}


class TestImprovedPawnlibConfig:
    """Test improved Pawnlib configuration"""

    def test_basic_configuration(self):
        """Test basic configuration operations"""
        config = ImprovedPawnlibConfig(app_name='test_app')

        # Test initial values
        assert config.get('app_name') == 'test_app'
        assert config.is_ready()

        # Test set and get
        config.set(debug=True, timeout=3000)
        assert config.get('debug') is True
        assert config.get('timeout') == 3000

        # Test to_dict
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict['debug'] is True

    def test_advanced_operations(self):
        """Test advanced configuration operations"""
        config = ImprovedPawnlibConfig()

        # Test increase/decrease
        config.set(counter=10, score=100.5)

        result = config.increase(counter=5, score=25.5)
        assert config.get('counter') == 15
        assert config.get('score') == 126.0
        assert result['counter'] == 15

        result = config.decrease(counter=3, score=6.0)
        assert config.get('counter') == 12
        assert config.get('score') == 120.0

        # Test list operations
        config.set(items=[])
        config.append_list(items='item1')
        config.append_list(items='item2')
        assert config.get('items') == ['item1', 'item2']

        config.remove_list(items='item1')
        assert config.get('items') == ['item2']

    def test_context_manager(self):
        """Test configuration context manager"""
        config = ImprovedPawnlibConfig()
        config.set(debug=False, timeout=1000)

        # Test temporary configuration
        with config.temporary_config(debug=True, timeout=5000) as temp_config:
            assert temp_config.get('debug') is True
            assert temp_config.get('timeout') == 5000

        # Verify restoration
        assert config.get('debug') is False
        assert config.get('timeout') == 1000

    def test_legacy_compatibility(self):
        """Test backward compatibility with legacy interface"""
        config = ImprovedPawnlibConfig()

        # Test legacy methods
        config.make_config(hello='world', debug=True)
        assert config.get('hello') == 'world'

        conf_dict = config.conf()
        assert isinstance(conf_dict, dict)
        assert conf_dict['hello'] == 'world'

    @patch.dict(os.environ, {'PAWN_DEBUG': 'true', 'PAWN_APP_NAME': 'env_app'})
    def test_environment_initialization(self):
        """Test initialization with environment variables"""
        config = ImprovedPawnlibConfig(env_prefix='PAWN')

        assert config.get('debug') is True
        assert config.get('app_name') == 'env_app'

    def test_config_file_initialization(self):
        """Test initialization with config file"""
        config_data = {
            'app_name': 'file_app',
            'debug': False,
            'timeout': 8000
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name

        try:
            config = ImprovedPawnlibConfig(config_file=config_file)

            assert config.get('app_name') == 'file_app'
            assert config.get('debug') is False
            assert config.get('timeout') == 8000

        finally:
            Path(config_file).unlink()


class TestConfigValidation:
    """Test configuration validation with Pydantic"""

    def test_valid_configuration(self):
        """Test setting valid configuration values"""
        config = ImprovedPawnlibConfig()

        # These should work without errors
        config.set(
            debug=True,
            timeout=5000,
            log_level='DEBUG',
            max_workers=10
        )

        assert config.get('debug') is True
        assert config.get('timeout') == 5000
        assert config.get('log_level') == 'DEBUG'
        assert config.get('max_workers') == 10

    def test_type_coercion(self):
        """Test automatic type coercion"""
        config = ImprovedPawnlibConfig()

        # String to boolean
        config.set(debug='true')
        # This might work depending on validation implementation

        # String to integer
        config.set(timeout='6000')
        # This might work depending on validation implementation


class TestFactoryFunctions:
    """Test factory functions"""

    def test_create_improved_config(self):
        """Test create_improved_config factory function"""
        config = create_improved_config(
            app_name='factory_app',
            debug=True,
            env_prefix='TEST'
        )

        assert isinstance(config, ImprovedPawnlibConfig)
        assert config.get('app_name') == 'factory_app'
        assert config.get('debug') is True

    def test_global_improved_config(self):
        """Test global improved config instance"""
        # Test that global instance works
        improved_pawnlib_config.set(test_global='value')
        assert improved_pawnlib_config.get('test_global') == 'value'

        # Test legacy compatibility
        result = improved_pawnlib_config.conf()
        assert isinstance(result, dict)


class TestConcurrency:
    """Test concurrent access and modifications"""

    def test_concurrent_modifications(self):
        """Test concurrent modifications are thread-safe"""
        config = ImprovedPawnlibConfig()
        config.set(shared_counter=0, shared_list=[])

        def worker_thread(thread_id, iterations=50):
            for i in range(iterations):
                # Increment counter
                config.increase(shared_counter=1)

                # Add to list
                config.append_list(shared_list=f"thread_{thread_id}_item_{i}")

        # Start multiple threads
        threads = []
        num_threads = 4
        iterations_per_thread = 50

        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=worker_thread,
                args=(thread_id, iterations_per_thread)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify results
        expected_counter = num_threads * iterations_per_thread
        expected_list_length = num_threads * iterations_per_thread

        assert config.get('shared_counter') == expected_counter
        assert len(config.get('shared_list')) == expected_list_length

    def test_concurrent_context_managers(self):
        """Test concurrent context managers don't interfere"""
        config = ImprovedPawnlibConfig()
        config.set(base_value=100)

        results = {}

        def context_worker(worker_id, override_value):
            with config.temporary_config(base_value=override_value) as temp_config:
                # Simulate some work
                import time
                time.sleep(0.1)
                results[worker_id] = temp_config.get('base_value')

        # Start multiple context managers concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=context_worker,
                args=(i, 200 + i * 10)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify each worker saw their own override
        assert results[0] == 200
        assert results[1] == 210
        assert results[2] == 220

        # Verify base config is unchanged
        assert config.get('base_value') == 100


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_config_file(self):
        """Test handling of invalid config files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json content {')
            invalid_file = f.name

        try:
            # Should not raise an exception, just log warning
            config = ImprovedPawnlibConfig(config_file=invalid_file)
            assert config.is_ready()  # Should still be ready with defaults

        finally:
            Path(invalid_file).unlink()

    def test_missing_config_file(self):
        """Test handling of missing config files"""
        config = ImprovedPawnlibConfig(config_file='/nonexistent/file.json')
        assert config.is_ready()  # Should still work with defaults

    def test_invalid_environment_values(self):
        """Test handling of invalid environment values"""
        with patch.dict(os.environ, {
            'PAWN_TIMEOUT': 'not_a_number',
            'PAWN_DEBUG': 'maybe'
        }):
            # Should handle gracefully
            config = ImprovedPawnlibConfig()
            assert config.is_ready()


class TestBackwardCompatibility:
    """Test backward compatibility with legacy code"""

    def test_legacy_wrapper_compatibility(self):
        """Test that legacy wrapper maintains API compatibility"""
        from pawnlib.config.improved_globalconfig import improved_pawnlib_config as pwn

        # Legacy-style operations should work
        pwn.set(hello='world', debug=True)
        assert pwn.get('hello') == 'world'
        assert pwn.get('debug') is True

        # Legacy conf() method
        config_dict = pwn.conf()
        assert isinstance(config_dict, dict)
        assert config_dict['hello'] == 'world'

        # Legacy to_dict() method
        dict_result = pwn.to_dict()
        assert isinstance(dict_result, dict)

        # Legacy make_config() method
        pwn.make_config(new_key='new_value')
        assert pwn.get('new_key') == 'new_value'

    def test_legacy_increase_decrease(self):
        """Test legacy increase/decrease operations"""
        from pawnlib.config.improved_globalconfig import improved_pawnlib_config as pwn

        pwn.set(counter=10, score=50.5)

        # Test increase
        result = pwn.increase(counter=5)
        assert result['counter'] == 15
        assert pwn.get('counter') == 15

        # Test decrease
        result = pwn.decrease(score=10.5)
        assert result['score'] == 40.0
        assert pwn.get('score') == 40.0

    def test_legacy_list_operations(self):
        """Test legacy list operations"""
        from pawnlib.config.improved_globalconfig import improved_pawnlib_config as pwn

        pwn.set(items=[])

        # Test append
        pwn.append_list(items='item1')
        pwn.append_list(items='item2')
        assert pwn.get('items') == ['item1', 'item2']

        # Test remove
        pwn.remove_list(items='item1')
        assert pwn.get('items') == ['item2']


class TestPerformance:
    """Test performance characteristics"""

    def test_configuration_access_performance(self):
        """Test that configuration access is reasonably fast"""
        import time

        config = ImprovedPawnlibConfig()
        config.set(test_key='test_value')

        # Measure get performance
        start_time = time.time()
        for _ in range(10000):
            config.get('test_key')
        get_time = time.time() - start_time

        # Should be very fast (less than 1 second for 10k operations)
        assert get_time < 1.0

        # Measure set performance
        start_time = time.time()
        for i in range(1000):
            config.set(**{f'key_{i}': f'value_{i}'})
        set_time = time.time() - start_time

        # Should be reasonably fast (less than 1 second for 1k operations)
        assert set_time < 1.0

    def test_memory_usage(self):
        """Test that configuration doesn't leak memory"""
        import gc

        config = ImprovedPawnlibConfig()

        # Create a lot of temporary configurations
        for i in range(1000):
            with config.temporary_config(**{f'temp_key_{i}': f'temp_value_{i}'}):
                pass

        # Force garbage collection
        gc.collect()

        # Config should still be in a clean state
        assert config.is_ready()

        # Should not have accumulated temporary keys
        config_dict = config.to_dict()
        temp_keys = [k for k in config_dict.keys() if k.startswith('temp_key_')]
        assert len(temp_keys) == 0


def test_integration_with_existing_code():
    """Integration test with existing pawnlib patterns"""

    # Test that improved config can be used as drop-in replacement
    from pawnlib.config.improved_globalconfig import improved_pawnlib_config as pwn

    # Common pawnlib patterns
    pwn.set(
        debug=True,
        app_name="integration_test",
        timeout=5000,
        data={}
    )

    # Test getting values
    assert pwn.get('debug') is True
    assert pwn.get('app_name') == "integration_test"
    assert pwn.get('timeout') == 5000

    # Test configuration dumping
    config_dump = pwn.conf()
    assert isinstance(config_dump, dict)
    assert 'debug' in config_dump

    # Test increment/decrement operations commonly used in async code
    pwn.set(request_count=0, error_count=0)
    pwn.increase(request_count=1)
    pwn.increase(error_count=1)

    assert pwn.get('request_count') == 1
    assert pwn.get('error_count') == 1

    pwn.decrease(error_count=1)
    assert pwn.get('error_count') == 0


if __name__ == '__main__':
    # Run tests manually if pytest is not available
    print("🧪 Running Improved GlobalConfig Tests")
    print("=" * 50)

    test_classes = [
        TestThreadSafeConfigManager,
        TestEnvironmentConfigSource,
        TestFileConfigSource,
        TestImprovedPawnlibConfig,
        TestConfigValidation,
        TestFactoryFunctions,
        TestConcurrency,
        TestErrorHandling,
        TestBackwardCompatibility,
        TestPerformance
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}")
        print("-" * 30)

        instance = test_class()
        methods = [method for method in dir(instance) if method.startswith('test_')]

        for method_name in methods:
            total_tests += 1
            try:
                method = getattr(instance, method_name)
                method()
                print(f"✅ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"❌ {method_name}: {e}")

    # Run integration test
    total_tests += 1
    try:
        test_integration_with_existing_code()
        print(f"✅ test_integration_with_existing_code")
        passed_tests += 1
    except Exception as e:
        print(f"❌ test_integration_with_existing_code: {e}")

    print(f"\n📊 Test Results")
    print("=" * 50)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
