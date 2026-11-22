"""PDF client report (port of the 3.1 PDF export, generated in memory)."""
from fpdf import FPDF


def _latin1(value):
    # Core PDF fonts are latin-1 only; replace anything else instead of failing.
    return str(value).encode("latin-1", "replace").decode("latin-1")


def build_client_report(summary, plan=None):
    client = summary["client"]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _latin1(f"ACEest Client Report - {client['name']}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    def line(text, bold=False):
        pdf.set_font("Helvetica", "B" if bold else "", 12)
        pdf.cell(0, 8, _latin1(text), new_x="LMARGIN", new_y="NEXT")

    line("Profile", bold=True)
    line(f"Age: {client['age'] or '-'}")
    line(f"Height: {client['height'] or '-'} cm")
    line(f"Weight: {client['weight'] or '-'} kg")
    line(f"Program: {client['program']}")
    line(f"Calories: {client['calories'] or '-'} kcal/day")
    pdf.ln(4)
    line("Progress", bold=True)
    line(f"Weeks logged: {summary['weeks_logged']}")
    line(f"Average adherence: {summary['average_adherence']}%")
    line(f"Workouts logged: {summary['workouts_logged']} ({summary['training_minutes']} min)")
    if plan:
        pdf.ln(4)
        line(f"Generated plan ({plan['level']}, {plan['focus']})", bold=True)
        for item in plan["plan"]:
            line(f"{item['day']}: {item['exercise']} {item['sets']} x {item['reps']}")
    return bytes(pdf.output())
