# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import Warning as UserError


class LibraryPriceCategory(models.Model):
    _name = 'library.price.category'
    _description = 'Book Price Category'

    name = fields.Char('Category', required=True)
    price = fields.Float('Price', required=True, default=0)
    product_ids = fields.One2many('product.product', 'price_cat', 'Books')


class LibraryRack(models.Model):
    _name = 'library.rack'
    _description = "Library Rack"

    name = fields.Char('Name', required=True,
                       help="it will be show the position of book")
    code = fields.Char('Code')
    active = fields.Boolean('Active', default='True')


class LibraryCollection(models.Model):
    _name = 'library.collection'
    _description = "Library Collection"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')


class LibraryBookReturnday(models.Model):
    _name = 'library.book.returnday'
    _description = "Library Collection"
    _rec_name = 'day'

    day = fields.Integer('Days', required=True,
                         help="It show the no of day/s for returning book")
    code = fields.Char('Code')
    fine_amt = fields.Float('Fine Amount', required=True,
                            help="Fine amount after due of book return date")


class LibraryAuthor(models.Model):
    _name = 'library.author'
    _description = "Author"

    name = fields.Char('Name', required=True)
    born_date = fields.Date('Date of Birth')
    death_date = fields.Date('Date of Death')
    biography = fields.Text('Biography')
    note = fields.Text('Notes')
    editor_ids = fields.Many2many('res.partner', 'author_editor_rel',
                                  'author_id', 'parent_id', 'Editors')

    _sql_constraints = [('name_uniq', 'unique (name)',
                         'The name of the author must be unique !')]


class LibraryCard(models.Model):
    _name = "library.card"
    _description = "Library Card information"
    _rec_name = "code"

    @api.multi
    def on_change_student(self, student_id):
        '''  This method automatically fill up student roll number
             and standard field  on student_id field
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @student : Apply method on this Field name
        @param context : standard Dictionary
        @return : Dictionary having identifier of the record as key
            and the value of student roll number and standard'''
        if not student_id:
            return {'value': {}}
        student_data = self.env['student.student'].browse(student_id)
        val = {'standard_id': student_data.standard_id.id,
               'roll_no': student_data.roll_no}
        return {'value': val}

    @api.multi
    @api.depends('student_id')
    def get_name(self):
        for rec in self:
            if rec.student_id:
                user = rec.student_id.name
            else:
                user = rec.teacher_id.name
            rec.gt_name = user

    code = fields.Char('Card No', required=True, default=lambda self:
                       self.env['ir.sequence'].get('library.card') or '/')
    book_limit = fields.Integer('No Of Book Limit On Card', required=True)
    student_id = fields.Many2one('student.student', 'Student Name')
    standard_id = fields.Many2one('school.standard', 'Standard')
    gt_name = fields.Char(compute="get_name", method=True, string='Name')
    user = fields.Selection([('student', 'Student'), ('teacher', 'Teacher')],
                            'User')
    roll_no = fields.Integer('Roll No')
    teacher_id = fields.Many2one('hr.employee', 'Teacher Name')


class LibraryBookIssue(models.Model):
    '''Book variant of product'''
    _name = "library.book.issue"
    _description = "Library information"
    _rec_name = "standard_id"

    @api.onchange('date_issue', 'day_to_return_book')
    def onchange_day_to_return_book(self):
        ''' This method calculate a book return date.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param name : Functional field's name
        @param args : Other arguments
        @param context : standard Dictionary
        @return : Dictionary having identifier of the record as key
                  and the book return date as value'''
        t = "%Y-%m-%d %H:%M:%S"
        rd = relativedelta(days=self.day_to_return_book.day or 0.0)
        if self.date_issue and self.day_to_return_book:
            ret_date = datetime.strptime(self.date_issue, t) + rd
            self.date_return = ret_date

    @api.multi
    @api.depends('date_issue', 'day_to_return_book')
    def _calc_retunr_date(self):
        ''' This method calculate a book return date.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param name : Functional field's name
        @param args : Other arguments
        @param context : standard Dictionary
        @return : Dictionary having identifier of the record as key
                  and the book return date as value'''
        t = "%Y-%m-%d %H:%M:%S"
        rd = relativedelta(days=self.day_to_return_book.day or 0.0)
        if self.date_issue and self.day_to_return_book:
            ret_date = datetime.strptime(self.date_issue, t) + rd
            self.date_return = ret_date

    @api.multi
    @api.depends('date_return', 'day_to_return_book')
    def _calc_penalty(self):
        ''' This method calculate a penalty on book .
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param name : Functional field's name
        @param args : Other arguments
        @param context : standard Dictionary
        @return : Dictionary having identifier of the record as key
                  and penalty as value
        '''
        for line in self:
            if line.date_return: #and\
#                line.state not in ('fine', 'paid', 'cancel'):
                start_day = datetime.now()
                end_day = datetime.strptime(line.date_return,
                                            "%Y-%m-%d %H:%M:%S")
                if start_day > end_day:
                    diff = start_day - end_day
                    day = float(diff.days) or 1.0
                    if line.day_to_return_book:
                        line.penalty = day * line.day_to_return_book.fine_amt

    @api.multi
    @api.depends('state')
    def _calc_lost_penalty(self):
        ''' This method calculate a penalty on book lost .
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param name : Functional field's name
        @param args : Other arguments
        @param context : standard Dictionary
        @return : Dictionary having identifier of the record as key
                  and book lost penalty as value
        '''

        if self.state and self.state == 'lost':
            self.lost_penalty = self.name.book_price or 0.0

    @api.multi
    @api.constrains('card_id', 'state')
    def _check_issue_book_limit(self):
        ''' This method used how many book can issue as per user type  .
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param context : standard Dictionary
        @return : True or False
        '''
        if self.card_id:
            card_ids = self.search([('card_id', '=', self.card_id.id),
                                    ('state', 'in', ['issue', 'reissue'])])
            if self.state == 'issue' or self.state == 'reissue':
                if self.card_id.book_limit > len(card_ids) - 1:
                    return True
                else:
                    raise UserError(_('Book issue limit is over on this card'))
            else:
                if self.card_id.book_limit > len(card_ids):
                    return True
                else:
                    raise UserError(_('Book issue limit is over on this card'))

    name = fields.Many2one('product.product', 'Book Name', required=True)
    issue_code = fields.Char('Issue No.', required=True,
                             default=lambda self:
                             self.env['ir.sequence'].
                             get('library.book.issue') or '/')
    student_id = fields.Many2one('student.student', 'Student Name')
    teacher_id = fields.Many2one('hr.employee', 'Teacher Name')
    gt_name = fields.Char('Name')
    standard_id = fields.Many2one('standard.standard', 'Standard')
    roll_no = fields.Integer('Roll No')
    invoice_id = fields.Many2one('account.invoice', "User's Invoice")
    date_issue = fields.Datetime('Release Date', required=True,
                                 help="Release(Issue) date of the book",
                                 default=lambda *a:
                                 time.strftime('%Y-%m-%d %H:%M:%S'))
    date_return = fields.Datetime(compute="_calc_retunr_date",
                                  string='Return Date',
                                  store=True,
                                  help="Book To Be Return On This Date")
    actual_return_date = fields.Datetime("Actual Return Date", readonly=True,
                                         help="Actual Return Date of Book")
    penalty = fields.Float(compute="_calc_penalty",
                           string='Penalty', method=True,
                           help='It show the late book return penalty')
    lost_penalty = fields.Float(compute="_calc_lost_penalty", string='Fine',
                                store=True,
                                help='It show the penalty for lost book')
    return_days = fields.Integer('Return Days')
    day_to_return_book = fields.Many2one('library.book.returnday',
                                         'Book Return Days')
    card_id = fields.Many2one("library.card", "Card No", required=True)
    state = fields.Selection([('draft', 'Draft'), ('issue', 'Issued'),
                              ('reissue', 'Reissued'), ('cancel', 'Cancelled'),
                              ('return', 'Returned'), ('lost', 'Lost'),
                              ('fine', 'Fined'), ('paid', 'Fined Paid')],
                             "State", default='draft')
    user = fields.Char("User")
    color = fields.Integer("Color Index")

    @api.onchange('card_id')
    def onchange_card_issue(self):
        ''' This method automatically fill up values on card.
            @param self : Object Pointer
            @param cr : Database Cursor
            @param uid : Current Logged in User
            @param ids : Current Records
            @param card : applied change on this field
            @param context : standard Dictionary
            @return : Dictionary having identifier of the record as key
                      and the user info as value
        '''
        if self.card_id:
            self.user = str(self.card_id.user.title()) or ''
            if self.card_id.user.title() == 'Student':
                self.student_id = self.card_id.student_id.id or False
                self.standard_id = self.card_id.standard_id.id or False
                self.roll_no = int(self.card_id.roll_no) or False
                self.gt_name = self.card_id.gt_name or ''

            else:
                self.teacher_id = self.card_id.teacher_id.id
                self.gt_name = self.card_id.gt_name

    @api.multi
    def draft_book(self):
        '''
        This method for books in draft state.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param context : standard Dictionary
        @return : True
        '''
        self.write({'state': 'draft'})
        return True

    @api.multi
    def issue_book(self):
        '''

        This method used for issue a books.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param context : standard Dictionary
        @return : True
        '''
        for rec in self:
            if rec.student_id:
                issue_str = ''
                book_fines = rec.search([('card_id', '=', rec.card_id.id),
                                      ('state', '=', 'fine')])
                if book_fines:
                    for book in book_fines:
                        issue_str += str(book.issue_code) + ', '
                    raise UserError(_('You can not request for a book until\
                                the fine is not paid for book issues %s!') %
                                    issue_str)
            if rec.card_id:
                card_ids = rec.search([('card_id', '=', rec.card_id.id),
                                        ('state', 'in', ['issue', 'reissue'])])
                if rec.card_id.book_limit > len(card_ids):
                    rec.write({'state': 'issue'})
#                    product_id = self.name
#                    product_id.write({'availability': 'notavailable'})
            return True

    @api.multi
    def reissue_book(self):
        '''
        This method used for reissue a books.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param context : standard Dictionary
        @return : True
        '''
        self.state = 'reissue'
        self.write({'date_issue': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True

    @api.multi
    def return_book(self):
        '''
        This method used for return a books.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param context : standard Dictionary
        @return : True
        '''
        vals = {'actual_return_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'state': 'return'}
        self.write(vals)
        product_id = self.name
        product_id.write({'availability': 'available'})
        return True

    @api.multi
    def lost_book(self):
        stock_scrap_obj = self.env['stock.scrap']
        for rec in self:
            scrap_fields = list(stock_scrap_obj._fields)
            scrap_vals = stock_scrap_obj.default_get(scrap_fields)
            origin_str = 'Book lost : '
            if rec.issue_code:
                origin_str += rec.issue_code
            if rec.student_id:
                origin_str += "(" + rec.student_id.name + ")" or ''
            scrap_vals.update({'product_id': rec.name.id,
                               'product_uom_id': rec.name.uom_id.id,
                               'origin': origin_str})
            stock_scrap_obj.with_context({'book_lost': True}
                                         ).create(scrap_vals)
            rec.state = 'lost'
            rec.lost_penalty = self.name.book_price
        return True

    @api.multi
    def cancel_book(self):
        '''
        This method used for cancel book issue.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param context : standard Dictionary
        @return : True
        '''
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def user_fine(self):
        '''
        This method used when penalty on book either late return or book lost.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param context : standard Dictionary
        @return : new form of account.invoice
        '''
#
        invoice_obj = self.env['account.invoice']
        for record in self:
            if record.user == 'Student':
                usr = record.student_id.partner_id.id
                if not record.student_id.partner_id.contact_address:
                    raise UserError(_('Error !'
                                    'The Student must have a Home address.'))
            else:
                usr = record.teacher_id.id
                if not record.teacher_id.address_home_id:
                    raise UserError(_('Error !'
                                    'The Teacher must have a Home address.'))
            vals_invoice = {
                            'type': 'out_invoice',
                            'partner_id': usr,
                            'book_issue': record.id,
                            'book_issue_reference': record.issue_code or ''
                           }
            new_invoice_id = invoice_obj.create(vals_invoice)
            acc_id = new_invoice_id.journal_id.default_credit_account_id.id
            invoice_line_ids = []
            if record.lost_penalty:
                lost_pen = record.lost_penalty
                invoice_line2 = {'name': 'Book Lost Fine',
                                 'price_unit': lost_pen,
                                 'invoice_id': new_invoice_id.id,
                                 'account_id': acc_id
                                }
                invoice_line_ids.append((0, 0, invoice_line2))
            if record.penalty:
                pen = record.penalty
                invoice_line1 = {'name': 'Late Return Penalty',
                                 'price_unit': pen,
                                 'invoice_id': new_invoice_id.id,
                                 'account_id': acc_id}
                invoice_line_ids.append((0, 0, invoice_line1))
            new_invoice_id.write({'invoice_line_ids': invoice_line_ids})
        self.write({'state': 'fine'})
        view_id = self.env.ref('account.invoice_form')
        return {'name': _("New Invoice"),
                'view_mode': 'form',
                'view_id': view_id.ids,
                'view_type': 'form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'res_id': new_invoice_id.id,
                'target': 'current',
                'context': {'default_type': 'out_invoice'}}

    @api.multi
    def view_invoice(self):
        invoice_obj = self.env['account.invoice']
        invoice = invoice_obj.search([('book_issue', '=', self.id)])
        return {'name': _("View Invoice"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'res_id': invoice.id or False,
                'target': 'current'
                }


class LibraryBookRequest(models.Model):
    '''Request for Book'''
    _name = "library.book.request"
    _rec_name = 'req_id'

    @api.multi
    @api.depends('type')
    def gt_bname(self):
        if self.type:
            if self.type == 'existing':
                book = self.name.name
            else:
                book = self.new1
            self.bk_nm = book

    req_id = fields.Char('Request ID', readonly=True, default=lambda self:
                         self.env['ir.sequence'].
                         next_by_code('library.book.request') or '/')
    card_id = fields.Many2one("library.card", "Card No", required=True)
    type = fields.Selection([('existing', 'Existing'), ('new', 'New')],
                            'Book Type')
    name = fields.Many2one('product.product', 'Book Name')
    new1 = fields.Char('Book Name',)
    new2 = fields.Char('Book Name')
    bk_nm = fields.Char('Name', compute="gt_bname", store=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirm'),
                              ('cancel', 'Cancelled'),
                              ], "State", default='draft')

    @api.multi
    def draft_book_request(self):
        for book in self:
            book.state = 'draft'

    @api.multi
    def confirm_book_request(self):
        for book in self:
            book.state = 'confirm'
            book_issue_obj = self.env['library.book.issue']
            vals = {
                 'card_id': self.card_id.id,
                 'type': self.type,
                 'name': self.name.id
                 }
            issue_id = book_issue_obj.create(vals)
            issue_id.onchange_card_issue()
            return {
                'name': ('Book Issue'),
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': issue_id.id,
                'res_model': 'library.book.issue',
                'type': 'ir.actions.act_window',
               'target': 'current',
                }

    @api.multi
    def cancle_book_request(self):
        for book in self:
            book.state = 'cancel'
