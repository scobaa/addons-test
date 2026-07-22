/** @odoo-module **/
import { PortalHomeCounters } from '@portal/js/portal';

PortalHomeCounters.include({
    _getCountersAlwaysDisplayed() {
        return this._super(...arguments).concat(['regularization_count']);
    },
});
