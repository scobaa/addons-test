# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_event.controllers.main import WebsiteEventController

class WebsiteEventControllerInherit(WebsiteEventController):

    @http.route()
    def registration_confirm(self, event, **post):
        # Procesamos los datos antes
        registrations_data = self._process_attendees_form(event, post)
        attendee_emails = [attendee.get('email') for attendee in registrations_data if attendee.get('email')]
        
        # 1. Ejecución original
        response = super(WebsiteEventControllerInherit, self).registration_confirm(event, **post)
        
        # 2. Actualizar campos personalizados en las registraciones (por asistente)
        newsletter_accepted = post.get('subscribe_newsletter_global') in ('on', 'True', 'true', '1')
        newsletter_lang = post.get('newsletter_lang')
        for idx, attendee in enumerate(registrations_data, start=1):
            email = attendee.get('email')
            if not email:
                continue

            is_apen_client = post.get(f'is_apen_client_{idx}') in ('on', 'True', 'true', '1')

            registration = request.env['event.registration'].sudo().search([
                ('event_id', '=', event.id),
                ('email', '=', email)
            ], limit=1)
            if registration:
                registration.sudo().write({
                    'is_apen_client': is_apen_client,
                    'newsletter_accepted': newsletter_accepted,
                    'newsletter_lang': newsletter_lang if newsletter_accepted else False,
                })
        
        # 3. Suscripción a Newsletter según el idioma
        if newsletter_accepted:
            # Obtener IDs de las listas de correo según idioma (personalizables por Parámetros del Sistema)
            mailing_list_es_id = int(request.env['ir.config_parameter'].sudo().get_param('tl_custom_events.newsletter_es_list_id', 31))
            mailing_list_ca_id = int(request.env['ir.config_parameter'].sudo().get_param('tl_custom_events.newsletter_ca_list_id', 30))
            
            mailing_list_id = mailing_list_ca_id if newsletter_lang == 'ca' else mailing_list_es_id
            
            # Verificar si la lista seleccionada existe en la base de datos
            mailing_list = request.env['mailing.list'].sudo().browse(mailing_list_id).exists()
            if not mailing_list:
                # Si no existe la lista (ej. el ID 10 de catalán no está creado aún), usamos la de español por defecto
                mailing_list_id = mailing_list_es_id
                mailing_list = request.env['mailing.list'].sudo().browse(mailing_list_id).exists()
            
            # Proceder solo si la lista existe en la base de datos para evitar errores de clave foránea (ForeignKeyViolation)
            if mailing_list:
                for attendee in registrations_data:
                    email = attendee.get('email')
                    name = attendee.get('name')
                    
                    if email:
                        # MODELO CORRECTO EN ODOO 18: 'mailing.contact'
                        contact = request.env['mailing.contact'].sudo().search([
                            ('email', '=', email)
                        ], limit=1)
                        
                        if not contact:
                            contact = request.env['mailing.contact'].sudo().create({
                                'name': name,
                                'email': email,
                            })
                        
                        # MODELO CORRECTO EN ODOO 18: 'mailing.subscription'
                        existing_sub = request.env['mailing.subscription'].sudo().search([
                            ('contact_id', '=', contact.id),
                            ('list_id', '=', mailing_list_id)
                        ], limit=1)
                        
                        if not existing_sub:
                            request.env['mailing.subscription'].sudo().create({
                                'contact_id': contact.id,
                                'list_id': mailing_list_id,
                            })

        return response