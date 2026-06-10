from odoo import models, fields

class McpOauthToken(models.Model):
    _name = 'mcp.oauth.token'
    _description = 'MCP OAuth Access Token'

    access_token = fields.Char('Access Token', required=True, index=True)
    client_id = fields.Char('Client ID')
    user_id = fields.Many2one('res.users', 'User')
    expires_at = fields.Datetime('Expires At')
    active = fields.Boolean('Active', default=True)
    scope = fields.Char('Scope', default='mcp')
