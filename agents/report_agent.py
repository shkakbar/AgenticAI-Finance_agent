"""
Report Agent - Generates HTML reports.
Wraps the HTMLReportGenerator functionality.
"""
from agents.base_agent import BaseAgent
from html_report_generator import HTMLReportGenerator
from datetime import datetime
import os


class ReportAgent(BaseAgent):
    """Agent responsible for generating HTML reports."""

    def __init__(self, model_router=None, vector_db=None, output_dir='data/reports'):
        super().__init__('ReportAgent', model_router, vector_db)
        self.generator = HTMLReportGenerator()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def execute(self, analysis_data):
        """
        Generate HTML report from analysis data.

        Args:
            analysis_data: dict with all analysis results

        Returns:
            dict with:
                - report_path: path to generated HTML file
                - timestamp: generation timestamp
        """
        if not self.validate_input(analysis_data):
            return None

        self.log("Generating HTML report...")
        html_report = self.generator.generate_html_report(analysis_data)

        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f'{self.output_dir}/analysis_{timestamp}.html'

        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(html_report)

        self.log(f"Report saved to: {report_filename}", 'SUCCESS')

        return {
            'report_path': report_filename,
            'timestamp': timestamp
        }