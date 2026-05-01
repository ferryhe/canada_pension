from retirement_calculator.models import SimulationConfig
from retirement_calculator.output import render_pdf, render_result_html
from retirement_calculator.simulator import simulate


def test_render_html_report():
    html = render_result_html(simulate(SimulationConfig()))
    assert "Canada Retirement Planning Summary" in html


def test_render_pdf_when_available():
    html = render_result_html(simulate(SimulationConfig()))
    try:
        pdf = render_pdf(html)
    except RuntimeError:
        return
    assert pdf.startswith(b"%PDF")
