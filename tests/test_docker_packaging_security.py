"""Static packaging boundary checks; never load product or local configuration."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DockerPackagingSecurityTests(unittest.TestCase):
    def test_compose_ports_default_to_loopback_and_wsgi_is_explicit(self):
        for name, port in (
            ("docker-compose.yml", "8201"),
            ("docker-compose.staging.yml", "8301"),
        ):
            content = (ROOT / name).read_text(encoding="utf-8")
            expected_port = (
                f'"${{LUMENIS_DOCKER_BIND_IP:-127.0.0.1}}:{port}:{port}"'
            )
            self.assertIn(expected_port, content)
            self.assertIn("ZB_WSGI=waitress", content)

    def test_image_uses_fixed_nonroot_user_and_prepares_named_volume_paths(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("ZB_WSGI=waitress", dockerfile)
        self.assertIn("HOME=/home/lumenis", dockerfile)
        self.assertIn("chown -R 10001:10001 /app/data /app/logs /home/lumenis", dockerfile)
        self.assertRegex(dockerfile, r"(?m)^USER 10001:10001\s*$")
        user_index = dockerfile.index("USER 10001:10001")
        self.assertLess(dockerfile.index("RUN sed -i"), user_index)
        self.assertLess(user_index, dockerfile.index('ENTRYPOINT ["/entrypoint.sh"]'))
        self.assertIn('"--host", "0.0.0.0"', dockerfile)

    def test_entrypoint_reports_unwritable_data_and_log_volumes_before_exec(self):
        entrypoint = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn("for runtime_dir in /app/data /app/logs; do", entrypoint)
        self.assertIn('if [ ! -w "$runtime_dir" ]; then', entrypoint)
        self.assertIn("align the mounted volume ownership", entrypoint)
        self.assertIn('exec "$@"', entrypoint)
        self.assertLess(entrypoint.index('if [ ! -w "$runtime_dir" ]; then'), entrypoint.index('exec "$@"'))
        self.assertIn("exit 73", entrypoint)
        self.assertNotIn("chmod 777", entrypoint.lower())

    def test_dockerignore_has_narrow_secret_and_top_level_work_exceptions(self):
        lines = [
            line.strip()
            for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertIn("**/.env", lines)
        self.assertIn("**/.env.*", lines)
        self.assertIn("**/*.env", lines)
        self.assertIn("!/.env.example", lines)
        self.assertIn("/work", lines)
        self.assertIn("/work/**", lines)
        self.assertLess(lines.index("**/.env.*"), lines.index("!/.env.example"))
        self.assertNotIn("!*.env.example", lines)
        self.assertFalse(any(line == "work/" for line in lines))


if __name__ == "__main__":
    unittest.main()
