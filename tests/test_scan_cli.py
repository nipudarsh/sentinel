from sentinel.scan import main


def test_scan_main_imports() -> None:
    # We don't call network in tests. This simply ensures module imports correctly.
    assert callable(main)
