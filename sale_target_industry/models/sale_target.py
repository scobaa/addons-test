# -*- coding: utf-8 -*-
# License OPL-1
"""
sale_target.py
==============
Model: sale.target
Header record that groups a set of monthly industry targets under a
single "plan".  Holds general metadata (name, responsible user, fiscal
year) and provides a one-click recalculation button that refreshes
all its child lines.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleTarget(models.Model):
    _name = 'sale.target'
    _description = 'Sales Target Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, name asc'

    # -------------------------------------------------------------------------
    # Basic fields
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Plan Name',
        required=True,
        tracking=True,
        help='Descriptive name for this target plan, e.g. "Q1 2025 Industrial".',
    )

    year = fields.Integer(
        string='Year',
        required=True,
        default=lambda self: fields.Date.today().year,
        tracking=True,
        help='Fiscal / calendar year this plan covers.',
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
        help='Sales manager responsible for this plan.',
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
        help='Currency inherited from the company.',
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    notes = fields.Html(
        string='Notes',
        help='Internal notes about this target plan.',
    )

    # -------------------------------------------------------------------------
    # Relational fields
    # -------------------------------------------------------------------------
    line_ids = fields.One2many(
        comodel_name='sale.target.line',
        inverse_name='target_id',
        string='Target Lines',
        copy=True,
    )

    # -------------------------------------------------------------------------
    # Computed summary fields (stored for reporting)
    # -------------------------------------------------------------------------
    total_target_amount = fields.Monetary(
        string='Total Target',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        help='Sum of all target amounts across all lines.',
    )

    total_achieved_amount = fields.Monetary(
        string='Total Achieved',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        help='Sum of all achieved amounts across all lines.',
    )

    total_achievement_rate = fields.Float(
        string='Overall Achievement (%)',
        compute='_compute_totals',
        store=True,
        digits=(5, 2),
        help='Weighted average achievement rate across all lines.',
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------
    @api.depends(
        'line_ids.target_amount',
        'line_ids.achieved_amount',
        'line_ids.achievement_rate',
    )
    def _compute_totals(self):
        """Aggregate target and achieved amounts from all child lines."""
        for plan in self:
            total_target = sum(plan.line_ids.mapped('target_amount'))
            total_achieved = sum(plan.line_ids.mapped('achieved_amount'))
            plan.total_target_amount = total_target
            plan.total_achieved_amount = total_achieved
            if total_target:
                plan.total_achievement_rate = (total_achieved / total_target) * 100.0
            else:
                plan.total_achievement_rate = 0.0

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_recalculate(self):
        """
        Manual recalculation button.
        Triggers _compute_achieved_amount on every child line so that
        achieved figures are refreshed from the current sale.order data.
        """
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_(
                'There are no target lines to recalculate. '
                'Please add at least one line first.'
            ))
        # Force recompute of stored computed fields on all lines
        self.line_ids._compute_achieved_amount()
        # Recompute plan totals
        self._compute_totals()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recalculation Complete'),
                'message': _(
                    'All target lines for "%s" have been updated.', self.name
                ),
                'sticky': False,
                'type': 'success',
            },
        }

    def action_set_active(self):
        """Move the plan to Active state."""
        self.write({'state': 'active'})

    def action_set_done(self):
        """Mark the plan as Done."""
        self.write({'state': 'done'})

    def action_set_draft(self):
        """Reset the plan to Draft."""
        self.write({'state': 'draft'})

    def action_cancel(self):
        """Cancel the plan."""
        self.write({'state': 'cancelled'})
