# MCP Server (tl_mcp_server)

Este es un módulo de Odoo 19 que expone directamente un servidor **Model Context Protocol (MCP)** a través de HTTP.
Permite a herramientas como Claude Desktop conectarse al entorno de Odoo e interactuar con sus registros y modelos de forma segura y respetando los permisos (ACLs) configurados.

## Configuración de Claude Desktop

Para conectar Claude Desktop u otro cliente compatible con MCP a este servidor Odoo, añade la siguiente configuración a tu archivo `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "odoo": {
      "type": "http",
      "url": "https://TU_URL_ODOO/mcp",
      "headers": {
        "Authorization": "Bearer TU_TOKEN_AQUI"
      }
    }
  }
}
```

Reemplaza `TU_URL_ODOO` por la URL base de tu servidor Odoo y `TU_TOKEN_AQUI` por el token generado en el menú *Ajustes > Técnico > MCP Server > API Keys*.

## Características
- Implementación de las herramientas MCP estándar (`list_models`, `describe_model`, `search_records`, `get_record`, `create_record`, `update_record`, `delete_record`, `aggregate_records`).
- Control de acceso configurable por modelo (`can_read`, `can_write`, `can_create`, `can_delete`).
- Respeto total a los ACLs y reglas de acceso de Odoo a través de `sudo(user_id)`.
- Sin dependencias externas a la Standard Library de Python u Odoo.
