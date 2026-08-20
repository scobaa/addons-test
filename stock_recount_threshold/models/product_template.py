# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    recount_enabled = fields.Boolean(
        string='Recuento automático activo',
        default=False,
        help='Si está activo, cuando la cantidad disponible de este '
             'producto cruce el umbral definido abajo tras un picking o '
             'consumo, se generará automáticamente una solicitud de '
             'recuento.',
    )
    recount_threshold_qty = fields.Float(
        string='Umbral de recuento',
        default=0.0,
        help='Cuando la cantidad disponible (on hand) de este producto, '
             'en una ubicación dada, cae a este valor o por debajo tras '
             'un movimiento de stock, se generará una solicitud de '
             'recuento automáticamente.',
    )
    recount_responsible_id = fields.Many2one(
        'res.users',
        string='Responsable del recuento',
        help='Usuario al que se le asignará la actividad de recuento. '
             'Si se deja vacío, se usará el responsable de la operación '
             'de stock que disparó el umbral.',
    )
