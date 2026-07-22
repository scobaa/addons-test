from odoo import models, fields, api, _
from datetime import datetime, time, timedelta
import pytz

SELECCION_PERIODO = {'am': 'Mañana', 'pm': 'Tarde'}

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    flexible_hours = fields.Boolean(string='Horario flexible', default=False)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_exempt_employee = fields.Boolean(
        string='Empleado exento del auto fichaje',
        help='Si esta opción esta marcada, no se generará un auto fichaje para este empleado en el modulo de Asistencias.',
        default=False,
        copy=False,
        groups="hr.group_hr_user"
    )

    flexible_hours = fields.Boolean(
        string='Horario flexible',
        default=False
    )

    def float_to_time_str(self, value):
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"

    def get_attendance_status_today(self):

        today = fields.Date.context_today(self)

        user_tz_name = self.env.user.tz or 'Europe/Madrid'
        user_tz = pytz.timezone(user_tz_name)
        
        result = []
        
        for emp in self:
   
            
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', datetime.combine(today, time.min)),
                ('check_in', '<=', datetime.combine(today, time.max))
            ])            

            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', today),
                ('request_date_to', '>=', today)
            ])
            
            last_attendance = attendances.sorted(key=lambda a: a.check_in, reverse=True)[:1]

            check_in_str = ''
            location_link = ''
            
            if last_attendance:
             
                utc_dt = pytz.utc.localize(last_attendance.check_in)
                local_dt = utc_dt.astimezone(user_tz)
                check_in_str = local_dt.strftime('%H:%M')
                
                if last_attendance.in_latitude and last_attendance.in_longitude:
                    location_link = f"https://www.google.com/maps?q={last_attendance.in_latitude},{last_attendance.in_longitude}"

            leave_mode = ''
            if leaves:
                leave = leaves[0]
                if leave.request_unit_hours:
                    leave_mode = f"{self.float_to_time_str(leave.request_hour_from)} - {self.float_to_time_str(leave.request_hour_to)}"
                elif leave.request_unit_half:
                    leave_mode = SELECCION_PERIODO.get(leave.request_date_from_period, '')
                else:
                    leave_mode = 'Día completo'

            result.append({
                'name': emp.name,
                'has_attendance': bool(attendances),
                'check_in': check_in_str,
                'has_leave': bool(leaves),
                'leave_type': leaves[0].holiday_status_id.name if leaves else False,
                'location_name': last_attendance.location_name if last_attendance else '',
                'location_link': location_link,
                'leave_mode': leave_mode,
            })

        return result