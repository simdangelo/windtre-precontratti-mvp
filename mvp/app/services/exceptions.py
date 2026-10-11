class DomainError(Exception):
    """Base per tutti gli errori di dominio."""


class DomainNotFoundError(DomainError):
    pass


class DomainValidationError(DomainError):
    pass


class DuplicateNameError(DomainValidationError):
    pass


class OfferNotFoundError(DomainNotFoundError):
    pass


class DocumentNotFoundError(DomainNotFoundError):
    pass


class TemplateNotFoundError(DomainNotFoundError):
    pass


class BlockNotFoundError(DomainNotFoundError):
    pass


class VoceNotFoundError(DomainNotFoundError):
    pass


class VoceAlreadyExistsError(DomainValidationError):
    pass


class FieldNotFoundError(DomainNotFoundError):
    pass


class TechnologyNotFoundError(DomainNotFoundError):
    pass


class BulkOperationNotFoundError(DomainNotFoundError):
    pass


class InvalidRowError(DomainValidationError):
    pass


class GenerationError(DomainError):
    pass
