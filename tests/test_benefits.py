from retirement_calculator import cpp, oas


def test_cpp_deferral_caps_at_70():
    factor, warning = cpp.cpp_start_factor(71)
    assert round(factor, 2) == 1.42
    assert warning is not None


def test_cpp_reduction_before_65():
    factor, warning = cpp.cpp_start_factor(60)
    assert round(factor, 2) == 0.64
    assert warning is None


def test_oas_deferral_caps_at_70():
    factor, warning = oas.oas_start_factor(71)
    assert round(factor, 2) == 1.36
    assert warning is not None


def test_oas_75_plus_uses_higher_base():
    age_74, _ = oas.annual_oas(74, 65, 8_916.60, 0)
    age_75, _ = oas.annual_oas(75, 65, 8_916.60, 0)
    assert age_75 > age_74
