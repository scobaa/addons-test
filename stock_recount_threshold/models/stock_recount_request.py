# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.translate import _


class StockRecountRequest(models.Model):
    _name = 'stock.recount.request'
    _description = 'Solicitud de recuento por umbral'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'product_id'

    product_id = fields.Many2one(
        'product.product', string='Producto', required=True, index=True,
    )
    location_id = fields.Many2one(
        'stock.location', string='Ubicación', required=True, index=True,
    )
    triggering_move_id = fields.Many2one(
        'stock.move', string='Movimiento que lo disparó',
    )
    quantity_at_trigger = fields.Float(
        string='Cantidad disponible al disparar',
        help='Cantidad on-hand justo después del movimiento que cruzó '
             'el umbral.',
    )
    threshold_qty = fields.Float(string='Umbral configurado')
    responsible_id = fields.Many2one(
        'res.users', string='Responsable', required=True,
    )
    state = fields.Selection(
        [
            ('pending', 'Pendiente'),
            ('done', 'Recontado'),
            ('cancel', 'Cancelado'),
        ],
        string='Estado', default='pending', required=True,
    )
    activity_id = fields.Many2one(
        'mail.activity', string='Actividad relacionada',
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        default=lambda self: self.env.company,
    )

    def action_mark_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_open_inventory_adjustment(self):
        """Abre la vista de ajuste de inventario (quant) filtrada al
        producto/ubicación de esta solicitud, lista para que el usuario
        introduzca la cantidad contada.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ajuste de inventario'),
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', self.location_id.id),
            ],
            'context': {
                'default_product_id': self.product_id.id,
                'default_location_id': self.location_id.id,
                'search_default_product_id': self.product_id.id,
            },
        }

    @api.model
    def create_from_move(self, move, quantity_at_trigger, threshold_qty,
                          location):
        """Crea la solicitud de recuento y una actividad asociada al
        responsable configurado en el producto (o al usuario del
        movimiento si no hay ninguno configurado)."""
        product = move.product_id
        responsible = (
            product.recount_responsible_id
            or move.picking_id.user_id
            or self.env.user
        )
        request = self.create({
            'product_id': product.id,
            'location_id': location.id,
            'triggering_move_id': move.id,
            'quantity_at_trigger': quantity_at_trigger,
            'threshold_qty': threshold_qty,
            'responsible_id': responsible.id,
        })
        activity = request.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=_('Recuento requerido: %s') % product.display_name,
            note=_(
                'La cantidad disponible de %(product)s en %(location)s '
                'bajó a %(qty).2f, igual o por debajo del umbral '
                'configurado (%(threshold).2f). Por favor, realiza un '
                'recuento físico.'
            ) % {
                'product': product.display_name,
                'location': location.display_name,
                'qty': quantity_at_trigger,
                'threshold': threshold_qty,
            },
            user_id=responsible.id,
        )
        request.activity_id = activity.id
        return request
