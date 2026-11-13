import unittest

from lxml import etree

from facturacion_sunat.ejemplo import factura_ejemplo
from facturacion_sunat.serializador import generar_xml
from facturacion_sunat.verificacion_xml import PREFIJOS, verificar_perfil


def _factura_con_pago(*bloques):
    raiz = etree.fromstring(generar_xml(factura_ejemplo()))
    anterior = raiz.find("cac:PaymentTerms", PREFIJOS)
    posicion = raiz.index(anterior)
    raiz.remove(anterior)
    for indicador, medios in bloques:
        bloque = etree.Element(etree.QName(PREFIJOS["cac"], "PaymentTerms"))
        etree.SubElement(bloque, etree.QName(PREFIJOS["cbc"], "ID")).text = indicador
        for medio in medios:
            etree.SubElement(bloque, etree.QName(PREFIJOS["cbc"], "PaymentMeansID")).text = medio
        raiz.insert(posicion, bloque)
        posicion += 1
    return raiz


CONTADO = ("FormaPago", ("Contado",))
CREDITO = ("FormaPago", ("Credito",))


class PruebasFormaPago(unittest.TestCase):
    def test_contado_valido(self):
        verificar_perfil(_factura_con_pago(CONTADO))

    def test_3244_falta_indicador(self):
        for bloques in ((), (("Otro", ("Contado",)),)):
            with self.subTest(bloques=bloques):
                self._rechazar(3244, *bloques, elemento="cbc:ID")

    def test_3245_falta_el_elemento(self):
        self._rechazar(3245, ("FormaPago", ()))

    def test_3246_valor_incorrecto_incluido_elemento_vacio(self):
        for valor in ("", " ", "contado", " Contado", "Crédito", "Cuota", "Cuota01", "Cuota0001", "Cuota１２３"):
            with self.subTest(valor=valor):
                self._rechazar(3246, ("FormaPago", (valor,)))

    def test_3247_contado_y_credito_en_bloques_distintos(self):
        self._rechazar(3247, CONTADO, CREDITO)
        self._rechazar(3247, CREDITO, CONTADO)

    def test_3248_mismo_valor_en_bloques_distintos(self):
        for bloque in (CONTADO, CREDITO, ("FormaPago", ("Cuota001",))):
            with self.subTest(bloque=bloque):
                self._rechazar(3248, bloque, bloque)

    def test_3461_dos_medios_en_un_bloque(self):
        for bloque in (
            ("FormaPago", ("Credito", "Cuota001")),
            ("FormaPago", ("Contado", "Contado")),
            ("Otro", ("Contado", "Credito")),
        ):
            with self.subTest(bloque=bloque):
                self._rechazar(3461, bloque)

    def test_3252_cuota_sin_credito_incluidos_limites_lexicos(self):
        for valor in ("Cuota000", "Cuota001", "Cuota999"):
            with self.subTest(valor=valor):
                cuota = ("FormaPago", (valor,))
                self._rechazar(3252, cuota)
                self._rechazar(3252, CONTADO, cuota, ("Otro", ("Credito",)))

    def test_credito_con_cuotas_distintas_queda_fuera_del_perfil(self):
        raiz = _factura_con_pago(
            CREDITO, ("FormaPago", ("Cuota001",)), ("FormaPago", ("Cuota999",)),
        )
        with self.assertRaisesRegex(ValueError, "fuera del perfil académico") as error:
            verificar_perfil(raiz)
        self.assertNotIn("SUNAT", str(error.exception))

    def test_bloque_ajeno_no_cuenta_como_duplicado_de_formapago(self):
        raiz = _factura_con_pago(CONTADO, ("Otro", ("Contado",)))
        with self.assertRaisesRegex(ValueError, "fuera del perfil académico") as error:
            verificar_perfil(raiz)
        self.assertNotIn("SUNAT", str(error.exception))

    def _rechazar(self, codigo, *bloques, elemento="cbc:PaymentMeansID"):
        with self.assertRaisesRegex(ValueError, rf"^SUNAT {codigo} .*{elemento}:"):
            verificar_perfil(_factura_con_pago(*bloques))
