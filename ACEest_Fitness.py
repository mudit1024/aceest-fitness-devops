"""ACEest Fitness & Gym - web application entry point.

Run locally:   python ACEest_Fitness.py
In container:  gunicorn ACEest_Fitness:app
"""
import os

from aceest import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
