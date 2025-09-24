from functools import lru_cache

from ..database import repo
from ..services.ocr_service import OCRService
from ..services.parser_service import ParserService


@lru_cache(maxsize=1)
def get_ocr_service() -> OCRService:
    return OCRService()


@lru_cache(maxsize=1)
def get_parser_service() -> ParserService:
    return ParserService()


def get_repo():
    return repo


from ..services.queue_service import InMemoryQueueService


@lru_cache(maxsize=1)
def get_queue_service() -> InMemoryQueueService:
    return InMemoryQueueService()
