# -*- coding: utf-8 -*-
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        moves._check_recount_threshold()
        return moves

    def _check_recount_threshold(self):
        """Tras confirmar movimientos, revisa si alguno deja la cantidad
        disponible del producto, en la ubicación de origen (la que se
        vacía en picking/consumo), igual o por debajo del umbral
        configurado. Si es así, genera una solicitud de recuento.
        """
        RecountRequest = self.env['stock.recount.request']

        for move in self:
            product = move.product_id
            if not product.recount_enabled:
                continue
            if product.recount_threshold_qty is None:
                continue

            # La ubicación que "se vacía" es la de origen del movimiento,
            # solo nos interesa si es una ubicación interna (almacén),
            # no ubicaciones virtuales como Clientes o Proveedores.
            location = move.location_id
            if location.usage != 'internal':
                continue

            # Evitar duplicar solicitudes: si ya hay una pendiente para
            # este producto+ubicación, no crear otra.
            existing = RecountRequest.search([
                ('product_id', '=', product.id),
                ('location_id', '=', location.id),
                ('state', '=', 'pending'),
            ], limit=1)
            if existing:
                continue

            quant_qty = sum(self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id', '=', location.id),
            ]).mapped('quantity'))

            if quant_qty <= product.recount_threshold_qty:
                RecountRequest.create_from_move(
                    move,
                    quantity_at_trigger=quant_qty,
                    threshold_qty=product.recount_threshold_qty,
                    location=location,
                )
