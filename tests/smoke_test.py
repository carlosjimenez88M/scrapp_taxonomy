from importlib.metadata import version

from scrapp_taxonomy.cli import main


def test_package_imports() -> None:
    assert version("scrapp-taxonomy")


def test_cli_help_exits_successfully() -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0


def test_version_exposed() -> None:
    from scrapp_taxonomy import __version__

    assert __version__
