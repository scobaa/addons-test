import secrets
from odoo import models, fields, api
from odoo.exceptions import AccessDenied

class McpApiKey(models.Model):
    _name = 'mcp.api.key'
    _description = 'MCP API Key'

    name = fields.Char('Name', required=True)
    token = fields.Char('Token', readonly=True, copy=False)
    user_id = fields.Many2one('res.users', 'User', required=True, default=lambda self: self.env.user)
    active = fields.Boolean('Active', default=True)
    last_used = fields.Datetime('Last Used', readonly=True)
    note = fields.Text('Notes')
    
    # Model access relation
    model_access_ids = fields.One2many('mcp.model.access', 'api_key_id', string='Model Access')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('token'):
                vals['token'] = secrets.token_hex(32)
        return super().create(vals_list)

    @api.model
    def _authenticate(self, token):
        if not token:
            raise AccessDenied("Token not provided.")
        api_key = self.sudo().search([('token', '=', token), ('active', '=', True)], limit=1)
        if not api_key:
            raise AccessDenied("Invalid or inactive API Key.")
        api_key.sudo().write({'last_used': fields.Datetime.now()})
        return api_key
