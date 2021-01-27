from odoo import api, fields, models, _
from odoo.exceptions import UserError
import qrcode
import base64
from io import BytesIO
import hmac
from hashlib import sha256
from datetime import datetime
from uuid import uuid4


class ResPartnerBadgeWizard(models.TransientModel):
    _name = "res.partner.badge.wizard"

    line_ids = fields.One2many('res.partner.badge.wizard.line', 'wizard_id', 'Lines')

    def generate_temporary_badges(self):
        badge_obj = self.env['res.partner.badge']
        for line in self.line_ids:
            values = [{
                'type': 'temporary',
                'lot_ids': [(6, 0, line.lot_ids.ids)]
            } for _ in range(line.qty)]
            badge_obj.create(values)
        return True


class ResPartnerBadgeWizardLine(models.TransientModel):
    _name = "res.partner.badge.wizard.line"

    lot_ids = fields.Many2many('residence.lot', string=_('Lots'))
    qty = fields.Integer('Quantity', required=True)
    wizard_id = fields.Many2one('res.partner.badge.wizard')


class ResPartnerBadge(models.Model):
    _name = "res.partner.badge"
    _inherit = ['image.mixin']

    partner_id = fields.Many2one('res.partner', string=_('Partner'), domain=[('is_company', '=', False)])
    company_id = fields.Many2one('res.company', string=_('Company'), default=lambda s: s.env.user.company_id)
    name = fields.Char(_('Badge Token'))
    is_active = fields.Boolean(default=True)
    type = fields.Selection(selection=[
        ('resident', _('Resident')),
        ('temporary', _('Temporary'))
    ], default='resident', required=True, string=_('Type'))
    lot_ids = fields.Many2many('residence.lot', string=_('Lots'))
    display_name = fields.Char(string=_('Name'))
    code = fields.Char(string=_('Code'))
    paid = fields.Boolean(string=_('Paid'), default=False)
    state = fields.Selection(string='State', selection=[('draft', 'Draft'), ('printed', 'Printed')], default='draft')

    def set_paid(self):
        self.write({'paid': True})
        return True

    def get_json(self):
        res = []
        for badge in self:
            partner = badge.partner_id
            if partner:
                partner = {
                    'id': partner.id,
                    'image': (partner.image_128 or b'').decode('utf-8'),
                    'name': partner.display_name
                }
            else:
                partner = {}

            res.append({
                'id': badge.id,
                'partner': partner,
                'token': badge.name,
                'isActive': badge.is_active,
                'type': badge.type,
                'lots': [lot.name for lot in badge.lot_ids],
                'displayName': badge.display_name,
                'code': badge.code,
                'image': (badge.image_128 or b'').decode('utf-8')
            })
        return res

    @api.model
    def create(self, vals):
        partner = False
        resident = vals.get('type') == 'resident'

        if vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])

        if not vals.get('name'):
            if partner:
                vals['name'] = partner.get_qr_string()
            else:
                vals['name'] = uuid4()

        if not partner and resident:
            raise UserError(_('You cannot create a resident badge without assigning it to a partner.'))

        seq_obj = self.env['ir.sequence']
        code = seq_obj.next_by_code('res.partner.badge.sequence')
        vals['code'] = code

        if resident and partner:
            vals['lot_ids'] = [(6, 0, partner.lot_ids.ids)]
            vals['display_name'] = partner.display_name
            vals['image_1920'] = partner.image_1920
        else:
            seq_obj = self.env['ir.sequence']
            vals['display_name'] = code

        return super(ResPartnerBadge, self).create(vals)

    def write(self, vals):
        if vals.get('type'):
            raise UserError(_('You cannot change the type of a badge.'))
        if vals.get('partner_id') and vals.get('type') == 'resident':
            raise UserError(_('You cannot change the resident assigned to a resident badge.'))
        return super(ResPartnerBadge, self).write(vals)

    def toggle_active(self):
        self.is_active = not self.is_active

    def get_qr_code(self):
        img = qrcode.make(self.name)
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue())


class ResPartner(models.Model):
    _inherit = "res.partner"

    lot_ids = fields.Many2many('residence.lot', 'lot_resident_rel', 'resident_id', 'lot_id', string=_('Lots'))
    badge_ids = fields.One2many(
        'res.partner.badge', 'partner_id', string=_('Badges')
    )
    is_resident = fields.Boolean(string=_('Resident'), default=True)
    is_bureau = fields.Boolean(string=_('Member of the bureau'), default=False)

    def write(self, vals):
        if vals.get('lot_ids'):
            badges = self.mapped('badge_ids').filtered(lambda b: b.type == 'resident')
            badges = self.env['res.partner.badge'].search([('id', 'in', [badge.id for badge in badges])])
            badges.write({'lot_ids': vals.get('lot_ids')})
        return super(ResPartner, self).write(vals)
    
    def make_badge_if_doesnt_have(self):
        badge_obj = self.env['res.partner.badge']
        for partner in self:
            if not partner.badge_ids.filtered(lambda b: b.is_active):
                badge_obj.create({
                    'partner_id': partner.id,
                    'name': partner.get_qr_string(),
                    'type': 'resident'
                })
        return True

    def make_badge(self):
        badge_obj = self.env['res.partner.badge']
        for partner in self:
            badge_obj.create({
                'partner_id': partner.id,
                'name': partner.get_qr_string(),
                'type': 'resident'
            })
        return True

    @api.model
    def partner_from_qr_string(self, string):
        return self.search([('badge_ids.name', '=', string)])

    def get_qr_string(self):
        db_secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        content = str(self.id) + datetime.now().isoformat()
        h = hmac.new(bytes(db_secret, 'utf-8'), content.encode('utf-8'), sha256)
        return h.hexdigest()

    def get_qr_code(self):
        badges = self.badge_ids.filtered(lambda b: b.is_active)
        if not badges:
            self.make_badge()
        return self.badge_ids[-1].get_qr_code()
