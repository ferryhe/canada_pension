from retirement_calculator import oas, rrif, tax


def test_progressive_tax_uses_2026_federal_brackets():
    assert round(tax.federal_tax(40_000), 2) == 3296.72
    assert round(tax.federal_tax(100_000), 2) == 14392.72


def test_ontario_health_premium_thresholds():
    assert tax.ontario_health_premium(20_000) == 0
    assert tax.ontario_health_premium(25_000) == 300
    assert tax.ontario_health_premium(80_000) == 750
    assert tax.ontario_health_premium(240_000) == 900


def test_ontario_surtax():
    assert tax.ontario_surtax(5_818) == 0
    assert round(tax.ontario_surtax(6_818), 2) == 200
    assert round(tax.ontario_surtax(8_000), 2) == 635.84


def test_oas_recovery_is_capped_by_oas_amount():
    assert oas.oas_recovery(71, 95_323, 9_000) == 0
    assert round(oas.oas_recovery(71, 100_000, 9_000), 2) == 701.55
    assert oas.oas_recovery(71, 160_000, 9_000) == 9_000


def test_rrif_minimum_factor():
    assert round(rrif.minimum_withdrawal_factor(65), 4) == 0.04
    assert rrif.minimum_withdrawal_factor(71) == 0.0528
    assert rrif.minimum_withdrawal_factor(99) == 0.20
