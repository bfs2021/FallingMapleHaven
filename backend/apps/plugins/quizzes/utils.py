from collections.abc import Iterable
from typing import cast

from django.db.models import QuerySet

from .models import QuizQuestionBank


def filter_question_bank_by_tag(queryset: QuerySet[QuizQuestionBank], tag: str) -> QuerySet[QuizQuestionBank]:
    if not tag:
        return queryset
    rows = cast(Iterable[tuple[int, list[str] | None]], queryset.values_list("pk", "tags"))
    matching_ids = [question_id for question_id, tags in rows if tag in (tags or [])]
    return queryset.filter(pk__in=matching_ids)
