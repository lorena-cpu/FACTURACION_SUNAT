"""Construcción programática del documento UBL 2.1 académico."""

from decimal import Decimal

from xml.etree import ElementTree as etree

from .modelos import Adquirente, Emisor, Factura, IGV, Tributos


URN_UBL = "urn:oasis:names:specification:ubl:schema:xsd:"
NS = {
    None: URN_UBL + "Invoice-2",
    "cbc": URN_UBL + "CommonBasicComponents-2",
    "cac": URN_UBL + "CommonAggregateComponents-2",
}
SUNAT = "PE:SUNAT"
CATALOGO = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo"
UNECE = "United Nations Economic Commission for Europe"
MONEDA = "PEN"

for prefijo, namespace in NS.items():
    etree.register_namespace(prefijo or "", namespace)


def _elemento(padre, prefijo, nombre, texto=None, **atributos):
    elemento = etree.SubElement(padre, etree.QName(NS[prefijo], nombre), **atributos)
    if texto is not None:
        elemento.text = format(texto, "f") if isinstance(texto, Decimal) else str(texto)
    return elemento


def _importe(padre, nombre, valor):
    return _elemento(padre, "cbc", nombre, valor, currencyID=MONEDA)


def _metadatos_firmante(raiz, emisor: Emisor):
    firma = _elemento(raiz, "cac", "Signature")
    _elemento(firma, "cbc", "ID", "IDSign")
    firmante = _elemento(firma, "cac", "SignatoryParty")
    identificacion = _elemento(firmante, "cac", "PartyIdentification")
    _elemento(identificacion, "cbc", "ID", emisor.ruc)
    nombre = _elemento(firmante, "cac", "PartyName")
    _elemento(nombre, "cbc", "Name", emisor.razon_social)


def _parte(raiz, nombre, datos: Emisor | Adquirente):
    cuenta = _elemento(raiz, "cac", nombre)
    parte = _elemento(cuenta, "cac", "Party")
    identificacion = _elemento(parte, "cac", "PartyIdentification")
    _elemento(
        identificacion, "cbc", "ID", datos.ruc, schemeID="6",
        schemeName="Documento de Identidad", schemeAgencyName=SUNAT,
        schemeURI=CATALOGO + "06",
    )
    entidad = _elemento(parte, "cac", "PartyLegalEntity")
    _elemento(entidad, "cbc", "RegistrationName", datos.razon_social)
    if isinstance(datos, Emisor):
        direccion = _elemento(entidad, "cac", "RegistrationAddress")
        _elemento(
            direccion, "cbc", "AddressTypeCode", datos.establecimiento,
            listAgencyName=SUNAT, listName="Establecimientos anexos",
        )


def _igv(padre, tributo: Tributos, *, por_linea: bool):
    total = _elemento(padre, "cac", "TaxTotal")
    _importe(total, "TaxAmount", tributo.importe)
    subtotal = _elemento(total, "cac", "TaxSubtotal")
    _importe(subtotal, "TaxableAmount", tributo.base)
    _importe(subtotal, "TaxAmount", tributo.importe)
    categoria = _elemento(subtotal, "cac", "TaxCategory")
    if por_linea:
        _elemento(categoria, "cbc", "Percent", IGV)
        _elemento(
            categoria, "cbc", "TaxExemptionReasonCode", "10", listAgencyName=SUNAT,
            listName="Afectacion del IGV", listURI=CATALOGO + "07",
        )
    esquema = _elemento(categoria, "cac", "TaxScheme")
    _elemento(esquema, "cbc", "ID", "1000")
    _elemento(esquema, "cbc", "Name", "IGV")
    _elemento(esquema, "cbc", "TaxTypeCode", "VAT")


def generar_xml(factura: Factura) -> bytes:
    raiz = etree.Element(etree.QName(NS[None], "Invoice"))
    _elemento(raiz, "cbc", "UBLVersionID", "2.1")
    _elemento(raiz, "cbc", "CustomizationID", "2.0", schemeAgencyName=SUNAT)
    _elemento(raiz, "cbc", "ID", factura.identificador)
    _elemento(raiz, "cbc", "IssueDate", factura.fecha_emision.isoformat())
    _elemento(
        raiz, "cbc", "InvoiceTypeCode", "01", listID="0101",
        listAgencyName=SUNAT, listName="Tipo de Documento", listURI=CATALOGO + "01",
        name="Tipo de Operacion", listSchemeURI=CATALOGO + "51",
    )
    _elemento(raiz, "cbc", "Note", factura.leyenda_importe, languageLocaleID="1000")
    _elemento(
        raiz, "cbc", "DocumentCurrencyCode", MONEDA, listID="ISO 4217 Alpha",
        listName="Currency", listAgencyName=UNECE,
    )
    _metadatos_firmante(raiz, factura.emisor)
    _parte(raiz, "AccountingSupplierParty", factura.emisor)
    _parte(raiz, "AccountingCustomerParty", factura.adquirente)
    pago = _elemento(raiz, "cac", "PaymentTerms")
    _elemento(pago, "cbc", "ID", "FormaPago")
    _elemento(pago, "cbc", "PaymentMeansID", "Contado")
    totales = factura.totales
    _igv(raiz, Tributos(totales.valor_venta, totales.igv), por_linea=False)
    total_monetario = _elemento(raiz, "cac", "LegalMonetaryTotal")
    _importe(total_monetario, "LineExtensionAmount", totales.valor_venta)
    _importe(total_monetario, "TaxInclusiveAmount", totales.importe_con_impuestos)
    _importe(total_monetario, "PayableAmount", totales.importe_a_pagar)

    lineas = zip(factura.detalles, factura.tributos_linea, factura.precios_con_igv, strict=True)
    for numero, (detalle, tributo, precio) in enumerate(lineas, 1):
        linea = _elemento(raiz, "cac", "InvoiceLine")
        _elemento(linea, "cbc", "ID", numero)
        _elemento(
            linea, "cbc", "InvoicedQuantity", detalle.cantidad, unitCode="NIU",
            unitCodeListID="UN/ECE rec 20", unitCodeListAgencyName=UNECE,
        )
        _importe(linea, "LineExtensionAmount", tributo.base)
        referencia = _elemento(linea, "cac", "PricingReference")
        alternativa = _elemento(referencia, "cac", "AlternativeConditionPrice")
        _importe(alternativa, "PriceAmount", precio)
        _elemento(
            alternativa, "cbc", "PriceTypeCode", "01", listAgencyName=SUNAT,
            listName="Tipo de Precio", listURI=CATALOGO + "16",
        )
        _igv(linea, tributo, por_linea=True)
        item = _elemento(linea, "cac", "Item")
        _elemento(item, "cbc", "Description", detalle.descripcion)
        precio_base = _elemento(linea, "cac", "Price")
        _importe(precio_base, "PriceAmount", detalle.valor_unitario)

    etree.indent(raiz)
    return etree.tostring(raiz, encoding="UTF-8", xml_declaration=True)
