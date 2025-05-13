import argparse
import csv
import json
import subprocess
import requests
import re
import os

# SOQL Explain Plan Generator
# ----------------------------------------------------

"""
SOQL Explain Plan Generator for Salesforce Apex Classes
This script generates EXPLAIN plans for SOQL queries in Apex classes.
It retrieves the SOQL queries from a CSV file, cleans them, and fetches the EXPLAIN plan
from Salesforce using the REST API.
The script requires the Salesforce CLI (sf) to be installed and configured.
The output is saved in a CSV file and an HTML report.
"""
#author: mohan chinnappan
# ----------------------------------------------------

class SOQLExplainPlan:
    def __init__(self, input_csv, username, output_csv):
        self.input_csv = input_csv
        self.username = username
        self.output_csv = output_csv
        self.html_output = f"{self.output_csv}.html"
        self.access_token = None
        self.instance_url = None

    def get_auth_details(self):
        try:
            result = subprocess.run(
                ['sf', 'force', 'org', 'display', '-u', self.username, '--json'],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            data = json.loads(result.stdout)
            self.access_token = data['result']['accessToken']
            self.instance_url = data['result']['instanceUrl']
        except Exception as e:
            print(f"[ERROR] Failed to retrieve org credentials: {e}")
            exit(1)

    def clean_soql(self, soql):
        soql = soql.strip('[]')
        soql = re.sub(r'\s+WITH\s+[^\]]+', '', soql, flags=re.IGNORECASE).strip()
        return soql

    def explain_soql(self, query):
        url = f"{self.instance_url}/services/data/v60.0/query/?explain={query}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            try:
                plan = response.json()
                return json.dumps(plan.get('plans', []), indent=2)
            except Exception:
                return "Invalid JSON in response"
        else:
            return f"Error: {response.status_code} - {response.text}"

    def process_csv(self):
        output_rows = []
        html_rows = []
        with open(self.input_csv, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames + ['modified_soql', 'explain_plan']

            for row in reader:
                raw_soql = row['soql_query']
                cleaned_soql = self.clean_soql(raw_soql)
                row['modified_soql'] = cleaned_soql

                if row['testClass'].lower() == 'false' and row['has_binding'].lower() == 'false':
                    explain = self.explain_soql(cleaned_soql)
                    row['explain_plan'] = explain

                    # HTML row
                    html_rows.append(f"""
                    <tr class="hover:bg-gray-100 border-b">
                        <td class="px-4 py-2 text-sm">{row['class_name']}</td>
                        <td class="px-4 py-2 text-sm whitespace-pre-wrap">{row['soql_query']}</td>
                        <td class="px-4 py-2 text-sm whitespace-pre-wrap">{row['modified_soql']}</td>
                        <td class="px-4 py-2 text-sm whitespace-pre-wrap"><pre>{row['explain_plan']}</pre></td>
                    </tr>
                    """)
                else:
                    row['explain_plan'] = ''

                output_rows.append(row)

        # Write CSV
        with open(self.output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

        # Write HTML
        self.write_html(html_rows)

    def write_html(self, html_rows):
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>SOQL Explain Plan Report</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-50 p-4">
            <div class="max-w-full mx-auto bg-white shadow-lg rounded-lg overflow-x-auto">
                <table class="min-w-full table-auto text-left border">
                    <thead class="bg-gray-200 sticky top-0 z-10">
                        <tr>
                            <th class="px-4 py-2 text-sm font-bold text-gray-700">Class Name</th>
                            <th class="px-4 py-2 text-sm font-bold text-gray-700">SOQL Query</th>
                            <th class="px-4 py-2 text-sm font-bold text-gray-700">Modified SOQL</th>
                            <th class="px-4 py-2 text-sm font-bold text-gray-700">Explain Plan</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(html_rows)}
                    </tbody>
                    <tfoot class="bg-gray-100 sticky bottom-0">
                        <tr>
                            <td colspan="4" class="text-center text-xs text-gray-600 p-2">Generated by SOQL Explain Plan Tool</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </body>
        </html>
        """
        with open(self.html_output, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def run(self):
        print("[INFO] Fetching Salesforce org authentication details...")
        self.get_auth_details()
        print("[INFO] Processing SOQL explain plans...")
        self.process_csv()
        print(f"[SUCCESS] CSV written to: {self.output_csv}")
        print(f"[SUCCESS] HTML written to: {self.html_output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate EXPLAIN plans for SOQL queries in Apex classes")
    parser.add_argument('--input-soql-csv', required=True, help='Path to input CSV from SOQL extractor')
    parser.add_argument('--username', required=True, help='Salesforce org username')
    parser.add_argument('--output-csv', default='soql_with_explain.csv', help='Output CSV with EXPLAIN plans')
    args = parser.parse_args()

    explainer = SOQLExplainPlan(args.input_soql_csv, args.username, args.output_csv)
    explainer.run()
