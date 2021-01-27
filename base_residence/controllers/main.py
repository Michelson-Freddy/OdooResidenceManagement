from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError
import json


class SlackController(http.Controller):
    @http.route(['/residence/badges/'], type="http", auth="user",
                methods=["GET"], csrf=False)
    def list_badges(self, *args, **kwargs):
        badges = request.env['res.partner.badge'].search([('is_active', '=', True)])
        return Response(
            json.dumps(badges.get_json()),
            headers={'Content-Type': 'application/json'}
        )
