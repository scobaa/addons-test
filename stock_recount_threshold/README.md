# Stock Recount Threshold

Módulo esqueleto que dispara automáticamente una solicitud de recuento
cuando la cantidad disponible de un producto, en una ubicación interna,
cae a un umbral configurable (o por debajo) tras un movimiento de stock
(picking, entrega, consumo de fabricación).

## Qué incluye este esqueleto

- `product.template`: campos `recount_enabled`, `recount_threshold_qty`,
  `recount_responsible_id` para configurar el umbral por producto.
- `stock.move`: hereda `_action_done()` para revisar, tras cada
  confirmación de movimiento, si la cantidad disponible cruzó el umbral.
- `stock.recount.request`: modelo nuevo y ligero que representa cada
  solicitud generada, con estado (pendiente/recontado/cancelado) y una
  actividad (`mail.activity`) asignada al responsable.
- Vista de lista/formulario + menú bajo Inventario para gestionar las
  solicitudes.
- Seguridad básica (usuario de stock puede crear/leer/editar, manager
  puede además borrar).

## Cosas a validar/pulir antes de venderlo

1. **Target: Odoo 19.** El módulo ya usa la sintaxis moderna
   (`invisible="..."` en vez de `attrs`) y el manifest apunta a
   `19.0.1.0.0`. Dos ids concretos necesitan verificación manual en tu
   entorno real de 19 antes de instalar, porque Odoo ha reestructurado
   bastante las vistas de producto entre versiones (tú mismo viste el
   caso de los menús de variantes eliminados en 19.4):
   - El `xpath` de `product_template_form_view_recount` hereda de
     `product.product_template_form_view` y busca una `page` con
     `name="inventory"`. Confirma en modo desarrollador
     (Configuración > Técnico > Vistas) que esa pestaña existe con ese
     nombre en tu 19.x concreto.
   - El menú `menu_stock_recount_request` cuelga de
     `stock.menu_stock_warehouse_mgmt`. Verifica que ese id sigue
     existiendo o cámbialo por el menú padre correcto de tu versión.
2. **Sub-versión exacta (19.0 vs 19.3 vs 19.4...)**: como viste en el
   hilo de Reddit sobre las variantes, Odoo saca cambios de UI dentro
   de la misma versión mayor (SaaS releases). Antes de vender el
   módulo conviene fijar y documentar contra qué sub-versión lo has
   probado realmente.
3. **Ubicación relevante**: ahora mismo solo mira `move.location_id`
   (la ubicación de origen, la que se vacía). Para consumo de
   fabricación puede interesar revisar también movimientos con
   `raw_material_production_id` para afinar el disparo.
4. **Concurrencia**: si varios movimientos del mismo producto se
   confirman casi a la vez, hay una pequeña ventana donde podrían
   crearse dos solicitudes duplicadas antes de que el `search` de
   "existing" vea la primera. Para producción, valorar un
   `_cr.execute` con lock o una constraint SQL de unicidad
   (product_id, location_id, state='pending').
5. **UX del recuento**: `action_open_inventory_adjustment` abre la
   vista de `stock.quant` filtrada, que es funcional pero básica.
   Si quieres algo más pulido, se puede integrar con el wizard nativo
   de ajuste de inventario o con la app de Barcode (popup in-app en
   vez de solo una actividad de mail).
6. **Test**: no incluye tests automáticos todavía; para vender en el
   marketplace de Odoo conviene añadir al menos un test funcional
   básico (crear producto con umbral, confirmar un movimiento, verificar
   que se crea la solicitud).

## Instalación (dev)

1. Copia la carpeta `stock_recount_threshold` a tu carpeta de addons.
2. Actualiza la lista de apps y busca "Stock Recount Threshold".
3. Instala. Depende de `stock` y `mrp`.
