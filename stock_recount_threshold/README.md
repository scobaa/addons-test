# Stock Recount Threshold

**Autor:** srgcba
**Validado en producción por el autor** (Odoo 19, instalación real, agosto 2026):
instalación, hook en entregas, hook en fabricación, actividades, chatter,
botones de acción, no-duplicados y re-creación tras resolver una solicitud
— todo probado y funcionando en un entorno real, ver historial de este
mismo desarrollo.

Módulo que dispara automáticamente una solicitud de recuento cuando la
cantidad disponible de un producto, en una ubicación interna, cae a un
umbral configurable (o por debajo) tras un movimiento de stock (picking,
entrega, consumo de fabricación).

## Qué incluye

- `product.template`: campos `recount_enabled`, `recount_threshold_qty`,
  `recount_responsible_id` para configurar el umbral por producto.
- `stock.move`: hereda `_action_done()` para revisar, tras cada
  confirmación de movimiento, si la cantidad disponible cruzó el umbral.
- `stock.recount.request`: modelo (hereda `mail.thread` y
  `mail.activity.mixin`) que representa cada solicitud generada, con
  estado (pendiente/recontado/cancelado), chatter y una actividad
  (`mail.activity`) asignada al responsable.
- Vista de lista/formulario + menú bajo Inventario para gestionar las
  solicitudes.
- Seguridad básica (usuario de stock puede crear/leer/editar, manager
  puede además borrar).
- **Traducciones**: español (idioma fuente), inglés y francés
  (`i18n/en.po`, `i18n/fr.po`, plantilla en
  `i18n/stock_recount_threshold.pot`).
- Icono del módulo (`static/description/icon.png`) y página de
  presentación para el listado en Odoo Apps
  (`static/description/index.html`).

## Cosas a validar/pulir antes de venderlo

1. **Sub-versión exacta (19.0 vs 19.3 vs 19.4...)**: como viste en el
   hilo de Reddit sobre las variantes, Odoo saca cambios de UI dentro
   de la misma versión mayor (SaaS releases). Documenta contra qué
   sub-versión exacta lo has probado (tú ya lo validaste en tu propio
   entorno, anota la build concreta en la ficha del listado).
2. **Ubicación relevante**: ahora mismo solo mira `move.location_id`
   (la ubicación de origen, la que se vacía). Para consumo de
   fabricación puede interesar revisar también movimientos con
   `raw_material_production_id` para afinar el disparo.
3. **Concurrencia**: si varios movimientos del mismo producto se
   confirman casi a la vez, hay una pequeña ventana donde podrían
   crearse dos solicitudes duplicadas antes de que el `search` de
   "existing" vea la primera. Para producción, valorar un
   `_cr.execute` con lock o una constraint SQL de unicidad
   (product_id, location_id, state='pending').
4. **UX del recuento**: `action_open_inventory_adjustment` abre la
   vista de `stock.quant` filtrada, que es funcional pero básica.
   Si quieres algo más pulido, se puede integrar con el wizard nativo
   de ajuste de inventario o con la app de Barcode (popup in-app en
   vez de solo una actividad de mail).
5. **Test automáticos**: no incluye tests unitarios todavía; para
   vender en el marketplace de Odoo conviene añadir al menos un test
   funcional básico (crear producto con umbral, confirmar un
   movimiento, verificar que se crea la solicitud). Las pruebas
   manuales ya hechas cubren el flujo feliz; los tests automáticos
   protegerían contra regresiones futuras.
6. **Precio y ficha de venta**: cuando lo subas a apps.odoo.com,
   recuerda que hay que añadir las claves `price` y `currency` en el
   manifest, y que la ficha necesita capturas de pantalla reales
   además del `index.html` que ya incluye este paquete.
7. **`es.po` explícito**: el idioma fuente del código ya es español,
   así que funciona out-of-the-box en instalaciones en español sin
   necesidad de un `es.po`. Si en el futuro quieres seguir la
   convención habitual de OCA/Odoo (código fuente en inglés + `.po`
   para cada idioma incluido el español), sería un refactor a futuro,
   no algo urgente.

## Instalación (dev)

1. Copia la carpeta `stock_recount_threshold` a tu carpeta de addons.
2. Actualiza la lista de apps y busca "Stock Recount Threshold".
3. Instala. Depende de `stock`, `mrp` y `mail`.
4. Para cargar las traducciones: Ajustes > Traducciones > Cargar una
   traducción, o simplemente cambia el idioma del usuario/instalación
   a inglés o francés y Odoo debería recoger los términos de los
   ficheros `.po` automáticamente al instalar/actualizar el módulo.

