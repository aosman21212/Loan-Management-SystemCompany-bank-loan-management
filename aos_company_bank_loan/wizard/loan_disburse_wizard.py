from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LoanDisburseWizard(models.TransientModel):
    _name = 'loan.disburse.wizard'
    _description = 'Loan Disbursement Wizard'

    loan_id = fields.Many2one(
        comodel_name='loan.loan',
        string='Loan',
        required=True,
        readonly=True,
    )
    loan_amount = fields.Monetary(
        string='Loan Amount',
        related='loan_id.loan_amount',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='loan_id.currency_id',
        readonly=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Bank Journal',
        domain=[('type', 'in', ['bank', 'cash'])],
        required=True,
        help='Bank account into which the loan amount is received.',
    )
    loan_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Loan Payable Account',
        domain=[('account_type', 'in', ['liability_non_current', 'liability_current'])],
        required=True,
        help='Liability account — credited when loan is received, debited on repayments.',
    )
    interest_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Interest Expense Account',
        domain=[('account_type', '=', 'expense')],
        required=True,
        help='Expense account — debited with interest portion of each repayment.',
    )
    disburse_date = fields.Date(
        string='Date Received',
        default=fields.Date.today,
        required=True,
    )
    date_first_payment = fields.Date(
        string='First Repayment Date',
        required=True,
    )
    note = fields.Text(string='Notes')

    @api.onchange('loan_id')
    def _onchange_loan_id(self):
        if self.loan_id:
            self.journal_id = self.loan_id.journal_id
            self.loan_account_id = self.loan_id.loan_account_id
            self.interest_account_id = self.loan_id.interest_account_id

    def action_disburse(self):
        self.ensure_one()
        loan = self.loan_id

        if not self.journal_id.default_account_id:
            raise UserError(
                _('The selected journal "%s" does not have a default account configured.')
                % self.journal_id.name
            )

        # Write wizard values back to loan
        loan.write({
            'journal_id': self.journal_id.id,
            'loan_account_id': self.loan_account_id.id,
            'interest_account_id': self.interest_account_id.id,
            'date_first_payment': self.date_first_payment,
            'date_disburse': self.disburse_date,
        })

        lender_name = loan.partner_id.name or _('Bank')

        # Accounting: company receives loan from bank
        #   Dr  Bank / Cash       (asset increases — money received)
        #   Cr  Loan Payable      (liability increases — company owes bank)
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.disburse_date,
            'ref': _('Loan Received from %(lender)s — %(ref)s',
                     lender=lender_name, ref=loan.name),
            'loan_id': loan.id,
            'line_ids': [
                # Dr Bank
                (0, 0, {
                    'name': _('Loan received from %(lender)s', lender=lender_name),
                    'account_id': self.journal_id.default_account_id.id,
                    'debit': loan.loan_amount,
                    'credit': 0.0,
                    'partner_id': loan.partner_id.id or False,
                }),
                # Cr Loan Payable
                (0, 0, {
                    'name': _('Loan Payable — %(ref)s', ref=loan.name),
                    'account_id': self.loan_account_id.id,
                    'debit': 0.0,
                    'credit': loan.loan_amount,
                    'partner_id': loan.partner_id.id or False,
                }),
            ],
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        loan.write({
            'state': 'disburse',
            'date_disburse': self.disburse_date,
        })

        # Generate repayment schedule
        loan.action_generate_schedule()
        loan.state = 'running'

        return {
            'type': 'ir.actions.act_window',
            'name': _('Loan'),
            'res_model': 'loan.loan',
            'view_mode': 'form',
            'res_id': loan.id,
        }
