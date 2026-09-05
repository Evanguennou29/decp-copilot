import io

from decp.ingest.download import download_parquet


def test_download_parquet_streams_to_destination(tmp_path):
    payload = b"parquet-bytes-" * 1000

    def fake_opener(url, timeout):
        assert url == "https://example.invalid/decp.parquet"
        assert timeout == 60.0
        return io.BytesIO(payload)

    destination = tmp_path / "decp.parquet"
    result = download_parquet(
        destination,
        url="https://example.invalid/decp.parquet",
        opener=fake_opener,
    )

    assert result.path == destination
    assert result.bytes_downloaded == len(payload)
    assert result.elapsed_seconds >= 0
    assert destination.read_bytes() == payload
    assert not destination.with_name(destination.name + ".part").exists()


def test_download_parquet_creates_parent_directories(tmp_path):
    destination = tmp_path / "raw" / "nested" / "decp.parquet"

    def fake_opener(url, timeout):
        return io.BytesIO(b"data")

    result = download_parquet(destination, opener=fake_opener)

    assert result.path.exists()
    assert result.bytes_downloaded == 4


def test_download_parquet_overwrites_existing_file(tmp_path):
    destination = tmp_path / "decp.parquet"
    destination.write_bytes(b"stale-data-much-longer-than-new")

    def fake_opener(url, timeout):
        return io.BytesIO(b"new")

    result = download_parquet(destination, opener=fake_opener)

    assert destination.read_bytes() == b"new"
    assert result.bytes_downloaded == 3
