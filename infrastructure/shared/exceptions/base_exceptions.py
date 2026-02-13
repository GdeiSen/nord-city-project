"""
Base exceptions for microservices architecture
Provides standardized error handling across all services
"""

from typing import Optional, Dict, Any


class MicroserviceException(Exception):
    """
    Base exception for all microservice-related errors
    Provides structured error information for inter-service communication
    """

    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize microservice exception
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization"""
        return {
            "error": True,
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


class ValidationException(MicroserviceException):
    """
    Exception raised when input validation fails
    Used for invalid request data, missing required fields, etc.
    """

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        """
        Initialize validation exception
        
        Args:
            message: Validation error message
            field: Name of the field that failed validation
            **kwargs: Additional arguments for base exception
        """
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class NotFoundException(MicroserviceException):
    """
    Exception raised when requested resource is not found
    Used for missing entities, invalid IDs, etc.
    """

    def __init__(self, resource: str, identifier: Any, **kwargs):
        """
        Initialize not found exception
        
        Args:
            resource: Name of the resource that was not found
            identifier: Identifier used to search for the resource
            **kwargs: Additional arguments for base exception
        """
        message = f"{resource} not found"
        details = kwargs.get('details', {})
        details.update({
            'resource': resource,
            'identifier': str(identifier)
        })
        
        super().__init__(message, error_code="NOT_FOUND", details=details)


class AuthenticationException(MicroserviceException):
    """
    Exception raised when authentication fails
    Used for invalid credentials, expired tokens, etc.
    """

    def __init__(self, message: str = "Authentication failed", **kwargs):
        """
        Initialize authentication exception
        
        Args:
            message: Authentication error message
            **kwargs: Additional arguments for base exception
        """
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kwargs)


class AuthorizationException(MicroserviceException):
    """
    Exception raised when authorization fails
    Used for insufficient permissions, access denied, etc.
    """

    def __init__(self, message: str = "Access denied", resource: Optional[str] = None, **kwargs):
        """
        Initialize authorization exception
        
        Args:
            message: Authorization error message
            resource: Protected resource that was accessed
            **kwargs: Additional arguments for base exception
        """
        details = kwargs.get('details', {})
        if resource:
            details['resource'] = resource
            
        super().__init__(message, error_code="AUTHORIZATION_ERROR", details=details)


class ServiceUnavailableException(MicroserviceException):
    """
    Exception raised when a required service is unavailable
    Used for service timeouts, connection errors, etc.
    """

    def __init__(self, service: str, reason: Optional[str] = None, **kwargs):
        """
        Initialize service unavailable exception
        
        Args:
            service: Name of the unavailable service
            reason: Reason for service unavailability
            **kwargs: Additional arguments for base exception
        """
        message = f"Service '{service}' is unavailable"
        if reason:
            message += f": {reason}"
            
        details = kwargs.get('details', {})
        details.update({
            'service': service,
            'reason': reason
        })
        
        super().__init__(message, error_code="SERVICE_UNAVAILABLE", details=details)


class DatabaseException(MicroserviceException):
    """
    Exception raised for database-related errors
    Used for connection errors, constraint violations, etc.
    """

    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        """
        Initialize database exception
        
        Args:
            message: Database error message
            operation: Database operation that failed
            **kwargs: Additional arguments for base exception
        """
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
            
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class BusinessLogicException(MicroserviceException):
    """
    Exception raised for business logic violations
    Used for constraint violations, invalid state transitions, etc.
    """

    def __init__(self, message: str, rule: Optional[str] = None, **kwargs):
        """
        Initialize business logic exception
        
        Args:
            message: Business logic error message
            rule: Business rule that was violated
            **kwargs: Additional arguments for base exception
        """
        details = kwargs.get('details', {})
        if rule:
            details['rule'] = rule
            
        super().__init__(message, error_code="BUSINESS_LOGIC_ERROR", details=details)


class ConfigurationException(MicroserviceException):
    """
    Exception raised for configuration-related errors
    Used for missing environment variables, invalid settings, etc.
    """

    def __init__(self, message: str, setting: Optional[str] = None, **kwargs):
        """
        Initialize configuration exception
        
        Args:
            message: Configuration error message
            setting: Configuration setting that is invalid
            **kwargs: Additional arguments for base exception
        """
        details = kwargs.get('details', {})
        if setting:
            details['setting'] = setting
            
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


class SecurityException(MicroserviceException):
    """
    Exception raised for security-related violations
    Used for potential security threats, suspicious activity, etc.
    """

    def __init__(self, message: str, threat_type: Optional[str] = None, **kwargs):
        """
        Initialize security exception
        
        Args:
            message: Security error message
            threat_type: Type of security threat detected
            **kwargs: Additional arguments for base exception
        """
        details = kwargs.get('details', {})
        if threat_type:
            details['threat_type'] = threat_type
            
        super().__init__(message, error_code="SECURITY_ERROR", details=details) 