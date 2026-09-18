"""Black-box tests for scripts/base-image-digest (`make digest`).

Its output is pasted straight into .env / compose.yaml as ROS_BASE_DIGEST, so
the digest is pinned on exact text: one line, no stray carriage return.
"""

import unittest

from fakes import ScriptTestCase, rule

DIGEST = "sha256:1ea2d2c67e9a2d6b78a06dd6f6d7a04bd3e1a5cbb45d3f0cf7c2e6a0b5c4d3e2"
TOKEN_URL = (
    "https://auth.docker.io/token"
    "?service=registry.docker.io&scope=repository:library/ros:pull"
)
MANIFEST_URL = "https://registry-1.docker.io/v2/library/ros/manifests/{}-ros-base"

TOKEN_BODY = '{"token":"TOK123","access_token":"TOK123","expires_in":300}\n'


def headers(*lines):
    return "HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n" + "".join(
        line + "\r\n" for line in lines
    ) + "\r\n"


class BaseImageDigestTests(ScriptTestCase):
    script = "base-image-digest"

    def setUp(self):
        super().setUp()
        self.sandbox.link("sed", "tr")

    def curl(self, token_body=TOKEN_BODY, token_exit=0, header_block=None, header_exit=0):
        """A fake curl: the -I call answers with headers, any other with the token."""
        if header_block is None:
            header_block = headers("Docker-Content-Digest: " + DIGEST)
        self.sandbox.fake(
            "curl",
            stdout=token_body,
            exit_code=token_exit,
            rules=[rule(["-I"], stdout=header_block, exit_code=header_exit, match="all")],
        )

    def manifest_call(self):
        calls = [c for c in self.sandbox.argv("curl") if "-I" in c]
        self.assertEqual(1, len(calls), self.sandbox.argv("curl"))
        return calls[0]

    # --- the happy path ----------------------------------------------------

    def test_the_digest_is_printed_on_its_own_line(self):
        self.curl()
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertEqual(DIGEST + "\n", run.stdout)

    def test_the_default_distro_is_lyrical(self):
        self.curl()
        self.run_script()
        self.assertIn(MANIFEST_URL.format("lyrical"), self.manifest_call())

    def test_the_distro_argument_reaches_the_manifest_url(self):
        self.curl()
        self.run_script("jazzy")
        self.assertIn(MANIFEST_URL.format("jazzy"), self.manifest_call())

    def test_the_token_is_requested_for_the_ros_repository(self):
        self.curl()
        self.run_script()
        token_calls = [c for c in self.sandbox.argv("curl") if "-I" not in c]
        self.assertEqual([["-fsS", TOKEN_URL]], token_calls)

    def test_the_token_is_sent_as_a_bearer_header(self):
        self.curl()
        self.run_script()
        self.assertIn("Authorization: Bearer TOK123", self.manifest_call())

    def test_both_multi_arch_index_media_types_are_accepted(self):
        self.curl()
        self.run_script()
        call = self.manifest_call()
        self.assertIn("Accept: application/vnd.oci.image.index.v1+json", call)
        self.assertIn(
            "Accept: application/vnd.docker.distribution.manifest.list.v2+json", call
        )

    # --- header parsing ----------------------------------------------------

    def test_a_lowercase_header_name_is_matched(self):
        self.curl(header_block=headers("docker-content-digest: " + DIGEST))
        run = self.run_script()
        self.assertStatus(run, 0)
        self.assertEqual(DIGEST + "\n", run.stdout)

    def test_the_trailing_carriage_return_is_stripped(self):
        """curl -I emits CRLF line endings; a \\r in ROS_BASE_DIGEST breaks the build."""
        self.curl(header_block=headers("Docker-Content-Digest: " + DIGEST))
        run = self.run_script()
        self.assertNotIn("\r", run.stdout, repr(run.stdout))
        self.assertEqual([DIGEST], run.out_lines)

    def test_other_headers_are_ignored(self):
        self.curl(
            header_block=headers(
                "Etag: \"" + DIGEST + "\"",
                "Docker-Content-Digest: " + DIGEST,
                "Docker-Distribution-Api-Version: registry/2.0",
            )
        )
        self.assertEqual(DIGEST + "\n", self.run_script().stdout)

    def test_an_all_uppercase_header_is_not_matched_today(self):
        """Pins current behaviour: the match varies only the first letter of each word."""
        self.curl(header_block=headers("DOCKER-CONTENT-DIGEST: " + DIGEST))
        run = self.run_script()
        self.assertNotEqual(0, run.status, run.report())
        self.assertHas(run, "no digest for ros:lyrical-ros-base", where="stderr")

    # --- failures ----------------------------------------------------------

    def test_a_response_without_a_token_fails_with_a_message(self):
        self.curl(token_body='{"error":"unauthorized"}\n')
        run = self.run_script()
        self.assertNotEqual(0, run.status, run.report())
        self.assertEqual("", run.stdout, run.report())
        self.assertHas(run, "could not obtain a registry token", where="stderr")

    def test_a_failing_token_request_fails_with_a_message(self):
        self.curl(token_body="", token_exit=22)
        run = self.run_script()
        self.assertNotEqual(0, run.status, run.report())
        self.assertHas(run, "could not obtain a registry token", where="stderr")

    def test_no_digest_header_fails_with_a_message_naming_the_tag(self):
        self.curl(header_block=headers("Content-Length: 0"))
        run = self.run_script()
        self.assertNotEqual(0, run.status, run.report())
        self.assertEqual("", run.stdout, run.report())
        self.assertHas(run, "no digest for ros:lyrical-ros-base", where="stderr")

    def test_the_missing_digest_message_names_the_requested_distro(self):
        self.curl(header_block=headers("Content-Length: 0"))
        run = self.run_script("jazzy")
        self.assertHas(run, "no digest for ros:jazzy-ros-base", where="stderr")

    def test_a_failing_manifest_request_fails_with_a_message(self):
        self.curl(header_block="", header_exit=22)
        run = self.run_script()
        self.assertNotEqual(0, run.status, run.report())
        self.assertHas(run, "no digest for ros:lyrical-ros-base", where="stderr")


if __name__ == "__main__":
    unittest.main()
