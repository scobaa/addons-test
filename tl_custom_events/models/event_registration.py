# -*- coding: utf-8 -*-
from odoo import models, fields

class EventRegistration(models.Model):
    _inherit = 'event.registration'

    is_apen_client = fields.Boolean(string='Cliente de APEN')
    newsletter_accepted = fields.Boolean(string='Newsletter Aceptada')
    newsletter_lang = fields.Selection([
        ('es', 'Español'),
        ('ca', 'Catalán')
    ], string='Idioma de Newsletter')