from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResidenceLot(models.Model):
    _name = "residence.lot"

    name = fields.Char('Lot', required=True)
    resident_ids = fields.Many2many('res.partner', 'lot_resident_rel', 'lot_id', 'resident_id', string=_('Residents'))

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)',  _('You can not have two lots with the same name !'))
    ]

    def name_get(self):
        res = []
        for lot in self:
            res.append((lot.id, f'Lot {lot.name}'))
        return res

    @api.model
    def lot_init_with_number(self, number):
        if self.search([]):
            raise ValidationError(_('You cannot init this residence when lots already exist'))
        
        for x in range(1, number + 1):
            self.create({'name': str(x)})
        
        return True
