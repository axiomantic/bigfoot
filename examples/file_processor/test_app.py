"""Test file archival using bigfoot file_io."""

import bigfoot

from .app import archive_and_clean


def test_archive_and_clean():
    bigfoot.file_io.mock_operation("makedirs", "/backups/2024", returns=None)
    bigfoot.file_io.mock_operation("copytree", "/var/data/reports", returns=None)
    bigfoot.file_io.mock_operation(
        "write_text", "/var/log/manifest.txt", returns=None,
    )
    bigfoot.file_io.mock_operation("rmtree", "/var/data/reports", returns=None)

    with bigfoot:
        archive_and_clean(
            "/var/data/reports", "/backups/2024", "/var/log/manifest.txt",
        )

    bigfoot.file_io.assert_makedirs(path="/backups/2024", exist_ok=True)
    bigfoot.file_io.assert_copytree(
        src="/var/data/reports", dst="/backups/2024/latest",
    )
    bigfoot.file_io.assert_write_text(
        path="/var/log/manifest.txt", data="archived: /var/data/reports",
    )
    bigfoot.file_io.assert_rmtree(path="/var/data/reports")
