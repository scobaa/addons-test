from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    flexible_hours = fields.Boolean(string='Horario flexible', default=False, related='employee_id.flexible_hours', readonly=False)