from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    crear_lead = fields.Boolean(string="Crear Lead al completar encuesta", default=False)
    team_id = fields.Many2one('crm.team', string="Equipo de Ventas", help="Equipo de ventas al que se asignará el lead")
    source_id = fields.Many2one('utm.source', string="Origen de Lead", help="Origen que se asignará al lead creado")
    campaign_id = fields.Many2one('utm.campaign', string="Campaña de Lead", help="Campaña que se asignará al lead creado")
    medium_id = fields.Many2one('utm.medium', string="Medio de Lead", help="Medio que se asignará al lead creado")
    user_id = fields.Many2one('res.users', string="Responsable de Lead", help="Usuario responsable al que se asignará el lead creado")