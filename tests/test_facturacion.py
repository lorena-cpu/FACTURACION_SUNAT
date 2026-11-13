from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from xml.etree import ElementTree as etree

from lxml import etree as lxml_etree

from facturacion_sunat.ejemplo import factura_ejemplo
from facturacion_sunat.modelos import Detalle
from facturacion_sunat.serializador import NS, generar_xml
from facturacion_sunat.validacion_xsd import EsquemaNoDisponible, validar_xsd


PREFIJOS = {prefijo: uri for prefijo, uri in NS.items() if prefijo is not None}


class PruebasFactura(unittest.TestCase):
    def setUp(self):
        self.factura = factura_ejemplo()

    def test_calcula_base_igv_y_total(self):
        self.assertEqual(
            [(tributo.base, tributo.importe) for tributo in self.factura.tributos_linea],
            [(Decimal("110.00"), Decimal("19.80")), (Decimal("90.00"), Decimal("16.20"))],
        )
        totales = self.factura.totales
        self.assertEqual(totales.valor_venta, Decimal("200.00"))
        self.assertEqual(totales.igv, Decimal("36.00"))
        self.assertEqual(totales.importe_con_impuestos, Decimal("236.00"))
        self.assertEqual(totales.importe_a_pagar, Decimal("236.00"))

    def test_xml_generado_declara_los_namespaces_que_utiliza(self):
        parser = lxml_etree.XMLParser(recover=False, no_network=True, resolve_entities=False)
        raiz = lxml_etree.fromstring(generar_xml(self.factura), parser)
        self.assertEqual(raiz.tag, f"{{{NS[None]}}}Invoice")
        for prefijo in ("cac", "cbc"):
            self.assertEqual(raiz.nsmap[prefijo], NS[prefijo])

    def test_parser_estricto_rechaza_prefijos_sin_declarar(self):
        casos = (b"<Invoice><ext:UBLExtensions/></Invoice>", b'<Invoice ds:Id="firma"/>')
        for xml in casos:
            with self.subTest(xml=xml):
                parser = lxml_etree.XMLParser(recover=False, no_network=True, resolve_entities=False)
                with self.assertRaises(lxml_etree.XMLSyntaxError) as error:
                    lxml_etree.fromstring(xml, parser)
                self.assertEqual(error.exception.error_log.last_error.type_name, "NS_ERR_UNDEFINED_NAMESPACE")

    def test_redondea_base_e_igv_por_linea(self):
        detalle = Detalle("Artículo de prueba", Decimal("1.500"), Decimal("0.165"))
        factura = replace(self.factura, detalles=(detalle, detalle))
        self.assertEqual(factura.tributos_linea[0].base, Decimal("0.25"))
        self.assertEqual(factura.tributos_linea[0].importe, Decimal("0.05"))
        self.assertEqual(factura.tributos_linea[1].importe, Decimal("0.05"))
        self.assertEqual(factura.totales.igv, Decimal("0.09"))
        self.assertEqual(factura.precios_con_igv[0], Decimal("0.1947"))

    def test_rechaza_datos_de_cabecera_invalidos(self):
        casos = {
            "serie": "B001",
            "correlativo": 0,
            "fecha_emision": "2026-11-12",
            "emisor": replace(self.factura.emisor, ruc="20999999002"),
            "adquirente": replace(self.factura.adquirente, razon_social=" "),
            "detalles": (),
        }
        for campo, valor in casos.items():
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                replace(self.factura, **{campo: valor})

    def test_rechaza_lineas_invalidas(self):
        detalle = self.factura.detalles[0]
        casos = (
            replace(detalle, cantidad=Decimal("0")),
            replace(detalle, valor_unitario=Decimal("NaN")),
            replace(detalle, valor_unitario=40.0),
            replace(detalle, valor_unitario=Decimal("0.000001")),
            replace(detalle, descripcion="Caracter inválido\x00"),
        )
        for linea in casos:
            with self.subTest(linea=linea), self.assertRaises(ValueError):
                replace(self.factura, detalles=(linea,))

    def test_xml_cabecera_partes_orden_y_forma_de_pago(self):
        raiz = etree.fromstring(generar_xml(self.factura))
        self.assertEqual(raiz.tag, f"{{{NS[None]}}}Invoice")
        self.assertEqual(
            [elemento.tag.split("}")[1] for elemento in raiz],
            [
                "UBLVersionID", "CustomizationID", "ID", "IssueDate",
                "InvoiceTypeCode", "Note", "DocumentCurrencyCode",
                "Signature", "AccountingSupplierParty", "AccountingCustomerParty", "PaymentTerms",
                "TaxTotal", "LegalMonetaryTotal", "InvoiceLine", "InvoiceLine",
            ],
        )
        self.assertEqual(raiz.findtext("cbc:UBLVersionID", namespaces=PREFIJOS), "2.1")
        self.assertEqual(raiz.findtext("cbc:CustomizationID", namespaces=PREFIJOS), "2.0")
        tipo = raiz.find("cbc:InvoiceTypeCode", PREFIJOS)
        self.assertEqual((tipo.text, tipo.get("listID")), ("01", "0101"))
        self.assertEqual(raiz.findtext("cbc:DocumentCurrencyCode", namespaces=PREFIJOS), "PEN")
        self.assertEqual(
            [elemento.text for elemento in raiz.findall("cac:PaymentTerms/*", PREFIJOS)],
            ["FormaPago", "Contado"],
        )
        for tipo_parte, datos in (
            ("AccountingSupplierParty", self.factura.emisor),
            ("AccountingCustomerParty", self.factura.adquirente),
        ):
            identificacion = raiz.find(
                f"cac:{tipo_parte}/cac:Party/cac:PartyIdentification/cbc:ID", PREFIJOS
            )
            self.assertEqual((identificacion.text, identificacion.get("schemeID")), (datos.ruc, "6"))

    def test_metadatos_ubl_identifican_al_emisor_del_borrador(self):
        raiz = etree.fromstring(generar_xml(self.factura))
        firmas = raiz.findall("cac:Signature", PREFIJOS)
        self.assertEqual(len(firmas), 1)
        firma = firmas[0]
        self.assertTrue(firma.findtext("cbc:ID", namespaces=PREFIJOS))
        ruta = "cac:SignatoryParty/cac:PartyIdentification/cbc:ID"
        self.assertEqual(firma.findtext(ruta, namespaces=PREFIJOS), self.factura.emisor.ruc)
        ruta = "cac:SignatoryParty/cac:PartyName/cbc:Name"
        self.assertEqual(firma.findtext(ruta, namespaces=PREFIJOS), self.factura.emisor.razon_social)
        self.assertIsNone(firma.find("cac:DigitalSignatureAttachment", PREFIJOS))
        self.assertIsNone(raiz.find("{*}UBLExtensions"))
        self.assertIsNone(raiz.find(".//{http://www.w3.org/2000/09/xmldsig#}Signature"))

    def test_xml_lineas_importes_y_codigos_tributarios(self):
        xml = generar_xml(self.factura)
        self.assertIn(b"&amp;", xml)
        raiz = etree.fromstring(xml)
        lineas = raiz.findall("cac:InvoiceLine", PREFIJOS)
        self.assertEqual(len(lineas), 2)
        for numero, (linea, detalle, tributo, precio) in enumerate(
            zip(lineas, self.factura.detalles, self.factura.tributos_linea,
                self.factura.precios_con_igv, strict=True),
            1,
        ):
            def valor(ruta):
                return linea.findtext(ruta, namespaces=PREFIJOS)

            self.assertEqual(valor("cbc:ID"), str(numero))
            self.assertEqual(linea.find("cbc:InvoicedQuantity", PREFIJOS).get("unitCode"), "NIU")
            self.assertEqual(valor("cac:Item/cbc:Description"), detalle.descripcion)
            self.assertEqual(Decimal(valor("cbc:LineExtensionAmount")), tributo.base)
            self.assertEqual(Decimal(valor("cac:Price/cbc:PriceAmount")), detalle.valor_unitario)
            self.assertEqual(
                Decimal(valor("cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount")),
                precio,
            )
            self.assertEqual(Decimal(valor("cac:TaxTotal/cbc:TaxAmount")), tributo.importe)
            categoria = "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory"
            self.assertEqual(valor(f"{categoria}/cbc:Percent"), "18")
            self.assertEqual(valor(f"{categoria}/cbc:TaxExemptionReasonCode"), "10")
            self.assertEqual(valor(f"{categoria}/cac:TaxScheme/cbc:ID"), "1000")
            self.assertEqual(valor(f"{categoria}/cac:TaxScheme/cbc:Name"), "IGV")
            self.assertEqual(valor(f"{categoria}/cac:TaxScheme/cbc:TaxTypeCode"), "VAT")
            self.assertEqual(
                valor("cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceTypeCode"),
                "01",
            )

        self.assertEqual(raiz.findtext("cac:TaxTotal/cbc:TaxAmount", namespaces=PREFIJOS), "36.00")
        total = raiz.find("cac:LegalMonetaryTotal/cbc:PayableAmount", PREFIJOS)
        self.assertEqual(total.text, "236.00")
        self.assertEqual(
            {elemento.get("currencyID") for elemento in raiz.iter() if "currencyID" in elemento.attrib},
            {"PEN"},
        )

    def test_xsd_faltante_se_reporta_como_pendiente(self):
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio)
            with self.assertRaises(EsquemaNoDisponible):
                validar_xsd(ruta / "factura.xml", ruta / "UBL-Invoice-2.1.xsd")
