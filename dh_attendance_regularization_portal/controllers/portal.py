# -*- coding: utf-8 -*-
from collections import OrderedDict
from datetime import datetime

from pytz import timezone, utc

from odoo import fields, http, _
from odoo.http import request
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.tools import groupby as groupbyelem
from operator import itemgetter


def _fmt_dt(value):
    """Convierte un datetime UTC al timezone del usuario y lo formatea."""
    if not value:
        return ''
    local_dt = fields.Datetime.context_timestamp(request.env.user, value)
    return local_dt.strftime('%d/%m/%Y %H:%M')


def _local_str_to_utc(dt_str, fmt='%Y-%m-%dT%H:%M'):
    """Convierte un string datetime-local (hora local del usuario) a UTC naive."""
    user_tz = request.env.user.tz or 'UTC'
    local_tz = timezone(user_tz)
    naive_dt = datetime.strptime(dt_str, fmt)
    local_dt = local_tz.localize(naive_dt)
    return local_dt.astimezone(utc).replace(tzinfo=None)


def _dt_to_local_str(value):
    """Convierte un datetime UTC al timezone del usuario en formato datetime-local."""
    if not value:
        return ''
    local_dt = fields.Datetime.context_timestamp(request.env.user, value)
    return local_dt.strftime('%Y-%m-%dT%H:%M')


class AttendanceRegularizationPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'regularization_count' in counters:
            count = request.env['attendance.regular'].sudo().search_count([
                ('employee_id', '=', request.env.user.employee_id.id)
            ])
            values['regularization_count'] = count
        return values

    # ------------------------------------------------------------------
    # Search bar helpers
    # ------------------------------------------------------------------

    def _get_regularization_searchbar_sortings(self):
        return {
            'from_date': {'label': _('Fecha inicio'), 'order': 'from_date desc'},
            'create_date': {'label': _('Más reciente'), 'order': 'create_date desc'},
            'state': {'label': _('Estado'), 'order': 'state_select'},
        }

    def _get_regularization_searchbar_groupby(self):
        return {
            'none': {'input': 'none', 'label': _('Ninguno'), 'order': 1},
            'state': {'input': 'state_select', 'label': _('Estado'), 'order': 2},
        }

    def _get_regularization_searchbar_filterby(self):
        return {
            'all': {'label': _('Todos'), 'domain': []},
            'draft': {'label': _('Borrador'), 'domain': [('state_select', '=', 'draft')]},
            'requested': {'label': _('Solicitado'), 'domain': [('state_select', '=', 'requested')]},
            'approved': {'label': _('Aprobado'), 'domain': [('state_select', '=', 'approved')]},
            'rejected': {'label': _('Rechazado'), 'domain': [('state_select', '=', 'reject')]},
        }

    def _get_regularization_searchbar_inputs(self):
        return {
            'all': {'input': 'all', 'label': _('Buscar en todo'), 'order': 1},
        }

    def _get_regularization_search_domain(self, search_in, search):
        if search_in == 'all':
            return ['|',
                ('reg_reason', 'ilike', search),
                ('reg_category.type', 'ilike', search),
            ]
        return []

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @http.route(['/my/regularization'], type='http', auth='user', website=True)
    def portal_regularization(self, page=1, sortby=None, groupby=None,
                              filterby=None, search=None, search_in='all', **kw):
        values = self._prepare_portal_layout_values()
        RegObj = request.env['attendance.regular'].sudo()

        domain = [('employee_id', '=', request.env.user.employee_id.id)]

        searchbar_sortings = self._get_regularization_searchbar_sortings()
        searchbar_groupby = self._get_regularization_searchbar_groupby()
        searchbar_filterby = self._get_regularization_searchbar_filterby()
        searchbar_inputs = self._get_regularization_searchbar_inputs()

        if not sortby:
            sortby = 'from_date'
        sort_order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filterby[filterby]['domain']

        if not groupby:
            groupby = 'none'

        if search and search_in:
            domain += self._get_regularization_search_domain(search_in, search)

        all_records = RegObj.search(domain)
        total = len(all_records)

        pager = portal_pager(
            url='/my/regularization',
            total=total,
            page=page,
            step=self._items_per_page,
        )

        records = RegObj.search(
            [('id', 'in', all_records.ids)],
            order=sort_order,
            limit=self._items_per_page,
            offset=pager['offset'],
        )

        groupby_mapping = {'state': 'state_select'}
        group_field = groupby_mapping.get(groupby)
        if group_field:
            grouped_records = [
                RegObj.concat(*g)
                for k, g in groupbyelem(records, itemgetter(group_field))
            ]
        else:
            grouped_records = [records]

        request.session['regularization_history'] = records.ids[:100]

        state_labels = dict(
            request.env['attendance.regular'].fields_get(
                ['state_select'])['state_select']['selection']
        )

        values.update({
            'page_name': 'hr_regularization',
            'grouped_records': grouped_records,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_filters': searchbar_filterby,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
            'groupby': groupby,
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
            'pager': pager,
            'default_url': '/my/regularization',
            'state_labels': state_labels,
            'fmt_dt': _fmt_dt,
        })
        return request.render(
            'dh_attendance_regularization_portal.portal_my_regularization', values)

    @http.route(['/my/regularization/create'], type='http', auth='user', website=True)
    def portal_regularization_create(self, button_save=None, **kw):
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1)

        if not employee:
            return request.redirect('/my/regularization')

        if button_save == 'save':
            reg_category = kw.get('reg_category')
            from_date = kw.get('from_date')
            to_date = kw.get('to_date')
            reg_reason = kw.get('reg_reason')

            if reg_category and from_date and to_date and reg_reason:
                from_dt = _local_str_to_utc(from_date)
                to_dt = _local_str_to_utc(to_date)
                request.env['attendance.regular'].sudo().create({
                    'reg_category': int(reg_category),
                    'from_date': from_dt,
                    'to_date': to_dt,
                    'reg_reason': reg_reason,
                    'employee_id': employee.id,
                    'state_select': 'requested',
                })
            return request.redirect('/my/regularization')

        categories = request.env['reg.categories'].sudo().search([])
        values = {
            'page_name': 'hr_regularization',
            'categories': categories,
            'employee': employee,
        }
        return request.render(
            'dh_attendance_regularization_portal.portal_regularization_create', values)

    @http.route(['/my/regularization/edit/<int:reg_id>'], type='http', auth='user', website=True)
    def portal_regularization_edit(self, reg_id=None, button_save=None, **kw):
        reg = request.env['attendance.regular'].sudo().browse(reg_id)

        if not reg or reg.employee_id.id != request.env.user.employee_id.id:
            return request.render(
                'dh_attendance_regularization_portal.portal_regularization_access_denied', {})

        if reg.state_select != 'draft':
            return request.redirect('/my/regularization/%d' % reg_id)

        if button_save == 'save':
            reg_category = kw.get('reg_category')
            from_date = kw.get('from_date')
            to_date = kw.get('to_date')
            reg_reason = kw.get('reg_reason')

            if reg_category and from_date and to_date and reg_reason:
                from_dt = _local_str_to_utc(from_date)
                to_dt = _local_str_to_utc(to_date)
                reg.write({
                    'reg_category': int(reg_category),
                    'from_date': from_dt,
                    'to_date': to_dt,
                    'reg_reason': reg_reason,
                })
            return request.redirect('/my/regularization')

        categories = request.env['reg.categories'].sudo().search([])
        values = {
            'page_name': 'hr_regularization',
            'reg': reg,
            'categories': categories,
            'from_date_local': _dt_to_local_str(reg.from_date),
            'to_date_local': _dt_to_local_str(reg.to_date),
        }
        return request.render(
            'dh_attendance_regularization_portal.portal_regularization_edit', values)

    @http.route(['/my/regularization/submit/<int:reg_id>'], type='http', auth='user', website=True)
    def portal_regularization_submit(self, reg_id=None, **kw):
        reg = request.env['attendance.regular'].sudo().browse(reg_id)

        if not reg or reg.employee_id.id != request.env.user.employee_id.id:
            return request.render(
                'dh_attendance_regularization_portal.portal_regularization_access_denied', {})

        if reg.state_select == 'draft':
            reg.action_submit_reg()

        return request.redirect('/my/regularization')

    @http.route(['/my/regularization/delete/<int:reg_id>'], type='http', auth='user', website=True)
    def portal_regularization_delete(self, reg_id=None, **kw):
        reg = request.env['attendance.regular'].sudo().browse(reg_id)

        if reg and reg.employee_id.id == request.env.user.employee_id.id \
                and reg.state_select == 'draft':
            reg.unlink()

        return request.redirect('/my/regularization')

    @http.route(['/my/regularization/<int:reg_id>'], type='http', auth='user', website=True)
    def portal_regularization_view(self, reg_id=None, **kw):
        reg = request.env['attendance.regular'].sudo().browse(reg_id)

        if not reg or reg.employee_id.id != request.env.user.employee_id.id:
            return request.render(
                'dh_attendance_regularization_portal.portal_regularization_access_denied', {})

        state_labels = dict(
            request.env['attendance.regular'].fields_get(
                ['state_select'])['state_select']['selection']
        )

        values = {
            'page_name': 'hr_regularization',
            'reg': reg,
            'state_labels': state_labels,
            'fmt_dt': _fmt_dt,
        }
        return request.render(
            'dh_attendance_regularization_portal.portal_regularization_detail', values)
