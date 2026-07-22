import pytz
from odoo import models, fields, api, _
import datetime
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests
import logging

_logger = logging.getLogger(__name__)

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    location_name = fields.Char(string="Ubicación GPS", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            lat = vals.get("in_latitude")
            lon = vals.get("in_longitude")
            if lat and lon:
                address = self._get_address_from_coords(lat, lon, vals.get('in_mode', ''))
                vals["location_name"] = address
        return super().create(vals_list)

    def _get_address_from_coords(self, lat, lon, in_mode):
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
            headers = {"User-Agent": "OdooHR/1.0"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                display_name = data.get("display_name", "")
            

                if "kiosk" in in_mode:
                    return "Apen"
                if "Carrer de la Ribera del Congost" in display_name:
                    return "Apen"
               
                
                return display_name
        except Exception as e:
            _logger.warning(f"Error al obtener dirección: {e}")
        return "Dirección desconocida"

    def _cron_auto_check_out_all(self, checkout_time=None):
        to_verify = self.env['hr.attendance'].search(
            [
                ('check_out', '=', False),
                ('employee_id.active', '=', True)
            ]
        )
        if not to_verify:
            return
        
        body = _('Esta asistencia se ha cerrado automáticamente porque no se realizó el cierre manual.')
        
        for openatt in to_verify:
            emp = openatt.employee_id
            tz_name = emp.tz or (emp.resource_calendar_id and emp.resource_calendar_id.tz) or self.env.user.tz or 'Europe/Madrid'
            tz = pytz.timezone(tz_name)
            
            check_in_local = pytz.utc.localize(openatt.check_in).astimezone(tz)
            weekday_str = str(check_in_local.weekday())
            
            check_out_local = None
            if emp.resource_calendar_id:
                attendances = emp.resource_calendar_id.attendance_ids.filtered(lambda a: a.dayofweek == weekday_str)
                if attendances:
                    check_in_hour = check_in_local.hour + check_in_local.minute / 60.0 + check_in_local.second / 3600.0
                    
                    best_attendance = None
                    # Intentar encontrar si el fichaje está dentro de un turno
                    for att in attendances:
                        if att.hour_from <= check_in_hour <= att.hour_to:
                            best_attendance = att
                            break
                    
                    # Si no, buscar el primer turno que acabe después de la hora de entrada
                    if not best_attendance:
                        for att in attendances.sorted(key=lambda a: a.hour_from):
                            if att.hour_to > check_in_hour:
                                best_attendance = att
                                break
                    
                    # Si la entrada es posterior a todos los turnos, coger el último
                    if not best_attendance:
                        best_attendance = attendances.sorted(key=lambda a: a.hour_from)[-1]
                        
                    out_hour = best_attendance.hour_to
                    hour = int(out_hour)
                    minute = int(round((out_hour - hour) * 60))
                    if minute >= 60:
                        hour += 1
                        minute = 0
                    if hour > 23:
                        hour = 23
                        minute = 59
                        
                    naive_dt = datetime(check_in_local.year, check_in_local.month, check_in_local.day, hour, minute)
                    check_out_local = tz.localize(naive_dt, is_dst=None)
            
            if not check_out_local:
                # Fallback
                if checkout_time:
                    chk_h, chk_m = map(int, checkout_time.split(':'))
                    naive_dt = datetime(check_in_local.year, check_in_local.month, check_in_local.day, chk_h, chk_m)
                    check_out_local = tz.localize(naive_dt, is_dst=None)
                else:
                    naive_dt = datetime(check_in_local.year, check_in_local.month, check_in_local.day, 18, 0)
                    check_out_local = tz.localize(naive_dt, is_dst=None)
                    
            if check_out_local <= check_in_local:
                check_out_local = check_in_local + timedelta(hours=1)
                
            check_out_utc = check_out_local.astimezone(pytz.utc).replace(tzinfo=None)
            
            openatt.sudo().write({
                "check_out": check_out_utc.strftime('%Y-%m-%d %H:%M:%S'),
                "out_mode": "auto_check_out"
            })
            
            openatt.message_post(body=body)

    def baixa_laboral(self):
        self.ensure_one()
        attendance_date = self.check_in.date() if self.check_in else fields.Date.today()

        leave = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('request_date_from', '<=', attendance_date),
            ('request_date_to', '>=', attendance_date),
            ('state', '=', 'validate'),
            ('holiday_status_id','=',196)
        ], limit=1)

        return bool(leave)

    def defuncio(self):
        self.ensure_one()
        attendance_date = self.check_in.date() if self.check_in else fields.Date.today()

        leave = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('request_date_from', '<=', attendance_date),
            ('request_date_to', '>=', attendance_date),
            ('state', '=', 'validate'),
            ('holiday_status_id','=',180)
        ], limit=1)

        return bool(leave)   

    def _compute_color(self):
        for attendance in self:     
            if attendance.baixa_laboral():
                attendance.color = 2
            elif attendance.defuncio():
                attendance.color = 4
            elif attendance.check_out:
                attendance.color = 1 if attendance.worked_hours > 16 or attendance.out_mode == 'technical' else 0
            else:
                attendance.color = 1 if attendance.check_in < (datetime.today() - timedelta(days=1)) else 10
    
    def _cron_fix_split_shift(self):
        """
        Corrige los fichajes de turno partido cuando el empleado olvida fichar 
        la salida del primer turno y lo hace junto con la entrada del segundo turno.
        (Ej: Ficha de 8:00 a 15:00, y de 15:00 a 18:00 en lugar de 8:00-14:00 y 15:00-18:00)
        """
        today = fields.Date.today()
        start_date = datetime.combine(today - timedelta(days=1), datetime.min.time())
        end_date = datetime.combine(today, datetime.max.time())
        
        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', start_date),
            ('check_in', '<=', end_date),
            ('employee_id.active', '=', True)
        ], order='employee_id, check_in asc')
        
        emp_attendances = {}
        for att in attendances:
            emp_attendances.setdefault(att.employee_id, []).append(att)
            
        for emp, atts in emp_attendances.items():
            if len(atts) < 2 or not emp.resource_calendar_id:
                continue
                
            tz_name = emp.tz or (emp.resource_calendar_id and emp.resource_calendar_id.tz) or self.env.user.tz or 'Europe/Madrid'
            tz = pytz.timezone(tz_name)

            if emp.is_exempt_employee:
                continue
                
            adjusted = False
            adj_date = ""
            adj_time = ""
                
            atts_by_day = {}
            for att in atts:
                local_date = pytz.utc.localize(att.check_in).astimezone(tz).date()
                atts_by_day.setdefault(local_date, []).append(att)
                
            for local_date, day_atts in atts_by_day.items():
                weekday_str = str(local_date.weekday())
                calendar_atts = emp.resource_calendar_id.attendance_ids.filtered(lambda a: a.dayofweek == weekday_str).sorted(key=lambda a: a.hour_from)
                
                if len(calendar_atts) < 2:
                    continue
                    
                # 0. Detectar si un fichaje se ha abierto al final de un turno (olvido de entrar a su hora)
                # Ejemplo: Empieza a las 15:00, termina a las 18:00. Ficha solo a las 18:00 (se abre registro).
                # Lo ajustamos para que sea 15:00-18:00.
                for att in day_atts:
                    if att.in_mode == 'technical' or (att.message_ids and any('automática' in m.body for m in att.message_ids)):
                        continue
                    
                    check_in_local = pytz.utc.localize(att.check_in).astimezone(tz)
                    in_hour = check_in_local.hour + check_in_local.minute / 60.0 + check_in_local.second / 3600.0
                    
                    for shift in calendar_atts:
                        # Si el fichaje empieza cerca del final del turno (ej: entre -15min y +30min del final)
                        # Y NO hay ningún otro fichaje que cubra el grueso de ese turno
                        if abs(in_hour - shift.hour_to) <= 0.5:
                            # Verificar si hay algún fichaje previo que cubra este turno
                            already_covered = any(
                                (pytz.utc.localize(a.check_in).astimezone(tz).hour + pytz.utc.localize(a.check_in).astimezone(tz).minute/60.0) < shift.hour_to - 0.5
                                for a in day_atts if a.id != att.id
                            )
                            
                            if not already_covered:
                                h_in = int(shift.hour_from)
                                m_in = int(round((shift.hour_from - h_in) * 60))
                                if m_in >= 60: h_in += 1; m_in = 0
                                dt_in = tz.localize(datetime(local_date.year, local_date.month, local_date.day, h_in, m_in), is_dst=None)
                                
                                h_out = int(shift.hour_to)
                                m_out = int(round((shift.hour_to - h_out) * 60))
                                if m_out >= 60: h_out += 1; m_out = 0
                                dt_out = tz.localize(datetime(local_date.year, local_date.month, local_date.day, h_out, m_out), is_dst=None)
                                
                                check_in_utc = dt_in.astimezone(pytz.utc).replace(tzinfo=None)
                                check_out_utc = dt_out.astimezone(pytz.utc).replace(tzinfo=None)
                                
                                att.sudo().write({
                                    'check_in': check_in_utc.strftime('%Y-%m-%d %H:%M:%S'),
                                    'check_out': check_out_utc.strftime('%Y-%m-%d %H:%M:%S'),
                                    'in_mode': 'technical', # Marcamos como técnico para que no se re-procese
                                    'out_mode': 'auto_check_out'
                                })
                                att.message_post(body=_('Ajuste automático: Se detectó fichaje de salida sin entrada previa. Ajustado al horario previsto.'))
                                adjusted = True
                                if not adj_date:
                                    adj_date = check_in_local.strftime('%d/%m/%Y')
                                    adj_time = check_in_local.strftime('%H:%M')
                                break

                # 1. Detectar si hay un fichaje único que engloba un descanso no fichado
                i = 0
                while i < len(day_atts):
                    att = day_atts[i]
                    if not att.check_out:
                        i += 1
                        continue
                        
                    check_in_local = pytz.utc.localize(att.check_in).astimezone(tz)
                    check_out_local = pytz.utc.localize(att.check_out).astimezone(tz)
                    in_hour = check_in_local.hour + check_in_local.minute / 60.0 + check_in_local.second / 3600.0
                    out_hour = check_out_local.hour + check_out_local.minute / 60.0 + check_out_local.second / 3600.0
                    
                    has_split = False
                    for j in range(len(calendar_atts) - 1):
                        s1 = calendar_atts[j]
                        s2 = calendar_atts[j+1]
                        
                        if (s2.hour_from - s1.hour_to) >= 0.5:
                            if in_hour <= s1.hour_to + 0.5 and out_hour >= s2.hour_from - 0.5:
                                h1 = int(s1.hour_to)
                                m1 = int(round((s1.hour_to - h1) * 60))
                                if m1 >= 60:
                                    h1 += 1
                                    m1 = 0
                                dt_out1 = tz.localize(datetime(local_date.year, local_date.month, local_date.day, h1, m1), is_dst=None)
                                
                                h2 = int(s2.hour_from)
                                m2 = int(round((s2.hour_from - h2) * 60))
                                if m2 >= 60:
                                    h2 += 1
                                    m2 = 0
                                dt_in2 = tz.localize(datetime(local_date.year, local_date.month, local_date.day, h2, m2), is_dst=None)
                                
                                check_out_utc_1 = dt_out1.astimezone(pytz.utc).replace(tzinfo=None)
                                check_in_utc_2 = dt_in2.astimezone(pytz.utc).replace(tzinfo=None)
                                
                                if check_out_utc_1 <= att.check_in:
                                    check_out_utc_1 = att.check_in + timedelta(minutes=1)
                                if check_in_utc_2 >= att.check_out:
                                    check_in_utc_2 = att.check_out - timedelta(minutes=1)
                                    
                                old_check_out = att.check_out
                                att.sudo().write({
                                    'check_out': check_out_utc_1.strftime('%Y-%m-%d %H:%M:%S'),
                                    'out_mode': 'auto_check_out'
                                })
                                att.message_post(body=_('Check-out automático: descontado el descanso (fichaje continuo partido).'))
                                
                                new_att = self.env['hr.attendance'].sudo().create({
                                    'employee_id': emp.id,
                                    'check_in': check_in_utc_2.strftime('%Y-%m-%d %H:%M:%S'),
                                    'check_out': old_check_out.strftime('%Y-%m-%d %H:%M:%S'),
                                    'in_mode': 'technical',
                                    'out_mode': att.out_mode or 'manual'
                                })
                                new_att.message_post(body=_('Check-in automático: retorno de descanso (fichaje continuo partido).'))
                                adjusted = True
                                if not adj_date:
                                    adj_date = check_in_local.strftime('%d/%m/%Y')
                                    adj_time = check_in_local.strftime('%H:%M')
                                
                                day_atts.append(new_att)
                                has_split = True
                                break
                    
                    if has_split:
                        day_atts.sort(key=lambda a: a.check_in)
                    else:
                        i += 1

                if len(day_atts) < 2:
                    continue
                    
                for i in range(len(day_atts) - 1):
                    att1 = day_atts[i]
                    att2 = day_atts[i+1]
                    
                    if not att1.check_out or not att2.check_in:
                        continue
                        
                    diff_seconds = (att2.check_in - att1.check_out).total_seconds()
                    
                    if 0 <= diff_seconds < 30 * 60:
                        check_in_local = pytz.utc.localize(att1.check_in).astimezone(tz)
                        check_in_hour = check_in_local.hour + check_in_local.minute / 60.0 + check_in_local.second / 3600.0
                        
                        shift1 = None
                        shift2 = None
                        for j in range(len(calendar_atts) - 1):
                            s1 = calendar_atts[j]
                            s2 = calendar_atts[j+1]
                            if s1.hour_from <= check_in_hour <= s1.hour_to or check_in_hour <= s1.hour_to:
                                shift1 = s1
                                shift2 = s2
                                break
                                
                        if shift1 and shift2:
                            if (shift2.hour_from - shift1.hour_to) >= 0.5:
                                h1 = int(shift1.hour_to)
                                m1 = int(round((shift1.hour_to - h1) * 60))
                                if m1 >= 60:
                                    h1 += 1
                                    m1 = 0
                                dt_out1 = tz.localize(datetime(local_date.year, local_date.month, local_date.day, h1, m1), is_dst=None)
                                
                                h2 = int(shift2.hour_from)
                                m2 = int(round((shift2.hour_from - h2) * 60))
                                if m2 >= 60:
                                    h2 += 1
                                    m2 = 0
                                dt_in2 = tz.localize(datetime(local_date.year, local_date.month, local_date.day, h2, m2), is_dst=None)
                                
                                check_out_utc_1 = dt_out1.astimezone(pytz.utc).replace(tzinfo=None)
                                check_in_utc_2 = dt_in2.astimezone(pytz.utc).replace(tzinfo=None)
                                
                                if check_out_utc_1 <= att1.check_in:
                                    check_out_utc_1 = att1.check_in + timedelta(minutes=1)
                                    
                                if att2.check_out and check_in_utc_2 >= att2.check_out:
                                    check_in_utc_2 = att2.check_out - timedelta(minutes=1)
                                
                                body1 = _('Check-out automático por ajuste de turno partido (olvido de fichaje).')
                                att1.sudo().write({
                                    'check_out': check_out_utc_1.strftime('%Y-%m-%d %H:%M:%S'),
                                    'out_mode': 'auto_check_out'
                                })
                                att1.message_post(body=body1)
                                
                                body2 = _('Check-in automático por ajuste de turno partido (olvido de fichaje).')
                                att2.sudo().write({
                                    'check_in': check_in_utc_2.strftime('%Y-%m-%d %H:%M:%S'),
                                    'in_mode': 'technical'
                                })
                                att2.message_post(body=body2)
                                adjusted = True
                                if not adj_date:
                                    adj_date = check_in_local.strftime('%d/%m/%Y')
                                    adj_time = check_in_local.strftime('%H:%M')


                # Al final del día, reevaluamos todos los fichajes del día para asegurar que no se pase más de 1 hora de su jornada prevista
                if day_atts:
                    day_atts_sorted = sorted(day_atts, key=lambda a: a.check_in)
                    
                    total_worked_seconds = 0
                    for a in day_atts_sorted:
                        if a.check_out:
                            total_worked_seconds += (a.check_out - a.check_in).total_seconds()
                        else:
                            # Si hay alguno abierto, calculamos contra la hora actual del cron asumiendo ese será el cierre
                            # u omitimos, pero dado que _cron_auto_check_out se ejecuta también, los debe haber cerrado
                            pass
                            
                    total_expected_seconds = 0
                    for s in calendar_atts:
                        total_expected_seconds += (s.hour_to - s.hour_from) * 3600
                        
                    if total_expected_seconds > 0 and (total_worked_seconds - total_expected_seconds) >= 3600:
                        # Ha trabajado > 1 hora extra respecto a la jornada prevista. 
                        # Cortamos el ÚLTIMO fichaje para que coincida con el fin teórico del turno asignado.
                        last_att = day_atts_sorted[-1]
                        if last_att.check_out:
                            check_in_local = pytz.utc.localize(last_att.check_in).astimezone(tz)
                            in_hour = check_in_local.hour + check_in_local.minute / 60.0 + check_in_local.second / 3600.0
                            
                            best_shift = None
                            for s in calendar_atts:
                                if s.hour_from <= in_hour <= s.hour_to or in_hour <= s.hour_to:
                                    best_shift = s
                                    break
                            
                            if not best_shift:
                                best_shift = calendar_atts[-1]
                                
                            h = int(best_shift.hour_to)
                            m = int(round((best_shift.hour_to - h) * 60))
                            if m >= 60:
                                h += 1
                                m = 0
                                
                            dt_out = tz.localize(datetime(local_date.year, local_date.month, local_date.day, h, m), is_dst=None)
                            check_out_utc = dt_out.astimezone(pytz.utc).replace(tzinfo=None)
                            
                            if check_out_utc < last_att.check_out:
                                last_att.sudo().write({
                                    'check_out': check_out_utc.strftime('%Y-%m-%d %H:%M:%S'),
                                    'out_mode': 'auto_check_out'
                                })
                                last_att.message_post(body=_('Check-out automático: jornada ajustada al superar > 1hr el horario previsto.'))
                                adjusted = True
                                if not adj_date:
                                    adj_date = check_in_local.strftime('%d/%m/%Y')
                                    adj_time = check_in_local.strftime('%H:%M')
            
            if adjusted and emp.work_email:
                subject = _('Ajuste automático de horario aplicado')
                body_html = f'''
                    <p>Hola {emp.name}:</p>
                    <p>Hemos detectado un posible fichaje incorrecto el día {adj_date} a las {adj_time}.</p>
                    <p>Dado que no consta ninguna solicitud de modificación de horario por parte de la empresa, entendemos que puede tratarse de un error puntual u olvido. Por este motivo, el sistema procederá automáticamente a regularizar el registro conforme a su horario habitual.</p>
                    <p>En caso de que el fichaje registrado sea correcto y responda a alguna circunstancia específica, le rogamos que nos lo comunique respondiendo a este correo para poder revisarlo internamente y justificar la incidencia.</p>
                    <p>Gracias por su colaboración.</p>
                    <p>Un saludo,</p>
                '''
                mail = self.env['mail.mail'].sudo().create({
                    'subject': subject,
                    'body_html': body_html,
                    'email_to': emp.work_email,
                    'email_from': 'amartinez@apen.es',
                })
                mail.send()

    def _cron_cap_daily_hours(self):
        """
        Ejecutado a las 22:00. Si un empleado ha superado 9 horas totales en el día,
        recorta el check_out del último fichaje para que el total quede en exactamente 9h.
        """
        threshold_seconds = 9.5 * 3600  # dispara el ajuste si supera 9h 30min
        target_seconds = 9.0 * 3600    # ajusta hasta exactamente 9h

        employees = self.env['hr.employee'].search([('active', '=', True)])

        for emp in employees:
            tz_name = (
                emp.tz
                or (emp.resource_calendar_id and emp.resource_calendar_id.tz)
                or 'Europe/Madrid'
            )
            tz = pytz.timezone(tz_name)

            today_local = datetime.now(tz).date()
            day_start_utc = tz.localize(
                datetime(today_local.year, today_local.month, today_local.day, 0, 0, 0)
            ).astimezone(pytz.utc).replace(tzinfo=None)
            day_end_utc = tz.localize(
                datetime(today_local.year, today_local.month, today_local.day, 23, 59, 59)
            ).astimezone(pytz.utc).replace(tzinfo=None)

            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', day_start_utc),
                ('check_in', '<=', day_end_utc),
                ('check_out', '!=', False),
            ], order='check_in asc')

            if not attendances:
                continue

            total_seconds = sum(
                (a.check_out - a.check_in).total_seconds() for a in attendances
            )

            if total_seconds <= threshold_seconds:
                continue

            excess_seconds = total_seconds - target_seconds
            last_att = attendances[-1]
            new_check_out = last_att.check_out - timedelta(seconds=excess_seconds)

            if new_check_out <= last_att.check_in:
                new_check_out = last_att.check_in + timedelta(minutes=1)

            last_att.sudo().write({
                'check_out': new_check_out.strftime('%Y-%m-%d %H:%M:%S'),
                'out_mode': 'auto_check_out',
            })
            last_att.message_post(body=_(
                'Ajuste automático: jornada recortada al superar las 9h 30min diarias '
                '(%.2fh trabajadas → 9h).' % (total_seconds / 3600)
            ))

            if emp.work_email:
                new_check_out_local = pytz.utc.localize(new_check_out).astimezone(tz)
                body_html = _('''
                    <p>Hola %(name)s,</p>
                    <p>Te informamos de que hoy has superado el máximo de <strong>9h 30min</strong> de jornada diaria.</p>
                    <p>El sistema ha ajustado automáticamente tu fichaje de salida a las <strong>%(new_out)s</strong>
                    para que el total del día quede en 9h (horas registradas: %(total)s).</p>
                    <p>Si crees que este ajuste es incorrecto, contacta con tu responsable.</p>
                    <p>Un saludo.</p>
                ''') % {
                    'name': emp.name,
                    'new_out': new_check_out_local.strftime('%H:%M'),
                    'total': '%dh %02dmin' % (int(total_seconds // 3600), int((total_seconds % 3600) // 60)),
                }
                self.env['mail.mail'].sudo().create({
                    'subject': _('Ajuste automático de fichaje – máximo de 9h superado'),
                    'body_html': body_html,
                    'email_to': emp.work_email,
                    'email_from': 'amartinez@apen.es',
                }).send()

    # SOBRESCRITO DEL ORIGINAL
    def _cron_absence_detection(self):
        """
        Objective is to create technical attendances on absence days to have negative overtime created for that day
        """
        yesterday = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=1)
        yesterday_date = yesterday.date()
        
        companies = self.env['res.company'].search([('absence_management', '=', True)])
        if not companies:
            return

        checked_in_employees = self.env['hr.attendance.overtime'].search([
            ('date', '=', yesterday),
            ('adjustment', '=', False)
        ]).employee_id

        absent_employees = self.env['hr.employee'].search([
            ('id', 'not in', checked_in_employees.ids),
            ('company_id', 'in', companies.ids),
            ('is_exempt_employee', '=', False)
        ])

        if absent_employees:
            valid_leaves = self.env['hr.leave'].search([
                ('employee_id', 'in', absent_employees.ids),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', yesterday_date),
                ('request_date_to', '>=', yesterday_date),
            ])
            
            employees_on_leave = valid_leaves.mapped('employee_id')
            
            absent_employees = absent_employees - employees_on_leave

        technical_attendances_vals = []
        
        for emp in absent_employees:
            if emp.flexible_hours == False:
                tz_name = emp._get_tz() or 'UTC' 
                local_day_start = pytz.utc.localize(yesterday).astimezone(pytz.timezone(tz_name))
                
                technical_attendances_vals.append({
                    'check_in': local_day_start.strftime('%Y-%m-%d %H:%M:%S'),
                    'check_out': (local_day_start + relativedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'in_mode': 'technical',
                    'out_mode': 'technical',
                    'employee_id': emp.id
                })

        technical_attendances = self.env['hr.attendance'].create(technical_attendances_vals)
        
        to_unlink = technical_attendances.filtered(lambda a: a.overtime_hours == 0)

        body = _('This attendance was automatically created to cover an unjustified absence on that day.')
        

        for technical_attendance in technical_attendances - to_unlink:
            technical_attendance.message_post(body=body)

        to_unlink.unlink()

   