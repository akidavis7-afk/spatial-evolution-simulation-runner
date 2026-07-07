from multipop_runner.parsers import parse_simulation_output, parse_theory_output, relative_error


def test_theory_parser():
    text = """
    invasive or not : 1
    applicable or not : 1
    max lambda : -0.025
    absorption time : 1234.5
    """
    result = parse_theory_output(text)
    assert result["theory_status"] == "ok"
    assert result["theory_applicable"] is True
    assert result["theory_absorption_time"] == 1234.5


def test_simulation_parser_and_relative_error():
    text = """
    # of replicates : 2000
    mean absorption time : 1200
    sd of absorption time : 34.2
    existence of long run : 0
    """
    result = parse_simulation_output(text)
    assert result["simulation_replicates"] == 2000
    assert result["simulation_long_run"] is False
    assert relative_error(1000, 1200) == 1 / 6
