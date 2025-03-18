def process_batch(self, images):
    self._cancelled = False  # initialize cancellation flag
    # ... existing code for summary initialization ...
    for image in images:
         if self._cancelled:  # check if cancellation was requested
             break
         # ... existing processing logic ...
    # ... existing code for returning summary ... 

    def cancel_batch(self):
        """Sets the cancellation flag to True to cancel ongoing batch processing."""
        self._cancelled = True
        # You might also want to add any cleanup logic here if necessary 