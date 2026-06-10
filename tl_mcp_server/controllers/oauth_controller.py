import json
import secrets
import hashlib
import base64
import werkzeug
from datetime import timedelta
from urllib.parse import urlencode, quote
from odoo import http, fields
from odoo.http import request, Response

class OAuthController(http.Controller):

    @http.route('/.well-known/oauth-authorization-server', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    def get_oauth_metadata(self):
        base_url = request.httprequest.host_url.rstrip('/')
        metadata = {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256", "plain"],
            "scopes_supported": ["mcp"]
        }
        return Response(json.dumps(metadata), content_type='application/json')

    @http.route('/oauth/authorize', type='http', auth='none', methods=['GET', 'POST'], csrf=False, cors='*')
    def oauth_authorize(self, **kwargs):
        client_id = kwargs.get('client_id')
        redirect_uri = kwargs.get('redirect_uri')
        state = kwargs.get('state')
        code_challenge = kwargs.get('code_challenge')
        code_challenge_method = kwargs.get('code_challenge_method', 'plain')

        # Check if user is logged in via session
        uid = request.session.uid
        if not uid or uid == request.env.ref('base.public_user').id:
            # Store OAuth params in session so we can recover them after login
            request.session['oauth_params'] = {
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': code_challenge_method,
            }
            return werkzeug.utils.redirect('/web/login')

        # Recover params from session if not in kwargs (post-login redirect)
        if not client_id:
            oauth_params = request.session.pop('oauth_params', {})
            client_id = oauth_params.get('client_id')
            redirect_uri = oauth_params.get('redirect_uri')
            state = oauth_params.get('state')
            code_challenge = oauth_params.get('code_challenge')
            code_challenge_method = oauth_params.get('code_challenge_method', 'plain')

        if not client_id or not redirect_uri:
            return Response("Missing client_id or redirect_uri", status=400)

        # Validate client
        client = request.env['mcp.oauth.client'].sudo().search([
            ('client_id', '=', client_id),
            ('active', '=', True)
        ], limit=1)
        if not client:
            return Response("Invalid client_id", status=400)

        # Generate authorization code
        code = secrets.token_hex(32)
        request.env['mcp.oauth.code'].sudo().create({
            'code': code,
            'client_id': client_id,
            'user_id': uid,
            'expires_at': fields.Datetime.now() + timedelta(minutes=10),
            'redirect_uri': redirect_uri,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': code_challenge_method,
        })

        # Redirect back to client
        params = {'code': code}
        if state:
            params['state'] = state
        separator = '&' if '?' in redirect_uri else '?'
        final_redirect = redirect_uri + separator + urlencode(params)
        return werkzeug.utils.redirect(final_redirect)

    @http.route('/oauth/token', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    def oauth_token(self, **kwargs):
        params = dict(kwargs)
        if request.httprequest.data:
            try:
                json_data = json.loads(request.httprequest.data.decode('utf-8'))
                params.update(json_data)
            except Exception:
                pass

        grant_type = params.get('grant_type')
        code_str = params.get('code')
        client_id = params.get('client_id')
        code_verifier = params.get('code_verifier')

        if grant_type != 'authorization_code':
            return self._json_error("unsupported_grant_type")

        auth_code = request.env['mcp.oauth.code'].sudo().search([
            ('code', '=', code_str),
            ('client_id', '=', client_id),
            ('used', '=', False)
        ], limit=1)

        if not auth_code:
            return self._json_error("invalid_grant", "Invalid code")

        if auth_code.expires_at and auth_code.expires_at < fields.Datetime.now():
            return self._json_error("invalid_grant", "Code expired")

        # Verify PKCE if present
        if auth_code.code_challenge:
            if not code_verifier:
                return self._json_error("invalid_request", "Missing code_verifier")
            if auth_code.code_challenge_method == 'S256':
                challenge = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                ).rstrip(b'=').decode()
                if challenge != auth_code.code_challenge:
                    return self._json_error("invalid_grant", "Code verifier mismatch")
            else:
                if code_verifier != auth_code.code_challenge:
                    return self._json_error("invalid_grant", "Code verifier mismatch")

        auth_code.sudo().write({'used': True})

        access_token = secrets.token_hex(32)
        request.env['mcp.oauth.token'].sudo().create({
            'access_token': access_token,
            'client_id': client_id,
            'user_id': auth_code.user_id.id,
            'expires_at': fields.Datetime.now() + timedelta(hours=1),
            'scope': 'mcp'
        })

        return Response(json.dumps({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "mcp"
        }), content_type='application/json')

    def _json_error(self, error, error_description=None):
        resp = {"error": error}
        if error_description:
            resp["error_description"] = error_description
        return Response(json.dumps(resp), status=400, content_type='application/json')
