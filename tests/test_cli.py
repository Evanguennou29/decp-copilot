import decp.cli as cli_module
from decp.ingest.download import DownloadResult
from decp.ingest.normalize import NormalizeResult


def test_parser_accepts_all_subcommands():
    parser = cli_module.build_parser()
    for command in ("ingest", "index", "serve"):
        args = parser.parse_args([command])
        assert args.command == command


def test_main_with_no_args_prints_help(capsys):
    exit_code = cli_module.main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "usage" in captured.out.lower()


def test_main_with_planned_command_reports_not_implemented(capsys):
    exit_code = cli_module.main(["index"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "not implemented" in captured.out


def test_ingest_downloads_then_normalizes(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DECP_DATA_DIR", str(tmp_path))

    def fake_download(destination, url, *args, **kwargs):
        return DownloadResult(path=destination, bytes_downloaded=123, elapsed_seconds=0.1)

    def fake_normalize(parquet_path, database_path):
        return NormalizeResult(
            database_path=database_path,
            rows_in=10,
            rows_out=4,
            elapsed_seconds=0.2,
            database_bytes=456,
        )

    monkeypatch.setattr(cli_module, "download_parquet", fake_download)
    monkeypatch.setattr(cli_module, "normalize_to_duckdb", fake_normalize)

    exit_code = cli_module.main(["ingest"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "10" in captured.out
    assert "4" in captured.out


def test_ingest_skip_download_never_calls_download(monkeypatch, tmp_path):
    monkeypatch.setenv("DECP_DATA_DIR", str(tmp_path))

    def fail_download(*args, **kwargs):
        raise AssertionError("download_parquet must not run with --skip-download")

    def fake_normalize(parquet_path, database_path):
        return NormalizeResult(
            database_path=database_path,
            rows_in=1,
            rows_out=1,
            elapsed_seconds=0.0,
            database_bytes=1,
        )

    monkeypatch.setattr(cli_module, "download_parquet", fail_download)
    monkeypatch.setattr(cli_module, "normalize_to_duckdb", fake_normalize)

    exit_code = cli_module.main(["ingest", "--skip-download"])

    assert exit_code == 0
