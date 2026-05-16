from odoo import api, fields, models


class LoanType(models.Model):
    _name = 'loan.type'
    _description = 'Loan Type'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Loan Type', required=True, tracking=True)
    code = fields.Char(string='Code')
    interest_rate = fields.Float(
        string='Default Interest Rate (%)',
        default=10.0,
        tracking=True,
    )
    interest_method = fields.Selection(
        selection=[
            ('flat', 'Flat Rate'),
            ('reducing', 'Reducing Balance'),
        ],
        string='Interest Method',
        default='reducing',
        required=True,
        tracking=True,
    )
    max_amount = fields.Monetary(string='Max Loan Amount')
    max_duration = fields.Integer(string='Max Duration (Months)', default=60)
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    loan_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Loan Payable Account',
        domain=[('account_type', 'in', ['liability_non_current', 'liability_current'])],
        help='Default liability account — credited on disbursement, debited on repayments.',
    )
    interest_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Interest Expense Account',
        domain=[('account_type', '=', 'expense')],
        help='Default expense account — debited with the interest portion of each repayment.',
    )
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    loan_count = fields.Integer(
        string='Loans',
        compute='_compute_loan_count',
    )
    description = fields.Text(string='Description')

    def _compute_loan_count(self):
        loan_data = self.env['loan.loan'].read_group(
            domain=[('loan_type_id', 'in', self.ids)],
            fields=['loan_type_id'],
            groupby=['loan_type_id'],
        )
        mapped = {row['loan_type_id'][0]: row['loan_type_id_count'] for row in loan_data}
        for rec in self:
            rec.loan_count = mapped.get(rec.id, 0)

    def action_view_loans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} Loans',
            'res_model': 'loan.loan',
            'view_mode': 'list,form,kanban',
            'domain': [('loan_type_id', '=', self.id)],
            'context': {'default_loan_type_id': self.id},
        }
