{
    "name": "MCP Server",
    "version": "19.0.1.0.0",
    "summary": "Implementa un servidor MCP (Model Context Protocol) sobre HTTP en Odoo.",
    "category": "Technical",
    "author": "Antigravity",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/mcp_security.xml",
        "security/ir.model.access.csv",
        "views/mcp_menus.xml",
        "views/mcp_api_key_views.xml",
        "views/mcp_model_access_views.xml",
    ],
    "installable": True,
    "application": False,
}
