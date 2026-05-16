from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    loan_id = fields.Many2one(
        comodel_name='loan.loan',
        string='Loan',
        index=True,
        ondelete='set null',
    )
