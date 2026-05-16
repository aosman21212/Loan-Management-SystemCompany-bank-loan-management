from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LoanInstallment(models.Model):
    _name = 'loan.installment'
    _description = 'Loan Installment'
    _order = 'loan_id, sequence'

    loan_id = fields.Many2one(
        comodel_name='loan.loan',
        string='Loan',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='#', default=1)
    due_date = fields.Date(string='Due Date', required=True)
    principal_amount = fields.Monetary(string='Principal')
    interest_amount = fields.Monetary(string='Interest')
    total_amount = fields.Monetary(string='EMI Amount')
    amount_paid = fields.Monetary(string='Amount Paid')
    balance = fields.Monetary(string='Remaining Balance')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='loan_id.currency_id',
        store=True,
    )
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('partial', 'Partially Paid'),
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
        ],
        string='Status',
        default='pending',
        index=True,
    )
    payment_date = fields.Date(string='Payment Date')
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Payment Entry',
        readonly=True,
    )
    note = fields.Char(string='Note')

    # =========================================================================
    # Payment action
    # =========================================================================

    def action_pay(self):
        """Record full payment for this installment and post a journal entry."""
        for rec in self:
            if rec.state == 'paid':
                raise UserError(_('Installment #%s is already paid.') % rec.sequence)

            loan = rec.loan_id
            if not loan.journal_id:
                raise UserError(
                    _('Please set a Disbursement Journal on the loan before recording payments.')
                )
            if not loan.loan_account_id:
                raise UserError(
                    _('Please set a Loan Account on the loan before recording payments.')
                )
            if not loan.interest_account_id:
                raise UserError(
                    _('Please set an Interest Account on the loan before recording payments.')
                )
            if not loan.journal_id.default_account_id:
                raise UserError(
                    _('The loan journal does not have a default account configured.')
                )

            # Accounting (company repays bank):
            #   Dr  Loan Payable      (liability decreases — principal portion)
            #   Dr  Interest Expense  (expense — interest portion)
            #   Cr  Bank / Cash       (asset decreases — cash paid out)
            lender_name = loan.partner_id.name or _('Bank')
            line_ids = [
                # Dr Loan Payable — reduce liability
                (0, 0, {
                    'name': _('Principal Repayment #%(seq)s — %(loan)s',
                              seq=rec.sequence, loan=loan.name),
                    'account_id': loan.loan_account_id.id,
                    'debit': rec.principal_amount,
                    'credit': 0.0,
                    'partner_id': loan.partner_id.id or False,
                }),
            ]
            if rec.interest_amount:
                line_ids.append(
                    # Dr Interest Expense
                    (0, 0, {
                        'name': _('Interest Expense #%(seq)s — %(loan)s',
                                  seq=rec.sequence, loan=loan.name),
                        'account_id': loan.interest_account_id.id,
                        'debit': rec.interest_amount,
                        'credit': 0.0,
                        'partner_id': loan.partner_id.id or False,
                    })
                )
            # Cr Bank — cash paid out (use sum of debit lines to avoid rounding gap)
            bank_credit = round(rec.principal_amount + rec.interest_amount, 2)
            line_ids.append(
                (0, 0, {
                    'name': _('Loan Repayment to %(lender)s — Instalment #%(seq)s',
                              lender=lender_name, seq=rec.sequence),
                    'account_id': loan.journal_id.default_account_id.id,
                    'debit': 0.0,
                    'credit': bank_credit,
                    'partner_id': loan.partner_id.id or False,
                })
            )

            move_vals = {
                'journal_id': loan.journal_id.id,
                'date': fields.Date.today(),
                'ref': _(
                    'Loan Payment - %(loan)s - Installment #%(seq)s',
                    loan=loan.name,
                    seq=rec.sequence,
                ),
                'loan_id': loan.id,
                'line_ids': line_ids,
            }
            move = self.env['account.move'].create(move_vals)
            move.action_post()

            rec.write({
                'state': 'paid',
                'amount_paid': rec.total_amount,
                'payment_date': fields.Date.today(),
                'move_id': move.id,
            })

            # Close the loan if all installments are paid
            if all(inst.state == 'paid' for inst in loan.installment_ids):
                loan.state = 'done'

    def action_mark_overdue(self):
        """Cron-callable: mark pending installments past due date as overdue."""
        today = fields.Date.today()
        overdue = self.search([
            ('state', '=', 'pending'),
            ('due_date', '<', today),
        ])
        overdue.write({'state': 'overdue'})

    def action_view_payment_entry(self):
        self.ensure_one()
        if not self.move_id:
            return {}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }
