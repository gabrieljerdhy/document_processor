class DocumentProcessingError(Exception):
    """Base class for document processing exceptions."""


class ValidationError(DocumentProcessingError):
    pass


class NotFoundError(DocumentProcessingError):
    pass


class OCRServiceError(DocumentProcessingError):
    pass


class CircuitBreakerOpenError(DocumentProcessingError):
    pass

