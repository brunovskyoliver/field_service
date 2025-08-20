# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo.http import request, route
from odoo.addons.industry_fsm_sale.controllers.catalog import CatalogControllerFSM

class CatalogControllerFSMStock(CatalogControllerFSM):

    @route()
    def product_catalog_update_order_line_info(self, res_model, order_id, product_id, quantity=0, **kwargs):
        """ Update sale order line information on a given sale order for a given product.

        :param int order_id: The sale order, as a `sale.order` id.
        :param int product_id: The product, as a `product.product` id.
        :param int task_id: The task, as a `project.task` id. also available in the context but clearer in argument
        :param float quantity: The quantity selected in the product catalog.
        :param list context: the context comming from the view, used only to propagate the 'fsm_task_id' for the action_assign_serial on the product.
        :return: The unit price of the product, based on the pricelist of the sale order and
                 the quantity selected. Plus the new minimum quantity for the product
        :rtype: A dictionary containing the SN action and the SOL price_unit
        """
        _logger = logging.getLogger(__name__)
        task_id = kwargs.get('task_id')
        
        # Log product addition/update
        product = request.env['product.product'].sudo().browse(product_id)
        
        if not task_id:
            return super().product_catalog_update_order_line_info(res_model, order_id, product_id, quantity, **kwargs)

        # Ensure we have a task and a valid sale order
        task = request.env['project.task'].sudo().browse(task_id)
        sale_order = task.sale_order_id if task else False
        if not sale_order:
            return super().product_catalog_update_order_line_info(res_model, order_id, product_id, quantity, **kwargs)

        sale_order.sudo().action_unlock()

        # Search for existing sale order line or create a new one
        sol = request.env['sale.order.line'].sudo().search([
            ('order_id', '=', sale_order.id),
            ('product_id', '=', product_id),
            ('task_id', '=', task_id),
        ], limit=1)

        if not sol:
            sol = request.env['sale.order.line'].sudo().create({
                'order_id': sale_order.id,
                'product_id': product_id,
                'product_uom_qty': quantity,
                'task_id': task_id,
            })
        else:
            sol.sudo().write({
                'product_uom_qty': quantity,
            })

        # Log the update
        _logger.info(
            'FSM Product Update - Order: %s, Task: %s, Product: [%s] %s, Quantity: %s',
            task.sale_order_id.name,
            task.name,
            product.default_code or 'No Code',
            product.name,
            quantity
        )

        # Get standard information from parent method
        super_dict = super().product_catalog_update_order_line_info(res_model, order_id, product_id, quantity, **kwargs)
        super_dict["min_quantity"] = sol.product_id.fsm_quantity - sol.product_id.quantity_decreasable_sum
        return super_dict
        super_dict = super().product_catalog_update_order_line_info(res_model, order_id, product_id, quantity, **kwargs)
        super_dict["min_quantity"] = product.fsm_quantity - product.quantity_decreasable_sum

        return super_dict
