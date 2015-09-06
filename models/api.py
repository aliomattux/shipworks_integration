from openerp.osv import osv, fields
from pprint import pprint as pp
from datetime import datetime
from pytz import timezone

class StockPicking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
	'sw_exp': fields.boolean('Shipworks Exported', select=True),
    }
    _defaults = {
	'sw_exp': False
    }


class ShipworksApi(osv.osv_memory):
    _name = 'shipworks.api'


    def get_store(self, cr, uid, context=None):
	company_obj = self.pool.get('res.company')
	company_ids = company_obj.search(cr, uid, [])
	company = company_obj.browse(cr, uid, company_ids[0])
	res = {
		'name': 'Kyles Store Name',
		'company': 'Kyles Cool Company',
		'email': 'kyle.waid@gcotech.com',
		'state': 'Minnesota',
		'country': 'US',
		'website': 'http://www.yahoo.com',
	}
	print 'Returning Get Store'
	return res


    def get_picking_search_domain(self, cr, uid, start, end):
	return [('sw_exp', '=', False),
	('picking_type_id.code', '=', 'outgoing'),
	('create_date', '>', '2015-08-24 01:10:34')
	]
#	('write_date', '>', '2015-08-24 01:10:34'), ('write_date', '<=', end)
#	]


    def get_order_count(self, cr, uid, start, end, context=None):
	picking_ids = self.get_picking_ids(cr, uid, start, end, limit=False)
	return len(picking_ids)
	

    def get_picking_ids(self, cr, uid, start, end, limit, context=None):
        picking_obj = self.pool.get('stock.picking')
        domain = self.get_picking_search_domain(cr, uid, start, end)

        picking_ids = picking_obj.search(cr, uid, domain, limit=limit)
	return picking_ids


    def get_pickings(self, cr, uid, start, end, limit, context=None):
	picking_obj = self.pool.get('stock.picking')
	picking_ids = self.get_picking_ids(cr, uid, start, end, limit=False)
	picking_obj.write(cr, uid, picking_ids, {'sw_exp': True})
	pickings = picking_obj.browse(cr, uid, picking_ids)
	return self.prepare_and_send_pickings(cr, uid, pickings)


    def prepare_address(self, cr, uid, address):
        vals = {
		'name': address.name,
		'company': address.parent_id.name if address.parent_id else address.name,
		'street': address.street,
		'street2': address.street2,
		'street3': '',
		'city': address.city,
		'state': address.state_id.name,
		'postal_code': address.zip,
		'country': address.country_id.code,
		'phone': address.phone,
		'email': address.email,
	}

        return vals


    def prepare_order_items(self, cr, uid, move_lines):
	items = []
	for move in move_lines:
	    vals = {
		'item_id': move.product_id.id,
		'product_id': move.product_id.id,
		'code': move.product_id.default_code,
		'sku': move.product_id.default_code,
		'name': move.name,
		'weight': move.product_id.weight,
		'cost': move.product_id.standard_price,
		'quantity': move.product_qty,
		'price': 0.00,
	    }

	    items.append(vals)

	return items


    def prepare_picking_header(self, cr, uid, picking):
#	import re
#	re.sub(r'\D', '', theString)
	if picking.sale:
	    order_number = picking.sale.name
	else:
	    order_number = picking.name

	customer = picking.partner_id.parent_id if picking.partner_id.parent_id else picking.partner_id

        vals = {
		'picking_id': picking.id,
		'order_number': picking.id,
		'note': order_number,
		'date': self.convert_date(cr, uid, picking.date),
		'last_modified': self.convert_date(cr, uid, picking.write_date),
		'status_code': picking.state,
		'customer_id': customer.id,
		'shipping_method': picking.sale.carrier_id.name
	}

	if picking.sale and picking.sale.custom_account:
	    sale = picking.sale
	    vals['shipping_method'] = 'ATTENTION: Use Customer Account: %s' % sale.account_number
	    vals['notes'] = "Customer Shipping Account Number: %s \n" \
			    "Account Name: %s \n" \
			    "Service: %s \n" \
			    "Zipcode: %s" \
		% (sale.account_number, sale.account_name, sale.service.name, sale.account_zipcode)

	return vals


    def convert_date(self, cr, uid, date, context=None):
	ny_timezone = timezone('America/New_York')
	utc_tz = timezone('UTC')
	now = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
	utc_date = utc_tz.localize(now)
	ny_datetime = utc_date.astimezone(tz=ny_timezone)
	return ny_datetime.strftime('%Y-%m-%d %H:%M:%S')


    def prepare_picking(self, cr, uid, picking):
	shipping_address = self.prepare_address(cr, uid, picking.partner_id)
	billing_partner = picking.sale.partner_invoice_id if picking.sale else picking.partner_id
	billing_address = self.prepare_address(cr, uid, billing_partner)
	header = self.prepare_picking_header(cr, uid, picking)
	moves = self.prepare_order_items(cr, uid, picking.move_lines)

	if not shipping_address['email']:
	    shipping_address['email'] = billing_address['email'] or picking.sale.order_email or ''

        vals = {
		'billing_address': billing_address,
		'shipping_address': shipping_address,
		'items': moves,
	}

	vals.update(header)
	
	
	return vals


    def prepare_and_send_pickings(self, cr, uid, pickings):
	result = []
        for picking in pickings:
	    prepared_picking = self.prepare_picking(cr, uid, picking)
	    result.append(prepared_picking)

	pp(result)
	return result


    def get_status_codes(self, cr, uid, context=None):
        statuses = [
		{'code': 'draft',
		'name': 'Draft',
		},
                {'code': 'cancel',
                'name': 'Cancelled',
                },
                {'code': 'waiting',
                'name': 'Waiting',
                },
                {'code': 'confirmed',
                'name': 'Waiting Availability',
                },
                {'code': 'partially_available',
                'name': 'Partially Available',
                },
                {'code': 'assigned',
                'name': 'Ready to Ship',
                },
                {'code': 'done',
                'name': 'Transferred',
                }
	]

	print 'Returning Statuses'
	return statuses
