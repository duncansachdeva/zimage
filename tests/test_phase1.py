import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
import shutil
from src.core.optimized_processor import OptimizedProcessor


class DummyAction:
    def __init__(self, name, params):
        self.name = name
        self.params = params


def dummy_method(input_file, output_file, **params):
    # Simulate processing by copying the file
    with open(input_file, 'rb') as f:
        data = f.read()
    with open(output_file, 'wb') as f:
        f.write(data)
    return True


def dummy_process_with_verification(self, method, current_file, temp_file, **params):
    return method(current_file, temp_file, **params)


def test_cache_and_parallel():
    # create temporary directory and dummy file
    tmp_dir = tempfile.mkdtemp()
    try:
        file_path = os.path.join(tmp_dir, "test.jpg")
        with open(file_path, "wb") as f:
            f.write(b"dummy data")

        dummy_action = DummyAction("Dummy Action", {"param1": "value1"})
        actions = [dummy_action]

        proc = OptimizedProcessor()
        # Monkey patch process_with_verification
        proc.process_with_verification = dummy_process_with_verification.__get__(proc, OptimizedProcessor)
        # Monkey patch generate_output_path to return a consistent file name
        proc.generate_output_path = lambda file, output_dir, naming_option, custom_suffix, file_index=None: os.path.join(output_dir, "output.jpg")
        # Set dummy method for the action
        setattr(proc, "dummy_action", dummy_method)

        output_dir = tmp_dir
        naming_option = "default"  # not sequential
        custom_suffix = ""
        file_index = 1

        # First run should process the file and cache the result
        out1 = proc.process_file(file_path, actions, output_dir, naming_option, custom_suffix, file_index)
        # Second run should hit cache
        out2 = proc.process_file(file_path, actions, output_dir, naming_option, custom_suffix, file_index)

        assert out1 == out2, "Cache not working, outputs differ"
        assert os.path.exists(out1), "Output file does not exist"

        # Test parallel processing with one file
        results = proc.process_batch_parallel([file_path], actions, output_dir, naming_option, custom_suffix)
        assert len(results) == 1, "Parallel processing did not return one result"
        assert results[0][1] == out1, "Parallel processing result does not match expected output"
    finally:
        shutil.rmtree(tmp_dir)


if __name__ == '__main__':
    test_cache_and_parallel()
    print("All Phase 1 tests passed.") 