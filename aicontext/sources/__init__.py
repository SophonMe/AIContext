"""Auto-discovery registry for data sources."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import pkgutil

from aicontext.sources.base import DataSource

log = logging.getLogger(__name__)

_registry: dict[str, DataSource] = {}


def _discover() -> None:
    if _registry:
        return
    package_path = __path__
    for importer, modname, ispkg in pkgutil.iter_modules(package_path):
        if modname.startswith("_") or modname == "base":
            continue
        try:
            mod = importlib.import_module(f"{__name__}.{modname}")
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, DataSource)
                        and attr is not DataSource):
                    instance = attr()
                    _registry[instance.source_key] = instance
                    log.debug("Registered source: %s (%s)", instance.name, instance.source_key)
        except Exception as exc:
            log.warning("Failed to load source module %s: %s", modname, exc)

    # Agent-generated sources from ~/.aicontext/data_sources/
    user_ds_dir = os.path.expanduser("~/.aicontext/data_sources")
    if os.path.isdir(user_ds_dir):
        for fname in sorted(os.listdir(user_ds_dir)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            fpath = os.path.join(user_ds_dir, fname)
            modname = fname[:-3]
            try:
                spec = importlib.util.spec_from_file_location(
                    f"aicontext_user_sources.{modname}", fpath)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (isinstance(attr, type)
                            and issubclass(attr, DataSource)
                            and attr is not DataSource):
                        instance = attr()
                        _registry[instance.source_key] = instance
                        log.debug("Registered user source: %s (%s)",
                                  instance.name, instance.source_key)
            except Exception as exc:
                log.warning("Failed to load user source %s: %s", fname, exc)


def get_all_sources() -> dict[str, DataSource]:
    _discover()
    return dict(_registry)


def get_source(key: str) -> DataSource | None:
    _discover()
    return _registry.get(key)
