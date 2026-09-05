from pathlib import Path

import numpy as np

import decp.cli as cli_module
from decp.index.store import load_index
from decp.ingest.download import DownloadResult
from decp.ingest.normalize import NormalizeResult, normalize_to_duckdb

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "decp_sample.parquet"


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


def _fake_encoder(texts):
    dim = 8
    vectors = np.zeros((len(texts), dim), dtype=np.float32)
    for i, text in enumerate(texts):
        vectors[i, len(text) % dim] = 1.0
    return vectors


def test_index_builds_vector_index_without_network(monkeypatch, tmp_path):
    monkeypatch.setenv("DECP_DATA_DIR", str(tmp_path))
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)

    monkeypatch.setattr(cli_module, "load_encoder", lambda *args, **kwargs: _fake_encoder)

    exit_code = cli_module.main(["index"])

    assert exit_code == 0
    index = load_index(tmp_path / "index" / "decp.index.npz")
    assert len(index) >= 1
    assert index.vectors.shape[1] == 8
    assert index.metadata["scope_window_days"] == 60


def test_serve_wires_the_app_and_calls_uvicorn_run(monkeypatch):
    sentinel_deps = object()
    sentinel_app = object()
    calls = {}

    def fake_create_app(deps):
        assert deps is sentinel_deps
        return sentinel_app

    monkeypatch.setattr(cli_module, "load_real_dependencies", lambda: sentinel_deps)
    monkeypatch.setattr(cli_module, "create_app", fake_create_app)

    def fake_run(app, host, port):
        calls["app"] = app
        calls["host"] = host
        calls["port"] = port

    monkeypatch.setattr(cli_module.uvicorn, "run", fake_run)

    exit_code = cli_module.main(["serve"])

    assert exit_code == 0
    assert calls == {"app": sentinel_app, "host": "0.0.0.0", "port": 8000}


def test_serve_accepts_custom_host_and_port(monkeypatch):
    monkeypatch.setattr(cli_module, "load_real_dependencies", lambda: object())
    monkeypatch.setattr(cli_module, "create_app", lambda deps: object())
    calls = {}

    def fake_run(app, host, port):
        calls["host"] = host
        calls["port"] = port

    monkeypatch.setattr(cli_module.uvicorn, "run", fake_run)

    exit_code = cli_module.main(["serve", "--host", "127.0.0.1", "--port", "9000"])

    assert exit_code == 0
    assert calls == {"host": "127.0.0.1", "port": 9000}
