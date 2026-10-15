"""Normalize the documented job identifier before DPDispatcher downloads."""
import inspect


def normalize_job_detail(detail, requested_id):
    if not isinstance(detail, dict):
        raise RuntimeError("OpenAPI job detail must be an object")
    result = dict(detail)
    identifier = result.get("id", result.get("jobId"))
    if identifier is None or str(identifier) != str(requested_id):
        raise RuntimeError("OpenAPI job detail identifier does not match request")
    if result.get("jobId") is not None and str(result["jobId"]) != str(identifier):
        raise RuntimeError("OpenAPI job detail has conflicting identifiers")
    result["id"] = identifier
    return result


def dispatcher_pre_script():
    return inspect.getsource(normalize_job_detail) + '''
from dpdispatcher.contexts.openapi_context import Job as _APEXOpenAPIJob
_apex_original_detail = _APEXOpenAPIJob.detail
def _apex_detail(self, job_id, *args, **kwargs):
    return normalize_job_detail(_apex_original_detail(self, job_id, *args, **kwargs), job_id)
_APEXOpenAPIJob.detail = _apex_detail
'''
