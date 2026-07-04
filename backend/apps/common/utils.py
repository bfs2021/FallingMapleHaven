from rest_framework.response import Response


def safe_int(value, default=1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def api_response(data=None, code=0, message="success", status=200):
    return Response({"code": code, "message": message, "data": data}, status=status)


def paginate_queryset(queryset, request, page_size=20):
    page = safe_int(request.query_params.get("page"), 1)
    start = (page - 1) * page_size
    end = start + page_size
    total = queryset.count()
    page_items = queryset[start:end]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": page_items,
    }
