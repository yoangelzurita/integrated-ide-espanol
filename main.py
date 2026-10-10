"""
Integrated — Entorno de desarrollo en español para Arduino / ESP.
"""

from __future__ import annotations

import os
import ctypes
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog, colorchooser, simpledialog
from pathlib import Path

import serial
import serial.tools.list_ports

from vocabulario import SUGERENCIAS, REFERENCIA_LENGUAJE
from traductor import traducir_codigo
from placas import nombres_placas, fqbn_de, baud_de, core_de, CORE_INDEX_URLS
from consola import ConsolaSalida
from ejemplos import nombres_ejemplos, codigo_ejemplo
from biblioteca import lista_categorias, comandos_de, buscar_comandos, total_comandos
import build_manager as build
import config as app_config

EXT_PROYECTO = ".int_esp"
FILTROS_ARCHIVO = [
    ("Proyecto Integrated", f"*{EXT_PROYECTO}"),
    ("Español legado", "*.es"),
    ("Todos", "*.*"),
]


class LineNumberedText(tk.Frame):
    """Editor con numeración de líneas sincronizada."""

    def __init__(self, parent, bg, fg, insertbg, font, border_color="#2A3544", **kwargs):
        super().__init__(parent, bg=parent.cget("bg") if hasattr(parent, "cget") else bg)
        self.linenumbers = tk.Text(
            self, width=4, padx=6, takefocus=0, border=0, highlightthickness=0,
            bg="#121820", fg="#5C6B7A", font=font, state=tk.DISABLED,
        )
        self.linenumbers.pack(side=tk.LEFT, fill=tk.Y)

        self.text = scrolledtext.ScrolledText(
            self, wrap=tk.NONE, bg=bg, fg=fg, insertbackground=insertbg,
            font=font, bd=0, highlightthickness=0,
            undo=True, maxundo=-1, **kwargs,
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text.bind("<KeyRelease>", self._on_change)
        self.text.bind("<MouseWheel>", self._on_scroll)
        self.text.bind("<Button-1>", lambda e: self.after(1, self._sync_scroll))
        self.text.vbar = getattr(self.text, "vbar", None)
        # Sincronizar scroll del ScrolledText interno
        self.text.bind("<Configure>", lambda e: self._actualizar_numeros())
        self.after(50, self._actualizar_numeros)

    def _on_change(self, _event=None):
        self._actualizar_numeros()

    def _on_scroll(self, _event=None):
        self.after(1, self._sync_scroll)

    def _sync_scroll(self):
        try:
            yview = self.text.yview()
            self.linenumbers.yview_moveto(yview[0])
        except tk.TclError:
            pass

    def _actualizar_numeros(self):
        try:
            final = self.text.index("end-1c")
            total = int(final.split(".")[0])
            numeros = "\n".join(str(i) for i in range(1, total + 1))
            self.linenumbers.config(state=tk.NORMAL)
            self.linenumbers.delete("1.0", tk.END)
            self.linenumbers.insert("1.0", numeros)
            self.linenumbers.config(state=tk.DISABLED)
            self._sync_scroll()
        except tk.TclError:
            pass

    def get(self, *args):
        return self.text.get(*args)

    def insert(self, *args, **kwargs):
        r = self.text.insert(*args, **kwargs)
        self._actualizar_numeros()
        return r

    def delete(self, *args):
        r = self.text.delete(*args)
        self._actualizar_numeros()
        return r

    def index(self, *args):
        return self.text.index(*args)

    def bind(self, *args, **kwargs):
        return self.text.bind(*args, **kwargs)

    def focus_set(self):
        self.text.focus_set()

    def config_editor(self, **kwargs):
        self.text.config(**kwargs)
        if "highlightbackground" in kwargs:
            self.text.config(highlightbackground=kwargs["highlightbackground"])
        if "font" in kwargs:
            self.linenumbers.config(font=kwargs["font"])
        if "bg" in kwargs:
            # gutter un poco más oscuro
            pass

    def bbox(self, index):
        return self.text.bbox(index)

    def see(self, index):
        self.text.see(index)

    def mark_set(self, *args):
        return self.text.mark_set(*args)

    def tag_remove(self, *args):
        return self.text.tag_remove(*args)

    def tag_add(self, *args):
        return self.text.tag_add(*args)

    def tag_config(self, *args, **kwargs):
        return self.text.tag_config(*args, **kwargs)

    def edit_undo(self):
        try:
            self.text.edit_undo()
        except tk.TclError:
            pass

    def edit_redo(self):
        try:
            self.text.edit_redo()
        except tk.TclError:
            pass


class IDEInteligente(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Integrated — Entorno de Desarrollo en Español")
        self.minsize(1000, 650)

        cfg = app_config.cargar()
        self.bg_principal = cfg["bg_principal"]
        self.bg_secundario = cfg["bg_secundario"]
        self.bg_editor = cfg["bg_editor"]
        self.bg_elevado = cfg["bg_elevado"]
        self.fg_texto = cfg["fg_texto"]
        self.fg_muted = cfg["fg_muted"]
        self.fg_editor = cfg["fg_editor"]
        self.acento = cfg["acento"]
        self.acento_2 = cfg["acento_2"]
        self.peligro = cfg["peligro"]
        self.borde = cfg.get("borde", "#051930")
        self.header_texto = cfg.get("header_texto", self.fg_texto)
        self.tam_fuente = int(cfg.get("tam_fuente", 11))
        self.fuente_editor = self._fuente_mono(self.tam_fuente)
        self.fuente_ui = ("Segoe UI", 10)
        self.header_titulo = cfg.get("header_titulo") or "Integrated"
        self.header_subtitulo = cfg.get("header_subtitulo") or "IDE en español"
        self.header_color = cfg.get("header_color")
        self.recursos_web = cfg.get("recursos_web") or ""
        if not self.recursos_web:
            recursos_detectados = build.descubrir_recursos_web()
            self.recursos_web = str(recursos_detectados) if recursos_detectados else ""
        self.placa_inicial = cfg.get("placa") or "ESP32 S2 Mini"
        self.baud_monitor = int(cfg.get("baud_monitor", 115200))

        try:
            self.geometry(cfg.get("geometry") or "1400x900")
        except tk.TclError:
            self.geometry("1400x900")

        self.cpp_visible = True
        self.rutas_archivo = {}
        self.serial_activo = None
        self.monitor_abierto = False
        self._ocupado = False
        self._sugerencia_rango = None

        self.configure(bg=self.bg_principal)
        self.crear_estilos_ttk()
        self.crear_menu_superior()
        self.crear_atajos()
        self.crear_interfaz_principal()
        self.after(250, self._aplicar_color_barra_nativa)
        self.crear_ventana_serial()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    def _fuente_mono(self, size: int):
        """Elige una fuente monoespaciada disponible en el sistema."""
        candidatos = ("Cascadia Code", "Consolas", "Courier New")
        disponibles = set(self.tk.call("font", "families"))
        for nombre in candidatos:
            if nombre in disponibles:
                return (nombre, size)
        return ("Courier", size)

    # ── Estilos ──────────────────────────────────────────────
    def crear_estilos_ttk(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.actualizar_estilos_visuales()

    def actualizar_estilos_visuales(self):
        self.configure(bg=self.bg_principal)
        self.style.configure("TNotebook", background=self.bg_principal, borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=self.bg_secundario,
            foreground=self.fg_muted,
            padding=[14, 8],
            font=("Segoe UI", 9, "bold"),
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", self.bg_elevado)],
            foreground=[("selected", self.acento_2)],
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=self.bg_elevado,
            background=self.bg_elevado,
            foreground=self.fg_texto,
            arrowcolor=self.fg_texto,
            bordercolor=self.bg_elevado,
        )
        self.style.map("TCombobox", fieldbackground=[("readonly", self.bg_elevado)])
        self.style.configure(
            "Horizontal.TProgressbar",
            troughcolor=self.bg_secundario,
            background=self.acento,
            bordercolor=self.bg_secundario,
            lightcolor=self.acento,
            darkcolor=self.acento,
        )

    def _btn(self, parent, text, bg, command, **kw):
        kw.setdefault("padx", 14)
        kw.setdefault("pady", 6)
        return tk.Button(
            parent, text=text, bg=bg, fg="#FFFFFF", font=("Segoe UI", 9, "bold"),
            bd=0, highlightthickness=0,
            cursor="hand2", activebackground=bg,
            activeforeground="#1C0266", relief=tk.FLAT, command=command, **kw,
        )

    def _aplicar_color_barra_nativa(self, ventana=None):
        """Colorea la barra de título real de Windows cuando DWM lo permite."""
        if os.name != "nt":
            return
        try:
            ventana = ventana or self
            hwnd_cliente = ventana.winfo_id()
            hwnd = ctypes.windll.user32.GetAncestor(hwnd_cliente, 2)
            if not hwnd:
                hwnd = hwnd_cliente
            color = self.header_color or self.bg_secundario
            color = color.lstrip("#")
            rojo, verde, azul = (int(color[i:i + 2], 16) for i in (0, 2, 4))
            valor = ctypes.c_int((azul << 16) | (verde << 8) | rojo)
            dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute
            dwm.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            dwm.restype = ctypes.c_long
            # Windows 11: color de caption y texto; Windows 10: modo oscuro como fallback.
            dwm(hwnd, 35, ctypes.byref(valor), ctypes.sizeof(valor))
            dwm(hwnd, 36, ctypes.byref(ctypes.c_int(0x00FFFFFF)), ctypes.sizeof(ctypes.c_int))
            modo_oscuro = ctypes.c_int(1)
            dwm(hwnd, 20, ctypes.byref(modo_oscuro), ctypes.sizeof(modo_oscuro))
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                0x0001 | 0x0002 | 0x0004 | 0x0020,
            )
        except (AttributeError, OSError, ValueError):
            pass

    # ── Menús ────────────────────────────────────────────────
    def crear_menu_superior(self):
        self.menubar = tk.Menu(
            self, bg=self.bg_secundario, fg=self.fg_texto,
            activebackground=self.bg_elevado, activeforeground="#FFFFFF", bd=0,
        )
        # Barra visual propia: la barra Menu nativa de Windows ignora colores en algunos temas.
        self.config(menu="")
        self.menu_bar_frame = tk.Frame(self, bg=self.bg_secundario, height=30)
        self.menu_bar_frame.pack(fill=tk.X)
        self.menu_bar_frame.pack_propagate(False)

        m = dict(tearoff=0, bg=self.bg_secundario, fg=self.fg_texto,
            activebackground=self.bg_elevado, activeforeground="#FFFFFF")

        self.menu_archivo = tk.Menu(self.menubar, **m)
        self.menu_archivo.add_command(label="Nuevo", accelerator="Ctrl+N", command=self.nuevo_archivo)
        self.menu_archivo.add_command(label="Abrir...", accelerator="Ctrl+O", command=self.abrir_archivo)
        self.menu_archivo.add_command(label="Guardar", accelerator="Ctrl+S", command=self.guardar_archivo)
        self.menu_archivo.add_command(label="Guardar como...", command=self.guardar_archivo_como)
        self.menu_archivo.add_command(label="Exportar C++...", command=self.exportar_cpp)
        self.menu_archivo.add_separator()
        self.menu_archivo.add_command(label="Cerrar pestaña", accelerator="Ctrl+W", command=self.cerrar_pestana_activa)
        self.menu_archivo.add_separator()
        self.menu_archivo.add_command(label="Salir", command=self._al_cerrar)
        self.menubar.add_cascade(label="Archivo", menu=self.menu_archivo)

        self.menu_editar = tk.Menu(self.menubar, **m)
        self.menu_editar.add_command(label="Deshacer", accelerator="Ctrl+Z", command=self.deshacer)
        self.menu_editar.add_command(label="Rehacer", accelerator="Ctrl+Y", command=self.rehacer)
        self.menu_editar.add_separator()
        self.menu_editar.add_command(label="Buscar...", accelerator="Ctrl+F", command=self.buscar_texto)
        self.menu_editar.add_command(label="Reemplazar...", accelerator="Ctrl+H", command=self.reemplazar_texto)
        self.menu_editar.add_separator()
        self.menu_editar.add_command(label="Aumentar fuente", accelerator="Ctrl++", command=lambda: self.cambiar_tam_fuente(1))
        self.menu_editar.add_command(label="Reducir fuente", accelerator="Ctrl+-", command=lambda: self.cambiar_tam_fuente(-1))
        self.menubar.add_cascade(label="Editar", menu=self.menu_editar)

        self.menu_proyecto = tk.Menu(self.menubar, **m)
        self.menu_proyecto.add_command(label="Limpiar caché de builds", command=self.limpiar_cache_builds)
        self.menu_proyecto.add_command(label="Crear archivos web...", command=self.crear_archivos_web)
        self.menu_proyecto.add_command(label="Seleccionar carpeta web...", command=self.seleccionar_recursos_web)
        self.menu_proyecto.add_command(label="Instalar core de la placa actual", command=self.instalar_core_actual)
        self.menubar.add_cascade(label="Proyecto", menu=self.menu_proyecto)

        self.menu_ejemplos = tk.Menu(self.menubar, **m)
        for nombre in nombres_ejemplos():
            self.menu_ejemplos.add_command(
                label=nombre,
                command=lambda n=nombre: self.abrir_ejemplo(n),
            )
        self.menubar.add_cascade(label="Ejemplos", menu=self.menu_ejemplos)

        self.menu_estilo = tk.Menu(self.menubar, **m)
        self.menu_estilo.add_command(label="Tema oscuro (por defecto)", command=self.tema_por_defecto)
        self.menu_estilo.add_command(label="Tema claro", command=self.tema_claro)
        self.menu_estilo.add_command(label="Tema océano", command=self.tema_oceano)
        self.menu_estilo.add_separator()
        self.menu_estilo.add_command(label="Personalizar barra superior...", command=self.personalizar_header)
        self.menu_estilo.add_command(label="Color de fondo personalizado...", command=self.cambiar_color_fondo_general)
        self.menu_estilo.add_command(label="Color de letra del editor...", command=self.cambiar_color_letra)
        self.menu_estilo.add_separator()
        self.menu_estilo.add_command(label="Guardar preferencias ahora", command=self.guardar_preferencias)
        self.menubar.add_cascade(label="Estilo", menu=self.menu_estilo)

        self.menu_vista = tk.Menu(self.menubar, **m)
        self.menu_vista.add_command(label="Alternar panel C++", accelerator="Ctrl+\\", command=self.alternar_panel_cpp)
        self.menu_vista.add_command(label="Monitor serie", accelerator="Ctrl+Shift+M", command=self.abrir_monitor_serie)
        self.menu_vista.add_command(label="Limpiar consola", command=self.limpiar_consola)
        self.menubar.add_cascade(label="Vista", menu=self.menu_vista)

        self.menu_ayuda = tk.Menu(self.menubar, **m)
        self.menu_ayuda.add_command(label="Biblioteca de comandos", accelerator="F1", command=self.abrir_biblioteca)
        self.menu_ayuda.add_command(label="Referencia del lenguaje", command=self.mostrar_ayuda)
        self.menu_ayuda.add_command(label="Guía para comenzar", command=self.mostrar_guia_inicio)
        self.menu_ayuda.add_command(label="Acerca de Integrated", command=self.mostrar_acerca)
        self.menubar.add_cascade(label="Ayuda", menu=self.menu_ayuda)

        for etiqueta, menu in (
            ("Archivo", self.menu_archivo), ("Editar", self.menu_editar),
            ("Proyecto", self.menu_proyecto), ("Ejemplos", self.menu_ejemplos),
            ("Estilo", self.menu_estilo), ("Vista", self.menu_vista),
            ("Ayuda", self.menu_ayuda),
        ):
            boton = tk.Button(
                self.menu_bar_frame, text=etiqueta,
                bg=self.bg_secundario, fg=self.fg_texto,
                activebackground=self.bg_elevado, activeforeground="#FFFFFF",
                relief=tk.FLAT, bd=0, padx=10, pady=4, cursor="hand2",
            )
            boton.config(command=lambda m=menu, b=boton: self._abrir_menu_visual(m, b))
            boton.pack(side=tk.LEFT)
        self.menu_bar_buttons = self.menu_bar_frame.winfo_children()

    def _abrir_menu_visual(self, menu, boton):
        """Abre un menú visual propio sin depender del menú nativo de Windows."""
        x = boton.winfo_rootx()
        y = boton.winfo_rooty() + boton.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def crear_atajos(self):
        self.bind_all("<Control-n>", lambda e: self.nuevo_archivo())
        self.bind_all("<Control-o>", lambda e: self.abrir_archivo())
        self.bind_all("<Control-s>", lambda e: self.guardar_archivo())
        self.bind_all("<Control-w>", lambda e: self.cerrar_pestana_activa())
        self.bind_all("<Control-f>", lambda e: self.buscar_texto())
        self.bind_all("<Control-h>", lambda e: self.reemplazar_texto())
        self.bind_all("<Control-u>", lambda e: self.cargar_a_placa())
        self.bind_all("<F5>", lambda e: self.traducir_pestana_activa())
        self.bind_all("<F1>", lambda e: self.abrir_biblioteca())
        self.bind_all("<Control-plus>", lambda e: self.cambiar_tam_fuente(1))
        self.bind_all("<Control-minus>", lambda e: self.cambiar_tam_fuente(-1))
        self.bind_all("<Control-equal>", lambda e: self.cambiar_tam_fuente(1))
        self.bind_all("<Control-backslash>", lambda e: self.alternar_panel_cpp())
        self.bind_all("<Control-Shift-M>", lambda e: self.abrir_monitor_serie())

    # ── Interfaz ─────────────────────────────────────────────
    def crear_interfaz_principal(self):
        header_bg = self.header_color or self.bg_secundario
        self.header_frame = tk.Frame(self, bg=header_bg, height=56)
        self.header_frame.pack(fill=tk.X)
        self.header_frame.pack_propagate(False)

        self.label_title = tk.Label(
            self.header_frame, text=self.header_titulo, bg=header_bg,
            fg=self.header_texto, font=("Segoe UI", 14, "bold"),
        )
        self.label_title.pack(side=tk.LEFT, padx=(18, 6), pady=12)

        self.label_subtitle = tk.Label(
            self.header_frame, text=self.header_subtitulo, bg=header_bg,
            fg=self.fg_muted, font=("Segoe UI", 9),
        )
        self.label_subtitle.pack(side=tk.LEFT, padx=(0, 20))

        self.lbl_placa = tk.Label(
            self.header_frame, text="Placa", bg=header_bg,
            fg=self.fg_muted, font=("Segoe UI", 9),
        )
        self.lbl_placa.pack(side=tk.LEFT, padx=(8, 4))

        self.combo_placas = ttk.Combobox(
            self.header_frame, values=nombres_placas(), state="readonly",
            width=22, font=("Segoe UI", 9),
        )
        placas = nombres_placas()
        if self.placa_inicial in placas:
            self.combo_placas.set(self.placa_inicial)
        else:
            self.combo_placas.set(placas[0])
        self.combo_placas.pack(side=tk.LEFT, padx=4)
        self.combo_placas.bind("<<ComboboxSelected>>", self._on_placa_cambiada)

        self.lbl_puerto = tk.Label(
            self.header_frame, text="Puerto", bg=header_bg,
            fg=self.fg_muted, font=("Segoe UI", 9),
        )
        self.lbl_puerto.pack(side=tk.LEFT, padx=(14, 4))

        self.combo_puertos = ttk.Combobox(
            self.header_frame, values=self.obtener_puertos(), state="readonly",
            width=14, font=("Segoe UI", 9),
        )
        self.combo_puertos.pack(side=tk.LEFT, padx=4)
        self.actualizar_lista_puertos()
        self._programar_actualizacion_puertos()

        self.btn_serial = self._btn(
            self.header_frame, "Monitor serie", self.bg_elevado, self.abrir_monitor_serie,
        )
        self.btn_serial.pack(side=tk.LEFT, padx=10)

        # Barra de acciones visibles (no solo menú)
        self.toolbar = tk.Frame(self, bg=self.bg_principal, height=48)
        self.toolbar.pack(fill=tk.X, padx=10, pady=(8, 0))

        self.btn_traducir = self._btn(
            self.toolbar, "Traducir (F5)", self.bg_elevado, self.traducir_pestana_activa,
        )
        self.btn_traducir.pack(side=tk.LEFT, padx=(0, 6), pady=6)

        self.btn_compilar = self._btn(
            self.toolbar, "Compilar", self.acento_2, self.solo_compilar,
        )
        self.btn_compilar.pack(side=tk.LEFT, padx=6, pady=6)

        self.btn_cargar = self._btn(
            self.toolbar, "Cargar a la placa", "#00921D", self.cargar_a_placa,
        )
        self.btn_cargar.pack(side=tk.LEFT, padx=6, pady=6)

        self.btn_exportar = self._btn(
            self.toolbar, "Exportar C++", self.bg_elevado, self.exportar_cpp,
        )
        self.btn_exportar.pack(side=tk.LEFT, padx=6, pady=6)

        # Centro
        self.main_paned = tk.PanedWindow(
            self, orient=tk.VERTICAL, bg=self.bg_principal, sashwidth=4, bd=0,
        )
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 4))

        self.frame_editores = tk.Frame(self.main_paned, bg=self.bg_principal)
        self.main_paned.add(self.frame_editores, height=520)

        self.notebook = ttk.Notebook(self.frame_editores)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<Button-3>", self.mostrar_menu_pestana)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._actualizar_status())

        self.crear_nueva_pestana(f"proyecto_principal{EXT_PROYECTO}")

        # Consola
        self.frame_inferior_consola = tk.Frame(self.main_paned, bg=self.bg_principal)
        self.main_paned.add(self.frame_inferior_consola)

        cab_cons = tk.Frame(self.frame_inferior_consola, bg=self.bg_principal)
        cab_cons.pack(fill=tk.X)
        self.lbl_consola = tk.Label(
            cab_cons, text="Salida", bg=self.bg_principal,
            fg=self.fg_muted, font=("Segoe UI", 9, "bold"),
        )
        self.lbl_consola.pack(side=tk.LEFT, pady=(4, 2))
        self._btn(cab_cons, "Limpiar", self.bg_elevado, self.limpiar_consola).pack(
            side=tk.RIGHT, pady=2,
        )

        self.consola_widget = scrolledtext.ScrolledText(
            self.frame_inferior_consola, wrap=tk.WORD, bg=self.bg_editor,
            fg=self.acento, font=("Consolas", 10), height=7, bd=0,
            highlightthickness=0,
        )
        self.consola_widget.pack(fill=tk.BOTH, expand=True)
        self.consola_widget.tag_config("info", foreground=self.acento_2)
        self.consola_widget.tag_config("ok", foreground=self.acento)
        self.consola_widget.tag_config("error", foreground=self.peligro)
        self.consola = ConsolaSalida(self.consola_widget, self)

        self.barra_progreso = ttk.Progressbar(
            self.frame_inferior_consola, orient="horizontal", mode="indeterminate",
        )
        self.barra_progreso.pack(fill=tk.X, pady=(4, 0))

        # Status bar
        self.status_bar = tk.Label(
            self, text="Listo", anchor="w", bg=self.bg_secundario,
            fg=self.fg_muted, font=("Segoe UI", 8), padx=12, pady=3,
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Autocompletado
        self.listbox_sugerencias = tk.Listbox(
            self, bg=self.bg_elevado, fg=self.fg_texto, font=("Consolas", 10),
            selectbackground=self.acento_2, bd=0, highlightthickness=0,
        )
        self.listbox_sugerencias.bind("<Double-Button-1>", self.insertar_sugerencia)
        self.listbox_sugerencias.bind("<Return>", self.insertar_sugerencia)
        self.listbox_sugerencias.bind("<Escape>", lambda e: self.listbox_sugerencias.place_forget())

    # ── Puertos ──────────────────────────────────────────────
    def obtener_puertos(self):
        puertos = [p.device for p in serial.tools.list_ports.comports()]
        return puertos or ["Sin puertos detectados"]

    def actualizar_lista_puertos(self, automatico=False):
        puertos = self.obtener_puertos()
        anterior = self.combo_puertos.get()
        self.combo_puertos["values"] = puertos
        if anterior in puertos and anterior not in ("Sin puertos", "Sin puertos detectados"):
            self.combo_puertos.set(anterior)
        elif puertos and puertos[0] != "Sin puertos detectados":
            self.combo_puertos.set(puertos[0])
        else:
            self.combo_puertos.set("Sin puertos")
        if not automatico:
            self._set_status(f"Puertos actualizados: {', '.join(puertos)}")

    def _programar_actualizacion_puertos(self):
        self._actualizador_puertos = self.after(3000, self._actualizar_puertos_automaticamente)

    def _actualizar_puertos_automaticamente(self):
        if not self.winfo_exists():
            return
        self.actualizar_lista_puertos(automatico=True)
        self._programar_actualizacion_puertos()

    def _on_placa_cambiada(self, _event=None):
        nombre = self.combo_placas.get()
        self.baud_monitor = baud_de(nombre)
        self._set_status(f"Placa: {nombre} · baud recomendado {self.baud_monitor}")
        self.guardar_preferencias(silencioso=True)

    def seleccionar_recursos_web(self):
        ruta = filedialog.askdirectory(title="Carpeta de recursos web")
        if not ruta:
            self._set_status("Selección de carpeta web cancelada")
            return
        carpeta = Path(ruta)
        archivos_web = sorted(
            str(archivo.relative_to(carpeta))
            for archivo in carpeta.rglob("*")
            if archivo.is_file()
        )
        if not any(archivo.lower().endswith(".html") for archivo in archivos_web):
            messagebox.showwarning(
                "Carpeta web",
                "La carpeta no contiene archivos HTML. Se enlazará, pero crea un index.html.",
            )
        self.recursos_web = ruta
        self.guardar_preferencias(silencioso=True)
        self._set_status(f"Recursos web seleccionados: {ruta}")
        self.consola.info(f"Carpeta web enlazada: {ruta}")
        self.consola.info(f"Archivos detectados: {len(archivos_web)}")
        self.consola.info("LittleFS/SPIFFS requiere una herramienta de filesystem compatible con la placa.")

    def crear_archivos_web(self):
        padre = filedialog.askdirectory(title="Elige la carpeta donde crear el sitio web")
        if not padre:
            self._set_status("Creación de archivos web cancelada")
            return
        nombre = simpledialog.askstring(
            "Nuevo sitio web", "Nombre de la carpeta del sitio:", initialvalue="web",
            parent=self,
        )
        if not nombre:
            self._set_status("Creación de archivos web cancelada")
            return
        nombre = "".join(caracter for caracter in nombre.strip() if caracter.isalnum() or caracter in "-_ ").strip()
        if not nombre:
            messagebox.showerror("Nombre no válido", "Usa letras, números, espacios, guiones o guiones bajos.")
            return
        carpeta = Path(padre) / nombre
        carpeta.mkdir(parents=True, exist_ok=True)
        archivos = {
            "index.html": """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mi ESP32</title>
  <link rel="stylesheet" href="/estilos.css">
</head>
<body>
  <main>
    <h1>Hola desde mi ESP32</h1>
    <button id="probar">Probar JavaScript</button>
    <p id="estado">Listo</p>
  </main>
  <script src="/app.js"></script>
</body>
</html>
""",
            "estilos.css": """body {
  margin: 0;
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #101820;
  color: #40d47e;
  font-family: sans-serif;
  text-align: center;
}

button { padding: 0.7rem 1rem; cursor: pointer; }
""",
            "app.js": """document.querySelector('#probar').addEventListener('click', () => {
  document.querySelector('#estado').textContent = 'JavaScript funcionando';
});
""",
        }
        creados = []
        for nombre, contenido in archivos.items():
            destino = carpeta / nombre
            if destino.exists() and not messagebox.askyesno(
                "Archivo existente", f"{destino.name} ya existe. ¿Reemplazarlo?",
            ):
                continue
            destino.write_text(contenido, encoding="utf-8")
            creados.append(destino.name)
        self.recursos_web = str(carpeta)
        self.guardar_preferencias(silencioso=True)
        self._set_status(f"Archivos web creados: {', '.join(creados)}")
        self.consola.info(f"Carpeta web enlazada: {carpeta}")
        self.consola.info(f"Estructura creada: {len(creados)} archivo(s)")
        messagebox.showinfo(
            "Sitio web creado",
            f"Se creó la carpeta:\n{carpeta}\n\nArchivos: {', '.join(creados)}",
        )
        if os.name == "nt":
            try:
                os.startfile(str(carpeta))
            except OSError:
                pass

    def crear_nueva_pestana(self, nombre_archivo=None):
        if not nombre_archivo:
            nombre_archivo = f"nuevo_codigo{EXT_PROYECTO}"
        tab_frame = tk.Frame(self.notebook, bg=self.bg_principal)
        self.notebook.add(tab_frame, text=f"  {nombre_archivo}  ")

        sub_paned = tk.PanedWindow(
            tab_frame, orient=tk.HORIZONTAL, bg=self.bg_principal, sashwidth=4, bd=0,
        )
        sub_paned.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        frame_izq = tk.Frame(sub_paned, bg=self.bg_principal)
        sub_paned.add(frame_izq, width=620)
        
        lbl_ed = tk.Label(
            frame_izq, text=f"Español ({EXT_PROYECTO})", bg=self.bg_principal,
            fg=self.fg_muted, font=("Segoe UI", 9, "bold"),
        )
        lbl_ed.pack(anchor="w", pady=(0, 4))

        texto_entrada = LineNumberedText(
            frame_izq, bg=self.bg_editor, fg=self.fg_editor,
            insertbg="#410000", font=self.fuente_editor, border_color=self.borde,
        )
        texto_entrada.pack(fill=tk.BOTH, expand=True)
        
        codigo_inicial = (
            "variable entero = valor\n"
            "velocidad serie 115200\n"
            "\n"
            "al iniciar\n"
            "configurar pin 13, salida\n"
            "\n"
            "repetir siempre\n"
            "leer pin analógico A0 en valor\n"
            "escribe el valor analógico es , valor\n"
            "hacer que pin 13, encendido\n"
            "esperar 200\n"
            "hacer que pin 13, apagado\n"
            "esperar 800\n"
        )
        texto_entrada.insert(tk.END, codigo_inicial)
        texto_entrada.bind("<KeyRelease>", lambda e: self.manejar_tecleo(e, texto_entrada))
        texto_entrada.bind("<KeyRelease>", lambda e: self._actualizar_status(), add="+")

        frame_der = tk.Frame(sub_paned, bg=self.bg_principal)
        sub_paned.add(frame_der, width=620)
        
        lbl_sal = tk.Label(
            frame_der, text="C++ generado", bg=self.bg_principal,
            fg=self.fg_muted, font=("Segoe UI", 9, "bold"),
        )
        lbl_sal.pack(anchor="w", pady=(0, 4))

        texto_salida = scrolledtext.ScrolledText(
            frame_der, wrap=tk.NONE, bg=self.bg_editor, fg="#00C410",
            font=self.fuente_editor, bd=0, highlightthickness=0,
        )
        texto_salida.pack(fill=tk.BOTH, expand=True)
        texto_salida.config(state=tk.DISABLED)

        tab_frame.texto_entrada = texto_entrada
        tab_frame.texto_salida = texto_salida
        tab_frame.sub_paned = sub_paned
        tab_frame.frame_der = frame_der
        tab_frame.frame_izq = frame_izq
        tab_frame.lbl_ed = lbl_ed
        tab_frame.lbl_sal = lbl_sal
        tab_frame.nombre = nombre_archivo
        tab_frame.cpp_visible = True

        self.notebook.select(tab_frame)
        self.after(100, self.traducir_pestana_activa)
        return tab_frame

    def _tab_actual(self):
        sel = self.notebook.select()
        if not sel:
            return None
        return self.notebook.nametowidget(sel)

    def cerrar_pestana_activa(self):
        if self.notebook.index("end") <= 1:
            messagebox.showwarning("Aviso", "Debe quedar al menos una pestaña abierta.")
            return
        current = self.notebook.select()
        if current:
            self.rutas_archivo.pop(current, None)
            self.notebook.forget(current)

    def mostrar_menu_pestana(self, event):
        try:
            idx = self.notebook.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return
        menu = tk.Menu(self, tearoff=0, bg=self.bg_secundario, fg=self.fg_texto)
        menu.add_command(
            label="Cerrar pestaña",
            command=lambda: self._cerrar_por_indice(idx),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _cerrar_por_indice(self, idx):
        if self.notebook.index("end") <= 1:
            messagebox.showwarning("Aviso", "Debe quedar al menos una pestaña abierta.")
            return
        tab_id = self.notebook.tabs()[idx]
        self.rutas_archivo.pop(tab_id, None)
        self.notebook.forget(idx)

    # ── Archivo ──────────────────────────────────────────────
    def nuevo_archivo(self):
        self.crear_nueva_pestana(f"archivo_nuevo{EXT_PROYECTO}")

    def abrir_archivo(self):
        ruta = filedialog.askopenfilename(
            defaultextension=EXT_PROYECTO,
            filetypes=FILTROS_ARCHIVO,
        )
        if not ruta:
            return
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        tab = self.crear_nueva_pestana(os.path.basename(ruta))
        tab.texto_entrada.delete("1.0", tk.END)
        tab.texto_entrada.insert(tk.END, contenido)
        self.rutas_archivo[self.notebook.select()] = ruta
        self.traducir_pestana_activa()

    def guardar_archivo(self):
        tab = self._tab_actual()
        if not tab:
            return
        tab_id = self.notebook.select()
        ruta = self.rutas_archivo.get(tab_id)
        if ruta:
            self._escribir_archivo(tab, ruta)
        else:
            self.guardar_archivo_como()

    def guardar_archivo_como(self):
        tab = self._tab_actual()
        if not tab:
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=EXT_PROYECTO,
            filetypes=FILTROS_ARCHIVO,
        )
        if ruta:
            if not ruta.lower().endswith(EXT_PROYECTO) and not ruta.lower().endswith(".es"):
                ruta += EXT_PROYECTO
            self._escribir_archivo(tab, ruta)

    def abrir_ejemplo(self, nombre: str):
        codigo = codigo_ejemplo(nombre)
        if not codigo:
            return
        seguro = "".join(c if c.isalnum() or c in "-_" else "_" for c in nombre.lower())
        tab = self.crear_nueva_pestana(f"{seguro}{EXT_PROYECTO}")
        tab.texto_entrada.delete("1.0", tk.END)
        tab.texto_entrada.insert(tk.END, codigo.strip() + "\n")
        self.traducir_pestana_activa()
        self._set_status(f"Ejemplo cargado: {nombre}")

    def _escribir_archivo(self, tab, ruta):
        contenido = tab.texto_entrada.get("1.0", tk.END)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        nombre = os.path.basename(ruta)
        self.notebook.tab(tab, text=f"  {nombre}  ")
        tab.nombre = nombre
        self.rutas_archivo[self.notebook.select()] = ruta
        self._set_status(f"Guardado: {ruta}")

    def exportar_cpp(self):
        resultado = self.traducir_pestana_activa()
        if not resultado:
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".ino",
            filetypes=[("Sketch Arduino", "*.ino"), ("C++", "*.cpp")],
        )
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(resultado)
            self._set_status(f"C++ exportado: {ruta}")

    # ── Edición ──────────────────────────────────────────────
    def deshacer(self):
        tab = self._tab_actual()
        if tab:
            tab.texto_entrada.edit_undo()

    def rehacer(self):
        tab = self._tab_actual()
        if tab:
            tab.texto_entrada.edit_redo()

    def buscar_texto(self):
        tab = self._tab_actual()
        if not tab:
            return
        termino = simpledialog.askstring("Buscar", "Texto a buscar:")
        if not termino:
            return
        editor = tab.texto_entrada
        editor.tag_remove("busca", "1.0", tk.END)
        editor.tag_config("busca", background="#9E6A03", foreground="#FFFFFF")
        start = "1.0"
        encontrados = 0
        while True:
            pos = editor.text.search(termino, start, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(termino)}c"
            editor.tag_add("busca", pos, end)
            start = end
            encontrados += 1
        self._set_status(f"Buscar: {encontrados} coincidencia(s)")

    def reemplazar_texto(self):
        tab = self._tab_actual()
        if not tab:
            return
        buscar = simpledialog.askstring("Reemplazar", "Buscar:")
        if buscar is None:
            return
        nuevo = simpledialog.askstring("Reemplazar", "Reemplazar por:")
        if nuevo is None:
            return
        contenido = tab.texto_entrada.get("1.0", tk.END)
        n = contenido.count(buscar)
        reemplazado = contenido.replace(buscar, nuevo)
        tab.texto_entrada.delete("1.0", tk.END)
        tab.texto_entrada.insert("1.0", reemplazado)
        self._set_status(f"Reemplazadas {n} ocurrencia(s)")

    def cambiar_tam_fuente(self, delta):
        self.tam_fuente = max(8, min(28, self.tam_fuente + delta))
        self.fuente_editor = self._fuente_mono(self.tam_fuente)
        for tab_id in self.notebook.tabs():
            tab = self.notebook.nametowidget(tab_id)
            tab.texto_entrada.config_editor(font=self.fuente_editor)
            tab.texto_salida.config(font=self.fuente_editor)
        self._set_status(f"Tamaño de fuente: {self.tam_fuente}")
        self.guardar_preferencias(silencioso=True)

    # ── Temas ────────────────────────────────────────────────
    def tema_por_defecto(self):
        self.bg_principal = "#0D1117"
        self.bg_secundario = "#161B22"
        self.bg_editor = "#0D1117"
        self.bg_elevado = "#21262D"
        self.fg_texto = "#E6EDF3"
        self.fg_muted = "#8B949E"
        self.fg_editor = "#E6EDF3"
        self.acento = "#3FB950"
        self.acento_2 = "#58A6FF"
        self.aplicar_cambios_tema_visual()
        self.guardar_preferencias(silencioso=True)

    def tema_claro(self):
        self.bg_principal = "#F6F8FA"
        self.bg_secundario = "#FFFFFF"
        self.bg_editor = "#FFFFFF"
        self.bg_elevado = "#EAEEF2"
        self.fg_texto = "#1F2328"
        self.fg_muted = "#656D76"
        self.fg_editor = "#1F2328"
        self.acento = "#1A7F37"
        self.acento_2 = "#0969DA"
        self.aplicar_cambios_tema_visual()
        self.guardar_preferencias(silencioso=True)

    def tema_oceano(self):
        self.bg_principal = "#0A1628"
        self.bg_secundario = "#12233A"
        self.bg_editor = "#07101C"
        self.bg_elevado = "#1A3352"
        self.fg_texto = "#D7E3F4"
        self.fg_muted = "#7A93B0"
        self.fg_editor = "#D7E3F4"
        self.acento = "#3DDC97"
        self.acento_2 = "#4EA8DE"
        self.aplicar_cambios_tema_visual()
        self.guardar_preferencias(silencioso=True)

    def personalizar_header(self):
        win = tk.Toplevel(self)
        win.title("Personalizar barra superior")
        win.geometry("420x260")
        win.configure(bg=self.bg_principal)
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Título", bg=self.bg_principal, fg=self.fg_texto).pack(anchor="w", padx=16, pady=(16, 2))
        entry_titulo = tk.Entry(win, bg=self.bg_editor, fg=self.fg_texto, insertbackground="white")
        entry_titulo.insert(0, self.header_titulo)
        entry_titulo.pack(fill=tk.X, padx=16)

        tk.Label(win, text="Subtítulo", bg=self.bg_principal, fg=self.fg_texto).pack(anchor="w", padx=16, pady=(12, 2))
        entry_sub = tk.Entry(win, bg=self.bg_editor, fg=self.fg_texto, insertbackground="white")
        entry_sub.insert(0, self.header_subtitulo)
        entry_sub.pack(fill=tk.X, padx=16)

        color_var = {"val": self.header_color}
        texto_var = {"val": self.header_texto}
        borde_var = {"val": self.borde}

        def elegir_color():
            c = colorchooser.askcolor(title="Color de la barra superior")[1]
            if c:
                color_var["val"] = c

        def reset_color():
            color_var["val"] = None

        def elegir_texto():
            c = colorchooser.askcolor(title="Color del texto superior")[1]
            if c:
                texto_var["val"] = c

        def elegir_borde():
            c = colorchooser.askcolor(title="Color de bordes")[1]
            if c:
                borde_var["val"] = c

        fila = tk.Frame(win, bg=self.bg_principal)
        fila.pack(fill=tk.X, padx=16, pady=14)
        self._btn(fila, "Color de barra...", self.bg_elevado, elegir_color).pack(side=tk.LEFT)
        self._btn(fila, "Usar color del tema", self.bg_elevado, reset_color).pack(side=tk.LEFT, padx=8)
        self._btn(fila, "Texto...", self.bg_elevado, elegir_texto).pack(side=tk.LEFT, padx=8)
        self._btn(fila, "Bordes...", self.bg_elevado, elegir_borde).pack(side=tk.LEFT)

        def aplicar():
            self.header_titulo = entry_titulo.get().strip() or "Integrated"
            self.header_subtitulo = entry_sub.get().strip() or "IDE en español"
            self.header_color = color_var["val"]
            self.header_texto = texto_var["val"]
            self.borde = borde_var["val"]
            self.aplicar_cambios_tema_visual()
            self.guardar_preferencias(silencioso=True)
            win.destroy()

        self._btn(win, "Aplicar y guardar", "#238636", aplicar).pack(pady=12)

    def cambiar_color_fondo_general(self):
        color = colorchooser.askcolor(title="Color base")[1]
        if color:
            self.bg_principal = color
            self.bg_secundario = color
            self.bg_editor = self.ajustar_tono_oscuro(color, 0.7)
            self.bg_elevado = self.ajustar_tono_oscuro(color, 1.15)
            self.aplicar_cambios_tema_visual()
            self.guardar_preferencias(silencioso=True)

    def ajustar_tono_oscuro(self, hex_color, factor):
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        out = tuple(max(0, min(255, int(c * factor))) for c in rgb)
        return f"#{out[0]:02x}{out[1]:02x}{out[2]:02x}"

    def aplicar_cambios_tema_visual(self):
        self.configure(bg=self.bg_principal)
        header_bg = self.header_color or self.bg_secundario
        self.header_frame.config(bg=header_bg)
        self.menu_bar_frame.config(bg=self.bg_secundario)
        for boton in self.menu_bar_buttons:
            boton.config(bg=self.bg_secundario, fg=self.fg_texto, activebackground=self.bg_elevado)
        self.label_title.config(bg=header_bg, fg=self.header_texto, text=self.header_titulo)
        self.label_subtitle.config(bg=header_bg, fg=self.fg_muted, text=self.header_subtitulo)
        self.lbl_placa.config(bg=header_bg, fg=self.fg_muted)
        self.lbl_puerto.config(bg=header_bg, fg=self.fg_muted)
        self._aplicar_color_barra_nativa()
        if hasattr(self, "ventana_serial"):
            self._aplicar_color_barra_nativa(self.ventana_serial)
        if hasattr(self, "toolbar"):
            self.toolbar.config(bg=self.bg_principal)
        if hasattr(self, "status_bar"):
            self.status_bar.config(bg=self.bg_secundario, fg=self.fg_muted)
        self.main_paned.config(bg=self.bg_principal)
        self.frame_editores.config(bg=self.bg_principal)
        self.frame_inferior_consola.config(bg=self.bg_principal)
        self.lbl_consola.config(bg=self.bg_principal, fg=self.fg_muted)
        self.consola_widget.config(bg=self.bg_editor, fg=self.acento, highlightbackground=self.bg_elevado)
        self.consola_widget.tag_config("info", foreground=self.acento_2)
        self.consola_widget.tag_config("ok", foreground=self.acento)
        self.consola_widget.tag_config("error", foreground=self.peligro)

        for menu in (
            self.menubar, self.menu_archivo, self.menu_editar, self.menu_proyecto,
            self.menu_ejemplos, self.menu_estilo, self.menu_vista, self.menu_ayuda,
        ):
            menu.config(bg=self.bg_secundario, fg=self.fg_texto, activebackground=self.bg_elevado)

        for tab_id in self.notebook.tabs():
            tab = self.notebook.nametowidget(tab_id)
            tab.config(bg=self.bg_principal)
            tab.sub_paned.config(bg=self.bg_principal)
            tab.frame_izq.config(bg=self.bg_principal)
            tab.frame_der.config(bg=self.bg_principal)
            tab.lbl_ed.config(bg=self.bg_principal, fg=self.fg_muted)
            tab.lbl_sal.config(bg=self.bg_principal, fg=self.fg_muted)
            tab.texto_entrada.config_editor(
                bg=self.bg_editor, fg=self.fg_editor, highlightbackground=self.borde,
            )
            tab.texto_salida.config(bg=self.bg_editor)

        self.listbox_sugerencias.config(bg=self.bg_elevado, fg=self.fg_texto, selectbackground=self.acento_2)
        self.actualizar_estilos_visuales()

    def cambiar_color_letra(self):
        color = colorchooser.askcolor(title="Color de texto")[1]
        if color:
            self.fg_editor = color
            for tab_id in self.notebook.tabs():
                tab = self.notebook.nametowidget(tab_id)
                tab.texto_entrada.config_editor(fg=color)
            self.guardar_preferencias(silencioso=True)

    def guardar_preferencias(self, silencioso: bool = False):
        data = {
            "bg_principal": self.bg_principal,
            "bg_secundario": self.bg_secundario,
            "bg_editor": self.bg_editor,
            "bg_elevado": self.bg_elevado,
            "fg_texto": self.fg_texto,
            "fg_muted": self.fg_muted,
            "fg_editor": self.fg_editor,
            "acento": self.acento,
            "acento_2": self.acento_2,
            "peligro": self.peligro,
            "borde": self.borde,
            "header_texto": self.header_texto,
            "header_titulo": self.header_titulo,
            "header_subtitulo": self.header_subtitulo,
            "header_color": self.header_color,
            "tam_fuente": self.tam_fuente,
            "placa": self.combo_placas.get() if hasattr(self, "combo_placas") else self.placa_inicial,
            "baud_monitor": self.baud_monitor,
            "geometry": self.geometry(),
            "recursos_web": self.recursos_web,
        }
        app_config.guardar(data)
        if not silencioso:
            messagebox.showinfo("Preferencias", "Preferencias guardadas.")
            self._set_status("Preferencias guardadas")

    def alternar_panel_cpp(self):
        tab = self._tab_actual()
        if not tab:
            return
        visible = getattr(tab, "cpp_visible", True)
        if visible:
            tab.sub_paned.remove(tab.frame_der)
            tab.cpp_visible = False
        else:
            tab.sub_paned.add(tab.frame_der)
            tab.cpp_visible = True

    # ── Traducción / Build ───────────────────────────────────
    def traducir_pestana_activa(self, _event=None):
        tab = self._tab_actual()
        if not tab:
            return ""
        codigo = tab.texto_entrada.get("1.0", tk.END)
        baud = baud_de(self.combo_placas.get())
        recursos = Path(self.recursos_web) if self.recursos_web else build.descubrir_recursos_web()
        resultado = traducir_codigo(
            codigo,
            baud_default=baud,
            fqbn=fqbn_de(self.combo_placas.get()),
            recursos_web=recursos,
        )
        if recursos and recursos.is_dir():
            archivos = sum(1 for archivo in recursos.rglob("*") if archivo.is_file())
            self.consola.info(f"Recursos web enlazados al traducir: {archivos} archivo(s) desde {recursos}")
        tab.texto_salida.config(state=tk.NORMAL)
        tab.texto_salida.delete("1.0", tk.END)
        tab.texto_salida.insert(tk.END, resultado)
        tab.texto_salida.config(state=tk.DISABLED)
        self._set_status("Traducción actualizada")
        return resultado

    def _puerto_valido(self):
        puerto = self.combo_puertos.get()
        if not puerto or puerto in ("Sin puertos detectados", "Sin puertos"):
            messagebox.showerror("Error", "No hay ningún puerto COM seleccionado.")
            return None
        return puerto

    def _fqbn_actual(self):
        nombre = self.combo_placas.get()
        fqbn = fqbn_de(nombre)
        if not fqbn:
            messagebox.showwarning("Atención", "Selecciona una placa válida.")
            return None, None
        return nombre, fqbn

    def _set_busy(self, busy: bool):
        self._ocupado = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.btn_compilar.config(state=state)
        self.btn_cargar.config(state=state)
        if busy:
            self.barra_progreso.config(mode="indeterminate", value=0)
            self.barra_progreso.start(12)
        else:
            self.barra_progreso.stop()
            self.barra_progreso.config(mode="determinate", value=0)

    def _evento_proceso(self, evento, fase):
        """Actualiza estado y porcentaje sin inventar progreso de compilación."""
        tipo = evento.get("tipo")
        if tipo == "progreso" and fase == "Subiendo":
            porcentaje = evento.get("porcentaje")
            if porcentaje is not None:
                self.barra_progreso.stop()
                self.barra_progreso.config(mode="determinate", maximum=100, value=porcentaje)
                self._set_status(f"{fase} · {porcentaje}%")
            return
        if tipo == "timeout":
            segundos = int(evento.get("segundos", 0))
            self.consola.error(f"Tiempo agotado durante {fase.lower()} ({segundos} s).")
            self._set_status(f"{fase} cancelado por tiempo agotado")
            return
        if tipo == "iniciado":
            self._set_status(fase)

    def _ui(self, fn):
        """Ejecuta fn en el hilo de la UI."""
        self.after(0, fn)

    def solo_compilar(self):
        if self._ocupado:
            return
        nombre, fqbn = self._fqbn_actual()
        if not fqbn:
            return
        backend = build.backend_para(fqbn)
        if backend == "arduino-cli" and not build.cli_disponible():
            messagebox.showerror("Error", "No hay un backend de compilación disponible para esta placa.")
            return
        codigo = self.traducir_pestana_activa()
        if "// AVISO:" in codigo:
            lineas_aviso = [l.replace("// AVISO: ", "").strip() for l in codigo.splitlines() if l.startswith("// AVISO:")]
            self.consola.error("No se puede compilar debido a los siguientes avisos:")
            for av in lineas_aviso:
                self.consola.error(f"  • {av}")
            messagebox.showerror("Código con avisos", "Revisa los detalles señalados en la consola antes de compilar.")
            return
        recursos = Path(self.recursos_web) if self.recursos_web else build.descubrir_recursos_web()
        sketch_dir = build.preparar_sketch(codigo, fqbn, recursos)
        cmd = build.comando_compilar(sketch_dir, fqbn)

        self.consola.limpiar()
        self.consola.info(f"Compilando [{nombre}] con {backend} (caché: {sketch_dir.name})…")
        self.consola.info("Las recompilaciones reutilizan la caché del backend.")
        self._set_busy(True)

        def worker():
            try:
                code = build.ejecutar_comando(
                    cmd,
                    lambda l: self.consola.escribir(l),
                    timeout=900,
                    on_event=lambda e: self._ui(lambda e=e: self._evento_proceso(e, "Compilando")),
                )
                if code == 0:
                    self._ui(lambda: (
                        self.consola.exito("Compilación correcta."),
                        self._set_busy(False),
                        self._set_status("Compilación OK"),
                    ))
                else:
                    self._ui(lambda: (
                        self.consola.error("Falló la compilación."),
                        self._set_busy(False),
                        messagebox.showerror("Error de compilación", "Revisa la consola inferior."),
                    ))
            except Exception as e:
                self._ui(lambda: (
                    self._set_busy(False),
                    messagebox.showerror("Excepción", str(e)),
                ))

        threading.Thread(target=worker, daemon=True).start()

    def cargar_a_placa(self):
        if self._ocupado:
            return
        puerto = self._puerto_valido()
        if not puerto:
            return
        nombre, fqbn = self._fqbn_actual()
        if not fqbn:
            return
        backend = build.backend_para(fqbn)
        if backend == "arduino-cli" and not build.cli_disponible():
            messagebox.showerror("Error", "No hay un backend de carga disponible para esta placa.")
            return

        # Cerrar monitor si usa el mismo puerto
        if self.monitor_abierto:
            self.cerrar_monitor_serie()

        codigo = self.traducir_pestana_activa()
        if "// AVISO:" in codigo:
            lineas_aviso = [l.replace("// AVISO: ", "").strip() for l in codigo.splitlines() if l.startswith("// AVISO:")]
            self.consola.error("No se puede cargar debido a los siguientes avisos:")
            for av in lineas_aviso:
                self.consola.error(f"  • {av}")
            messagebox.showerror("Código con avisos", "Revisa los detalles señalados en la consola antes de cargar.")
            return
        recursos = Path(self.recursos_web) if self.recursos_web else build.descubrir_recursos_web()
        sketch_dir = build.preparar_sketch(codigo, fqbn, recursos)
        cmd_c = build.comando_compilar(sketch_dir, fqbn)
        cmd_u = build.comando_subir(sketch_dir, fqbn, puerto)

        self.consola.limpiar()
        self.consola.info(f"Compilar + cargar [{nombre}] con {backend} → {puerto}")
        self.consola.info(f"Caché de build: {sketch_dir}")
        if recursos and recursos.is_dir():
            self.consola.info("Recursos web copiados a data/. El filesystem debe subirse por separado.")
        self._set_busy(True)

        def worker():
            try:
                code = build.ejecutar_comando(
                    cmd_c,
                    lambda l: self.consola.escribir(l),
                    timeout=900,
                    on_event=lambda e: self._ui(lambda e=e: self._evento_proceso(e, "Compilando")),
                )
                if code != 0:
                    self._ui(lambda: (
                        self.consola.error("Compilación fallida."),
                        self._set_busy(False),
                        messagebox.showerror("Error de compilación", "Revisa la consola."),
                    ))
                    return
                self.consola.exito("Compilación OK. Subiendo…")
                self._ui(lambda: self._set_status("Subiendo"))
                code2 = build.ejecutar_comando(
                    cmd_u,
                    lambda l: self.consola.escribir(l),
                    timeout=180,
                    on_event=lambda e: self._ui(lambda e=e: self._evento_proceso(e, "Subiendo")),
                )
                if code2 == 0:
                    self._ui(lambda: (
                        self.consola.exito(f"Código cargado en {nombre}."),
                        self.consola.info("La placa se reinició; esperando que vuelva a aparecer el USB..."),
                        self._set_busy(False),
                        self.after(2500, lambda: self.actualizar_lista_puertos()),
                        messagebox.showinfo("Éxito", f"Código cargado en {nombre}."),
                    ))
                else:
                    self._ui(lambda: (
                        self.consola.error("Falló la subida."),
                        self._set_busy(False),
                        messagebox.showerror(
                            "Error de carga",
                            "Revisa el puerto o cierra otros monitores serie.",
                        ),
                    ))
            except Exception as e:
                self._ui(lambda: (
                    self._set_busy(False),
                    messagebox.showerror("Excepción", str(e)),
                ))

        threading.Thread(target=worker, daemon=True).start()

    def limpiar_cache_builds(self):
        n = build.limpiar_cache()
        self.consola.info(f"Caché limpiada ({n} carpetas).")
        messagebox.showinfo("Caché", f"Se eliminaron {n} builds en caché.")

    def instalar_core_actual(self):
        if self._ocupado:
            return
        if not build.cli_disponible():
            messagebox.showerror("Error", "No se encontró arduino-cli.exe.")
            return
        nombre = self.combo_placas.get()
        core = core_de(nombre)
        if not core:
            return
        self.consola.limpiar()
        self.consola.info(f"Instalando core {core} (puede tardar)…")
        self._set_busy(True)

        def worker():
            try:
                code = build.instalar_core(core, lambda l: self.consola.escribir(l), CORE_INDEX_URLS)
                self._ui(lambda: (
                    self.consola.exito("Core instalado.") if code == 0 else self.consola.error("Falló la instalación."),
                    self._set_busy(False),
                ))
            except Exception as e:
                self._ui(lambda: (self._set_busy(False), messagebox.showerror("Error", str(e))))

        threading.Thread(target=worker, daemon=True).start()

    # ── Monitor serie ────────────────────────────────────────
    def crear_ventana_serial(self):
        self.ventana_serial = tk.Toplevel(self)
        self.ventana_serial.title("Monitor serie — Integrated")
        self.ventana_serial.geometry("640x420")
        self.ventana_serial.configure(bg=self.bg_principal)
        self._aplicar_color_barra_nativa(self.ventana_serial)
        self.ventana_serial.protocol("WM_DELETE_WINDOW", self.cerrar_monitor_serie)
        self.ventana_serial.withdraw()

        top = tk.Frame(self.ventana_serial, bg=self.bg_secundario)
        top.pack(fill=tk.X)
        tk.Label(top, text="Baud", bg=self.bg_secundario, fg=self.fg_muted, font=("Segoe UI", 9)).pack(
            side=tk.LEFT, padx=8, pady=6,
        )
        self.combo_baud = ttk.Combobox(
            top, values=["9600", "19200", "38400", "57600", "115200", "230400", "460800"],
            width=10, state="readonly",
        )
        self.combo_baud.set(str(self.baud_monitor))
        self.combo_baud.pack(side=tk.LEFT, padx=4)
        self._btn(top, "Limpiar", self.bg_elevado, self._limpiar_serial).pack(side=tk.RIGHT, padx=8, pady=4)

        self.texto_serial_output = scrolledtext.ScrolledText(
            self.ventana_serial, wrap=tk.WORD, bg=self.bg_editor, fg=self.fg_texto,
            font=("Consolas", 10), bd=0,
        )
        self.texto_serial_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        frame_input = tk.Frame(self.ventana_serial, bg=self.bg_secundario)
        frame_input.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.entry_serial_input = tk.Entry(
            frame_input, bg=self.bg_editor, fg=self.fg_texto, font=("Consolas", 10),
            insertbackground="white", bd=0,
        )
        self.entry_serial_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, ipady=5)
        self.entry_serial_input.bind("<Return>", lambda e: self.enviar_comando_serial())
        self._btn(frame_input, "Enviar", self.acento_2, self.enviar_comando_serial).pack(
            side=tk.RIGHT, padx=6, pady=6,
        )

    def _limpiar_serial(self):
        self.texto_serial_output.delete("1.0", tk.END)

    def abrir_monitor_serie(self):
        puerto = self._puerto_valido()
        if not puerto:
            return
        if self.monitor_abierto and self.serial_activo and self.serial_activo.is_open:
            self.ventana_serial.deiconify()
            self.ventana_serial.lift()
            return
        try:
            baud = int(self.combo_baud.get() or self.baud_monitor)
            self.serial_activo = serial.Serial(puerto, baud, timeout=0.2)
            self.monitor_abierto = True
            self.ventana_serial.deiconify()
            self.ventana_serial.lift()
            self._set_status(f"Monitor serie en {puerto} @ {baud}")
            threading.Thread(target=self._leer_serial_loop, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir {puerto}:\n{e}")

    def _leer_serial_loop(self):
        while self.monitor_abierto and self.serial_activo and self.serial_activo.is_open:
            try:
                if self.serial_activo.in_waiting > 0:
                    data = self.serial_activo.read(self.serial_activo.in_waiting)
                    texto = data.decode("utf-8", errors="ignore")
                    self.after(0, lambda t=texto: self._append_serial(t))
                else:
                    # Pequeña pausa para no consumir CPU cuando no llegan datos.
                    import time
                    time.sleep(0.05)
            except Exception:
                break

    def _append_serial(self, texto):
        try:
            self.texto_serial_output.insert(tk.END, texto)
            self.texto_serial_output.see(tk.END)
        except tk.TclError:
            pass

    def cerrar_monitor_serie(self):
        self.monitor_abierto = False
        if self.serial_activo and self.serial_activo.is_open:
            try:
                self.serial_activo.close()
            except Exception:
                pass
        self.serial_activo = None
        self.ventana_serial.withdraw()
        self._set_status("Monitor serie cerrado")

    def enviar_comando_serial(self):
        if self.serial_activo and self.serial_activo.is_open:
            cmd = self.entry_serial_input.get() + "\n"
            try:
                self.serial_activo.write(cmd.encode("utf-8"))
                self.entry_serial_input.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ── Autocompletado ───────────────────────────────────────
    def manejar_tecleo(self, event, texto_entrada):
        if event.keysym in ("Up", "Down", "Return", "Tab", "Shift_L", "Shift_R", "Escape"):
            if event.keysym == "Down" and self.listbox_sugerencias.winfo_ismapped():
                self.listbox_sugerencias.focus_set()
                self.listbox_sugerencias.selection_set(0)
            if event.keysym == "Escape":
                self.listbox_sugerencias.place_forget()
                self._sugerencia_rango = None
            return "break"

        cursor_pos = texto_entrada.index(tk.INSERT)
        linea_inicio = f"{cursor_pos.split('.')[0]}.0"
        texto_linea = texto_entrada.get(linea_inicio, cursor_pos).strip().lower()

        if len(texto_linea) >= 2:
            coincidencias = [s for s in SUGERENCIAS if s.lower().startswith(texto_linea)]
            if coincidencias:
                self.listbox_sugerencias.delete(0, tk.END)
                for c in coincidencias[:12]:
                    self.listbox_sugerencias.insert(tk.END, c)
                self._sugerencia_rango = (linea_inicio, cursor_pos)
                bbox = texto_entrada.bbox(cursor_pos)
                if bbox:
                    x, y, _, cy = bbox
                    # Posicionar relativo a la ventana
                    try:
                        abs_x = texto_entrada.text.winfo_rootx() - self.winfo_rootx() + x + 40
                        abs_y = texto_entrada.text.winfo_rooty() - self.winfo_rooty() + y + cy + 2
                        self.listbox_sugerencias.place(x=abs_x, y=abs_y, width=340, height=110)
                    except tk.TclError:
                        pass
                return
        self.listbox_sugerencias.place_forget()

    def insertar_sugerencia(self, _event=None):
        selection = self.listbox_sugerencias.curselection()
        if not selection:
            return
        sugerencia = self.listbox_sugerencias.get(selection[0])
        tab = self._tab_actual()
        if not tab:
            return
        editor = tab.texto_entrada
        rango = self._sugerencia_rango
        if rango is None:
            cursor_pos = editor.index(tk.INSERT)
            linea_num = cursor_pos.split(".")[0]
            rango = (f"{linea_num}.0", cursor_pos)
        linea_inicio, cursor_pos = rango
        editor.delete(linea_inicio, cursor_pos)
        editor.insert(linea_inicio, sugerencia)
        self.listbox_sugerencias.place_forget()
        self._sugerencia_rango = None
        editor.focus_set()

    # ── Ayuda / status ───────────────────────────────────────
    def limpiar_consola(self):
        self.consola.limpiar()

    def mostrar_ayuda(self):
        win = tk.Toplevel(self)
        win.title("Referencia del lenguaje")
        win.geometry("560x520")
        win.configure(bg=self.bg_principal)
        txt = scrolledtext.ScrolledText(
            win, wrap=tk.WORD, bg=self.bg_editor, fg=self.fg_texto,
            font=("Consolas", 10), bd=0,
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        txt.insert(tk.END, REFERENCIA_LENGUAJE)
        txt.config(state=tk.DISABLED)

    def mostrar_guia_inicio(self):
        win = tk.Toplevel(self)
        win.title("Guía para comenzar")
        win.geometry("680x560")
        win.configure(bg=self.bg_principal)
        texto = scrolledtext.ScrolledText(
            win, wrap=tk.WORD, bg=self.bg_editor, fg=self.fg_texto,
            font=("Segoe UI", 10), bd=0,
        )
        texto.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        texto.insert(tk.END, """INTEGRATED: PRIMEROS PASOS

1. Selecciona la placa y espera a que aparezca el puerto COM.
2. Escribe el programa en la pestaña izquierda.
3. Pulsa Traducir (F5) y revisa el C++ de la derecha.
4. Pulsa Cargar a la placa. La compilación se realiza automáticamente.
5. Abre Monitor serie con la velocidad indicada por el programa.

PRIMERA PRUEBA DE LED
    al iniciar
    configurar led integrado
    repetir siempre
    parpadear led integrado 500

RED PROPIA DEL ESP32
    al iniciar
    wifi crear punto de acceso "MiRed" "12345678"
    servidor iniciar 80
    servidor html "/" "<h1>Hola</h1>"
    repetir siempre
    servidor atender
    Conecta el teléfono a MiRed y abre http://192.168.4.1.

PAGINA WEB CON ARCHIVOS
    Usa Proyecto > Crear archivos web...
    Se crearán index.html, estilos.css y app.js enlazados.
    Edita esos archivos y vuelve a cargar el proyecto.

SI ALGO FALLA
    Estado WiFi 6: el SSID no fue encontrado.
    No hay COM: conecta la placa, revisa el cable de datos y espera 3 segundos.
    La placa no responde: cierra Monitor serie y pulsa reset.
    AVR no tiene WiFi integrado; usa ESP32 o ESP8266.
""")
        texto.config(state=tk.DISABLED)

    def abrir_biblioteca(self):
        """Abre la ventana interactiva de la biblioteca de comandos con buscador y ejemplos."""
        win = tk.Toplevel(self)
        win.title("Biblioteca de Comandos — Integrated")
        win.geometry("1000x700")
        win.minsize(850, 520)
        win.configure(bg=self.bg_principal)
        self._aplicar_color_barra_nativa(win)

        # Barra superior con búsqueda y filtros
        top_bar = tk.Frame(win, bg=self.bg_secundario, padx=16, pady=12)
        top_bar.pack(fill=tk.X)

        lbl_tit = tk.Label(
            top_bar, text="Biblioteca de Comandos", bg=self.bg_secundario,
            fg=self.fg_texto, font=("Segoe UI", 13, "bold"),
        )
        lbl_tit.pack(side=tk.LEFT, padx=(0, 8))

        lbl_conteo = tk.Label(
            top_bar, text=f"({total_comandos()} comandos)", bg=self.bg_secundario,
            fg=self.fg_muted, font=("Segoe UI", 9),
        )
        lbl_conteo.pack(side=tk.LEFT, padx=(0, 20))

        # Buscador
        lbl_busc = tk.Label(
            top_bar, text="Buscar:", bg=self.bg_secundario,
            fg=self.fg_muted, font=("Segoe UI", 9, "bold"),
        )
        lbl_busc.pack(side=tk.LEFT, padx=(0, 6))

        var_busqueda = tk.StringVar()
        entry_busqueda = tk.Entry(
            top_bar, textvariable=var_busqueda, bg=self.bg_elevado,
            fg=self.fg_texto, insertbackground=self.acento_2,
            font=("Segoe UI", 9), width=24, bd=0, relief=tk.FLAT,
        )
        entry_busqueda.pack(side=tk.LEFT, padx=(0, 16), ipady=4)

        # Filtro de categoría
        lbl_cat = tk.Label(
            top_bar, text="Categoría:", bg=self.bg_secundario,
            fg=self.fg_muted, font=("Segoe UI", 9, "bold"),
        )
        lbl_cat.pack(side=tk.LEFT, padx=(0, 6))

        categorias = ["Todas las categorías"] + lista_categorias()
        combo_cat = ttk.Combobox(
            top_bar, values=categorias, state="readonly", width=22, font=("Segoe UI", 9),
        )
        combo_cat.set("Todas las categorías")
        combo_cat.pack(side=tk.LEFT)

        # Panel principal dividido
        paned = tk.PanedWindow(
            win, orient=tk.HORIZONTAL, bg=self.bg_principal, sashwidth=4, bd=0,
        )
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Panel izquierdo: lista de comandos
        frame_izq = tk.Frame(paned, bg=self.bg_principal)
        paned.add(frame_izq, width=280)

        lbl_lista = tk.Label(
            frame_izq, text="Comandos", bg=self.bg_principal,
            fg=self.fg_muted, font=("Segoe UI", 9, "bold"),
        )
        lbl_lista.pack(anchor="w", pady=(0, 4))

        frame_listbox = tk.Frame(frame_izq, bg=self.bg_editor)
        frame_listbox.pack(fill=tk.BOTH, expand=True)

        scrollbar_y = tk.Scrollbar(frame_listbox, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        lista_cmd = tk.Listbox(
            frame_listbox, bg=self.bg_editor, fg=self.fg_texto,
            selectbackground=self.acento_2, selectforeground="#051930",
            font=("Segoe UI", 9), bd=0, highlightthickness=0,
            yscrollcommand=scrollbar_y.set,
        )
        lista_cmd.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)
        scrollbar_y.config(command=lista_cmd.yview)

        # Panel derecho: detalle del comando
        frame_der = tk.Frame(paned, bg=self.bg_principal)
        paned.add(frame_der, width=680)

        detalle_scroll = scrolledtext.ScrolledText(
            frame_der, wrap=tk.WORD, bg=self.bg_editor, fg=self.fg_texto,
            font=("Segoe UI", 10), bd=0, highlightthickness=0,
        )
        detalle_scroll.pack(fill=tk.BOTH, expand=True)

        # Configurar estilos de texto / tags en el ScrolledText
        detalle_scroll.tag_config("titulo", font=("Segoe UI", 14, "bold"), foreground=self.acento_2)
        detalle_scroll.tag_config("badge", font=("Segoe UI", 9, "bold"), foreground=self.acento)
        detalle_scroll.tag_config("seccion", font=("Segoe UI", 10, "bold"), foreground=self.acento_2)
        detalle_scroll.tag_config("codigo", font=("Consolas", 10), foreground="#00E676", background=self.bg_secundario)
        detalle_scroll.tag_config("cpp", font=("Consolas", 10), foreground="#80D8FF", background=self.bg_secundario)
        detalle_scroll.tag_config("texto", font=("Segoe UI", 10), foreground=self.fg_texto)
        detalle_scroll.tag_config("nota", font=("Segoe UI", 9, "italic"), foreground=self.fg_muted)

        # Barra de acciones inferiores
        bar_acciones = tk.Frame(frame_der, bg=self.bg_principal, pady=8)
        bar_acciones.pack(fill=tk.X)

        comando_actual: list[dict] = []
        comandos_filtrados: list[dict] = []

        def copiar_al_portapapeles(txt: str, mensaje: str = "Copiado al portapapeles"):
            try:
                self.clipboard_clear()
                self.clipboard_append(txt)
                self._set_status(mensaje)
            except Exception:
                pass

        def insertar_en_editor_activo(txt: str):
            tab = self._tab_actual()
            if tab and hasattr(tab, "texto_entrada"):
                try:
                    tab.texto_entrada.insert(tk.INSERT, txt + "\n")
                    tab.texto_entrada.focus_set()
                    self._set_status("Insertado en el editor")
                except Exception:
                    pass

        def accion_copiar_sintaxis():
            if comando_actual:
                copiar_al_portapapeles(comando_actual[0]["sintaxis"], "Sintaxis copiada")

        def accion_insertar_sintaxis():
            if comando_actual:
                insertar_en_editor_activo(comando_actual[0]["sintaxis"])

        def accion_copiar_ejemplo():
            if comando_actual:
                copiar_al_portapapeles(comando_actual[0]["ejemplo"], "Ejemplo copiado")

        def accion_insertar_ejemplo():
            if comando_actual:
                insertar_en_editor_activo(comando_actual[0]["ejemplo"])

        btn_ins_sintaxis = self._btn(bar_acciones, "+ Insertar comando", self.acento_2, accion_insertar_sintaxis)
        btn_ins_sintaxis.pack(side=tk.LEFT, padx=(0, 6))

        btn_cop_sintaxis = self._btn(bar_acciones, "Copiar sintaxis", self.bg_elevado, accion_copiar_sintaxis)
        btn_cop_sintaxis.pack(side=tk.LEFT, padx=6)

        btn_ins_ej = self._btn(bar_acciones, "+ Insertar ejemplo", self.acento, accion_insertar_ejemplo)
        btn_ins_ej.pack(side=tk.LEFT, padx=6)

        btn_cop_ej = self._btn(bar_acciones, "Copiar ejemplo", self.bg_elevado, accion_copiar_ejemplo)
        btn_cop_ej.pack(side=tk.LEFT, padx=6)

        def mostrar_detalle(cmd: dict):
            comando_actual.clear()
            comando_actual.append(cmd)
            detalle_scroll.config(state=tk.NORMAL)
            detalle_scroll.delete("1.0", tk.END)

            # Titulo
            detalle_scroll.insert(tk.END, f"{cmd['nombre']}\n", "titulo")

            # Badges
            cat = cmd.get("categoria", "")
            placas = cmd.get("placas", "Todas")
            detalle_scroll.insert(tk.END, f"  Categoría: {cat}   |   Placas: {placas}\n\n", "badge")

            # Sintaxis
            detalle_scroll.insert(tk.END, "SINTAXIS:\n", "seccion")
            detalle_scroll.insert(tk.END, f"  {cmd['sintaxis']}\n\n", "codigo")

            # Descripcion
            detalle_scroll.insert(tk.END, "DESCRIPCIÓN:\n", "seccion")
            desc = cmd.get("descripcion", "")
            detalle_scroll.insert(tk.END, f"{desc}\n\n", "texto")

            # Ejemplo
            detalle_scroll.insert(tk.END, "EJEMPLO (.int_esp):\n", "seccion")
            ej = cmd.get("ejemplo", "")
            lineas_ej = "\n".join(f"  {l}" for l in ej.splitlines())
            detalle_scroll.insert(tk.END, f"{lineas_ej}\n\n", "codigo")

            # C++ generado
            detalle_scroll.insert(tk.END, "C++ EQUIVALENTE:\n", "seccion")
            cpp = cmd.get("cpp", "")
            lineas_cpp = "\n".join(f"  {l}" for l in cpp.splitlines())
            detalle_scroll.insert(tk.END, f"{lineas_cpp}\n\n", "cpp")

            # Notas adicionales
            notas = cmd.get("notas")
            if notas:
                detalle_scroll.insert(tk.END, "NOTAS:\n", "seccion")
                detalle_scroll.insert(tk.END, f"{notas}\n", "nota")

            detalle_scroll.config(state=tk.DISABLED)

        def actualizar_lista(*args):
            termino = var_busqueda.get().strip().lower()
            cat_sel = combo_cat.get()

            comandos_filtrados.clear()
            if termino:
                resultados = buscar_comandos(termino)
            elif cat_sel != "Todas las categorías":
                resultados = comandos_de(cat_sel)
            else:
                resultados = [cmd for c in lista_categorias() for cmd in comandos_de(c)]

            if cat_sel != "Todas las categorías" and termino:
                resultados = [cmd for cmd in resultados if cmd.get("categoria") == cat_sel]

            comandos_filtrados.extend(resultados)
            lista_cmd.delete(0, tk.END)
            for cmd in comandos_filtrados:
                lista_cmd.insert(tk.END, f"  {cmd['nombre']}")

            lbl_conteo.config(text=f"({len(comandos_filtrados)} comandos)")
            if comandos_filtrados:
                lista_cmd.select_set(0)
                mostrar_detalle(comandos_filtrados[0])
            else:
                detalle_scroll.config(state=tk.NORMAL)
                detalle_scroll.delete("1.0", tk.END)
                detalle_scroll.insert(tk.END, "No se encontraron comandos que coincidan con la búsqueda.", "texto")
                detalle_scroll.config(state=tk.DISABLED)

        def al_seleccionar_comando(event=None):
            sel = lista_cmd.curselection()
            if sel and sel[0] < len(comandos_filtrados):
                mostrar_detalle(comandos_filtrados[sel[0]])

        def al_doble_clic(event=None):
            sel = lista_cmd.curselection()
            if sel and sel[0] < len(comandos_filtrados):
                cmd = comandos_filtrados[sel[0]]
                insertar_en_editor_activo(cmd["sintaxis"])

        lista_cmd.bind("<<ListboxSelect>>", al_seleccionar_comando)
        lista_cmd.bind("<Double-Button-1>", al_doble_clic)
        var_busqueda.trace_add("write", actualizar_lista)
        combo_cat.bind("<<ComboboxSelected>>", actualizar_lista)

        entry_busqueda.focus_set()
        actualizar_lista()

    def mostrar_acerca(self):
        messagebox.showinfo(
            "Acerca de Integrated",
            "Integrated — IDE en español para Arduino y ESP.\n\n"
            f"Proyectos: extensión {EXT_PROYECTO}\n"
            "Traduce → C++, compila con caché local\n"
            "y carga a la placa vía arduino-cli.\n\n"
            "Menú Ejemplos: seguidor de línea, invernadero, etc.",
        )

    def _set_status(self, msg: str):
        if hasattr(self, "status_bar"):
            self.status_bar.config(text=msg)

    def _actualizar_status(self):
        tab = self._tab_actual()
        if not tab:
            return
        try:
            pos = tab.texto_entrada.index(tk.INSERT)
            lin, col = pos.split(".")
            self._set_status(f"{tab.nombre}  ·  Línea {lin}, Col {int(col)+1}  ·  {self.combo_placas.get()}")
        except Exception:
            pass

    def _al_cerrar(self):
        if hasattr(self, "_actualizador_puertos"):
            self.after_cancel(self._actualizador_puertos)
        self.guardar_preferencias(silencioso=True)
        self.cerrar_monitor_serie()
        self.destroy()


if __name__ == "__main__":
    # Asegurar cwd = carpeta del proyecto
    os.chdir(Path(__file__).resolve().parent)
    app = IDEInteligente()
    app.mainloop()
