from . import models
from . import wizard


def post_init_hook(env):
    """Create demo loan types, bank partners, and 3 running loans."""
    _create_demo_data(env)


def _create_demo_data(env):
    company = env.company
    currency = company.currency_id

    # -------------------------------------------------------------------------
    # 1. Find suitable accounts
    # -------------------------------------------------------------------------
    LoanAccount = env['account.account']

    # Loan Payable — long-term liability
    loan_payable_account = LoanAccount.search([
        ('company_ids', 'in', company.id),
        ('account_type', 'in', ['liability_non_current', 'liability_current']),
        ('deprecated', '=', False),
    ], limit=1)

    # Interest Expense
    interest_account = LoanAccount.search([
        ('company_ids', 'in', company.id),
        ('account_type', '=', 'expense'),
        ('deprecated', '=', False),
    ], limit=1)

    # Bank journal
    bank_journal = env['account.journal'].search([
        ('company_id', '=', company.id),
        ('type', 'in', ['bank', 'cash']),
    ], limit=1)

    if not loan_payable_account or not interest_account or not bank_journal:
        # Not enough accounting setup — skip demo data silently
        return

    # -------------------------------------------------------------------------
    # 2. Loan Types
    # -------------------------------------------------------------------------
    LoanType = env['loan.type']

    term_loan_type = LoanType.search([('name', '=', 'Term Loan')], limit=1)
    if not term_loan_type:
        term_loan_type = LoanType.create({
            'name': 'Term Loan',
            'code': 'TL',
            'interest_rate': 6.5,
            'interest_method': 'reducing',
            'max_amount': 5000000.0,
            'max_duration': 60,
            'loan_account_id': loan_payable_account.id,
            'interest_account_id': interest_account.id,
        })

    mortgage_type = LoanType.search([('name', '=', 'Mortgage Loan')], limit=1)
    if not mortgage_type:
        mortgage_type = LoanType.create({
            'name': 'Mortgage Loan',
            'code': 'MTG',
            'interest_rate': 5.5,
            'interest_method': 'reducing',
            'max_amount': 20000000.0,
            'max_duration': 300,
            'loan_account_id': loan_payable_account.id,
            'interest_account_id': interest_account.id,
        })

    working_capital_type = LoanType.search([('name', '=', 'Working Capital Loan')], limit=1)
    if not working_capital_type:
        working_capital_type = LoanType.create({
            'name': 'Working Capital Loan',
            'code': 'WC',
            'interest_rate': 8.0,
            'interest_method': 'flat',
            'max_amount': 1000000.0,
            'max_duration': 24,
            'loan_account_id': loan_payable_account.id,
            'interest_account_id': interest_account.id,
        })

    vehicle_type = LoanType.search([('name', '=', 'Vehicle Finance')], limit=1)
    if not vehicle_type:
        vehicle_type = LoanType.create({
            'name': 'Vehicle Finance',
            'code': 'VF',
            'interest_rate': 4.5,
            'interest_method': 'reducing',
            'max_amount': 500000.0,
            'max_duration': 60,
            'loan_account_id': loan_payable_account.id,
            'interest_account_id': interest_account.id,
        })

    # -------------------------------------------------------------------------
    # 3. Bank Partners (Lenders)
    # -------------------------------------------------------------------------
    Partner = env['res.partner']

    def _get_or_create_bank(name):
        p = Partner.search([('name', '=', name), ('is_company', '=', True)], limit=1)
        if not p:
            p = Partner.create({'name': name, 'is_company': True, 'supplier_rank': 1})
        return p

    alrajhi = _get_or_create_bank('Al Rajhi Bank')
    sabb = _get_or_create_bank('SABB')
    alinma = _get_or_create_bank('Alinma Bank')

    # -------------------------------------------------------------------------
    # 4. Helper: create a loan, disburse it, generate schedule, pay N instalments
    # -------------------------------------------------------------------------
    import datetime
    from odoo import fields as odoo_fields

    Loan = env['loan.loan']
    Sequence = env['ir.sequence']

    def _make_loan(ref, loan_type, partner, amount, duration, months_ago, paid_count):
        existing = Loan.search([('name', '=', ref)], limit=1)
        if existing:
            return existing

        disburse_date = datetime.date.today() - datetime.timedelta(days=30 * months_ago)
        first_payment = disburse_date + datetime.timedelta(days=30)

        loan = Loan.create({
            'name': ref,
            'loan_type_id': loan_type.id,
            'lender_type': 'bank',
            'partner_id': partner.id,
            'company_id': company.id,
            'loan_amount': amount,
            'interest_rate': loan_type.interest_rate,
            'interest_method': loan_type.interest_method,
            'duration': duration,
            'date_application': disburse_date - datetime.timedelta(days=15),
            'date_approve': disburse_date - datetime.timedelta(days=5),
            'date_disburse': disburse_date,
            'date_first_payment': first_payment,
            'journal_id': bank_journal.id,
            'loan_account_id': loan_payable_account.id,
            'interest_account_id': interest_account.id,
            'state': 'approve',
        })

        # Disbursement journal entry: Dr Bank / Cr Loan Payable
        lender_name = partner.name
        disburse_move = env['account.move'].create({
            'journal_id': bank_journal.id,
            'date': disburse_date,
            'ref': f'Loan Received from {lender_name} — {ref}',
            'loan_id': loan.id,
            'line_ids': [
                (0, 0, {
                    'name': f'Loan received from {lender_name}',
                    'account_id': bank_journal.default_account_id.id,
                    'debit': amount,
                    'credit': 0.0,
                    'partner_id': partner.id,
                }),
                (0, 0, {
                    'name': f'Loan Payable — {ref}',
                    'account_id': loan_payable_account.id,
                    'debit': 0.0,
                    'credit': amount,
                    'partner_id': partner.id,
                }),
            ],
        })
        disburse_move.action_post()

        loan.write({'state': 'disburse', 'date_disburse': disburse_date})
        loan.action_generate_schedule()
        loan.state = 'running'

        # Pay first N instalments
        for inst in loan.installment_ids[:paid_count]:
            pay_date = inst.due_date
            repay_move = env['account.move'].create({
                'journal_id': bank_journal.id,
                'date': pay_date,
                'ref': f'Loan Payment - {ref} - Installment #{inst.sequence}',
                'loan_id': loan.id,
                'line_ids': [
                    # Dr Loan Payable (principal)
                    (0, 0, {
                        'name': f'Principal Repayment #{inst.sequence} — {ref}',
                        'account_id': loan_payable_account.id,
                        'debit': inst.principal_amount,
                        'credit': 0.0,
                        'partner_id': partner.id,
                    }),
                    # Dr Interest Expense
                    (0, 0, {
                        'name': f'Interest Expense #{inst.sequence} — {ref}',
                        'account_id': interest_account.id,
                        'debit': inst.interest_amount,
                        'credit': 0.0,
                        'partner_id': partner.id,
                    }),
                    # Cr Bank
                    (0, 0, {
                        'name': f'Loan Repayment to {lender_name} — Instalment #{inst.sequence}',
                        'account_id': bank_journal.default_account_id.id,
                        'debit': 0.0,
                        'credit': inst.total_amount,
                        'partner_id': partner.id,
                    }),
                ],
            })
            repay_move.action_post()
            inst.write({
                'state': 'paid',
                'amount_paid': inst.total_amount,
                'payment_date': pay_date,
                'move_id': repay_move.id,
            })

        return loan

    # -------------------------------------------------------------------------
    # 5. Create 3 demo loans
    # -------------------------------------------------------------------------
    _make_loan(
        ref='LN/2025/0001',
        loan_type=term_loan_type,
        partner=alrajhi,
        amount=500000.0,
        duration=60,
        months_ago=8,
        paid_count=8,
    )

    _make_loan(
        ref='LN/2025/0002',
        loan_type=working_capital_type,
        partner=sabb,
        amount=200000.0,
        duration=24,
        months_ago=5,
        paid_count=5,
    )

    _make_loan(
        ref='LN/2025/0003',
        loan_type=vehicle_type,
        partner=alinma,
        amount=120000.0,
        duration=48,
        months_ago=3,
        paid_count=3,
    )
