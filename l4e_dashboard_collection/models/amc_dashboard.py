# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2026 Links4Engg Private Limited.
# All Rights Reserved.
#
# This software is proprietary and confidential.
#
# Unauthorized copying, modification, redistribution,
# reverse engineering, decompilation, sublicensing,
# or commercial use of this software is strictly prohibited
# without prior written permission from
# Links4Engg Private Limited.
#
# Licensed under the Odoo Proprietary License v1.0 (OPL-1).
#
# Links4Engg Private Limited
# Website : https://links4engg.com
# Email   : info@links4engg.com
# Phone   : +91 471 3592209 | +91 7306889096
#
##############################################################################
from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_amc = fields.Boolean(string="Is AMC", default=False)
    assignee_ids = fields.Many2many(
        'res.users',
        compute='_compute_assignee_ids',
        string="Assignees"
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        compute='_compute_employee_ids',
        string="Employees"
    )

    @api.depends('task_ids', 'task_ids.user_ids')
    def _compute_assignee_ids(self):
        for project in self:
            tasks = self.env['project.task'].search([('project_id', '=', project.id)])
            users = tasks.mapped('user_ids')
            project.assignee_ids = [(6, 0, users.ids)]

    @api.depends('task_ids', 'task_ids.employee_ids')
    def _compute_employee_ids(self):
        for project in self:
            tasks = self.env['project.task'].search([('project_id', '=', project.id)])
            employees = tasks.mapped('employee_ids')
            project.employee_ids = [(6, 0, employees.ids)]

class ProjectTask(models.Model):
    _inherit = 'project.task'

    employee_ids = fields.Many2many(
        'hr.employee',
        string="Employees"
    )

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

        # 1. Filter projects by is_amc = True, dates, customer, and employee
        if date_from and date_to and date_from > date_to:
            # Reverse date range: return empty
            projects = Project.browse()
            project_ids = []
        else:
            proj_domain = [('is_amc', '=', True)]
            if date_from:
                proj_domain.append(('date', '>=', date_from))
            if date_to:
                proj_domain.append(('date_start', '<=', date_to))
            if customer_id:
                proj_domain.append(('partner_id', '=', customer_id))
            if employee_id:
                # Find projects that have tasks/subtasks assigned to this employee
                tasks_for_emp = Task.search([('employee_ids', 'in', [employee_id])])
                emp_proj_ids = tasks_for_emp.mapped('project_id').ids
                proj_domain.append(('id', 'in', emp_proj_ids))
            
            projects = Project.search(proj_domain)
            project_ids = projects.ids

        # 2. Setup employee filter dynamically
        has_employee_field = 'employee_ids' in Task._fields
        emp_filter = []
        if employee_id:
            emp_filter = [('employee_ids', 'in', [employee_id])]

        # 3. Base domain for tasks (Total Cards)
        base_domain = [('project_id', 'in', project_ids)]
        if emp_filter:
            base_domain += emp_filter
        if customer_id:
            base_domain.append(('partner_id', '=', customer_id))

        all_tasks = Task.search(base_domain)

        # 4. Status domain for tasks (Pie Chart)
        # All rules (dates, employee/customer filters) must apply to the pie chart.
        status_domain = [('project_id', 'in', project_ids)]
        if emp_filter:
            status_domain += emp_filter
        if customer_id:
            status_domain.append(('partner_id', '=', customer_id))
            
        has_planned_date = 'planned_date_begin' in Task._fields
        has_deadline = 'date_deadline' in Task._fields

        def build_task_date_domain(date_from_str, date_to_str):
            domain = []
            if date_from_str:
                dt_val = datetime.combine(fields.Date.from_string(date_from_str), time.min)
                dt_str = fields.Datetime.to_string(dt_val)
                if has_planned_date:
                    domain.append('|')
                    domain.append(('planned_date_begin', '>=', dt_str))
                    if has_deadline:
                        domain.append('&')
                        domain.append(('planned_date_begin', '=', False))
                        domain.append(('date_deadline', '>=', date_from_str))
                    else:
                        domain.append(('planned_date_begin', '=', False))
                elif has_deadline:
                    domain.append(('date_deadline', '>=', date_from_str))

            if date_to_str:
                dt_val = datetime.combine(fields.Date.from_string(date_to_str), time.max)
                dt_str = fields.Datetime.to_string(dt_val)
                if has_planned_date:
                    domain.append('|')
                    domain.append(('planned_date_begin', '<=', dt_str))
                    if has_deadline:
                        domain.append('&')
                        domain.append(('planned_date_begin', '=', False))
                        domain.append(('date_deadline', '<=', date_to_str))
                    else:
                        domain.append(('planned_date_begin', '=', False))
                elif has_deadline:
                    domain.append(('date_deadline', '<=', date_to_str))
            return domain

        status_domain += build_task_date_domain(status_date_from, status_date_to)
        status_tasks = Task.search(status_domain)

        # 5. Schedule domain for tasks (Bar Chart)
        schedule_domain = [('project_id', 'in', project_ids)]
        if has_planned_date:
            schedule_domain.append(('planned_date_begin', '!=', False))
        elif has_deadline:
            schedule_domain.append(('date_deadline', '!=', False))
            
        if emp_filter:
            schedule_domain += emp_filter
        if customer_id:
            schedule_domain.append(('partner_id', '=', customer_id))
            
        schedule_domain += build_task_date_domain(schedule_date_from, schedule_date_to)
        schedule_tasks = Task.search(schedule_domain)

        # Define stage lists for classification
        completed_stages = ['done', 'completed', 'complete', 'finished', 'closed']
        not_started_stages = ['new', 'inbox', 'to do', 'todo', 'draft', 'backlog', 'unassigned']
        ongoing_stages = ['in progress', 'in_progress', 'ongoing', 'progress', 'doing', 'active']

        # Partition all_tasks into mutually exclusive groups
        completed_tasks = all_tasks.filtered(
            lambda t: t.stage_id and t.stage_id.name.lower() in completed_stages
        )

        overdue_tasks = all_tasks.filtered(
            lambda t: (t.planned_date_begin or (has_deadline and t.date_deadline))
            and ((t.planned_date_begin and t.planned_date_begin.date() < today) or (has_deadline and t.date_deadline and t.date_deadline.date() < today))
            and not (t.stage_id and t.stage_id.name.lower() in completed_stages)
        )
        overdue_task_ids = set(overdue_tasks.ids)

        ongoing_tasks = all_tasks.filtered(
            lambda t: t.id not in overdue_task_ids
            and t.id not in completed_tasks.ids
            and (t.stage_id and (t.stage_id.name.lower() in ongoing_stages or t.stage_id.name.lower() not in not_started_stages))
        )

        not_started_tasks = all_tasks.filtered(
            lambda t: t.id not in overdue_task_ids
            and t.id not in completed_tasks.ids
            and t.id not in ongoing_tasks.ids
        )

        # Partition status_tasks for Pie Chart
        status_completed_tasks = status_tasks.filtered(
            lambda t: t.stage_id and t.stage_id.name.lower() in completed_stages
        )
        status_overdue_tasks = status_tasks.filtered(
            lambda t: (t.planned_date_begin or (has_deadline and t.date_deadline))
            and ((t.planned_date_begin and t.planned_date_begin.date() < today) or (has_deadline and t.date_deadline and t.date_deadline.date() < today))
            and not (t.stage_id and t.stage_id.name.lower() in completed_stages)
        )
        status_overdue_task_ids = set(status_overdue_tasks.ids)
        status_ongoing_tasks = status_tasks.filtered(
            lambda t: t.id not in status_overdue_task_ids
            and t.id not in status_completed_tasks.ids
            and (t.stage_id and (t.stage_id.name.lower() in ongoing_stages or t.stage_id.name.lower() not in not_started_stages))
        )
        status_not_started_tasks = status_tasks.filtered(
            lambda t: t.id not in status_overdue_task_ids
            and t.id not in status_completed_tasks.ids
            and t.id not in status_ongoing_tasks.ids
        )

        monthly_actions = {month: [] for month in range(1, 13)}
        for task in schedule_tasks:
            task_date = None
            if has_planned_date and task.planned_date_begin:
                task_date = task.planned_date_begin
            elif has_deadline and task.date_deadline:
                task_date = task.date_deadline
            else:
                task_date = task.create_date
            if task_date:
                monthly_actions[task_date.month].append(task.id)

        scheduled_services = []
        display_tasks = all_tasks.sorted(
            key=lambda t: t.planned_date_begin if has_planned_date and t.planned_date_begin else (t.date_deadline if has_deadline and t.date_deadline else t.create_date),
            reverse=False
        )[:50]

        for task in display_tasks:
            employee_name = ''
            if task.user_ids:
                for user in task.user_ids:
                    emp = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                    if emp:
                        employee_name = emp.name
                        break
                if not employee_name:
                    if has_employee_field:
                        employee_name = ', '.join(task.employee_ids.mapped('name'))
                    else:
                        employee_name = ', '.join(task.user_ids.mapped('name'))
            elif has_employee_field and task.employee_ids:
                employee_name = ', '.join(task.employee_ids.mapped('name'))

            product_name = ''
            if hasattr(task, 'equipment_id') and task.equipment_id:
                product_name = task.equipment_id.name
            elif 'equipment_id' in task._fields and task.equipment_id:
                product_name = task.equipment_id.name
            elif task.tag_ids:
                product_name = task.tag_ids[0].name

            status = 'New'
            if task.id in completed_tasks.ids:
                status = 'Done'
            elif task.id in overdue_tasks.ids:
                status = 'Overdue'
            elif task.id in ongoing_tasks.ids:
                status = 'In Progress'
            else:
                status = 'New'

            task_scheduled_date = ''
            if has_planned_date and task.planned_date_begin:
                task_scheduled_date = fields.Datetime.to_string(task.planned_date_begin)
            elif has_deadline and task.date_deadline:
                task_scheduled_date = fields.Date.to_string(task.date_deadline)
            else:
                task_scheduled_date = fields.Datetime.to_string(task.create_date)

            scheduled_services.append({
                'id': task.id,
                'customer': task.partner_id.name if task.partner_id else '',
                'amc_reference': task.name,
                'scheduled_date': task_scheduled_date,
                'product': product_name,
                'employees': [
                    {
                        'id': emp.id,
                        'name': emp.name,
                    }
                    for emp in (task.employee_ids if has_employee_field else self.env['hr.employee'].search([('user_id', 'in', task.user_ids.ids)]))
                ],
                'status': status,
            })

        monthly_data = {}
        for i in range(1, 13):
            monthly_data[i] = 0

        for task in schedule_tasks:
            task_date = None
            if has_planned_date and task.planned_date_begin:
                task_date = task.planned_date_begin
            elif has_deadline and task.date_deadline:
                task_date = task.date_deadline
            else:
                task_date = task.create_date
            if task_date:
                month = task_date.month
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
            ('project_id.is_amc', '=', True),
            ('partner_id', '!=', False),
        ])
        customers = tasks.mapped('partner_id').sorted(key=lambda partner: partner.name or '')
        return [{'id': customer.id, 'name': customer.name} for customer in customers]
