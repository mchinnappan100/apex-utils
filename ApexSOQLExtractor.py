import os
import re
import argparse
import csv
# ----------------------------------------------------

"""
This script extracts SOQL, SOSL, and DML operations from Apex class files in a specified folder.
It identifies the following:
1. SOQL queries: Queries that start with SELECT and are enclosed in square brackets.
2. SOSL queries: Queries that start with FIND and are enclosed in square brackets.
3. DML operations: Operations that include insert, update, delete, upsert, and merge.
4. Test classes: Classes that are marked with @isTest or contain the keyword isTest in their definition.
The extracted information is saved in a CSV file with the following columns:
- class_name: Name of the Apex class file.
- start_linenumber: Line number where the SOQL query starts.
- testClass: Indicates if the class is a test class (true/false).
- has_binding: Indicates if the SOQL query contains a binding variable (true/false).
- soql_query: The extracted SOQL query.
- sosl_query: The extracted SOSL query (if any).
- dml_operations: The extracted DML operations (if any).
"""

# author: mohan chinnappan
# ----------------------------------------------------

class ApexSOQLExtractor:
    def __init__(self, folder_cls, output_csv):
        self.folder_cls = folder_cls
        self.output_csv = output_csv
        self.soql_pattern = re.compile(r'\[\s*SELECT.*?\]', re.IGNORECASE | re.DOTALL)
        self.sosl_pattern = re.compile(r'FIND\s+[\'"].+?[\'"]\s+IN\s+ALL\s+FIELDS\s+RETURNING.+?;', re.IGNORECASE | re.DOTALL)
        self.dml_pattern = re.compile(r'\b(insert|update|delete|upsert|merge)\b', re.IGNORECASE)
        self.test_class_pattern = re.compile(r'@isTest|class\s+\w+\s+.*isTest', re.IGNORECASE)

    def extract_details_from_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        content = ''.join(lines)

        # SOQL
        soql_matches = list(self.soql_pattern.finditer(content))
        soql_results = []
        for match in soql_matches:
            soql_query = ' '.join(match.group(0).split())
            start_pos = match.start()
            line_number = content[:start_pos].count('\n') + 1
            soql_results.append((soql_query, line_number))

        # SOSL
        sosl_matches = self.sosl_pattern.findall(content)
        sosl_queries = [' '.join(m.split()) for m in sosl_matches]
        sosl_combined = ' | '.join(sosl_queries)

        # DML
        dml_ops = set(self.dml_pattern.findall(content))
        dml_ops_cleaned = ', '.join(sorted(op.lower() for op in dml_ops))

        # Test Class
        is_test = bool(self.test_class_pattern.search(content))

        return soql_results, sosl_combined, dml_ops_cleaned, is_test

    def process_folder(self):
        records = []
        for root, _, files in os.walk(self.folder_cls):
            for filename in files:
                if filename.endswith(".cls"):
                    file_path = os.path.join(root, filename)
                    soql_results, sosl_combined, dml_ops, is_test = self.extract_details_from_file(file_path)
                    for soql_query, line_number in soql_results:
                        records.append({
                            'class_name': filename,
                            'start_linenumber': line_number,
                            'testClass': str(is_test).lower(),
                            'has_binding': str(':' in soql_query).lower(),
                            'soql_query': soql_query,
                            'sosl_query': sosl_combined,
                            'dml_operations': dml_ops
                        })
        return records

    def write_csv(self, records):
        fieldnames = ['class_name', 'start_linenumber', 'testClass', 'has_binding',
                      'soql_query', 'sosl_query', 'dml_operations']
        with open(self.output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    def run(self):
        records = self.process_folder()
        self.write_csv(records)
        print(f"Extracted {len(records)} SOQL queries to {self.output_csv}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract SOQL, SOSL, and DML from Apex classes")
    parser.add_argument('--folder-cls', required=True, help='Folder containing Apex class files')
    parser.add_argument('--output-csv', required=True, help='Path to output CSV file')
    args = parser.parse_args()

    extractor = ApexSOQLExtractor(args.folder_cls, args.output_csv)
    extractor.run()
