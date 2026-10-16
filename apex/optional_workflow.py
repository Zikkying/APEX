"""Package registration without importing the optional workflow engine."""
import sys

class PackageRegistry(list):
    def append(self, path):
        if path not in self:
            super().append(path)
        module = sys.modules.get("dflow.python")
        if module is not None and path not in module.upload_packages:
            module.upload_packages.append(path)

upload_packages = PackageRegistry()

def enable_workflow():
    try:
        from dflow.python import upload_packages as packages
    except ImportError as exc:
        raise RuntimeError("Install apex-flow[workflow] to use workflow commands") from exc
    for path in upload_packages:
        if path not in packages:
            packages.append(path)
