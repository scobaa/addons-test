from odoo import models, fields

class McpOauthCode(models.Model):
    _name = 'mcp.oauth.code'
    _description = 'MCP OAuth Authorization Code'

    code = fields.Char('Authorization Code', required=True, index=True)
    client_id = fields.Char('Client ID')
    user_id = fields.Many2one('res.users', 'User')
    expires_at = fields.Datetime('Expires At')
    used = fields.Boolean('Used', default=False)
    redirect_uri = fields.Char('Redirect URI')
    state = fields.Char('State')
    code_challenge = fields.Char('Code Challenge')
    code_challenge_method = fields.Char('Code Challenge Method')
