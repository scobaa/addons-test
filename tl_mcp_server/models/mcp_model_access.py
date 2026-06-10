from odoo import models, fields

class McpModelAccess(models.Model):
    _name = 'mcp.model.access'
    _description = 'MCP Model Access'

    api_key_id = fields.Many2one('mcp.api.key', 'API Key', required=True, ondelete='cascade')
    model_id = fields.Many2one('ir.model', 'Model', required=True, ondelete='cascade')
    
    can_read = fields.Boolean('Read', default=True)
    can_write = fields.Boolean('Write', default=False)
    can_create = fields.Boolean('Create', default=False)
    can_delete = fields.Boolean('Delete', default=False)

    _sql_constraints = [
        ('api_key_model_uniq', 'unique(api_key_id, model_id)', 'A model can only be defined once per API Key.')
    ]
