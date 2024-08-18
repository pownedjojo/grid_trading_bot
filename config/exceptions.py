class ConfigError(Exception):
    pass

class ConfigFileNotFoundError(ConfigError):
    def __init__(self, config_file, message="Configuration file not found"):
        self.config_file = config_file
        self.message = f"{message}: {config_file}"
        super().__init__(self.message)

class ConfigValidationError(ConfigError):
    def __init__(self, missing_fields, message="Configuration validation error"):
        self.missing_fields = missing_fields
        self.message = f"{message}: Missing required fields - {', '.join(missing_fields)}"
        super().__init__(self.message)

class ConfigParseError(ConfigError):
    def __init__(self, config_file, original_exception, message="Error parsing configuration file"):
        self.config_file = config_file
        self.original_exception = original_exception
        self.message = f"{message} ({config_file}): {str(original_exception)}"
        super().__init__(self.message)