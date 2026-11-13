"""Pestaña de captura y exportación de facturas."""

from dataclasses import replace
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .ejemplo import factura_ejemplo
from .formulario_factura import crear_factura, leer_producto
from .serializador import generar_xml


class PestañaGenerar(ttk.Frame):
    def __init__(self, padre, validar_archivo):
        super().__init__(padre, padding=18)
        self.validar_archivo = validar_archivo
        self.productos = {}
        self.campos = {}
        self.resumen = tk.StringVar(value="Añade productos para calcular los importes.")
        self.mensaje = tk.StringVar()
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(4, weight=1)

        ttk.Label(self, text="Generar factura", style="Titulo.TLabel").grid(row=0, columnspan=2, sticky="w")
        ttk.Label(self, text="Factura 01 · Venta interna 0101 · PEN · Contado · IGV 18 %").grid(
            row=1, columnspan=2, sticky="w", pady=(0, 10)
        )
        for columna, titulo, campos in (
            (0, "Emisor", (("ruc_emisor", "RUC", ""), ("razon_emisor", "Razón social", ""),
                           ("establecimiento", "Establecimiento", "0000"))),
            (1, "Adquirente", (("ruc_adquirente", "RUC", ""), ("razon_adquirente", "Razón social", ""))),
        ):
            grupo = ttk.LabelFrame(self, text=titulo, padding=8)
            grupo.grid(row=2, column=columna, sticky="nsew", padx=(0, 8) if columna == 0 else 0)
            for fila, (clave, etiqueta, inicial) in enumerate(campos):
                self._entrada(grupo, clave, etiqueta, inicial, fila)

        cabecera = ttk.LabelFrame(self, text="Comprobante", padding=8)
        cabecera.grid(row=3, columnspan=2, sticky="ew", pady=8)
        cabecera.columnconfigure(7, weight=1)
        for columna, (clave, etiqueta, inicial, ancho) in enumerate((
            ("serie", "Serie", "F001", 7), ("correlativo", "Correlativo", "1", 10),
            ("fecha", "Fecha (AAAA-MM-DD)", date.today().isoformat(), 13),
            ("leyenda", "Importe en letras", "", 24),
        )):
            self._entrada(cabecera, clave, etiqueta, inicial, 0, 2 * columna, ancho)

        detalle = ttk.LabelFrame(self, text="Productos", padding=8)
        detalle.grid(row=4, columnspan=2, sticky="nsew")
        detalle.columnconfigure(0, weight=1)
        detalle.rowconfigure(0, weight=1)
        self.tabla = ttk.Treeview(
            detalle, columns=("descripcion", "cantidad", "valor"), show="headings",
            selectmode="browse", height=4,
        )
        for columna, texto, ancho, ancla in (
            ("descripcion", "Descripción", 360, "w"),
            ("cantidad", "Cantidad", 100, "e"),
            ("valor", "Valor unitario sin IGV (S/)", 180, "e"),
        ):
            self.tabla.heading(columna, text=texto)
            self.tabla.column(columna, width=ancho, anchor=ancla, stretch=columna == "descripcion")
        self.tabla.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(detalle, orient="vertical", command=self.tabla.yview)
        barra.grid(row=0, column=1, sticky="ns")
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.bind("<Double-1>", self._editar_fila)

        acciones = ttk.Frame(detalle)
        acciones.grid(row=1, column=0, sticky="w", pady=(6, 0))
        for texto, accion in (("Agregar", self.editar), ("Modificar", lambda: self.editar(seleccionada=True)),
                              ("Quitar", self.quitar)):
            ttk.Button(acciones, text=texto, command=accion).pack(side="left", padx=(0, 6))

        ttk.Label(self, textvariable=self.resumen, style="Estado.TLabel").grid(
            row=5, columnspan=2, sticky="w", pady=(9, 2)
        )
        ttk.Label(self, textvariable=self.mensaje, wraplength=740).grid(row=6, columnspan=2, sticky="w")
        ttk.Button(self, text="Generar XML", style="Principal.TButton", command=self.generar).grid(
            row=7, columnspan=2, sticky="w", pady=(7, 0)
        )

    def _entrada(self, grupo, clave, etiqueta, inicial, fila, columna=0, ancho=28):
        variable = self.campos[clave] = tk.StringVar(master=self, value=inicial)
        ttk.Label(grupo, text=etiqueta).grid(row=fila, column=columna, sticky="w", padx=(0, 5))
        ttk.Entry(grupo, textvariable=variable, width=ancho).grid(
            row=fila, column=columna + 1, sticky="ew", padx=(0, 8), pady=2
        )
        if columna == 0 and ancho == 28:
            grupo.columnconfigure(1, weight=1)

    def _editar_fila(self, evento):
        fila = self.tabla.identify_row(evento.y)
        if fila:
            self.tabla.selection_set(fila)
            self.editar(seleccionada=True)

    def editar(self, seleccionada=False):
        seleccion = self.tabla.selection()
        if seleccionada and not seleccion:
            self.mensaje.set("Selecciona el producto que deseas modificar.")
            return
        identificador = seleccion[0] if seleccionada else None
        producto = self.productos.get(identificador)
        dialogo = tk.Toplevel(self)
        dialogo.title("Modificar producto" if producto else "Agregar producto")
        dialogo.transient(self.winfo_toplevel())
        dialogo.resizable(False, False)
        cuerpo = ttk.Frame(dialogo, padding=16)
        cuerpo.pack(fill="both", expand=True)
        valores = (
            producto.descripcion, format(producto.cantidad, "f"), format(producto.valor_unitario, "f")
        ) if producto else ("", "1", "")
        entradas = []
        for fila, (etiqueta, valor) in enumerate(zip(
            ("Descripción", "Cantidad", "Valor unitario sin IGV"), valores, strict=True
        )):
            ttk.Label(cuerpo, text=etiqueta).grid(row=fila, column=0, sticky="w", padx=(0, 10), pady=4)
            entrada = ttk.Entry(cuerpo, width=36)
            entrada.insert(0, valor)
            entrada.grid(row=fila, column=1, sticky="ew")
            entradas.append(entrada)
        error = tk.StringVar(master=dialogo)
        ttk.Label(cuerpo, textvariable=error, wraplength=410).grid(row=3, columnspan=2, sticky="w")

        def guardar():
            try:
                nuevo = leer_producto(*(entrada.get() for entrada in entradas))
                candidatos = self.productos.copy()
                candidatos[identificador] = nuevo
                if len(candidatos) > 999:
                    raise ValueError("La factura admite hasta 999 líneas.")
                # El modelo también comprueba los límites de bases y totales.
                totales = replace(factura_ejemplo(), detalles=tuple(candidatos.values())).totales
            except ValueError as fallo:
                error.set(str(fallo))
                return
            fila = (nuevo.descripcion, format(nuevo.cantidad, "f"), format(nuevo.valor_unitario, "f"))
            if identificador is None:
                clave = self.tabla.insert("", "end", values=fila)
            else:
                clave = identificador
                self.tabla.item(clave, values=fila)
            self.productos[clave] = nuevo
            self.tabla.selection_set(clave)
            self._mostrar_totales(totales)
            dialogo.destroy()

        ttk.Button(cuerpo, text="Guardar producto", command=guardar).grid(row=4, columnspan=2, sticky="e")
        dialogo.bind("<Return>", lambda _: guardar())
        dialogo.bind("<Escape>", lambda _: dialogo.destroy())
        dialogo.grab_set()
        entradas[0].focus_set()

    def _mostrar_totales(self, totales):
        self.resumen.set(
            f"Base S/ {totales.valor_venta:.2f}     IGV S/ {totales.igv:.2f}     "
            f"Total S/ {totales.importe_a_pagar:.2f}"
        )
        self.mensaje.set("")

    def quitar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            self.mensaje.set("Selecciona el producto que deseas quitar.")
            return
        clave = seleccion[0]
        self.tabla.delete(clave)
        del self.productos[clave]
        if self.productos:
            self._mostrar_totales(replace(factura_ejemplo(), detalles=tuple(self.productos.values())).totales)
        else:
            self.resumen.set("Añade productos para calcular los importes.")
            self.mensaje.set("")

    def generar(self):
        try:
            factura = crear_factura(
                **{clave: valor.get() for clave, valor in self.campos.items()},
                productos=tuple(self.productos.values()),
            )
            contenido = generar_xml(factura)
        except ValueError as error:
            self.mensaje.set(str(error))
            return

        seleccion = filedialog.asksaveasfilename(
            parent=self, title="Guardar factura XML", defaultextension=".xml",
            initialfile=f"{factura.emisor.ruc}-01-{factura.identificador}.xml",
            filetypes=[("Factura XML", "*.xml")], confirmoverwrite=False,
        )
        if not seleccion:
            return
        ruta = Path(seleccion)
        try:
            if ruta.suffix.lower() != ".xml":
                raise ValueError("Elige un archivo con extensión .xml.")
            salida = Path(__file__).resolve().parents[1] / "output"
            for nombre in (
                "20999999001-01-F001-1.xml", "20999999001-01-F001-1_respaldo.xml",
                "20999999001-01-F001-2.xml", "factura_prueba_namespace_ext.xml",
            ):
                protegido = salida / nombre
                if ruta.exists() and protegido.exists() and ruta.samefile(protegido):
                    raise ValueError("Este XML de ejemplo se conserva. Elige otro nombre o carpeta.")
            try:
                with ruta.open("xb") as archivo:
                    archivo.write(contenido)
            except FileExistsError:
                if not messagebox.askyesno("Confirmar reemplazo", f"¿Reemplazar este archivo?\n{ruta}", parent=self):
                    return
                ruta.write_bytes(contenido)
        except (OSError, ValueError) as error:
            self.mensaje.set(f"No se pudo guardar el XML. {error}")
            return
        self.mensaje.set(f"XML guardado en {ruta}")
        self.validar_archivo(ruta)
