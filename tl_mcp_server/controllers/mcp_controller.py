import json
import logging
from odoo import http, fields
from odoo.http import request, Response
from odoo.exceptions import AccessDenied, AccessError

_logger = logging.getLogger(__name__)

class McpController(http.Controller):

    def _json_response(self, result=None, error=None, id=None):
        resp = {"jsonrpc": "2.0"}
        if id is not None:
            resp["id"] = id
        if error:
            resp["error"] = error
        elif result is not None:
            resp["result"] = result
        return Response(json.dumps(resp), content_type='application/json')

    def _authenticate(self):
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise AccessDenied("Missing or invalid Authorization header.")
        
        token = auth_header.split(' ')[1]
        
        # Primero buscar en mcp.api.key (tokens estáticos)
        api_key = request.env['mcp.api.key'].sudo()._authenticate_silent(token)
        if api_key:
            return api_key
            
        # Luego buscar en mcp.oauth.token (tokens OAuth)
        oauth_token = request.env['mcp.oauth.token'].sudo().search([
            ('access_token', '=', token),
            ('active', '=', True)
        ], limit=1)
        
        if not oauth_token:
            raise AccessDenied("Invalid or expired token.")
            
        if oauth_token.expires_at and oauth_token.expires_at < fields.Datetime.now():
            raise AccessDenied("Token expired.")
            
        # Actualizar timestamp
        oauth_token.sudo().write({'active': True})
        return oauth_token

    def _check_model_access(self, api_key, model_name, operation):
        """
        operation: 'can_read', 'can_write', 'can_create', 'can_delete'
        """
        model_access = request.env['mcp.model.access'].sudo().search([
            ('api_key_id', '=', api_key.id)
        ])
        if not model_access:
            # Open mode: if no rules, permit everything (Odoo ACLs still apply)
            return True
        
        model_id = request.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)
        if not model_id:
            raise AccessError(f"Model {model_name} not found in ir.model.")

        access = model_access.filtered(lambda a: a.model_id.id == model_id.id)
        if not access:
            raise AccessError(f"API Key does not have access to model {model_name}.")
        
        if not getattr(access[0], operation):
            raise AccessError(f"API Key does not have {operation} permission on {model_name}.")
        return True

    @http.route('/mcp/health', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    def mcp_health(self):
        return Response(json.dumps({"status": "ok", "version": "1.0.0"}), content_type='application/json')

    @http.route('/mcp', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    def mcp_endpoint(self, **kw):
        try:
            body = request.httprequest.get_data().decode('utf-8')
            payload = json.loads(body)
        except Exception as e:
            return self._json_response(error={"code": -32700, "message": "Parse error"})

        req_id = payload.get('id')
        method = payload.get('method')
        params = payload.get('params', {})

        try:
            api_key = self._authenticate()
        except AccessDenied as e:
            return self._json_response(error={"code": -32000, "message": str(e)}, id=req_id)
        except Exception as e:
            return self._json_response(error={"code": -32603, "message": str(e)}, id=req_id)

        try:
            env = request.env(user=api_key.user_id.id)
            result = self._dispatch(env, api_key, method, params)
            return self._json_response(result=result, id=req_id)
        except AccessError as e:
            return self._json_response(error={"code": -32001, "message": str(e)}, id=req_id)
        except Exception as e:
            _logger.exception("MCP Error")
            return self._json_response(error={"code": -32603, "message": str(e)}, id=req_id)

    def _dispatch(self, env, api_key, method, params):
        if method == 'initialize':
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "Odoo MCP Server",
                    "version": "1.0.0"
                }
            }
        elif method == 'notifications/initialized':
            return {}
        elif method == 'ping':
            return {}
        elif method == 'tools/list':
            return self._tools_list()
        elif method == 'tools/call':
            tool_name = params.get('name')
            args = params.get('arguments', {})
            return self._tools_call(env, api_key, tool_name, args)
        else:
            raise Exception(f"Method {method} not found")

    def _tools_list(self):
        tools = [
            {
                "name": "list_models",
                "description": "Returns all available models in Odoo.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "describe_model",
                "description": "Returns the fields for a specific model.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "description": "The technical name of the model"}
                    },
                    "required": ["model"]
                }
            },
            {
                "name": "search_records",
                "description": "Searches for records in a model based on a domain.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "domain": {"type": "array", "items": {}},
                        "fields": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "default": 80},
                        "offset": {"type": "integer", "default": 0},
                        "order": {"type": "string"}
                    },
                    "required": ["model"]
                }
            },
            {
                "name": "get_record",
                "description": "Gets a single record by its ID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "id": {"type": "integer"},
                        "fields": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["model", "id"]
                }
            },
            {
                "name": "create_record",
                "description": "Creates a new record in a model.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "values": {"type": "object"}
                    },
                    "required": ["model", "values"]
                }
            },
            {
                "name": "update_record",
                "description": "Updates an existing record.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "id": {"type": "integer"},
                        "values": {"type": "object"}
                    },
                    "required": ["model", "id", "values"]
                }
            },
            {
                "name": "delete_record",
                "description": "Deletes a record.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "id": {"type": "integer"}
                    },
                    "required": ["model", "id"]
                }
            },
            {
                "name": "aggregate_records",
                "description": "Groups and aggregates records using read_group.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "domain": {"type": "array", "items": {}},
                        "groupby": {"type": "array", "items": {"type": "string"}},
                        "fields": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "default": 80}
                    },
                    "required": ["model", "domain", "groupby", "fields"]
                }
            }
        ]
        return {"tools": tools}

    def _tools_call(self, env, api_key, tool_name, args):
        if tool_name == 'list_models':
            self._check_model_access(api_key, 'ir.model', 'can_read')
            models = env['ir.model'].search_read([], ['name', 'model'], limit=5000)
            return {"content": [{"type": "text", "text": json.dumps(models)}]}
            
        elif tool_name == 'describe_model':
            model_name = args.get('model')
            self._check_model_access(api_key, 'ir.model.fields', 'can_read')
            fields_data = env['ir.model.fields'].search_read(
                [('model', '=', model_name)],
                ['name', 'field_description', 'ttype', 'required', 'relation']
            )
            return {"content": [{"type": "text", "text": json.dumps(fields_data)}]}
            
        elif tool_name == 'search_records':
            model_name = args.get('model')
            self._check_model_access(api_key, model_name, 'can_read')
            domain = args.get('domain', [])
            fields_list = args.get('fields', [])
            limit = args.get('limit', 80)
            offset = args.get('offset', 0)
            order = args.get('order', '')
            
            records = env[model_name].search_read(domain, fields_list, offset=offset, limit=limit, order=order)
            self._serialize_dates(records)
            return {"content": [{"type": "text", "text": json.dumps(records)}]}

        elif tool_name == 'get_record':
            model_name = args.get('model')
            record_id = args.get('id')
            self._check_model_access(api_key, model_name, 'can_read')
            fields_list = args.get('fields', [])
            record = env[model_name].browse(record_id).read(fields_list)
            if record:
                self._serialize_dates(record)
            return {"content": [{"type": "text", "text": json.dumps(record[0] if record else {})} ]}

        elif tool_name == 'create_record':
            model_name = args.get('model')
            values = args.get('values', {})
            self._check_model_access(api_key, model_name, 'can_create')
            new_record = env[model_name].create(values)
            return {"content": [{"type": "text", "text": json.dumps({"id": new_record.id})} ]}

        elif tool_name == 'update_record':
            model_name = args.get('model')
            record_id = args.get('id')
            values = args.get('values', {})
            self._check_model_access(api_key, model_name, 'can_write')
            env[model_name].browse(record_id).write(values)
            return {"content": [{"type": "text", "text": json.dumps({"success": True})} ]}

        elif tool_name == 'delete_record':
            model_name = args.get('model')
            record_id = args.get('id')
            self._check_model_access(api_key, model_name, 'can_delete')
            env[model_name].browse(record_id).unlink()
            return {"content": [{"type": "text", "text": json.dumps({"success": True})} ]}

        elif tool_name == 'aggregate_records':
            model_name = args.get('model')
            domain = args.get('domain', [])
            groupby = args.get('groupby', [])
            fields_list = args.get('fields', [])
            limit = args.get('limit', 80)
            self._check_model_access(api_key, model_name, 'can_read')
            groups = env[model_name].read_group(domain, fields_list, groupby, limit=limit)
            return {"content": [{"type": "text", "text": json.dumps(groups)}]}

        else:
            raise Exception(f"Tool {tool_name} not found")

    def _serialize_dates(self, records):
        for r in records:
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
