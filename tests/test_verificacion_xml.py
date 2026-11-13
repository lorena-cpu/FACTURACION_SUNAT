from dataclasses import replace
from decimal import Decimal
import unittest
from xml.etree import ElementTree as ET

from lxml import etree

from facturacion_sunat.ejemplo import factura_ejemplo
from facturacion_sunat.modelos import Detalle
from facturacion_sunat.serializador import generar_xml
from facturacion_sunat.verificacion_xml import PREFIJOS, verificar_perfil


class PruebasVerificacionXML(unittest.TestCase):
    def test_perfil_valido(self):
        verificar_perfil(ET.fromstring(generar_xml(factura_ejemplo())))

    def test_ruc_del_emisor_en_la_ruta_del_anexo_9a(self):
        factura = factura_ejemplo()
        raiz = ET.fromstring(generar_xml(factura))
        parte = raiz.find("cac:AccountingSupplierParty/cac:Party", PREFIJOS)
        ids = parte.findall("cac:PartyIdentification/cbc:ID", PREFIJOS)
        self.assertEqual(len(ids), 1)
        self.assertEqual(ids[0].text, factura.emisor.ruc)
        self.assertEqual(ids[0].attrib, {
            "schemeID": "6",
            "schemeName": "Documento de Identidad",
            "schemeAgencyName": "PE:SUNAT",
            "schemeURI": "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06",
        })
        self.assertIsNone(parte.find(".//cbc:CompanyID", PREFIJOS))

    def test_rechaza_ruc_del_emisor_ausente_vacio_o_solo_en_ruta_antigua(self):
        factura = factura_ejemplo()
        xml = generar_xml(factura)
        ruta = "AccountingSupplierParty/Party/cac:PartyIdentification/cbc:ID"
        for caso in ("ausente", "vacío", "solo CompanyID"):
            with self.subTest(caso=caso):
                raiz = ET.fromstring(xml)
                parte = raiz.find("cac:AccountingSupplierParty/cac:Party", PREFIJOS)
                identificacion = parte.find("cac:PartyIdentification", PREFIJOS)
                if caso == "vacío":
                    identificacion.find("cbc:ID", PREFIJOS).text = " "
                    mensaje = f"{ruta}: el RUC está vacío"
                else:
                    parte.remove(identificacion)
                    mensaje = f"{ruta}: se requiere un elemento"
                if caso == "solo CompanyID":
                    fiscal = ET.Element(f"{{{PREFIJOS['cac']}}}PartyTaxScheme")
                    parte.insert(0, fiscal)
                    empresa = ET.SubElement(fiscal, f"{{{PREFIJOS['cbc']}}}CompanyID", schemeID="6")
                    empresa.text = factura.emisor.ruc
                    ET.SubElement(fiscal, f"{{{PREFIJOS['cac']}}}TaxScheme")
                with self.assertRaisesRegex(ValueError, mensaje):
                    verificar_perfil(raiz)

    def test_2023_id_numerico_de_hasta_tres_digitos_distinto_de_cero(self):
        ruta = "cac:InvoiceLine/cbc:ID"
        for valor in ("1", "001", "999"):
            with self.subTest(valor=valor):
                self._verificar_campo_item(ruta, valor)
        for valor in ("0", "000", "1000", "-1", "A1", " 1", ""):
            with self.subTest(valor=valor), self.assertRaisesRegex(ValueError, r"SUNAT 2023 .*cbc:ID"):
                self._verificar_campo_item(ruta, valor)

    def test_2752_rechaza_id_repetido_en_otra_linea(self):
        self._verificar_campo_item("cac:InvoiceLine/cbc:ID", "3")
        with self.assertRaisesRegex(ValueError, r"SUNAT 2752 .*InvoiceLine\[2\]/cbc:ID"):
            self._verificar_campo_item("cac:InvoiceLine/cbc:ID", "2")

    def test_2024_rechaza_cantidad_ausente_o_cero(self):
        ruta = "cac:InvoiceLine/cbc:InvoicedQuantity"
        self._verificar_campo_item(ruta, "2.0000000000")
        for valor in (None, "0", "0.000", "+0", "-0", ".0"):
            with self.subTest(valor=valor), self.assertRaisesRegex(ValueError, r"SUNAT 2024 .*cbc:InvoicedQuantity"):
                self._verificar_campo_item(ruta, valor)
        with self.assertRaisesRegex(ValueError, "decimal no negativo"):
            self._verificar_campo_item(ruta, "-1")

    def test_2026_rechaza_descripcion_ausente_o_vacia(self):
        ruta = "cac:InvoiceLine/cac:Item/cbc:Description"
        for valor in ("A", " \t\n", "Artículo & accesorios"):
            with self.subTest(valor=valor):
                self._verificar_campo_item(ruta, valor)
        for valor in (None, ""):
            with self.subTest(valor=valor), self.assertRaisesRegex(ValueError, r"SUNAT 2026 .*cbc:Description"):
                self._verificar_campo_item(ruta, valor)

    def test_2027_verifica_longitud_sin_quitar_espacios(self):
        ruta = "cac:InvoiceLine/cac:Item/cbc:Description"
        self._verificar_campo_item(ruta, "á" * 498 + "\t\n")
        with self.assertRaisesRegex(ValueError, r"SUNAT 2027 .*cbc:Description"):
            self._verificar_campo_item(ruta, "á" * 500 + " ")

    def _verificar_campo_item(self, ruta, valor):
        raiz = etree.fromstring(generar_xml(factura_ejemplo()))
        nodo = raiz.find(ruta, PREFIJOS)
        if valor is None:
            nodo.getparent().remove(nodo)
        else:
            nodo.text = valor
        verificar_perfil(raiz)

    def test_perfil_valido_con_redondeo_local_por_linea(self):
        detalle = Detalle("Producto de prueba", Decimal("1.500"), Decimal("0.165"))
        factura = replace(factura_ejemplo(), detalles=(detalle, detalle))
        verificar_perfil(ET.fromstring(generar_xml(factura)))

    def test_rechaza_codigos_e_identificacion_incorrectos(self):
        emisor = "cac:AccountingSupplierParty/cac:Party"
        adquirente = "cac:AccountingCustomerParty/cac:Party"
        linea = "cac:InvoiceLine"
        categoria = f"{linea}/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory"
        casos = (
            ("cbc:InvoiceTypeCode", None, "03", "catálogo 01"),
            ("cbc:InvoiceTypeCode", "listID", "0200", "catálogo 51"),
            ("cbc:DocumentCurrencyCode", None, "USD", "DocumentCurrencyCode"),
            (f"{emisor}/cac:PartyIdentification/cbc:ID", "schemeID", "1", "catálogo 06"),
            (f"{adquirente}/cac:PartyIdentification/cbc:ID", None, "20999999010", "dígito verificador"),
            (f"{linea}/cbc:InvoicedQuantity", "unitCode", "KGM", "catálogo 03"),
            (f"{categoria}/cbc:TaxExemptionReasonCode", None, "20", "catálogo 07"),
            (f"{categoria}/cac:TaxScheme/cbc:ID", None, "9997", "catálogo 05"),
            (f"{categoria}/cbc:Percent", None, "10", "tasa general 2026"),
            ("cac:PaymentTerms/cbc:PaymentMeansID", None, "Credito", "PaymentTerms"),
        )
        self._comprobar_mutaciones(casos)

    def test_rechaza_importes_inconsistentes(self):
        linea = "cac:InvoiceLine"
        casos = (
            (f"{linea}/cbc:LineExtensionAmount", None, "110.01", "SUNAT 3272"),
            (f"{linea}/cac:TaxTotal/cbc:TaxAmount", None, "19.81", "TaxTotal/TaxAmount"),
            (f"{linea}/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount", None, "19.79", "TaxSubtotal/TaxAmount"),
            ("cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount", None, "199.99", "TaxableAmount"),
            ("cac:TaxTotal/cbc:TaxAmount", None, "35.99", "TaxTotal/TaxAmount"),
            ("cac:LegalMonetaryTotal/cbc:PayableAmount", None, "235.99", "PayableAmount"),
            ("cac:LegalMonetaryTotal/cbc:PayableAmount", None, "236.001", "precisión"),
            ("cac:LegalMonetaryTotal/cbc:PayableAmount", "currencyID", "USD", "currencyID"),
            (
                f"{linea}/cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount",
                None, "63.89", "SUNAT 3270",
            ),
        )
        self._comprobar_mutaciones(casos)

    def test_identifica_redondeo_explicito_fuera_del_perfil(self):
        raiz = ET.fromstring(generar_xml(factura_ejemplo()))
        totales = raiz.find("cac:LegalMonetaryTotal", PREFIJOS)
        ajuste = ET.SubElement(totales, f"{{{PREFIJOS['cbc']}}}PayableRoundingAmount")
        ajuste.text = "0.01"
        with self.assertRaisesRegex(ValueError, "PayableRoundingAmount.*fuera del perfil"):
            verificar_perfil(raiz)

    def _comprobar_mutaciones(self, casos):
        xml = generar_xml(factura_ejemplo())
        for ruta, atributo, valor, mensaje in casos:
            with self.subTest(ruta=ruta, atributo=atributo, valor=valor):
                raiz = ET.fromstring(xml)
                nodo = raiz.find(ruta, PREFIJOS)
                if atributo is None:
                    nodo.text = valor
                else:
                    nodo.set(atributo, valor)
                with self.assertRaisesRegex(ValueError, mensaje):
                    verificar_perfil(raiz)
