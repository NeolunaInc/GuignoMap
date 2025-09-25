import re
import os
import csv

# Script d'extraction des warnings et erreurs Pylance
# Analyse le rapport pylance_error_report.txt et ressort tout ce qui est warning/problème


def extract_pylance_issues(report_path):
    with open(report_path, encoding='utf-8') as f:
        content = f.read()
    issues = []
    current_file = None
    in_no_error_list = False
    for line in content.splitlines():
        # detect file header
        file_match = re.match(r'Fichier\s*:\s*(.+)', line)
        if file_match:
            current_file = file_match.group(1).strip()
            in_no_error_list = False
            continue

        # detect start of 'Aucune erreur détectée dans' section
        if 'Aucune erreur détectée' in line:
            in_no_error_list = True
            continue

        # blank line resets the no-error-list flag
        if in_no_error_list and line.strip() == '':
            in_no_error_list = False

        if not current_file:
            continue

        if line.strip().startswith('-'):
            if in_no_error_list:
                # skip bullet list of files with no errors
                continue

            # Normalize and remove leading '-'
            error_text = line.strip()[1:].strip()

            # Pattern: 'Lignes 220-224 : message...' or 'Ligne 354, 552, 2650 : message'
            m = re.match(r'^(?:Lignes?|Ligne)\s+([\d,\s\-]+)\s*:?\s*(.*)$', error_text)
            if m:
                nums_part = m.group(1)
                msgs_part = m.group(2)
                # parse numbers (expand ranges)
                nums = []
                for part in re.split(r',', nums_part):
                    part = part.strip()
                    if '-' in part:
                        a, b = part.split('-', 1)
                        try:
                            a_i = int(a.strip())
                            b_i = int(b.strip())
                            nums.extend(list(range(a_i, b_i + 1)))
                        except ValueError:
                            continue
                    else:
                        try:
                            nums.append(int(part))
                        except ValueError:
                            continue

                # split messages by comma or semicolon
                msgs = [s.strip() for s in re.split(r',|;', msgs_part) if s.strip()]
                if not msgs:
                    msgs = [msgs_part.strip()] if msgs_part.strip() else ['(no message)']

                for n in nums:
                    for msg in msgs:
                        issues.append(f"{current_file} | line {n} | {msg}")
                continue

            # Otherwise, try to split messages on commas/semicolons and record without line
            parts = [s.strip() for s in re.split(r',|;', error_text) if s.strip()]
            for p in parts:
                issues.append(f"{current_file} | {p}")

    return issues


def write_reports(issues, out_txt='exports/pylance_issues.txt', out_csv='exports/pylance_issues.csv'):
    os.makedirs(os.path.dirname(out_txt), exist_ok=True)

    # write plain text (same format as printed lines)
    with open(out_txt, 'w', encoding='utf-8') as f:
        for issue in issues:
            f.write(issue + '\n')

    # write CSV with columns: file, line, message
    with open(out_csv, 'w', encoding='utf-8', newline='') as csvf:
        writer = csv.writer(csvf)
        writer.writerow(['file', 'line', 'message'])
        for issue in issues:
            parts = [p.strip() for p in issue.split(' | ')]
            if len(parts) == 3:
                file_part, line_part, msg_part = parts
                # normalize 'line N' to just number
                if line_part.lower().startswith('line'):
                    line_part = line_part.split(None, 1)[1].strip()
            elif len(parts) == 2:
                file_part, msg_part = parts
                line_part = ''
            else:
                file_part = parts[0] if parts else ''
                line_part = ''
                msg_part = ' '.join(parts[1:]) if len(parts) > 1 else ''
            writer.writerow([file_part, line_part, msg_part])


if __name__ == "__main__":
    report_path = "pylance_error_report.txt"
    issues = extract_pylance_issues(report_path)
    print("\n--- Warnings & Problèmes Pylance ---\n")
    for issue in issues:
        print(issue)
    print(f"\nTotal détecté : {len(issues)}")

    # also write to files for easier review
    write_reports(issues)
    print("\nRapports écrits :\n - exports/pylance_issues.txt\n - exports/pylance_issues.csv")
