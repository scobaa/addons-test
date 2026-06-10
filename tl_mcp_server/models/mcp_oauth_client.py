import secrets
from odoo import models, fields, api

class McpOauthClient(models.Model):
    _name = 'mcp.oauth.client'
    _description = 'MCP OAuth Client'

    name = fields.Char('Client Name', required=True)
    client_id = fields.Char('Client ID', readonly=True, copy=False)
    client_secret = fields.Char('Client Secret', readonly=True, copy=False)
    active = fields.Boolean('Active', default=True)
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    note = fields.Text('Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('client_id'):
                vals['client_id'] = 'mcp_' + secrets.token_hex(16)
            if not vals.get('client_secret'):
                vals['client_secret'] = secrets.token_hex(32)
        return super().create(vals_list)
