# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, datetime, time

class AmcDashboard(models.TransientModel):
    _name = 'amc.dashboard'
    _description = 'AMC Dashboard'

    @api.model
    def get_dashboard_data(
        self, date_from=None, date_to=None, employee_id=None, customer_id=None,
        status_date_from=None, status_date_to=None,
        schedule_date_from=None, schedule_date_to=None,
    ):
        today = date.today()

        Project = self.env['project.project']
        Task = self.env['project.task']
        SaleOrder = self.env['sale.order']

        sale_orders = SaleOrder.search([
            ('state', '=', 'sale'),
            ('order_type', '=', 'amc'),
            ('project_id', '!=', False),
        ])

        projects = sale_orders.mapped('project_id').filtered(lambda p: p.is_fsm)
        project_ids = projects.ids

        base_domain = [('project_id', 'in', project_ids)]
        if date_from:
            start_dt = datetime.combine(fields.Date.from_string(date_from), time.min)
            base_domain.append(('create_date', '>=', fields.Datetime.to_string(start_dt)))
        if date_to:
            end_dt = datetime.combine(fields.Date.from_string(date_to), time.max)
            base_domain.append(('create_date', '<=', fields.Datetime.to_string(end_dt)))
        if employee_id:
            base_domain.append(('employee_ids', 'in', [employee_id]))
        if customer_id:
            base_domain.append(('partner_id', '=', customer_id))

        all_tasks = Task.search(base_domain)

        status_domain = [('project_id', 'in', project_ids)]
        if status_date_from:
            status_start_dt = datetime.combine(fields.Date.from_string(status_date_from), time.min)
            status_domain.append(('create_date', '>=', fields.Datetime.to_string(status_start_dt)))
        if status_date_to:
            status_end_dt = datetime.combine(fields.Date.from_string(status_date_to), time.max)
            status_domain.append(('create_date', '<=', fields.Datetime.to_string(status_end_dt)))
        if employee_id:
            status_domain.append(('employee_ids', 'in', [employee_id]))
        if customer_id:
            status_domain.append(('partner_id', '=', customer_id))
        status_tasks = Task.search(status_domain)

        schedule_domain = [('project_id', 'in', project_ids), ('planned_date_begin', '!=', False)]
        if schedule_date_from:
            schedule_start_dt = datetime.combine(fields.Date.from_string(schedule_date_from), time.min)
            schedule_domain.append(('planned_date_begin', '>=', fields.Datetime.to_string(schedule_start_dt)))
        if schedule_date_to:
            schedule_end_dt = datetime.combine(fields.Date.from_string(schedule_date_to), time.max)
            schedule_domain.append(('planned_date_begin', '<=', fields.Datetime.to_string(schedule_end_dt)))
        if employee_id:
            schedule_domain.append(('employee_ids', 'in', [employee_id]))
        if customer_id:
            schedule_domain.append(('partner_id', '=', customer_id))
        schedule_tasks = Task.search(schedule_domain)

        completed_tasks = all_tasks.filtered(
            lambda t: t.stage_id and t.stage_id.name.lower() in ['done', 'completed', 'complete']
        )

        overdue_tasks = all_tasks.filtered(
            lambda t: t.planned_date_begin and t.planned_date_begin.date() < today
            and not (t.stage_id and t.stage_id.name.lower() in ['done', 'completed', 'complete'])
        )
        overdue_task_ids = set(overdue_tasks.ids)

        ongoing_tasks = all_tasks.filtered(
            lambda t: t.stage_id and t.stage_id.name.lower() in ['in progress', 'in_progress', 'ongoing', 'progress']
            and t.id not in overdue_task_ids
        )

        not_started_tasks = all_tasks.filtered(
            lambda t: t.stage_id and t.stage_id.name.lower() in ['new', 'inbox']
            and t.id not in overdue_task_ids
        )

        status_completed_tasks = status_tasks.filtered(
            lambda t: t.stage_id and t.stage_id.name.lower() in ['done', 'completed', 'complete']
        )
        status_overdue_tasks = status_tasks.filtered(
            lambda t: t.planned_date_begin and t.planned_date_begin.date() < today
            and not (t.stage_id and t.stage_id.name.lower() in ['done', 'completed', 'complete'])
        )
        status_overdue_task_ids = set(status_overdue_tasks.ids)
        status_ongoing_tasks = status_tasks.filtered(
            lambda t: t.stage_id and t.stage_id.name.lower() in ['in progress', 'in_progress', 'ongoing', 'progress']
            and t.id not in status_overdue_task_ids
        )
        status_not_started_tasks = status_tasks.filtered(
            lambda t: t.stage_id and t.stage_id.name.lower() in ['new', 'inbox']
            and t.id not in status_overdue_task_ids
        )

        monthly_actions = {month: [] for month in range(1, 13)}
        for task in schedule_tasks:
            if task.planned_date_begin:
                monthly_actions[task.planned_date_begin.month].append(task.id)

        scheduled_services = []
        display_tasks = all_tasks.sorted(key=lambda t: t.planned_date_begin or t.create_date, reverse=False)[:50]

        for task in display_tasks:
            employee_name = ''
            if task.user_ids:
                for user in task.user_ids:
                    emp = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                    if emp:
                        employee_name = emp.name
                        break
                if not employee_name:
                    employee_name = ', '.join(task.employee_ids.mapped('name'))

            product_name = ''
            if hasattr(task, 'equipment_id') and task.equipment_id:
                product_name = task.equipment_id.name
            elif 'equipment_id' in task._fields and task.equipment_id:
                product_name = task.equipment_id.name
            elif task.tag_ids:
                product_name = task.tag_ids[0].name

            status = 'New'
            if task.stage_id:
                stage_lower = task.stage_id.name.lower()
                if stage_lower in ['done', 'completed', 'complete']:
                    status = 'Done'
                elif task.planned_date_begin and task.planned_date_begin.date() < today:
                    status = 'Overdue'
                elif stage_lower in ['in progress', 'in_progress', 'ongoing', 'progress']:
                    status = 'In Progress'
                elif stage_lower in ['new', 'inbox']:
                    status = 'New'
                else:
                    status = task.stage_id.name

            scheduled_services.append({
                'id': task.id,
                'customer': task.partner_id.name if task.partner_id else '',
                'amc_reference': task.name,
                'scheduled_date': fields.Datetime.to_string(task.planned_date_begin) if task.planned_date_begin else '',
                'product': product_name,
                'employees': [
                    {
                        'id': emp.id,
                        'name': emp.name,
                    }
                    for emp in task.employee_ids
                ],
                'status': status,
            })

        monthly_data = {}
        for i in range(1, 13):
            monthly_data[i] = 0

        for task in schedule_tasks:
            if task.planned_date_begin:
                month = task.planned_date_begin.month
                monthly_data[month] = monthly_data.get(month, 0) + 1

        return {
            'projects': len(projects),
            'services': len(all_tasks),
            'completed': len(completed_tasks),
            'ongoing': len(ongoing_tasks),
            'not_started': len(not_started_tasks),
            'overdue': len(overdue_tasks),
            'scheduled_services': scheduled_services,
            'monthly_data': [monthly_data[i] for i in range(1, 13)],
            'monthly_actions': [monthly_actions[i] for i in range(1, 13)],
            'status_chart': {
                'total': len(status_tasks),
                'completed': len(status_completed_tasks),
                'ongoing': len(status_ongoing_tasks),
                'not_started': len(status_not_started_tasks),
                'overdue': len(status_overdue_tasks),
            },
            'status_actions': {
                'completed': status_completed_tasks.ids,
                'ongoing': status_ongoing_tasks.ids,
                'not_started': status_not_started_tasks.ids,
                'overdue': status_overdue_tasks.ids,
            },
            'actions': {
                'projects': {'model': 'project.project', 'ids': projects.ids},
                'services': {'model': 'project.task', 'ids': all_tasks.ids},
                'completed': {'model': 'project.task', 'ids': completed_tasks.ids},
                'ongoing': {'model': 'project.task', 'ids': ongoing_tasks.ids},
                'not_started': {'model': 'project.task', 'ids': not_started_tasks.ids},
                'overdue': {'model': 'project.task', 'ids': overdue_tasks.ids},
            },
        }

    @api.model
    def get_employees(self):
        employees = self.env['hr.employee'].search([('active', '=', True)], order='name')
        return [{'id': emp.id, 'name': emp.name} for emp in employees]

    @api.model
    def get_customers(self):
        tasks = self.env['project.task'].search([
            ('project_id.is_fsm', '=', True),
            ('partner_id', '!=', False),
        ])
        customers = tasks.mapped('partner_id').sorted(key=lambda partner: partner.name or '')
        return [{'id': customer.id, 'name': customer.name} for customer in customers]
