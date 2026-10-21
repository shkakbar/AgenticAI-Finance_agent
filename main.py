"""
Finance Agent - Multi-Agent Architecture (v4.0)

This is the main entry point that uses the orchestrator to coordinate
specialized agents running in parallel.
Outputs:
HTML report (data/reports/analysis_*.html) for offline viewing
JSON data (data/reports/analysis_*.json) for Streamlit dashboard
To view the interactive dashboard:
 streamlit run app.py
"""

from orchestrator import Orchestrator
def __main__():
    """Run the multi-agent finance analysis pipeline."""
    orchestrator = Orchestrator()
    """orchestrator = Orchestrator(
        max_workers_phase1=2, # News + Market in parallel
        max_workers_phase2=5 # 5 analysis agents in parallel
    )"""
    result = orchestrator.run(
        hours_back=24,
        calendar_days_ahead=14
    )

    if result is None:
        print("❌ Pipeline failed - check logs above")
        return 1

    return 0



if __name__ == "__main__":
    exit(__main__())