import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LoanLoan(models.Model):
    _name = 'loan.loan'
    _description = 'Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_application desc, id desc'

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Loan Reference',
        readonly=True,
        default='New',
        copy=False,
        tracking=True,
    )
    loan_type_id = fields.Many2one(
        comodel_name='loan.type',
        string='Loan Type',
        required=True,
        tracking=True,
    )
    lender_type = fields.Selection(
        selection=[
            ('bank', 'Bank'),
            ('financial_institution', 'Financial Institution'),
            ('partner', 'Other Partner'),
        ],
        string='Lender Type',
        default='bank',
        required=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Lender / Bank',
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company (Borrower)',
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # Loan Terms
    # -------------------------------------------------------------------------
    loan_amount = fields.Monetary(
        string='Loan Amount',
        required=True,
        tracking=True,
    )
    interest_rate = fields.Float(
        string='Interest Rate (%)',
        required=True,
        default=10.0,
        tracking=True,
    )
    interest_method = fields.Selection(
        selection=[
            ('flat', 'Flat Rate'),
            ('reducing', 'Reducing Balance'),
        ],
        string='Interest Method',
        required=True,
        default='reducing',
        tracking=True,
    )
    duration = fields.Integer(
        string='Duration (Months)',
        required=True,
        default=12,
        tracking=True,
    )
    date_application = fields.Date(
        string='Application Date',
        default=fields.Date.today,
        required=True,
    )
    date_approve = fields.Date(string='Approval Date', readonly=True, copy=False)
    date_disburse = fields.Date(string='Disbursement Date', readonly=True, copy=False)
    date_first_payment = fields.Date(string='First Payment Date')

    # -------------------------------------------------------------------------
    # Computed totals
    # -------------------------------------------------------------------------
    total_interest = fields.Monetary(
        string='Total Interest',
        compute='_compute_totals',
        store=True,
    )
    total_amount = fields.Monetary(
        string='Total Payable',
        compute='_compute_totals',
        store=True,
    )
    emi_amount = fields.Monetary(
        string='Monthly Instalment',
        compute='_compute_totals',
        store=True,
    )
    amount_paid = fields.Monetary(
        string='Amount Repaid',
        compute='_compute_paid',
        store=True,
    )
    amount_residual = fields.Monetary(
        string='Outstanding Balance',
        compute='_compute_paid',
        store=True,
    )

    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------
    installment_ids = fields.One2many(
        comodel_name='loan.installment',
        inverse_name='loan_id',
        string='Repayment Schedule',
    )
    installment_count = fields.Integer(
        string='Instalments',
        compute='_compute_installment_count',
    )
    move_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='loan_id',
        string='Journal Entries',
    )
    move_count = fields.Integer(
        string='# Journal Entries',
        compute='_compute_move_count',
    )

    # -------------------------------------------------------------------------
    # Accounting
    # Disbursement:  Dr Bank  /  Cr Loan Payable
    # Repayment:     Dr Loan Payable + Dr Interest Expense  /  Cr Bank
    # -------------------------------------------------------------------------
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Bank Journal',
        domain=[('type', 'in', ['bank', 'cash'])],
        tracking=True,
    )
    loan_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Loan Payable Account',
        domain=[('account_type', 'in', ['liability_non_current', 'liability_current'])],
        help='Liability account — credit on disbursement, debited on each repayment.',
    )
    interest_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Interest Expense Account',
        domain=[('account_type', '=', 'expense')],
        help='Expense account — debited with the interest portion of each repayment.',
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('approve', 'Approved'),
            ('disburse', 'Disbursed'),
            ('running', 'Running'),
            ('done', 'Closed'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
        index=True,
    )
    note = fields.Text(string='Internal Notes')
    rejection_reason = fields.Text(string='Rejection Reason')

    # =========================================================================
    # Compute methods
    # =========================================================================

    @api.depends('loan_amount', 'interest_rate', 'duration', 'interest_method')
    def _compute_totals(self):
        for rec in self:
            if rec.loan_amount and rec.duration and rec.interest_rate:
                P = rec.loan_amount
                r = rec.interest_rate / 100.0
                n = rec.duration
                if rec.interest_method == 'flat':
                    total_interest = P * r * (n / 12.0)
                    total_amount = P + total_interest
                    emi = total_amount / n
                else:  # reducing balance (EMI formula)
                    monthly_rate = r / 12.0
                    if monthly_rate > 0:
                        emi = (
                            P * monthly_rate * (1 + monthly_rate) ** n
                            / ((1 + monthly_rate) ** n - 1)
                        )
                    else:
                        emi = P / n
                    total_amount = emi * n
                    total_interest = total_amount - P
                rec.emi_amount = round(emi, 2)
                rec.total_interest = round(total_interest, 2)
                rec.total_amount = round(total_amount, 2)
            else:
                rec.emi_amount = 0.0
                rec.total_interest = 0.0
                rec.total_amount = 0.0

    @api.depends('installment_ids.state', 'installment_ids.amount_paid')
    def _compute_paid(self):
        for rec in self:
            paid = sum(
                inst.total_amount
                for inst in rec.installment_ids
                if inst.state == 'paid'
            )
            rec.amount_paid = paid
            rec.amount_residual = rec.total_amount - paid

    def _compute_installment_count(self):
        for rec in self:
            rec.installment_count = len(rec.installment_ids)

    def _compute_move_count(self):
        for rec in self:
            rec.move_count = len(rec.move_ids)

    # =========================================================================
    # Onchange
    # =========================================================================

    @api.onchange('loan_type_id')
    def _onchange_loan_type(self):
        if self.loan_type_id:
            self.interest_rate = self.loan_type_id.interest_rate
            self.interest_method = self.loan_type_id.interest_method
            self.loan_account_id = self.loan_type_id.loan_account_id
            self.interest_account_id = self.loan_type_id.interest_account_id

    @api.onchange('lender_type')
    def _onchange_lender_type(self):
        self.partner_id = False

    # =========================================================================
    # CRUD
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = 'New'
        return super().create(vals_list)

    # =========================================================================
    # Workflow actions
    # =========================================================================

    def action_confirm(self):
        for rec in self:
            if not rec.loan_amount or rec.loan_amount <= 0:
                raise UserError(_('Loan amount must be greater than zero.'))
            if not rec.duration or rec.duration <= 0:
                raise UserError(_('Loan duration must be greater than zero.'))
            if not rec.partner_id:
                raise UserError(_('Please select a Lender / Bank.'))
        self.write({'state': 'confirm'})
        return True

    def action_approve(self):
        for rec in self:
            if rec.name == 'New':
                rec.name = (
                    self.env['ir.sequence'].next_by_code('loan.loan') or 'New'
                )
        self.write({
            'state': 'approve',
            'date_approve': fields.Date.today(),
        })
        return True

    def action_generate_schedule(self):
        """Generate repayment instalment schedule."""
        for rec in self:
            rec.installment_ids.unlink()
            P = rec.loan_amount
            r = rec.interest_rate / 100.0
            n = rec.duration
            monthly_rate = r / 12.0

            start_date = rec.date_first_payment or fields.Date.today()
            if isinstance(start_date, str):
                start_date = fields.Date.from_string(start_date)

            installment_vals = []

            if rec.interest_method == 'flat':
                total_interest = P * r * (n / 12.0)
                emi = (P + total_interest) / n
                principal_per_month = P / n
                interest_per_month = total_interest / n
                balance = P
                for i in range(1, n + 1):
                    due_date = start_date + datetime.timedelta(days=30 * i)
                    balance -= principal_per_month
                    installment_vals.append({
                        'loan_id': rec.id,
                        'sequence': i,
                        'due_date': due_date,
                        'principal_amount': round(principal_per_month, 2),
                        'interest_amount': round(interest_per_month, 2),
                        'total_amount': round(emi, 2),
                        'balance': round(max(balance, 0.0), 2),
                    })
            else:  # reducing balance
                if monthly_rate > 0:
                    emi = (
                        P * monthly_rate * (1 + monthly_rate) ** n
                        / ((1 + monthly_rate) ** n - 1)
                    )
                else:
                    emi = P / n
                balance = P
                for i in range(1, n + 1):
                    due_date = start_date + datetime.timedelta(days=30 * i)
                    interest = balance * monthly_rate
                    principal = emi - interest
                    if i == n:
                        principal = balance
                        emi_actual = principal + interest
                    else:
                        emi_actual = emi
                    balance -= principal
                    installment_vals.append({
                        'loan_id': rec.id,
                        'sequence': i,
                        'due_date': due_date,
                        'principal_amount': round(principal, 2),
                        'interest_amount': round(interest, 2),
                        'total_amount': round(emi_actual, 2),
                        'balance': round(max(balance, 0.0), 2),
                    })

            self.env['loan.installment'].create(installment_vals)
        return True

    def action_disburse(self):
        """Open disbursement wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receive Loan from Bank'),
            'res_model': 'loan.disburse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_loan_id': self.id},
        }

    def _do_disburse(self):
        """
        Create disbursement journal entry.

        Accounting (company receives loan from bank):
            Dr  Bank / Cash Account     (asset increases)
            Cr  Loan Payable Account    (liability increases)
        """
        for rec in self:
            if not rec.journal_id:
                raise UserError(_('Please select a Bank Journal.'))
            if not rec.loan_account_id:
                raise UserError(_('Please set a Loan Payable Account.'))
            if not rec.journal_id.default_account_id:
                raise UserError(
                    _('The selected journal "%s" does not have a default account configured.')
                    % rec.journal_id.name
                )

            lender_name = rec.partner_id.name or _('Bank')
            move_vals = {
                'journal_id': rec.journal_id.id,
                'date': rec.date_disburse or fields.Date.today(),
                'ref': _('Loan Received from %(lender)s — %(ref)s',
                         lender=lender_name, ref=rec.name),
                'loan_id': rec.id,
                'line_ids': [
                    # Dr Bank  — company received cash
                    (0, 0, {
                        'name': _('Loan received from %(lender)s', lender=lender_name),
                        'account_id': rec.journal_id.default_account_id.id,
                        'debit': rec.loan_amount,
                        'credit': 0.0,
                        'partner_id': rec.partner_id.id or False,
                    }),
                    # Cr Loan Payable  — company owes the bank
                    (0, 0, {
                        'name': _('Loan Payable — %(ref)s', ref=rec.name),
                        'account_id': rec.loan_account_id.id,
                        'debit': 0.0,
                        'credit': rec.loan_amount,
                        'partner_id': rec.partner_id.id or False,
                    }),
                ],
            }
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            rec.write({
                'state': 'disburse',
                'date_disburse': move.date,
            })
            if not rec.installment_ids:
                rec.action_generate_schedule()
            rec.state = 'running'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_('Cannot cancel a closed loan.'))
        self.write({'state': 'cancel'})
        return True

    def action_reset_draft(self):
        self.write({'state': 'draft'})
        return True

    def action_mark_done(self):
        self.write({'state': 'done'})
        return True

    # =========================================================================
    # Smart-button actions
    # =========================================================================

    def action_view_installments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Repayment Schedule'),
            'res_model': 'loan.installment',
            'view_mode': 'list,form',
            'domain': [('loan_id', '=', self.id)],
            'context': {'default_loan_id': self.id},
        }

    def action_view_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('loan_id', '=', self.id)],
        }

    # =========================================================================
    # Helper
    # =========================================================================

    def _get_lender_name(self):
        self.ensure_one()
        return self.partner_id.name or _('Bank')
