class Action:
    """Represents an image processing action with parameters."""
    
    def __init__(self, name=None):
        """Initialize an action.
        
        Args:
            name (str, optional): Name of the action. Defaults to None.
        """
        self.name = name
        self.params = {}
        
    def __str__(self):
        """Return string representation of the action."""
        params_str = ', '.join(f'{k}={v}' for k, v in self.params.items())
        return f"{self.name} ({params_str})" 