from decp.cli import build_parser, main


def test_parser_accepts_planned_subcommands():
    parser = build_parser()
    for command in ("ingest", "index", "serve"):
        args = parser.parse_args([command])
        assert args.command == command


def test_main_with_no_args_prints_help(capsys):
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "usage" in captured.out.lower()


def test_main_with_planned_command_reports_not_implemented(capsys):
    exit_code = main(["ingest"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "not implemented" in captured.out
