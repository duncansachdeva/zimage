from concurrent.futures import ThreadPoolExecutor, as_completed
from src.core.image_processor import ImageProcessor
from loguru import logger
import os


class OptimizedProcessor(ImageProcessor):
    def __init__(self, max_workers=4):
        super().__init__()
        self.max_workers = max_workers
        # Simple cache: key is a tuple (file, action_list) and value is output_path
        self.cache = {}

    def process_file(self, file, actions, output_dir, naming_option, custom_suffix, file_index):
        """Process a single file through the specified actions.

        Returns the output path if successful, or None otherwise.
        """
        output_path = self.generate_output_path(
            file, output_dir, naming_option, custom_suffix,
            file_index if naming_option == 'sequential' else None
        )
        # Create a cache key: using file path and tuple of action names with parameters
        key = (file, tuple((action.name, frozenset(action.params.items())) for action in actions))
        if key in self.cache:
            logger.info(f"Cache hit for {file}")
            return self.cache[key]

        current_file = file
        temp_file = None
        success = True
        for action_idx, action in enumerate(actions, 1):
            if action_idx < len(actions):
                temp_file = f"{output_path}.temp{action_idx}"
            else:
                temp_file = output_path

            method_name = action.name.lower().replace(" ", "_")
            method = getattr(self, method_name, None)
            if not method:
                logger.error(f"Method {method_name} not found in processor")
                success = False
                break

            success = self.process_with_verification(method, current_file, temp_file, **action.params)
            if not success:
                logger.error(f"Processing failed for {file} on action: {action}")
                break
            current_file = temp_file

        if success:
            self.cache[key] = output_path
            # Remove temporary files
            for i in range(1, len(actions)):
                temp = f"{output_path}.temp{i}"
                if os.path.exists(temp):
                    try:
                        os.remove(temp)
                    except Exception as e:
                        logger.error(f"Failed to remove temp file {temp}: {e}")
            return output_path
        else:
            return None

    def process_batch_parallel(self, files, actions, output_dir, naming_option, custom_suffix, progress_callback=None, cancel_flag=None):
        """Processes multiple files in parallel and returns a list of tuples (file, output_path). Optionally, calls progress_callback(completed, total) after each file is processed. The cancel_flag is a callable that returns True if cancellation is requested."""
        results = []
        total = len(files)
        processed_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self.process_file, file, actions, output_dir, naming_option, custom_suffix, idx+1): file
                for idx, file in enumerate(files)
            }
            for future in as_completed(future_to_file):
                if cancel_flag is not None and cancel_flag():
                    for fut in future_to_file:
                        fut.cancel()
                    break
                file = future_to_file[future]
                try:
                    result = future.result()
                    results.append((file, result))
                except Exception as exc:
                    logger.error(f"{file} generated an exception: {exc}")
                    results.append((file, None))
                processed_count += 1
                if progress_callback is not None:
                    progress_callback(processed_count, total)
        return results 