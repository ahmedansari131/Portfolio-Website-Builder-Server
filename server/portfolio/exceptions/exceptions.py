class TemplateRetrievalError(Exception):
    """Custom exception for errors during template retrieval from S3."""
    pass

class DataNotPresent(Exception):
    """Custom exception for errors data already present in db."""
    pass

class GeneralError(Exception):
    """Custom exception for any errors."""
    pass