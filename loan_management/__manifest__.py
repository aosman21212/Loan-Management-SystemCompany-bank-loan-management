{
    'name': 'Loan Management System',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Finance',
    'summary': 'Company bank loan management — liability accounting, repayment schedules, journal entries',
    'description': """
Loan Management System
======================
Manages loans the **company takes from banks / financial institutions**.

* Multiple loan types (Term Loan, Mortgage, Working Capital, Vehicle Finance)
* Flat Rate & Reducing Balance interest calculation
* Automatic instalment schedule (amortisation table)
* Approval workflow: Draft → Confirm → Approve → Disburse → Running → Done
* Correct liability accounting:
    - Disbursement:  Dr Bank  /  Cr Loan Payable
    - Repayment:     Dr Loan Payable + Dr Interest Expense  /  Cr Bank
* Professional PDF loan statement with full amortisation table
* Demo data included (3 live loans from banks)
    """,
    'author': 'Custom',
    'images': [
        'static/description/banner.png',
        'static/description/screenshot_01_loans_list.png',
        'static/description/screenshot_02_loan_form.png',
        'static/description/screenshot_03_repayment_schedule.png',
        'static/description/screenshot_04_journal_entries.png',
    ],
    'depends': ['base', 'mail', 'account', 'hr'],
    'data': [
        'security/loan_security.xml',
        'security/ir.model.access.csv',
        'data/loan_sequence.xml',
        'views/loan_type_views.xml',
        'views/loan_views.xml',
        'views/loan_installment_views.xml',
        'views/loan_menu.xml',
        'report/loan_report.xml',
        'report/loan_report_template.xml',
        'wizard/loan_disburse_wizard.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
