#!/usr/bin/env python3
"""Portable source-level probes for the 2026-10-22 engineering handoff.

This script reads the pinned bridge.py and help files from the local Git object
store. It executes selected source functions with fake browser/CDP collaborators;
it does not launch a browser, NVDA, or a WASM runtime.
"""
from __future__ import annotations

import ast
import html
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

PIN = "2593b5409c29417965cd34db645a63ecdcaf6af7"
BRIDGE_PATH = "googleTtsForNvda/synthDrivers/googleTtsForNvda/bridge.py"
EN_HELP_PATH = "googleTtsForNvda/doc/en/readme.html"
ZH_HELP_PATH = "googleTtsForNvda/doc/zh_CN/readme.html"


def git_text(root: Path, path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{PIN}:{path}"], cwd=root, text=True, encoding="utf-8"
    )


def find_function(tree: ast.Module, name: str, class_name: str | None = None) -> ast.FunctionDef:
    if class_name is None:
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                return node
    else:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for member in node.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == name:
                        return member
    raise RuntimeError(f"Could not find {class_name + '.' if class_name else ''}{name}")


class ProbeCdpError(Exception):
    pass


class ProbeCancelled(Exception):
    pass


class ProbeLog:
    def debug(self, *args, **kwargs):
        pass


def extract_bridge_method(source: str, method: str) -> ast.FunctionDef:
    class_name = "ChromeTtsBridge" if method == "ensure_connection" else "BrowserProcessManager"
    return find_function(ast.parse(source), method, class_name)


class FakeCdp:
    def __init__(self, fail_runtime: str | None = None):
        self.fail_runtime = fail_runtime
        self.connects: list[str] = []
        self.closes = 0
        self.connected = False

    def is_connected(self):
        return self.connected

    def connect(self, url: str):
        self.connects.append(url)
        runtime = url.rsplit("/", 1)[-1]
        if runtime == self.fail_runtime:
            raise RuntimeError(f"simulated CDP connect failure for {runtime}")
        self.connected = True

    def close(self):
        self.closes += 1
        self.connected = False


class FakeEngine:
    def __init__(self, cancel_at_ready: bool = False, fail_ready_runtime: str | None = None):
        self.cancel_at_ready = cancel_at_ready
        self.fail_ready_runtime = fail_ready_runtime
        self.domain_calls: list[str] = []
        self.ready_calls: list[str] = []

    def enable_cdp_domains(self, cancelEvent=None):
        self.domain_calls.append(cancelEvent.current_runtime if cancelEvent else "none")

    def wait_until_ready(self, cancelEvent=None):
        runtime = cancelEvent.current_runtime if cancelEvent else "none"
        self.ready_calls.append(runtime)
        if self.cancel_at_ready:
            raise ProbeCancelled("simulated user cancellation during harness readiness")
        if runtime == self.fail_ready_runtime:
            raise RuntimeError(f"simulated harness readiness failure for {runtime}")


class RuntimeMarker:
    def __init__(self, current_runtime: str):
        self.current_runtime = current_runtime


class FakeProcessManager:
    def __init__(self, available: list[str]):
        self.available = available
        self.profile_runtime: str | None = None
        self.start_calls: list[tuple[str, ...]] = []
        self.terminated: list[str | None] = []

    def start_and_get_websocket_url(self, cancelEvent=None, skipRuntimes=None):
        skipped = set(skipRuntimes or ())
        self.start_calls.append(tuple(sorted(skipped)))
        for runtime in self.available:
            if runtime not in skipped:
                self.profile_runtime = runtime
                if cancelEvent is not None:
                    cancelEvent.current_runtime = runtime
                return f"ws://probe/{runtime}"
        raise ProbeCdpError("no fake runtime remains")

    def terminate(self):
        self.terminated.append(self.profile_runtime)
        self.profile_runtime = None

    def _log_browser_runtime_failure(self, runtime, error, willTryFallback):
        pass


class FakeBridge:
    def __init__(self, cdp, manager, engine):
        self._lock = threading.RLock()
        self._cdp_client = cdp
        self._process_manager = manager
        self._engine = engine
        self._runtimeReadyAt = 0.0
        self._lastMemoryCheckAt = 0.0
        self._highMemorySampleCount = 0


class FakeStartupManager:
    def __init__(self, fail_launch_for: str | None = "edge", fail_page_for: str | None = None):
        self._lock = threading.RLock()
        self._profileRuntime = None
        self.started: list[str] = []
        self.cleanup: list[bool] = []
        self.fail_launch_for = fail_launch_for
        self.fail_page_for = fail_page_for

    def _prepare_browser_start(self, cancelEvent=None):
        return False

    def _browser_choices_or_raise(self, skipRuntimes=None):
        return (("edge", "edge.exe"), ("brave", "brave.exe"))

    def _start_browser_choice(self, runtime, path, cancelEvent=None):
        self.started.append(runtime)
        self._profileRuntime = runtime
        if runtime == self.fail_launch_for:
            raise RuntimeError("simulated browser launch failure")
        return (1, 2)

    def get_page_websocket_url(self, cancelEvent=None):
        if self._profileRuntime == self.fail_page_for:
            raise RuntimeError("simulated speech-page discovery failure")
        return f"ws://probe/{self._profileRuntime}"

    def _stop_browser_process(self, removeProfile=False):
        self.cleanup.append(removeProfile)

    def _log_browser_runtime_failure(self, runtime, error, willTryFallback):
        pass


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[4]
    bridge_source = git_text(root, BRIDGE_PATH)
    en_help = git_text(root, EN_HELP_PATH)
    zh_help = git_text(root, ZH_HELP_PATH)
    bridge_tree = ast.parse(bridge_source)

    constants = {
        "BROWSER_RUNTIME_EDGE": "edge",
        "BROWSER_RUNTIME_CHROME": "chrome",
        "BROWSER_RUNTIME_BRAVE": "brave",
        "BROWSER_RUNTIMES": ("chrome", "edge", "brave"),
        "DEFAULT_BROWSER_RUNTIME": "chrome",
    }
    function_names = [
        "_normalize_browser_runtime",
        "_runtime_fallback_order",
        "_browser_choices",
        "_find_browser_choice",
        "edge_webview2_blocks_effective_runtime",
    ]
    browser_nodes = [find_function(bridge_tree, name) for name in function_names]
    ensure_node = extract_bridge_method(bridge_source, "ensure_connection")
    startup_node = extract_bridge_method(bridge_source, "start_and_get_websocket_url")
    browser_choice_error_node = find_function(bridge_tree, "_browser_choices_or_raise", "BrowserProcessManager")

    def make_namespace(paths: dict[str, str | None], webview2: bool, configured: str):
        ns = dict(constants)
        ns.update({
            "CONFIG": {"runtime": configured},
            "configured_browser_runtime": lambda: ns["CONFIG"]["runtime"],
            "browser_path_for_runtime": lambda runtime: paths.get(runtime),
            "browser_executable_available": lambda runtime: bool(paths.get(runtime)),
            "edge_webview2_available": lambda: webview2,
            "_friendly_cdp_error": lambda friendly, detail: ProbeCdpError(f"{friendly} | {detail}"),
            "_": lambda text: text,
            "log": ProbeLog(),
            "time": time,
            "threading": threading,
            "CdpCancelled": ProbeCancelled,
            "_raise_if_cancelled": lambda cancelEvent=None: None,
            "_browser_choices": None,
        })
        module = ast.Module(
            body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *browser_nodes],
            type_ignores=[],
        )
        exec(compile(ast.fix_missing_locations(module), BRIDGE_PATH, "exec"), ns)
        return ns

    order_ns = make_namespace({}, False, "chrome")
    configured_orders = {
        "edge": list(order_ns["_runtime_fallback_order"]("edge")),
        "brave": list(order_ns["_runtime_fallback_order"]("brave")),
        "chrome": list(order_ns["_runtime_fallback_order"]("chrome")),
    }
    assert configured_orders["edge"] == ["edge", "chrome", "brave"]
    assert configured_orders["brave"] == ["brave", "chrome", "edge"]
    assert configured_orders["chrome"] == ["chrome", "edge", "brave"]

    # Exercise BrowserProcessManager.start_and_get_websocket_url with fake process actions.
    startup_ns = make_namespace({"edge": "edge.exe", "brave": "brave.exe"}, False, "edge")
    startup_ns.update({"CdpCancelled": ProbeCancelled})
    startup_module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), startup_node],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(startup_module), BRIDGE_PATH, "exec"), startup_ns)
    startup_manager = FakeStartupManager()
    startup_result = startup_ns["start_and_get_websocket_url"](startup_manager)
    assert startup_result == "ws://probe/brave"
    assert startup_manager.started == ["edge", "brave"]
    assert startup_manager.cleanup == [True]

    page_ns = make_namespace({"edge": "edge.exe", "brave": "brave.exe"}, False, "edge")
    page_module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), startup_node],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(page_module), BRIDGE_PATH, "exec"), page_ns)
    page_manager = FakeStartupManager(fail_launch_for=None, fail_page_for="edge")
    page_result = page_ns["start_and_get_websocket_url"](page_manager)
    assert page_result == "ws://probe/brave"
    assert page_manager.started == ["edge", "brave"]
    assert page_manager.cleanup == [True]

    # Exercise ChromeTtsBridge.ensure_connection through a CDP failure and a harness failure.
    fallback_ns = make_namespace({"edge": "edge.exe", "chrome": "chrome.exe", "brave": "brave.exe"}, False, "edge")
    fallback_ns.update({"CdpCancelled": ProbeCancelled, "_raise_if_cancelled": lambda cancelEvent=None: None})
    ensure_module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), ensure_node],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(ensure_module), BRIDGE_PATH, "exec"), fallback_ns)
    original_choices = fallback_ns["_browser_choices"]
    manager = FakeProcessManager(["edge", "chrome", "brave"])
    cdp = FakeCdp(fail_runtime="edge")
    engine = FakeEngine(fail_ready_runtime=None)
    bridge = FakeBridge(cdp, manager, engine)
    fallback_ns["_browser_choices"] = lambda skipRuntimes=None: original_choices(runtime="edge", skipRuntimes=skipRuntimes)
    fallback_ns["ensure_connection"](bridge, cancelEvent=RuntimeMarker("edge"))
    assert cdp.connects == ["ws://probe/edge", "ws://probe/chrome"]
    assert manager.terminated == ["edge"]
    assert manager.start_calls == [(), ("edge",)]

    harness_manager = FakeProcessManager(["edge", "chrome", "brave"])
    harness_cdp = FakeCdp()
    harness_engine = FakeEngine(fail_ready_runtime="edge")
    harness_bridge = FakeBridge(harness_cdp, harness_manager, harness_engine)
    fallback_ns["ensure_connection"](harness_bridge, cancelEvent=RuntimeMarker("edge"))
    assert harness_cdp.connects == ["ws://probe/edge", "ws://probe/chrome"]
    assert harness_manager.terminated == ["edge"]
    assert harness_manager.start_calls == [(), ("edge",)]

    # Cancellation must close/terminate and propagate before another runtime is requested.
    cancel_manager = FakeProcessManager(["edge", "chrome", "brave"])
    cancel_cdp = FakeCdp()
    cancel_engine = FakeEngine(cancel_at_ready=True)
    cancel_bridge = FakeBridge(cancel_cdp, cancel_manager, cancel_engine)
    try:
        fallback_ns["ensure_connection"](cancel_bridge, cancelEvent=RuntimeMarker("edge"))
    except ProbeCancelled:
        pass
    else:
        raise AssertionError("CdpCancelled did not propagate")
    assert cancel_manager.start_calls == [()]
    assert cancel_manager.terminated == ["edge"]
    assert cancel_cdp.closes == 1

    # Edge without WebView2 is skipped when Brave works; it blocks only when no fallback works.
    edge_paths = {"edge": "edge.exe", "chrome": None, "brave": "brave.exe"}
    edge_ns = make_namespace(edge_paths, False, "edge")
    brave_choices = list(edge_ns["_browser_choices"]("edge"))
    brave_blocked = edge_ns["edge_webview2_blocks_effective_runtime"]("edge")
    assert brave_choices == [("brave", "brave.exe")]
    assert brave_blocked is False

    no_fallback_ns = make_namespace({"edge": "edge.exe", "chrome": None, "brave": None}, False, "edge")
    no_fallback_choices = list(no_fallback_ns["_browser_choices"]("edge"))
    edge_blocks = no_fallback_ns["edge_webview2_blocks_effective_runtime"]("edge")
    assert no_fallback_choices == []
    assert edge_blocks is True
    browser_error_module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), browser_choice_error_node],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(browser_error_module), BRIDGE_PATH, "exec"), no_fallback_ns)
    try:
        no_fallback_ns["_browser_choices_or_raise"](object())
    except ProbeCdpError as exc:
        edge_repair_error = str(exc)
    else:
        raise AssertionError("Missing Edge WebView2 did not produce the Edge repair error")
    assert "Microsoft Edge WebView2 Runtime was not found" in edge_repair_error

    # Compare the pinned help documents as content, recording literal headings and settings text.
    en_06 = re.search(r"<h3>Version 0\.6[^<]*</h3>", en_help)
    zh_headings = re.findall(r"<h3>([^<]+)</h3>", zh_help)
    assert en_06 is not None
    assert not any("0.6" in heading for heading in zh_headings)
    assert any("0.5.5" in heading for heading in zh_headings)
    en_setting = re.search(r"<li><strong>Keep Google TTS browser runtime ready in the background:</strong>(.*?)</li>", en_help, re.S)
    assert en_setting is not None
    assert "more memory" in en_setting.group(1) and "keep runtime files open" in en_setting.group(1)
    zh_config = zh_help.split("<h2>配置</h2>", 1)[1].split("<h2>", 1)[0]
    zh_config_labels = [
        html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
        for label in re.findall(r"<li>\s*<strong>(.*?)</strong>", zh_config, re.S)
    ]
    assert any("Chromium 浏览器运行环境" in label for label in zh_config_labels)

    results = {
        "probe": "portable source-level handoff probe",
        "captured_on": "2026-10-22",
        "source_commit": PIN,
        "source_paths": [BRIDGE_PATH, EN_HELP_PATH, ZH_HELP_PATH],
        "method": "Selected functions were extracted from the pinned Git objects and executed with fake browser/CDP collaborators; help content was compared directly. No browser, NVDA, network service, or WASM engine was launched.",
        "checks": [
            {"name": "configured runtime order and de-duplication", "status": "PASS", "results": configured_orders},
            {"name": "browser process launch failure cleanup and fallback", "status": "PASS", "attempted": startup_manager.started, "profile_cleanup_remove": startup_manager.cleanup, "result": startup_result},
            {"name": "speech-page discovery failure cleanup and fallback", "status": "PASS", "attempted": page_manager.started, "profile_cleanup_remove": page_manager.cleanup, "result": page_result},
            {"name": "CDP connection failure cleanup and fallback", "status": "PASS", "attempted": ["edge", "chrome"], "terminated_after_failure": manager.terminated},
            {"name": "harness readiness failure cleanup and fallback", "status": "PASS", "attempted": ["edge", "chrome"], "terminated_after_failure": harness_manager.terminated},
            {"name": "cancellation stops without fallback", "status": "PASS", "start_calls": cancel_manager.start_calls, "terminated": cancel_manager.terminated, "cdp_close_count": cancel_cdp.closes},
            {"name": "Edge WebView2 missing with usable Brave", "status": "PASS", "choices": brave_choices, "Edge_blocks_runtime": brave_blocked},
            {"name": "Edge WebView2 missing with no other usable runtime", "status": "PASS", "choices": no_fallback_choices, "Edge_is_blocking_condition": edge_blocks, "error": edge_repair_error},
            {"name": "Simplified Chinese help comparison", "status": "CONFIRMED_GAP", "English_version_heading": en_06.group(0).strip(), "zh_CN_version_headings": zh_headings, "English_setting_and_warning": re.sub(r"\\s+", " ", en_setting.group(1)).strip(), "zh_CN_configuration_labels": zh_config_labels, "manual_assessment": "The zh_CN configuration list includes browser runtime selection/status but has no background-readiness setting or its memory/runtime-files warning."},
        ],
        "limitations": [
            "The fake collaborators validate source control flow only; they do not prove Windows process, WebSocket, WebView2, NVDA, accessibility, or speech behavior.",
            "Original /workspace/review/edge_nvda.json and browser-capture logs were not present in this checkout and were not recreated.",
            "The historical Linux package artifact listed in the handoff was not present in this checkout; its prior recorded result remains historical evidence only.",
            "Manual native Windows/NVDA acceptance remains NOT RUN.",
        ],
    }
    output = Path(__file__).with_name("portable_probe.json")
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
