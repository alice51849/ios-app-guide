from __future__ import annotations

import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
PAGES = HERE.parents[1]
sys.path.insert(0, str(HERE))

import pages_artifact_gate as gate  # noqa: E402


class PagesArtifactGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = tempfile.TemporaryDirectory(dir=PAGES)
        self.root = Path(self.workspace.name)
        self.site = self.root / "site"
        self.site.mkdir()
        (self.site / "index.html").write_text("<h1>Guide</h1>")
        (self.site / "assets").mkdir()
        (self.site / "assets" / "app.css").write_text("body{color:#123}")
        self.artifact = self.root / "artifact.tar"

    def tearDown(self) -> None:
        self.workspace.cleanup()

    def test_hard_capacity_contract_preserves_thirty_mb_headroom(self) -> None:
        self.assertEqual(900_000_000, gate.PLATFORM_UNPACKED_BYTES)
        self.assertEqual(30_000_000, gate.MIN_HEADROOM_BYTES)
        self.assertEqual(870_000_000, gate.MAX_UNPACKED_BYTES)

    def test_real_artifact_matches_source_and_enforces_unpacked_bytes(self) -> None:
        built = gate.build_review_tar(self.site, self.artifact)
        verified = gate.verify_artifact(self.site, self.artifact)
        self.assertEqual(2, built["files"])
        self.assertEqual(built["tar_bytes"], verified["tar_bytes"])
        self.assertGreater(verified["deflate_upload_bytes"], 0)
        self.assertLessEqual(
            verified["unpacked_bytes"],
            verified["max_unpacked_bytes"],
        )
        self.assertLessEqual(
            verified["unpacked_bytes"],
            870_000_000,
        )
        self.assertGreaterEqual(
            verified["headroom_bytes"],
            30_000_000,
        )
        with self.assertRaisesRegex(
            ValueError,
            "staging unpacked bytes exceed 1 bytes",
        ):
            gate.verify_artifact(
                self.site,
                self.artifact,
                max_unpacked_bytes=1,
            )
        with self.assertRaisesRegex(
            ValueError,
            "deflate upload artifact exceeds 1 bytes",
        ):
            gate.verify_artifact(
                self.site,
                self.artifact,
                max_deflate_upload_bytes=1,
            )
        with self.assertRaisesRegex(
            ValueError,
            "cannot exceed 870000000",
        ):
            gate.verify_artifact(
                self.site,
                self.artifact,
                max_unpacked_bytes=870_000_001,
            )

    def test_compressible_upload_cannot_hide_oversized_unpacked_tree(
        self,
    ) -> None:
        payload = self.site / "compressible.txt"
        payload.write_bytes(b"0" * 100_000)
        gate.build_review_tar(self.site, self.artifact)
        self.assertLess(
            gate._measure_upload_zip(self.artifact),
            payload.stat().st_size,
        )
        with self.assertRaisesRegex(
            ValueError,
            "staging unpacked bytes exceed 1000 bytes",
        ):
            gate.verify_artifact(
                self.site,
                self.artifact,
                max_unpacked_bytes=1_000,
            )

    def test_source_symlink_hardlink_and_special_file_fail_closed(self) -> None:
        target = self.site / "index.html"
        link = self.site / "linked.html"
        link.symlink_to(target.name)
        with self.assertRaisesRegex(ValueError, "symlink"):
            gate.scan_tree(self.site)
        link.unlink()

        os.link(target, link)
        with self.assertRaisesRegex(ValueError, "hard-linked"):
            gate.scan_tree(self.site)
        link.unlink()

        fifo = self.site / "pipe"
        os.mkfifo(fifo)
        try:
            with self.assertRaisesRegex(ValueError, "special file"):
                gate.scan_tree(self.site)
        finally:
            fifo.unlink()

        sparse = self.site / "sparse.bin"
        with sparse.open("wb") as handle:
            handle.seek(99_999_999)
            handle.write(b"x")
        try:
            with self.assertRaisesRegex(ValueError, "sparse"):
                gate.scan_tree(self.site)
        finally:
            sparse.unlink()

    def _write_member(
        self,
        name: str,
        *,
        member_type: bytes = tarfile.REGTYPE,
        linkname: str = "",
    ) -> None:
        with tarfile.open(
            self.artifact,
            "w",
            format=tarfile.GNU_FORMAT,
        ) as archive:
            root = tarfile.TarInfo(".")
            root.type = tarfile.DIRTYPE
            archive.addfile(root)
            member = tarfile.TarInfo(name)
            member.type = member_type
            member.linkname = linkname
            if member_type == tarfile.REGTYPE:
                member.size = 1
                archive.addfile(member, io.BytesIO(b"x"))
            else:
                archive.addfile(member)

    def test_artifact_path_symlink_hardlink_and_parser_fail_closed(self) -> None:
        cases = (
            ("./../escape", tarfile.REGTYPE, "", "Unsafe"),
            ("./index.html/", tarfile.REGTYPE, "", "has slash"),
            ("./linked", tarfile.SYMTYPE, "index.html", "link member"),
            ("./linked", tarfile.LNKTYPE, "./index.html", "link member"),
        )
        for name, member_type, linkname, message in cases:
            with self.subTest(name=name, member_type=member_type):
                self._write_member(
                    name,
                    member_type=member_type,
                    linkname=linkname,
                )
                with self.assertRaisesRegex(ValueError, message):
                    gate.verify_artifact(self.site, self.artifact)

        self.artifact.write_bytes(b"not a tar archive")
        with self.assertRaisesRegex(ValueError, "Cannot parse"):
            gate.verify_artifact(self.site, self.artifact)

    def test_duplicate_member_and_nonzero_trailer_fail_closed(self) -> None:
        with tarfile.open(
            self.artifact,
            "w",
            format=tarfile.GNU_FORMAT,
        ) as archive:
            root = tarfile.TarInfo(".")
            root.type = tarfile.DIRTYPE
            archive.addfile(root)
            for _index in range(2):
                member = tarfile.TarInfo("./index.html")
                member.size = 14
                archive.addfile(member, io.BytesIO(b"<h1>Guide</h1>"))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            gate.verify_artifact(self.site, self.artifact)

        gate.build_review_tar(self.site, self.artifact)
        with self.artifact.open("ab") as handle:
            handle.write(b"x" * 512)
        with self.assertRaisesRegex(ValueError, "trailer"):
            gate.verify_artifact(self.site, self.artifact)

    def test_workflow_checks_tree_and_exact_action_artifact_before_deploy(
        self,
    ) -> None:
        workflow = (
            PAGES / ".github" / "workflows" / "pages.yml"
        ).read_text(encoding="utf-8")
        tree_gate = workflow.index("pages_artifact_gate.py tree")
        upload = workflow.index("actions/upload-pages-artifact@v3")
        artifact_gate = workflow.index("pages_artifact_gate.py artifact")
        deploy = workflow.index("actions/deploy-pages@v4")
        self.assertLess(tree_gate, upload)
        self.assertLess(upload, artifact_gate)
        self.assertLess(artifact_gate, deploy)
        self.assertIn("--max-unpacked-bytes 870000000", workflow)
        self.assertIn("--max-deflate-upload-bytes 900000000", workflow)
        self.assertIn("${{ runner.temp }}/pages-publish", workflow)
        self.assertIn('$RUNNER_TEMP/artifact.tar', workflow)


if __name__ == "__main__":
    unittest.main()
