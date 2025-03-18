import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
import shutil

from src.core.optimized_processor import OptimizedProcessor
from src.ui.main_window import BatchProcessingThread, Action


class DummyAction:
    def __init__(self, name, params):
        self.name = name
        self.params = params


# Dummy method to simulate processing by copying file contents
def dummy_method(input_file, output_file, **params):
    with open(input_file, 'rb') as f:
        data = f.read()
    with open(output_file, 'wb') as f:
        f.write(data)
    return True


def dummy_process_with_verification(self, method, current_file, temp_file, **params):
    return method(current_file, temp_file, **params)


def dummy_generate_output_path(file, output_dir, naming_option, custom_suffix, file_index=None):
    # Returns a consistent output path in the output directory
    return os.path.join(output_dir, "output_" + os.path.basename(file))


def test_batch_processing_thread():
    # Create temporary directory and dummy image files
    tmp_dir = tempfile.mkdtemp()
    try:
        file1 = os.path.join(tmp_dir, "test1.jpg")
        file2 = os.path.join(tmp_dir, "test2.jpg")
        with open(file1, "wb") as f:
            f.write(b"dummy data 1")
        with open(file2, "wb") as f:
            f.write(b"dummy data 2")

        dummy_action = DummyAction("Dummy Action", {"param1": "value1"})
        actions = [dummy_action]

        # Create an instance of OptimizedProcessor and monkey patch required methods
        proc = OptimizedProcessor()
        proc.process_with_verification = dummy_process_with_verification.__get__(proc, OptimizedProcessor)
        proc.generate_output_path = dummy_generate_output_path
        # Set dummy method for the action
        setattr(proc, "dummy_action", dummy_method)

        # Variable to capture results
        results_list = []

        def on_finished(results):
            nonlocal results_list
            results_list = results

        # Instantiate BatchProcessingThread with two dummy files
        thread = BatchProcessingThread(proc, [file1, file2], actions, tmp_dir, "default", "")
        thread.processing_finished.connect(on_finished)
        
        # Directly run the thread's run method (synchronously) since we are not in an event loop
        thread.run()

        # Verify that we have results for both files
        assert len(results_list) == 2, "Expected two results from batch processing"
        for file_processed, output in results_list:
            assert os.path.exists(output), f"Output file {output} was not created for {file_processed}"
            with open(output, 'rb') as f_out, open(file_processed, 'rb') as f_in:
                assert f_out.read() == f_in.read(), "Processed file content does not match original"
        
    finally:
        shutil.rmtree(tmp_dir)


if __name__ == '__main__':
    test_batch_processing_thread()
    print("Phase 2 tests passed.") 