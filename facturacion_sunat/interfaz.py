"""Ventana local para revisar una factura XML."""

import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, ttk
from zipfile import ZipFile

from .validacion_local import validar_factura
from .pestana_generar import PestañaGenerar


def configurar_tcl_tk():
    """Resuelve los recursos empaquetados de Python dentro de .venv."""
    if os.name != "nt" or sys.prefix == sys.base_prefix:
        return
    distribucion = Path(sys.base_prefix) / "tcl"
    destino = Path(sys.prefix) / "tcltk"
    for biblioteca, version, inicio in (
        ("tcl", tk.TclVersion, "init.tcl"),
        ("tk", tk.TkVersion, "tk.tcl"),
    ):
        directorio = distribucion / f"{biblioteca}{version}"
        if not (directorio / inicio).is_file():
            archivos = sorted(distribucion.glob(f"lib{biblioteca}{version}*.zip"))
            if len(archivos) != 1:
                continue
            with ZipFile(archivos[0]) as paquete:
                candidatos = [nombre for nombre in paquete.namelist() if nombre.endswith(f"/{inicio}")]
                if len(candidatos) != 1:
                    continue
                recurso = destino / archivos[0].stem
                directorio = (recurso / candidatos[0]).parent
                if not (directorio / inicio).is_file():
                    paquete.extractall(recurso)
        os.environ[f"{biblioteca.upper()}_LIBRARY"] = str(directorio)


class VentanaValidador:
    def __init__(self, ventana):
        self.ventana = ventana
        self.archivo = tk.StringVar()
        ventana.title("Validador de facturas | FACTURACION_SUNAT")
        ventana.geometry("960x650")
        ventana.minsize(850, 575)
        ventana.configure(bg="#edf3fb")

        estilo = ttk.Style(ventana)
        estilo.theme_use("clam")
        estilo.configure("TFrame", background="#edf3fb")
        estilo.configure("TLabel", background="#edf3fb", foreground="#17365d", font=("Segoe UI", 10))
        estilo.configure("TLabelframe", background="#edf3fb", bordercolor="#a9bfd8")
        estilo.configure("TLabelframe.Label", background="#edf3fb", foreground="#17365d")
        estilo.configure("TNotebook", background="#edf3fb", borderwidth=0)
        estilo.configure("TNotebook.Tab", padding=(18, 8), foreground="#17365d", background="#dbe8f8")
        estilo.map("TNotebook.Tab", background=[("selected", "#2059a5")], foreground=[("selected", "white")])
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 23, "bold"))
        estilo.configure("Estado.TLabel", font=("Segoe UI", 11, "bold"))
        estilo.configure("Principal.TButton", background="#2059a5", foreground="white", padding=(14, 8))
        estilo.map("Principal.TButton", background=[("disabled", "#617997"), ("active", "#17457f")])

        self.pestanas = ttk.Notebook(ventana)
        self.pestanas.pack(fill="both", expand=True, padx=12, pady=12)
        self.pestanas.add(PestañaGenerar(self.pestanas, self.validar_generado), text="Generar factura")
        cuerpo = self.pestana_validar = ttk.Frame(self.pestanas, padding=24)
        self.pestanas.add(cuerpo, text="Validar XML")
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.rowconfigure(6, weight=1)
        ttk.Label(cuerpo, text="Validar factura XML", style="Titulo.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(cuerpo, text="UBL 2.1 · Venta interna al contado · PEN · IGV 18 %").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(2, 18)
        )
        ttk.Entry(cuerpo, textvariable=self.archivo, state="readonly").grid(row=2, column=0, sticky="ew")
        ttk.Button(cuerpo, text="Seleccionar XML…", command=self.seleccionar).grid(row=2, column=1, padx=(10, 0))
        self.boton = ttk.Button(cuerpo, text="Validar factura", style="Principal.TButton", command=self.validar)
        self.boton.grid(row=3, column=0, sticky="w", pady=12)
        self.boton.state(["disabled"])

        self.estado_xsd = tk.StringVar(value="XSD oficial   ·   Sin evaluar")
        self.estado_perfil = tk.StringVar(value="Perfil académico   ·   Sin evaluar")
        for fila, estado in ((4, self.estado_xsd), (5, self.estado_perfil)):
            ttk.Label(cuerpo, textvariable=estado, style="Estado.TLabel").grid(
                row=fila, column=0, columnspan=2, sticky="w", pady=(0, 5)
            )

        panel = ttk.Frame(cuerpo)
        panel.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(8, 10))
        self.detalle = tk.Text(
            panel, wrap="word", height=8, bg="white", fg="#17365d",
            padx=12, pady=10, relief="flat", font=("Segoe UI", 10),
        )
        barra = ttk.Scrollbar(panel, command=self.detalle.yview)
        self.detalle.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.detalle.pack(side="left", fill="both", expand=True)
        self.mostrar_detalle("Selecciona una factura para ver su diagnóstico.")
        ttk.Label(
            cuerpo, text="La validación local no equivale a la aceptación de SUNAT ni de un OSE.",
            wraplength=600,
        ).grid(row=7, column=0, columnspan=2, sticky="w")

    def mostrar_detalle(self, texto):
        self.detalle.configure(state="normal")
        self.detalle.delete("1.0", "end")
        self.detalle.insert("1.0", texto)
        self.detalle.configure(state="disabled")

    def seleccionar(self):
        ruta = filedialog.askopenfilename(
            parent=self.ventana, title="Seleccionar factura XML", filetypes=[("Factura XML", "*.xml")],
        )
        if ruta:
            self.archivo.set(ruta)
            self.estado_xsd.set("XSD oficial   ·   Sin evaluar")
            self.estado_perfil.set("Perfil académico   ·   Sin evaluar")
            self.mostrar_detalle("Archivo seleccionado. Pulsa Validar factura.")
            self.boton.state(["!disabled"])

    def validar_generado(self, ruta):
        self.archivo.set(str(ruta))
        self.boton.state(["!disabled"])
        self.pestanas.select(self.pestana_validar)
        self.validar()

    def validar(self):
        resultado = validar_factura(Path(self.archivo.get()))
        self.estado_xsd.set(f"XSD oficial   ·   {resultado.xsd}")
        self.estado_perfil.set(f"Perfil académico   ·   {resultado.perfil}")
        campos = [resultado.categoria]
        if resultado.codigo:
            campos.append(f"Código SUNAT: {resultado.codigo}")
        if resultado.elemento:
            campos.append(f"Elemento: {resultado.elemento}")
        if resultado.descripcion:
            campos.append(resultado.descripcion)
        self.mostrar_detalle("\n\n".join(campos))


def main():
    configurar_tcl_tk()
    ventana = tk.Tk()
    VentanaValidador(ventana)
    ventana.mainloop()


if __name__ == "__main__":
    main()
