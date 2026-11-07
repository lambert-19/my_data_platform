from data_platform_project import main


def test_main_runs(capsys):
    main()
    assert "Hello" in capsys.readouterr().out
