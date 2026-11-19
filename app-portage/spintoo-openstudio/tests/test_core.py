import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from spintoo_openstudio.assistant import (
    AssistantError,
    LocalAssistant,
    build_request_payload,
    parse_matrix_draft,
    validate_local_endpoint,
)
from spintoo_openstudio.importers import (
    ImportError as ProfileImportError,
    import_config_files,
    import_overlay_targets,
    import_profile_catalog,
)
from spintoo_openstudio.matrix import BuildMatrix, BuildVariant, MatrixError, MatrixStore
from spintoo_openstudio.scheduler import (
    BuildJob,
    ResourceBudget,
    select_startable_jobs,
    suggested_resource_budget,
)


class MatrixTests(unittest.TestCase):
    def test_matrix_round_trip_and_private_atomic_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "matrix.json"
            store = MatrixStore(path)
            matrix = BuildMatrix([BuildVariant("baseline"), BuildVariant("qt6", vcpus=8)])

            store.save(matrix)

            self.assertEqual(store.load(), matrix)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(tmp).glob(".matrix-*")), [])

    def test_duplicate_names_are_rejected_case_insensitively(self):
        with self.assertRaisesRegex(MatrixError, "duplicated"):
            BuildMatrix([BuildVariant("Base"), BuildVariant("base")]).validate()

    def test_variant_rejects_path_like_names_and_bad_resources(self):
        with self.assertRaises(MatrixError):
            BuildVariant("../outside").validate()
        with self.assertRaises(MatrixError):
            BuildVariant("baseline", vcpus=0).validate()
        with self.assertRaises(MatrixError):
            BuildVariant("baseline", arch="../host").validate()

    def test_unknown_persisted_fields_are_rejected(self):
        with self.assertRaisesRegex(MatrixError, "Unknown"):
            BuildVariant.from_mapping({"name": "baseline", "command": "unsafe"})


class SchedulerTests(unittest.TestCase):
    def test_only_jobs_fitting_both_budgets_are_selected(self):
        pending = [
            BuildJob("a", "base", "cat/a", 4, 4096),
            BuildJob("b", "qt", "cat/a", 4, 4096),
            BuildJob("c", "debug", "cat/a", 2, 2048),
        ]
        running = [BuildJob("running", "base", "cat/b", 4, 4096)]

        started = select_startable_jobs(pending, running, ResourceBudget(10, 10240))

        self.assertEqual([job.job_id for job in started], ["a", "c"])
        self.assertLessEqual(sum(job.vcpus for job in [*running, *started]), 10)
        self.assertLessEqual(sum(job.memory_mib for job in [*running, *started]), 10240)

    def test_oversized_job_stays_queued_without_blocking_smaller_job(self):
        pending = [
            BuildJob("large", "base", "cat/a", 8, 8192),
            BuildJob("small", "base", "cat/b", 2, 2048),
        ]

        started = select_startable_jobs(pending, [], ResourceBudget(4, 4096))

        self.assertEqual([job.job_id for job in started], ["small"])

    def test_suggested_host_budget_is_valid(self):
        budget = suggested_resource_budget()
        budget.validate()
        self.assertGreaterEqual(budget.vcpus, 1)
        self.assertGreaterEqual(budget.memory_mib, 512)


class AssistantTests(unittest.TestCase):
    def test_only_local_http_endpoints_are_allowed(self):
        self.assertEqual(validate_local_endpoint("http://localhost:11434/v1"), "http://localhost:11434/v1/")
        with self.assertRaises(AssistantError):
            validate_local_endpoint("https://example.com/v1")
        with self.assertRaises(AssistantError):
            validate_local_endpoint("http://user:password@localhost/v1")
        with self.assertRaises(AssistantError):
            validate_local_endpoint("http://localhost:invalid/v1")

    def test_local_assistant_does_not_follow_redirects(self):
        class RedirectHandler(BaseHTTPRequestHandler):
            paths = []

            def do_POST(self):
                self.paths.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/redirected")
                self.end_headers()

            def do_GET(self):
                self.paths.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, _format, *_args):
                pass

        server = HTTPServer(("127.0.0.1", 0), RedirectHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            endpoint = f"http://127.0.0.1:{server.server_port}/v1"
            with self.assertRaisesRegex(AssistantError, "HTTP 302"):
                LocalAssistant(endpoint, "test-model").draft("compare variants", [BuildVariant("base")])
            self.assertEqual(RedirectHandler.paths, ["/v1/chat/completions"])
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_request_contains_only_selected_variants(self):
        selected = BuildVariant("selected", package_use="cat/pkg qt6")
        payload = build_request_payload("Compare Qt choices", [selected], "local-model")
        user_content = payload["messages"][1]["content"]

        self.assertIn("selected", user_content)
        self.assertNotIn("unselected", user_content)
        self.assertIn("cat/pkg qt6", user_content)

    def test_model_draft_is_validated_and_not_applied(self):
        content = json.dumps(
            {
                "summary": "Try a Qt-enabled variant.",
                "variants": [
                    {
                        "name": "qt",
                        "vcpus": 4,
                        "memory_mib": 8192,
                        "package_use": "cat/pkg qt6",
                        "accept_keywords": "",
                        "package_mask": "",
                        "package_env": "",
                        "patches": "",
                    }
                ],
            }
        )

        proposal = parse_matrix_draft(content)

        self.assertEqual(proposal.summary, "Try a Qt-enabled variant.")
        self.assertEqual(proposal.variants[0].package_use, "cat/pkg qt6")

    def test_malformed_model_proposal_is_rejected(self):
        with self.assertRaises(AssistantError):
            parse_matrix_draft('{"summary":"no variants","variants":[{"name":"bad/name"}]}')


class ImporterTests(unittest.TestCase):
    def test_imports_existing_profile_catalog_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            path.write_text(json.dumps({
                "profiles": [{
                    "id": "test-profile",
                    "name": "Test Profile",
                    "arch": "arm64",
                    "make_conf": {"USE": "qt6", "COMMON_FLAGS": "-O2 -pipe"},
                    "package_use": ["cat/pkg qt6"],
                    "package_keywords": ["cat/pkg ~amd64"],
                    "package_mask": ["cat/old"],
                    "kernel_config": "CONFIG_PREEMPT=y\n",
                    "world_packages": ["cat/pkg"],
                }]
            }), encoding="utf-8")

            variant = import_profile_catalog(path)[0]

            self.assertEqual(variant.name, "Test Profile")
            self.assertEqual(variant.arch, "arm64")
            self.assertIn("USE=qt6", variant.make_conf)
            self.assertEqual(variant.accept_keywords, "cat/pkg ~amd64")
            self.assertEqual(variant.world_packages, "cat/pkg")
            self.assertEqual(variant.kernel_config, "CONFIG_PREEMPT=y\n")

    def test_imports_nested_and_category_root_ebuilds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "app-misc" / "tool"
            nested.mkdir(parents=True)
            (nested / "tool-1.2.ebuild").touch()
            (root / "app-portage").mkdir()
            (root / "app-portage" / "scripts-2.0-r1.ebuild").touch()

            targets = import_overlay_targets(root)

            self.assertEqual(targets, ["app-misc/tool", "app-portage/scripts"])

    def test_missing_profile_catalog_is_reported(self):
        with self.assertRaises(ProfileImportError):
            import_profile_catalog(Path("/missing/profiles.json"))

if __name__ == "__main__":
    unittest.main()
