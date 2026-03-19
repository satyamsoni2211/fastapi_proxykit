import httpx
import structlog

logger = structlog.get_logger()


async def fetch_target_openapi(
    target_base_url: str,
    explicit_url: str | None,
    timeout: float = 5.0,
) -> dict | None:
    """
    Fetch OpenAPI spec from a target service.

    If explicit_url is provided, use it. Otherwise, construct
    {target_base_url.rstrip('/')}/openapi.json.

    Returns None if the fetch fails or the response is not valid JSON.
    """
    url = explicit_url or f"{target_base_url.rstrip('/')}/openapi.json"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        logger.warning(
            "proxy.openapi.fetch_failed",
            target_base_url=target_base_url,
            openapi_url=url,
            exc=exc,
        )
        return None


def merge_openapi_schemas(
    proxy_spec: dict,
    target_specs: list[dict],
    path_prefix: str,
) -> dict:
    """
    Merge target OpenAPI paths into the proxy's OpenAPI schema.

    For each path in target_specs:
      - If the path starts with the last segment of path_prefix (e.g., "/users" for prefix "/api/users"),
        replace that segment with path_prefix (e.g., "/users" → "/api/users", "/users/{id}" → "/api/users/{id}")
      - Otherwise, prepend path_prefix to the path
      - Deduplicate: if a path already exists in proxy_spec, skip it
      - Copy only the path item (no component/schema resolution — out of scope)

    Returns the merged spec dict.
    """
    result = {
        "openapi": proxy_spec.get("openapi", "3.1.0"),
        "info": proxy_spec.get("info", {"title": "Proxy API", "version": "1.0.0"}),
        "paths": dict(proxy_spec.get("paths", {})),
    }

    # Get the last segment of path_prefix for substitution matching
    prefix_segments = path_prefix.strip("/").split("/")
    last_prefix_segment = prefix_segments[-1] if prefix_segments else ""

    for spec in target_specs:
        if not spec:
            logger.debug("proxy.openapi.skipping_empty_spec")
            continue
        target_paths = spec.get("paths", {})
        for path, path_item in target_paths.items():
            # Check if path starts with the last segment of prefix (for substitution)
            if last_prefix_segment and path.startswith(f"/{last_prefix_segment}"):
                # Replace the first occurrence of /{last_segment} with path_prefix
                rest_of_path = path[len(f"/{last_prefix_segment}"):]
                prefixed = path_prefix.rstrip("/") + rest_of_path
            else:
                # Otherwise, simply prepend the prefix
                prefixed = f"{path_prefix.rstrip('/')}/{path.lstrip('/')}"
            prefixed = "/" + prefixed.strip("/")
            if prefixed not in result["paths"]:
                result["paths"][prefixed] = path_item
                logger.debug("proxy.openapi.path_merged", path=prefixed)

    return result