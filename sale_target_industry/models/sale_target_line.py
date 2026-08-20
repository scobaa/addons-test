# -*- coding: utf-8 -*-
# License OPL-1
"""
sale_target_line.py
===================
Model: sale.target.line
Each line represents a monthly billing target for a specific customer
industry within a parent plan (sale.target).

Key computed fields (store=True so they work in Pivot / Graph views):
  - achieved_amount  : Sum of amount_untaxed of confirmed sale.orders
                       filtered by industry + year + month.
  - achievement_rate : (achieved_amount / target_amount) * 100
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleTargetLine(models.Model):
    _name = 'sale.target.line'
    _description = 'Sales Target Line'
    _order = 'target_id, month asc, industry_id asc'

    # -------------------------------------------------------------------------
    # Relational / header fields
    # -------------------------------------------------------------------------
    target_id = fields.Many2one(
        comodel_name='sale.target',
        string='Target Plan',
        required=True,
        ondelete='cascade',
        index=True,
        help='Parent target plan this line belongs to.',
    )

    year = fields.Integer(
        string='Year',
        related='target_id.year',
        store=True,
        readonly=True,
        help='Year inherited from the parent plan.',
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='target_id.company_id',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='target_id.currency_id',
        store=True,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Core definition fields
    # -------------------------------------------------------------------------
    industry_id = fields.Many2one(
        comodel_name='res.partner.industry',
        string='Industry / Sector',
        required=True,
        index=True,
        help='Customer industry / sector this target applies to.',
    )

    month = fields.Selection(
        selection=[
            ('1', 'January'),
            ('2', 'February'),
            ('3', 'March'),
            ('4', 'April'),
            ('5', 'May'),
            ('6', 'June'),
            ('7', 'July'),
            ('8', 'August'),
            ('9', 'September'),
            ('10', 'October'),
            ('11', 'November'),
            ('12', 'December'),
        ],
        string='Month',
        required=True,
        help='Calendar month this target line covers.',
    )

    target_amount = fields.Monetary(
        string='Target Amount',
        currency_field='currency_id',
        required=True,
        default=0.0,
        help='Billing target (excl. taxes) for this industry and month.',
    )

    # -------------------------------------------------------------------------
    # Computed fields — store=True required for Pivot / Graph views
    # -------------------------------------------------------------------------
    achieved_amount = fields.Monetary(
        string='Achieved Amount',
        currency_field='currency_id',
        compute='_compute_achieved_amount',
        store=True,
        help=(
            'Sum of amount_untaxed of confirmed sale.orders '
            'whose date_order falls in this month/year and whose '
            "partner's industry matches this line's industry."
        ),
    )

    achievement_rate = fields.Float(
        string='Achievement Rate (%)',
        compute='_compute_achievement_rate',
        store=True,
        digits=(5, 2),
        help='Percentage of the target that has been achieved (achieved / target × 100).',
    )

    gap_amount = fields.Monetary(
        string='Gap',
        currency_field='currency_id',
        compute='_compute_achievement_rate',
        store=True,
        help='Difference between achieved and target amount (can be negative).',
    )

    # -------------------------------------------------------------------------
    # Compute: achieved_amount
    # -------------------------------------------------------------------------
    @api.depends(
        'industry_id',
        'year',
        'month',
        'company_id',
        'target_id.state',
    )
    def _compute_achieved_amount(self):
        """
        For each line, query confirmed sale.orders where:
          - state in ('sale', 'done')  [confirmed orders]
          - date_order month == self.month
          - date_order year  == self.year  (via related field)
          - partner_id.industry_id == self.industry_id
          - company_id == self.company_id

        We use a direct ORM read_group for performance instead of
        iterating individual records.
        """
        SaleOrder = self.env['sale.order']

        for line in self:
            if not line.industry_id or not line.month or not line.year:
                line.achieved_amount = 0.0
                continue

            month_int = int(line.month)
            year_int = int(line.year)

            # Build domain
            domain = [
                ('state', 'in', ['sale', 'done']),
                ('company_id', '=', line.company_id.id),
                ('partner_id.industry_id', '=', line.industry_id.id),
                # Filter by year-month using date_order (Datetime field)
                ('date_order', '>=', f'{year_int:04d}-{month_int:02d}-01 00:00:00'),
                ('date_order', '<',
                 # Next month boundary (handles December → January crossover)
                 f'{year_int + (1 if month_int == 12 else 0):04d}'
                 f'-{1 if month_int == 12 else month_int + 1:02d}'
                 f'-01 00:00:00'),
            ]

            # Aggregate without loading full records
            result = SaleOrder.read_group(
                domain=domain,
                fields=['amount_untaxed:sum'],
                groupby=[],
            )
            line.achieved_amount = result[0]['amount_untaxed'] if result else 0.0

    # -------------------------------------------------------------------------
    # Compute: achievement_rate & gap_amount
    # -------------------------------------------------------------------------
    @api.depends('target_amount', 'achieved_amount')
    def _compute_achievement_rate(self):
        """Compute achievement rate percentage and gap."""
        for line in self:
            if line.target_amount:
                line.achievement_rate = (
                    line.achieved_amount / line.target_amount
                ) * 100.0
            else:
                line.achievement_rate = 0.0
            line.gap_amount = line.achieved_amount - line.target_amount

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    _sql_constraints = [
        (
            'unique_industry_month_plan',
            'UNIQUE(target_id, industry_id, month)',
            'A target line for this industry and month already exists in this plan.',
        ),
    ]

    @api.constrains('target_amount')
    def _check_target_amount(self):
        """Target amount must be non-negative."""
        for line in self:
            if line.target_amount < 0:
                raise ValidationError(_(
                    'Target amount cannot be negative on line: %s',
                    line.industry_id.name or 'N/A',
                ))

    # -------------------------------------------------------------------------
    # Display name
    # -------------------------------------------------------------------------
    def name_get(self):
        result = []
        for line in self:
            month_label = dict(self._fields['month'].selection).get(line.month, '')
            name = f'{line.industry_id.name or "?"} — {month_label} {line.year}'
            result.append((line.id, name))
        return result
